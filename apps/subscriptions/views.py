from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import SubscriptionPlan, UserSubscription, Payment
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