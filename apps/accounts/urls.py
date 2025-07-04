
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    RegisterAPIView,
    VerifyOTPApiView,
    ResendOTPApiView,
    LogoutAPIView,
    ProfileView,
    UserAPIView
    # UserAPIView # Removed UserAPIView as it seems redundant with ProfileView and specific requirements
)

urlpatterns = [
    path('user_all/', UserAPIView.as_view(), name='user-list'),  
    path('user_detail/<int:pk>/', UserAPIView.as_view(), name='user-detail'),  
    # Registration endpoint (email only, OTP sent)
    path('register/', RegisterAPIView.as_view(), name='register'),
    # OTP verification
    path('verify-otp/', VerifyOTPApiView.as_view(), name='verify_otp'),
    # Resend OTP
    path('resend-otp/', ResendOTPApiView.as_view(), name='resend_otp'),

    # JWT Token Endpoints (for login after verification)

    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Logout (requires refresh token to blacklist)
    path('logout/', LogoutAPIView.as_view(), name='logout'),

    # User profile (retrieve/update)
    path('profile/', ProfileView.as_view(), name='user_profile'),
]