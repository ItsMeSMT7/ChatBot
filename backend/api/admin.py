from django.contrib import admin
from .models import User, UserChat

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'date_joined', 'is_active']
    search_fields = ['username', 'email']
    list_filter = ['is_active', 'date_joined']

@admin.register(UserChat)
class UserChatAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'created_at']
    search_fields = ['user__username', 'title']
    list_filter = ['created_at']
