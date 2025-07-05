from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription, Payment,Referral,SubscriptionStatusLog
# Register your models here.
admin.site.register(SubscriptionPlan)
admin.site.register(UserSubscription)
admin.site.register(Payment)
admin.site.register(Referral)
admin.site.register(SubscriptionStatusLog)