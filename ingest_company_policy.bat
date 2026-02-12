@echo off
echo ========================================
echo   PDF Ingestion for RAG System (Ollama)
echo ========================================
echo.

cd backend

echo Installing PyPDF2 if needed...
pip install PyPDF2==3.0.1
echo.

echo Starting PDF ingestion with Ollama...
python ingest_pdf.py

echo.
echo ========================================
echo   Ingestion Complete!
echo ========================================
pause
