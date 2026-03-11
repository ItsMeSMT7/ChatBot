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
from .rag import run_solven_analytics_pipeline, rag_query
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
from .document_parser import parse_document
from .chunking import create_chunks


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

            # ── THIS IS THE KEY FIX ──
            # rag_query() returns a STRING, not a dictionary
            # So just use it directly:
            if isinstance(result, dict):
                answer = result.get("answer", str(result))
            else:
                answer = str(result)

            return Response({"answer": answer})

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                "answer": f"Sorry, I couldn't process your question. Error: {str(e)}"
            })
        
        
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
    Process an uploaded document through the new intelligent pipeline.

    OLD FLOW:
        read file → split every 500 chars → embed → save

    NEW FLOW:
        parse file (extract headings, pages) →
        intelligent sentence-based chunking (respects headings) →
        extract keywords per chunk →
        embed each chunk →
        save with rich metadata (page, section, keywords)
    """
    from .ollama_service import generate_embedding

    try:
        doc.processing_status = 'processing'
        doc.save(update_fields=['processing_status'])

        file_path = doc.file.path

        # ── Step 1: Parse document ──────────────────────────
        #    Extracts structured sections with headings + page numbers
        parsed_doc = parse_document(file_path)

        if not parsed_doc.full_text.strip():
            doc.processing_status = 'failed'
            doc.save(update_fields=['processing_status'])
            print(f"No text extracted from {doc.name}")
            return

        # ── Step 2: Intelligent chunking ────────────────────
        #    Sentence-aware, heading-aware, keyword-extracted
        processed_chunks = create_chunks(parsed_doc)

        if not processed_chunks:
            doc.processing_status = 'failed'
            doc.save(update_fields=['processing_status'])
            print(f"No chunks created from {doc.name}")
            return

        # ── Step 3: Delete old chunks (if re-processing) ───
        from .models import DocumentChunk
        DocumentChunk.objects.filter(document=doc).delete()

        # ── Step 4: Embed and save each chunk ───────────────
        saved = 0
        for chunk in processed_chunks:
            embedding = generate_embedding(chunk.content)

            if embedding is None:
                print(f"  Skipping chunk {chunk.chunk_index}: embedding failed")
                continue

            DocumentChunk.objects.create(
                document=doc,
                content=chunk.content,
                embedding=embedding,
                metadata={
                    "source": doc.name,
                    **(chunk.metadata or {}),
                },
                page_number=chunk.page_number,
                section_title=chunk.section_title,
                keywords=chunk.keywords,
                chunk_index=chunk.chunk_index,
                char_count=len(chunk.content),
            )
            saved += 1

        doc.total_chunks = saved
        doc.processing_status = 'completed'
        doc.save(update_fields=['total_chunks', 'processing_status'])

        print(f"✓ '{doc.name}': {saved} chunks saved "
              f"(avg {sum(len(c.content) for c in processed_chunks) // max(len(processed_chunks), 1)} chars)")

    except Exception as e:
        print(f"✗ Error processing {doc.name}: {str(e)}")
        doc.processing_status = 'failed'
        doc.save(update_fields=['processing_status'])


@api_view(['GET', 'POST', 'DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])

def admin_documents(request, doc_id=None):
    if request.user.user_type != 1:
        return Response({'error': 'Unauthorized'}, status=403)

    if request.method == 'GET':
        # Only fetch documents that actually have a file attached (excludes chunks if any)
        docs = Document.objects.filter(file__isnull=False).exclude(file='').order_by('-created_at')
        data = [
            {
                'id': d.id,
                'name': d.name,
                'uploaded_at': d.created_at
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
