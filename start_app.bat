@echo off
echo ========================================
echo P Square Application Startup
echo ========================================
echo.

echo Checking Django Backend...
cd backend
python -c "import django; print('Django OK')" 2>nul
if errorlevel 1 (
    echo ERROR: Django not installed
    echo Run: pip install -r requirements.txt
    pause
    exit /b 1
)

echo Starting Django Backend...
start "Django Backend" cmd /k "python manage.py runserver"
timeout /t 5 /nobreak >nul

echo.
echo Starting React Frontend...
cd ..\frontend
start "React Frontend" cmd /k "npm start"

echo.
echo ========================================
echo Application Started!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Note: RAG features require:
echo 1. Run setup_rag.bat (one time)
echo 2. Start Ollama: ollama serve
echo.
echo Close the terminal windows to stop.
