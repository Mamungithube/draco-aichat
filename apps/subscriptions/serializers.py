from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import SubscriptionPlan, UserSubscription, Payment
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail

User = get_user_model()

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'

class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlan.objects.filter(is_active=True),
        source='plan',
        write_only=True
    )
    
    class Meta:
        model = UserSubscription
        fields = '__all__'
        read_only_fields = ('user', 'start_date', 'end_date', 'last_payment_date', 'next_payment_date')

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('user', 'subscription', 'payment_date', 'is_successful')

class UserSerializer(serializers.ModelSerializer):
    subscription = UserSubscriptionSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email','subscription']
        
        
        
# প্রাইসিং প্ল্যানের ডাইনামিক ক্যালকুলেশন

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    monthly_price_hkd = serializers.SerializerMethodField()
    annual_price_hkd = serializers.SerializerMethodField()
    hourly_rate = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = '__all__'

    def get_monthly_price_hkd(self, obj):
        return f"HK${obj.monthly_price}"

    def get_annual_price_hkd(self, obj):
        return f"HK${obj.annual_price}"

    def get_hourly_rate(self, obj):
        if obj.audio_rating_hours > 0:
            rate = obj.annual_price / (obj.audio_rating_hours * 12)
            return f"Only HK${rate:.2f}/hour on average"
        return None
    
    
    
# ক্যানসেলেশন সিস্টেম ইম্প্রুভমেন্ট
@action(detail=True, methods=['post'])
def request_cancellation(self, request, pk=None):
    subscription = self.get_object()
    subscription.cancellation_requested = True
    subscription.cancellation_date = timezone.now() + timedelta(hours=24)
    subscription.save()
    
    # Send confirmation email
    send_mail(
        'Subscription Cancellation Request',
        'Your subscription will be cancelled in 24 hours.',
        'mdmamun340921@gmail.com',
        [subscription.user.email],
        fail_silently=False,
    )
    
    return Response({'status': 'Cancellation requested', 'effective_date': subscription.cancellation_date})

@action(detail=True, methods=['post'])
def cancel_immediately(self, request, pk=None):
    subscription = self.get_object()
    subscription.is_active = False
    subscription.auto_renew = False
    subscription.end_date = timezone.now()
    subscription.save()
    
    return Response({'status': 'Subscription cancelled immediately'})


# সাবস্ক্রিপশন স্ট্যাটাস চেক API

@action(detail=False, methods=['get'])
def subscription_status(self, request):
    try:
        subscription = UserSubscription.objects.get(user=request.user)
        serializer = self.get_serializer(subscription)
        
        data = serializer.data
        data.update({
            'is_trial_active': subscription.is_trial and subscription.trial_end_date > timezone.now(),
            'days_remaining': (subscription.end_date - timezone.now()).days,
            'renewal_date': subscription.end_date,
            'next_payment_date': subscription.next_payment_date,
            'auto_renew_status': subscription.auto_renew,
        })
        
        return Response(data)
    except UserSubscription.DoesNotExist:
        return Response({'status': 'no_active_subscription'})