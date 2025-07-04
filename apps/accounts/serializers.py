# accounts/serializers.py
from rest_framework import serializers
from .models import User, Profile # Import Profile model
from .utils import generate_otp # Make sure utils.py is in the same directory
from django.core.mail import send_mail
# from rest_framework_simplejwt.tokens import RefreshToken # Not directly used in serializers, but useful for views


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # Removed password, confirm_password, first_name, last_name
        fields = ['id', 'email', 'profile_picture', 'bio']
        read_only_fields = ['id', 'email'] # Email should not be updatable directly via this serializer

    def update(self, instance, validated_data):
        # Allow updating profile_picture and bio
        # Ensure email is not in validated_data if you want to keep it read-only
        instance.profile_picture = validated_data.get('profile_picture', instance.profile_picture)
        instance.bio = validated_data.get('bio', instance.bio)
        instance.save()
        return instance


class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # Only 'email' is required for registration, no password, etc.
        fields = ['email'] # Only email for registration

    def validate_email(self, value):
        # Ensure email is unique during registration
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email address is already registered.")
        return value

    def create(self, validated_data):
        email = validated_data['email']
        
        # Create user with a dummy password and set username to email
        # User.objects.create_user handles hashing
        user = User.objects.create_user(email=email, username=email, password='dummy-password-for-otp-flow')
        user.is_active = False # User is inactive until OTP is verified
        user.save()

        # Create or update profile and generate OTP
        profile, created = Profile.objects.get_or_create(user=user)
        otp_code = generate_otp()
        profile.otp = otp_code
        profile.is_verified = False # Ensure it's not verified yet
        profile.save()

        # Send OTP email
        email_subject = 'Your OTP Code for Account Verification'
        email_body = f'Dear {user.email},\n\nYour OTP code is: {otp_code}\n\nPlease use this code to verify your account.'
        send_mail(
            email_subject,
            email_body,
            'mdmamun340921@gmail.com', # Your sender email
            [user.email],
            fail_silently=False,
        )

        return user