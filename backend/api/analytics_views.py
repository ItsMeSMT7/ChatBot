"""
Solven Analytics — API Views
POST /api/analytics/analyze/    — Run pipeline
GET  /api/analytics/progress/   — Get current phase (polled by frontend)
"""

import os
import uuid
import traceback
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from .rag import run_solven_analytics_pipeline, get_current_phase


MAX_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}


class AnalyticsView(APIView):
    """POST /api/analytics/analyze/ — Run the 9-phase pipeline."""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')

        if not file_obj:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(file_obj.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return Response({"error": f"Unsupported file type '{ext}'."}, status=status.HTTP_400_BAD_REQUEST)

        if file_obj.size > MAX_FILE_SIZE:
            return Response({"error": "File too large. Max 50 MB."}, status=status.HTTP_400_BAD_REQUEST)

        temp_filename = f"solven_temp_{uuid.uuid4().hex}{ext}"
        file_path = default_storage.save(temp_filename, file_obj)
        full_path = default_storage.path(file_path)

        try:
            result = run_solven_analytics_pipeline(full_path)
            if "error" in result:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            try:
                if os.path.exists(full_path):
                    os.remove(full_path)
            except Exception:
                pass


class AnalyticsProgressView(APIView):
    """GET /api/analytics/progress/ — Returns current pipeline phase."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        phase_info = get_current_phase()
        return Response(phase_info, status=status.HTTP_200_OK)