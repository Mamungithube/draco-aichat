from venv import logger
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import SubscriptionPlan, UserSubscription, Payment ,Referral, SubscriptionStatusLog
from .serializers import (
    SubscriptionPlanSerializer, 
    UserSubscriptionSerializer,
    PaymentSerializer,
    UserSerializer
)
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




# subscriptions/views.py তে স্ট্রাইপ ইন্টিগ্রেশন যোগ করুন
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

class PaymentViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def stripe_webhook(self, request):
        payload = request.body
        sig_header = request.META['HTTP_STRIPE_SIGNATURE']
        event = None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            return Response(status=400)
        except stripe.error.SignatureVerificationError as e:
            return Response(status=400)

        # Handle payment events
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            self._handle_payment_success(payment_intent)

        return Response(status=200)

    def _handle_payment_success(self, payment_intent):
        # Find the user and update their subscription
        metadata = payment_intent.get('metadata', {})
        user_id = metadata.get('user_id')
        plan_id = metadata.get('plan_id')
        
        try:
            user = User.objects.get(id=user_id)
            plan = SubscriptionPlan.objects.get(id=plan_id)
            
            # Create or update subscription
            subscription, created = UserSubscription.objects.get_or_create(
                user=user,
                defaults={
                    'plan': plan,
                    'is_active': True,
                    'end_date': timezone.now() + timedelta(days=30),
                    'auto_renew': True
                }
            )
            
            # Record payment
            Payment.objects.create(
                user=user,
                subscription=subscription,
                amount=payment_intent['amount']/100,  # Convert to dollars
                transaction_id=payment_intent['id'],
                payment_method='stripe',
                is_successful=True
            )
            
        except (User.DoesNotExist, SubscriptionPlan.DoesNotExist):
            logger.error(f"Payment succeeded but user/plan not found: {payment_intent['id']}")
            
            
            
            
@action(detail=False, methods=['post'])
def start_trial(self, request):
    plan_id = request.data.get('plan_id')
    try:
        plan = SubscriptionPlan.objects.get(id=plan_id)
        
        if UserSubscription.objects.filter(user=request.user, is_trial=True).exists():
            return Response({'error': 'You already used your trial'}, status=400)
            
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
        
        return Response({'status': 'Trial started', 'end_date': trial_end})
    except SubscriptionPlan.DoesNotExist:
        return Response({'error': 'Invalid plan'}, status=400)
    
    
@action(detail=False, methods=['post'])
def apply_referral(self, request):
    code = request.data.get('code')
    try:
        referral = Referral.objects.get(code=code, is_active=True)
        request.session['referral_discount'] = referral.discount_percent
        return Response({'discount': referral.discount_percent})
    except Referral.DoesNotExist:
        return Response({'error': 'Invalid referral code'}, status=400)
    
    
    
# views.py তে
@action(detail=False, methods=['get'])
def verify_payment(self, request):
    payment_intent_id = request.query_params.get('payment_intent')
    
    try:
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if payment_intent.status == 'succeeded':
            # Find and update the subscription
            subscription = UserSubscription.objects.get(
                user=request.user,
                payment_method='stripe',
                is_active=True
            )
            
            return Response({
                'status': 'success',
                'subscription': UserSubscriptionSerializer(subscription).data
            })
        else:
            return Response({'status': 'failed'}, status=400)
            
    except Exception as e:
        return Response({'error': str(e)}, status=400)