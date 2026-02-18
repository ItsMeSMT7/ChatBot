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
from .serializers import UserSerializer # Assuming you have this
import time # For simulating processing steps if needed
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from .models import StateData, Titanic, User, UserChat, Document, DocumentChunk
from .ollama_service import generate_embedding
import os
from django.conf import settings

@method_decorator(csrf_exempt, name='dispatch')
class ChatBotAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        question = request.data.get("question")
        chat_history = request.data.get("chat_history", [])
        
        if not question:
            return Response({"answer": "Please ask a question"})
        
        try:
            result = rag_query(question, chat_history)
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
                'profile_picture': user.profile_picture,
                'user_type': user.user_type
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
                    'profile_picture': user.profile_picture,
                    'user_type': user.user_type
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
                'profile_picture': user.profile_picture,
                'user_type': user.user_type
            }
        })

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

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_dashboard_stats(request):
    if request.user.user_type != 1:
        return Response({'error': 'Unauthorized'}, status=403)
    
    total_users = User.objects.count()
    total_admins = User.objects.filter(user_type=1).count()
    total_docs = Document.objects.count()
    total_chats = UserChat.objects.count()
    
    graph_data = {
        'user_growth': [10, 15, 25, 30, 45, total_users],
        'doc_uploads': [2, 4, 4, 6, 8, total_docs],
        'chat_activity': [50, 120, 200, 150, 300, 450],
        'storage_usage': [20, 40, 55, 70, 85, 90]
    }

    return Response({
        'kpis': {
            'total_users': total_users,
            'total_admins': total_admins,
            'total_documents': total_docs,
            'total_chats': total_chats
        },
        'graphs': graph_data
    })

def process_and_embed_document(doc):
    """
    Reads the file, chunks the text, generates embeddings, and saves to DocumentChunk.
    """
    try:
        file_path = doc.file.path
        text = ""
        ext = os.path.splitext(file_path)[1].lower()

        # 1. Extract Text
        if ext == '.pdf':
            try:
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            except ImportError:
                print("pypdf not installed. Skipping PDF content.")
                return
        elif ext in ['.txt', '.md', '.csv']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        
        if not text:
            return

        # 2. Chunk Text (Simple character split for now)
        chunk_size = 500
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

        # 3. Embed and Save
        for chunk_content in chunks:
            embedding = generate_embedding(chunk_content)
            DocumentChunk.objects.create(
                document=doc,
                content=chunk_content,
                embedding=embedding,
                metadata={"source": doc.name}
            )
            
    except Exception as e:
        print(f"Error processing document {doc.name}: {str(e)}")

@api_view(['GET', 'POST', 'DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_documents(request, doc_id=None):
    if request.user.user_type != 1:
        return Response({'error': 'Unauthorized'}, status=403)

    if request.method == 'GET':
        # Only fetch documents that actually have a file attached (excludes chunks if any)
        docs = Document.objects.filter(file__isnull=False).exclude(file='').order_by('-uploaded_at')
        data = [
            {
                'id': d.id,
                'name': d.name,
                'uploaded_at': d.uploaded_at
            }
            for d in docs
        ]
        return Response(data)

    elif request.method == 'POST':
        file = request.FILES.get('file')

        if not file:
            return Response({'error': 'No file provided'}, status=400)

        doc = Document.objects.create(
            name=file.name,
            file=file,
            uploaded_by=request.user
        )

        # Process the document (Chunking + Embedding)
        process_and_embed_document(doc)

        return Response({
            'message': 'Document uploaded successfully',
            'id': doc.id
        })

    elif request.method == 'DELETE':
        try:
            doc = Document.objects.get(id=doc_id)
            doc.delete()
            return Response({'message': 'Document deleted'})
        except Document.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
