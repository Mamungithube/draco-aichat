# accounts/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import RefreshToken # For logout

from django.template.loader import render_to_string # If you want to use HTML emails
from django.core.mail import EmailMultiAlternatives # For sending HTML emails

from .models import User, Profile # Import both User and Profile
from .serializers import UserSerializer, RegistrationSerializer
from .utils import generate_otp # Ensure this utility exists

# Removed Djoser related imports as you're handling registration manually
# Removed django.contrib.auth.models.User as you're using your custom User model
# Removed authenticate, login as you're using token-based auth with OTP verification

class ProfileView(APIView): # Changed from generics.RetrieveUpdateAPIView to APIView for more control if needed
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = self.serializer_class(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = self.serializer_class(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk=None):
        if pk:
            user = get_object_or_404(User, pk=pk)
            serializer = UserSerializer(user)
        else:
            users = User.objects.all()
            serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def put(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = UserSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class RegisterAPIView(APIView):
    # Removed serializer_class attribute, instantiate directly in post
    # serializer_class = RegistrationSerializer # Not necessary for simple APIView

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data) # Instantiate directly
        if serializer.is_valid():
            user = serializer.save() # User and Profile created, OTP sent in serializer's create method
            return Response({'detail': 'Registration successful. Check your email for OTP verification.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResendOTPApiView(APIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'User with this email does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        if user.is_active:
            return Response({'message': 'Account is already active. No need to resend OTP.'}, status=status.HTTP_200_OK)

        profile, created = Profile.objects.get_or_create(user=user) # Get or create profile
        otp_code = generate_otp()
        profile.otp = otp_code
        profile.save(update_fields=['otp'])

        send_mail(
            'Your New OTP Code',
            f'Dear {user.email},\n\nYour new OTP code is: {otp_code}\n\nPlease use this code to verify your account.',
            'mdmamun340921@gmail.com',
            [user.email],
            fail_silently=False,
        )

        return Response({'message': 'New OTP has been sent to your email.'}, status=status.HTTP_200_OK)


class VerifyOTPApiView(APIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        otp = request.data.get('otp')

        if not email or not otp:
            return Response({'error': 'Email and OTP are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'User with this email does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        if user.is_active:
            return Response({'message': 'Account is already active.'}, status=status.HTTP_200_OK)

        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return Response({'error': 'User profile not found. Please register first.'}, status=status.HTTP_404_NOT_FOUND)

        if profile.otp == otp:
            user.is_active = True
            user.save(update_fields=['is_active'])
            profile.otp = None  # Clear OTP after successful verification
            profile.is_verified = True # Mark profile as verified
            profile.save(update_fields=['otp', 'is_verified'])

            # Optionally, you can log the user in or return tokens here if you want
            # For simplicity, we'll just return a success message.
            # You would typically generate JWT tokens here for auto-login after verification.
            return Response({'message': 'Account activated successfully.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated] # Requires authentication to log out

    def post(self, request):
        try:
            # Assuming you're using Simple JWT's Blacklist app
            # If not, you might not need to blacklist, but it's good practice.
            # The refresh_token is typically sent in the request body for blacklisting.
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            else:
                return Response({'error': 'Refresh token not provided.'}, status=status.HTTP_400_BAD_REQUEST)

            # Django's built-in logout doesn't do much for token-based auth
            # but is kept for completeness if session auth is also involved.
            # from django.contrib.auth import logout # Uncomment if using session logout
            # logout(request)

            return Response({'message': 'Successfully logged out.'}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            # Catch all exceptions for token invalidity, etc.
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)