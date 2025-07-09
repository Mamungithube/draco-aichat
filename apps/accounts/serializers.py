from rest_framework import serializers
from .models import User, Profile
from .utils import generate_otp
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import RefreshToken


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'profile_picture']
        read_only_fields = ['id', 'email']

    def update(self, instance, validated_data):
        instance.profile_picture = validated_data.get('profile_picture', instance.profile_picture)
        instance.save()
        return instance


class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email']

    def create(self, validated_data):
        email = validated_data['email']

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("User with this email already exists.")

        # Create user with inactive status
        user = User.objects.create_user(
            email=email,
            username=email,
            password='dummy-password-for-otp-flow',
            is_active=False  # ✅ Set inactive
        )

        # Generate OTP and create profile
        otp = generate_otp()
        Profile.objects.create(user=user, otp=otp, is_verified=False)

        # Send OTP via email
        send_mail(
            'Your OTP Code for Account Verification',
            f'Dear {email},\n\nYour OTP code is: {otp}\n\nPlease use this code to verify your account.',
            'mdmamun340921@gmail.com',
            [email],
            fail_silently=False,
        )

        return user


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def create_token(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }
