from django.shortcuts import render
import json
import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .models import StateData, Titanic, User, UserChat
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .gemini import process_user_query, summarize_text
from .rag import rag_query
from django.db import connection
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

@method_decorator(csrf_exempt, name='dispatch')
class ChatBotAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        question = request.data.get("question")
        
        if not question:
            return Response({"answer": "Please ask a question"})
        
        try:
            result = rag_query(question)
            return Response({"answer": result})
            
        except Exception as e:
            return Response({"answer": f"Sorry, I couldn't process your question. Error: {str(e)}"})

@method_decorator(csrf_exempt, name='dispatch')
class SignupAPI(APIView):
    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.create_user(username=username, email=email, password=password)
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'profile_picture': user.profile_picture
            }
        })

@method_decorator(csrf_exempt, name='dispatch')
class LoginAPI(APIView):
    def post(self, request):
        login_field = request.data.get('login')
        password = request.data.get('password')
        
        user = None
        if '@' in login_field:
            try:
                user = User.objects.get(email=login_field)
            except User.DoesNotExist:
                pass
        else:
            try:
                user = User.objects.get(username=login_field)
            except User.DoesNotExist:
                pass
        
        if user and user.check_password(password):
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': {
                    'id': str(user.id),
                    'username': user.username,
                    'email': user.email,
                    'profile_picture': user.profile_picture
                }
            })
        
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@method_decorator(csrf_exempt, name='dispatch')
class GoogleAuthAPI(APIView):
    def post(self, request):
        email = request.data.get('email')
        name = request.data.get('name')
        picture = request.data.get('picture')
        google_id = request.data.get('google_id')
        
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            username = email.split('@')[0]
            counter = 1
            original_username = username
            while User.objects.filter(username=username).exists():
                username = f"{original_username}{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=email,
                profile_picture=picture
            )
        
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'profile_picture': user.profile_picture
            }
        })

@method_decorator(csrf_exempt, name='dispatch')

@method_decorator(csrf_exempt, name='dispatch')
class UserChatsAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        chats = UserChat.objects.filter(user=request.user)
        return Response([
            {
                'id': str(chat.id),
                'title': chat.title,
                'messages': chat.messages
            } for chat in chats
        ])

    def post(self, request):
        title = request.data.get('title', 'New Chat')
        messages = request.data.get('messages', [])

        chat = UserChat.objects.create(
            user=request.user,
            title=title,
            messages=messages
        )

        return Response({
            'id': str(chat.id),
            'title': chat.title,
            'messages': chat.messages
        })

    def put(self, request):
        chat_id = request.data.get('chat_id')
        messages = request.data.get('messages')

        if not chat_id:
            return Response(
                {'error': 'Chat ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            chat = UserChat.objects.get(id=chat_id, user=request.user)
            chat.messages = messages
            chat.save()
            return Response({'success': True})
        except UserChat.DoesNotExist:
            return Response(
                {'error': 'Chat not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request):
        chat_id = request.data.get('chat_id') or request.GET.get('chat_id')

        if not chat_id:
            return Response(
                {'error': 'Chat ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            chat = UserChat.objects.get(id=chat_id, user=request.user)
            chat.delete()
            return Response({'success': True})
        except UserChat.DoesNotExist:
            return Response(
                {'error': 'Chat not found'},
                status=status.HTTP_404_NOT_FOUND
            )


# class UserChatsAPI(APIView):
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]
    
#     def get(self, request):
#         chats = UserChat.objects.filter(user=request.user)
#         return Response([{
#             'id': str(chat.id),
#             'title': chat.title,
#             'messages': chat.messages
#         } for chat in chats])
    
#     def post(self, request):
#         title = request.data.get('title')
#         messages = request.data.get('messages', [])
        
#         chat = UserChat.objects.create(
#             user=request.user,
#             title=title,
#             messages=messages
#         )
        
#         return Response({
#             'id': str(chat.id),
#             'title': chat.title,
#             'messages': chat.messages
#         })
    
#     def put(self, request):
#         chat_id = request.data.get('chat_id')
#         messages = request.data.get('messages')
        
#         try:
#             chat = UserChat.objects.get(id=chat_id, user=request.user)
#             chat.messages = messages
#             chat.save()
#             return Response({'success': True})
#         except UserChat.DoesNotExist:
#             return Response({'error': 'Chat not found'}, status=status.HTTP_404_NOT_FOUND)
    
#     def delete(self, request):
#         chat_id = request.data.get('chat_id') or request.GET.get('chat_id')
        
#         if not chat_id:
#             return Response({'error': 'Chat ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
#         try:
#             chat = UserChat.objects.get(id=chat_id, user=request.user)
#             chat.delete()
#             return Response({'success': True})
#         except UserChat.DoesNotExist:
#             return Response({'error': 'Chat not found'}, status=status.HTTP_404_NOT_FOUND)
