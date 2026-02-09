@echo off
echo Setting up P Square Chatbot Application...
echo.

echo 1. Installing Python dependencies...
cd backend
pip install -r requirements.txt
echo.

echo 2. Running database migrations...
python manage.py makemigrations
python manage.py migrate
echo.

echo 3. Testing database connection...
python test_connection.py
echo.

echo 4. Installing Node.js dependencies...
cd ..\frontend
npm install
echo.

echo ========================================
echo   Setup completed successfully!
echo ========================================
echo.
echo To start the application, run: start_application.bat
echo.
pause