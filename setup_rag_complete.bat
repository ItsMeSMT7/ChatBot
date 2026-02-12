@echo off
echo ========================================
echo   P Square RAG System - Complete Setup
echo ========================================
echo.

echo Step 1: Installing dependencies...
cd backend
pip install -r requirements.txt
echo.

echo Step 2: Verifying system...
python verify_rag_setup.py
echo.

echo ========================================
echo.
echo If verification passed, you can now:
echo   1. Run: ingest_company_policy.bat (to load PDF)
echo   2. Run: start_all.bat (to start servers)
echo.
echo ========================================
pause
