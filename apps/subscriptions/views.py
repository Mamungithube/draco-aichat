from venv import logger
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import SubscriptionPlan, UserSubscription, Payment ,Referral, SubscriptionStatusLog
from .serializers import SubscriptionPlanSerializer, UserSubscriptionSerializer,PaymentSerializer,UserSerializer,ReferralSerializer,SubscriptionStatusLogSerializer,StartTrialSerializer

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import stripe
from django.conf import settings

User = get_user_model()

class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer

class UserSubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = UserSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserSubscription.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        plan = serializer.validated_data['plan']
        
        # Calculate end date (1 month from now)
        end_date = timezone.now() + timedelta(days=30)
        
        # Create the subscription
        subscription = serializer.save(
            user=self.request.user,
            end_date=end_date,
            next_payment_date=end_date
        )
        
        # Process payment (in a real app, this would call Stripe/Apple Pay/etc.)
        self._process_payment(subscription, plan)

    def _process_payment(self, subscription, plan):
        # In a real implementation, this would integrate with a payment processor
        # For demo purposes, we'll just create a mock payment record
        
        payment = Payment.objects.create(
            user=self.request.user,
            subscription=subscription,
            amount=plan.monthly_price,
            transaction_id=f"mock_pay_{timezone.now().timestamp()}",
            payment_method=subscription.payment_method,
            is_successful=True
        )
        
        return payment

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        subscription = self.get_object()
        subscription.auto_renew = False
        subscription.save()
        return Response({'status': 'auto-renew cancelled'})

    @action(detail=False, methods=['get'])
    def current(self, request):
        try:
            subscription = UserSubscription.objects.get(user=request.user)
            serializer = self.get_serializer(subscription)
            return Response(serializer.data)
        except UserSubscription.DoesNotExist:
            return Response({'detail': 'No active subscription'}, status=status.HTTP_404_NOT_FOUND)

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).order_by('-payment_date')
    
    
    
    
    # Referral code validation
    @action(detail=False, methods=['post'])
    def apply_referral(self, request):
        code = request.data.get('code')
        try:
            referral = Referral.objects.get(code=code, is_active=True)
            # Apply discount logic here
            return Response({'status': 'Discount applied'})
        except Referral.DoesNotExist:
            return Response({'error': 'Invalid referral code'}, status=400)

    # Free trial subscription
    @action(detail=False, methods=['post'])
    def start_trial(self, request):
        plan = SubscriptionPlan.objects.get(plan_type='platinum')
        end_date = timezone.now() + timedelta(days=3)  # 3-day trial

        subscription = UserSubscription.objects.create(
            user=request.user,
            plan=plan,
            is_active=True,
            is_trial=True,
            trial_end_date=end_date,
            end_date=end_date,
            auto_renew=True
        )

        return Response({'status': 'Trial started'})




import stripe
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
import logging
from .models import UserSubscription, SubscriptionPlan, Payment, Referral
from django.contrib.auth import get_user_model
import datetime

logger = logging.getLogger(__name__)
User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY

class PaymentViewSet(viewsets.ViewSet):
    serializer_class = StartTrialSerializer
    @action(detail=False, methods=['POST'])
    def stripe_webhook(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        
        if not sig_header:
            return Response({'error': 'Missing signature header'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = stripe.Webhook.construct_event(
                payload, 
                sig_header, 
                settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            return Response({'error': 'Invalid payload'}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)

        # Handle different event types
        if event['type'] == 'payment_intent.succeeded':
            self._handle_payment_success(event['data']['object'])
        elif event['type'] == 'customer.subscription.created':
            self._handle_subscription_created(event['data']['object'])
        
        return Response({'status': 'success'})

    def _handle_payment_success(self, payment_intent):
        metadata = payment_intent.get('metadata', {})
        user_id = metadata.get('user_id')
        plan_id = metadata.get('plan_id')
        
        try:
            user = User.objects.get(id=user_id)
            plan = SubscriptionPlan.objects.get(id=plan_id)
            
            subscription, created = UserSubscription.objects.update_or_create(
                user=user,
                defaults={
                    'plan': plan,
                    'is_active': True,
                    'end_date': timezone.now() + timedelta(days=30),
                    'next_payment_date': timezone.now() + timedelta(days=30),
                    'auto_renew': True,
                    'payment_method': 'stripe'
                }
            )
            
            Payment.objects.create(
                user=user,
                subscription=subscription,
                amount=payment_intent['amount']/100,
                transaction_id=payment_intent['id'],
                payment_method='stripe',
                is_successful=True
            )
            
        except (User.DoesNotExist, SubscriptionPlan.DoesNotExist) as e:
            logger.error(f"Payment processing failed: {str(e)}")
            # Consider notifying admin here

    @action(detail=False, methods=['POST'])
    def start_trial(self, request):
        serializer = StartTrialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        plan_id = serializer.validated_data.get('plan_id')
        
        if UserSubscription.objects.filter(user=request.user, is_trial=True).exists():
            return Response(
                {'error': 'You have already used your trial period'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
            trial_end = timezone.now() + timedelta(days=3)
            
            subscription = UserSubscription.objects.create(
                user=request.user,
                plan=plan,
                is_active=True,
                is_trial=True,
                trial_start_date=timezone.now(),
                trial_end_date=trial_end,
                end_date=trial_end,
                auto_renew=False
            )
            
            return Response({
                'status': 'Trial started successfully',
                'end_date': trial_end,
                'plan': plan.name
            })
            
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {'error': 'Invalid subscription plan'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['POST'])
    def apply_referral(self, request):
        code = request.data.get('code')
        if not code:
            return Response(
                {'error': 'Referral code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            referral = Referral.objects.get(
                code=code, 
                is_active=True,
                valid_until__gte=timezone.now()
            )
            
            # Apply discount logic
            request.user.profile.discount_active = True
            request.user.profile.discount_percent = referral.discount_percent
            request.user.profile.save()
            
            return Response({
                'success': True,
                'discount_percent': referral.discount_percent,
                'message': 'Discount applied successfully'
            })
            
        except Referral.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired referral code'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['GET'])
    def verify_payment(self, request):
        payment_intent_id = request.query_params.get('payment_intent')
        if not payment_intent_id:
            return Response(
                {'error': 'payment_intent parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if payment_intent.status == 'succeeded':
                subscription = UserSubscription.objects.get(
                    user=request.user,
                    payment_method='stripe',
                    is_active=True
                )
                
                return Response({
                    'status': 'success',
                    'subscription': UserSubscriptionSerializer(subscription).data,
                    'payment_details': {
                        'amount': payment_intent.amount/100,
                        'currency': payment_intent.currency,
                        'date': datetime.fromtimestamp(payment_intent.created)
                    }
                })
                
            return Response(
                {'status': 'pending', 'payment_status': payment_intent.status},
                status=status.HTTP_200_OK
            )
            
        except UserSubscription.DoesNotExist:
            return Response(
                {'error': 'Subscription not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except stripe.error.StripeError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        
        

class ReferralViewSet(viewsets.ModelViewSet):
    queryset = Referral.objects.all()
    serializer_class = ReferralSerializer
    permission_classes = [IsAuthenticated]  # বা IsAdminUser, যদি কন্ট্রোল দিতে না চাও

class SubscriptionStatusLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubscriptionStatusLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SubscriptionStatusLog.objects.filter(subscription__user=self.request.user)