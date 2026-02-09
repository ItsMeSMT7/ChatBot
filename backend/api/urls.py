from django.urls import path
from .views import ChatBotAPI, SignupAPI, LoginAPI, GoogleAuthAPI, UserChatsAPI

urlpatterns = [
    path('chat/', ChatBotAPI.as_view()),
    path('signup/', SignupAPI.as_view()),
    path('login/', LoginAPI.as_view()),
    path('google-auth/', GoogleAuthAPI.as_view()),
    path('user-chats/', UserChatsAPI.as_view()),
]
