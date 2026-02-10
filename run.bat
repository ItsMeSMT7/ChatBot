@echo off
echo ========================================
echo P Square Complete Setup and Start
echo ========================================
echo.

REM Check if first time setup needed
if not exist "backend\api\migrations\0001_initial.py" (
    echo [1/5] First time setup detected...
    cd backend
    echo Creating migrations...
    python manage.py makemigrations
    echo Applying migrations...
    python manage.py migrate
    echo Enabling pgvector...
    python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings'); import django; django.setup(); from django.db import connection; cursor = connection.cursor(); cursor.execute('CREATE EXTENSION IF NOT EXISTS vector;'); print('pgvector enabled')" 2>nul
    cd ..
    echo Setup complete!
    echo.
) else (
    echo [1/5] Database already setup, skipping...
    echo.
)

REM Check if documents exist
cd backend
python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings'); import django; django.setup(); from api.models import Document; exit(0 if Document.objects.exists() else 1)" 2>nul
if errorlevel 1 (
    echo [2/5] Loading RAG documents...
    python ingest_data.py 2>nul
    if errorlevel 1 (
        echo No documents loaded - RAG will use fallback mode
    )
    echo.
) else (
    echo [2/5] Documents already loaded, skipping...
    echo.
)
cd ..

echo [3/5] Starting Ollama...
start "Ollama" cmd /k "ollama serve"
timeout /t 2 /nobreak >nul

echo [4/5] Starting Django Backend...
start "Backend" cmd /k "cd backend && python manage.py runserver"
timeout /t 3 /nobreak >nul

echo [5/5] Starting React Frontend...
start "Frontend" cmd /k "cd frontend && npm start"

echo.
echo ========================================
echo All Services Running!
echo ========================================
echo.
echo Ollama:   http://localhost:11434
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press any key to stop all services...
pause >nul

echo.
echo Stopping services...
taskkill /FI "WINDOWTITLE eq Ollama*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Frontend*" /T /F >nul 2>&1
echo Done!
