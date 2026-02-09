import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import User, UserChat

def view_users():
    print("=== ALL USERS ===")
    users = User.objects.all()
    for user in users:
        print(f"ID: {user.id}")
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Date Joined: {user.date_joined}")
        print(f"Active: {user.is_active}")
        print("-" * 30)
    
    print(f"\nTotal Users: {users.count()}")

def view_user_chats():
    print("\n=== USER CHATS ===")
    chats = UserChat.objects.all()
    for chat in chats:
        print(f"Chat ID: {chat.id}")
        print(f"User: {chat.user.username}")
        print(f"Title: {chat.title}")
        print(f"Messages: {len(chat.messages)}")
        print(f"Created: {chat.created_at}")
        print("-" * 30)
    
    print(f"\nTotal Chats: {chats.count()}")

if __name__ == "__main__":
    view_users()
    view_user_chats()