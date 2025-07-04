from rest_framework import serializers
from .models import SubscriptionPlan, UserSubscription, Payment
from django.contrib.auth import get_user_model

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