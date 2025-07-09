
from django.contrib import admin
from .models import Profile,User

class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user','id', 'otp']


class Useradmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'email', 'profile_picture']
    search_fields = ['username', 'email']
    list_filter = ['is_staff', 'is_active']
    
admin.site.register(User, Useradmin)
admin.site.register(Profile, ProfileAdmin)