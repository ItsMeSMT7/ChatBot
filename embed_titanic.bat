@echo off
echo ========================================
echo Titanic Data Embedding Process
echo ========================================
echo.

echo [1/3] Starting Ollama...
start "Ollama Server" cmd /k "ollama serve"
echo Waiting for Ollama to start...
timeout /t 5 /nobreak >nul

echo.
echo [2/3] Checking Ollama connection...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo ERROR: Ollama not responding
    echo Please wait a few more seconds and try again
    pause
    exit /b 1
)
echo Ollama is ready!

echo.
echo [3/3] Converting Titanic data to vectors...
cd backend
python manage.py embed_titanic

echo.
echo ========================================
echo Process Complete!
echo ========================================
echo.
echo Check pgAdmin - documents table for vectors
echo.
pause
