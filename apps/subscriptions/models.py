from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class SubscriptionPlan(models.Model):
    PLAN_TYPES = [
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('platinum', 'Platinum'),
    ]
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, unique=True)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2)
    annual_price = models.DecimalField(max_digits=10, decimal_places=2)
    messages_limit = models.PositiveIntegerField(null=True, blank=True)  # null means unlimited
    message_length_limit = models.PositiveIntegerField()
    audio_rating_hours = models.PositiveIntegerField()
    analysis_reports = models.PositiveIntegerField()
    description = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    auto_renew = models.BooleanField(default=True,  blank=True)
    payment_method = models.CharField(max_length=50, blank=True)  # or 'credit_card', 'google_pay', etc.
    last_payment_date = models.DateTimeField(null=True, blank=True)
    next_payment_date = models.DateTimeField(null=True, blank=True)
    is_trial = models.BooleanField(default=False , blank=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    cancellation_requested = models.BooleanField(default=False , blank=True)
    cancellation_date = models.DateTimeField(null=True, blank=True)
    trial_activated = models.BooleanField(default=False, blank=True)
    trial_start_date = models.DateTimeField(null=True, blank=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    trial_converted = models.BooleanField(default=False , blank=True)

    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, unique=True)
    payment_method = models.CharField(max_length=50)
    is_successful = models.BooleanField(default=False)

    def __str__(self):
        return f"Payment #{self.id} - {self.user.email}"
    
    
    
# Referral system
class Referral(models.Model):
    code = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    discount_percent = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    
    
    
class SubscriptionStatusLog(models.Model):
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE)
    status = models.CharField(max_length=20)  # active/cancelled/paused
    changed_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(null=True, blank=True)

