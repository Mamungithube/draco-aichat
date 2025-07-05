
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ReferralViewSet,
    SubscriptionPlanViewSet,
    SubscriptionStatusLogViewSet,
    UserSubscriptionViewSet,
    PaymentViewSet
)

router = DefaultRouter()
router.register(r'subscription-plans', SubscriptionPlanViewSet)
router.register(r'subscriptions', UserSubscriptionViewSet, basename='subscription')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'referrals', ReferralViewSet)
router.register(r'subscription-status', SubscriptionStatusLogViewSet, basename='subscriptionstatus')

urlpatterns = [
    path('', include(router.urls)),
    path('payments/apply_referral/', PaymentViewSet.as_view({'post': 'apply_referral'}), name='apply-referral'),
    path('payments/verify_payment/', PaymentViewSet.as_view({'get': 'verify_payment'}), name='verify-payment'),
    path('payments/stripe_webhook/', PaymentViewSet.as_view({'post': 'stripe_webhook'}), name='stripe-webhook'),
]