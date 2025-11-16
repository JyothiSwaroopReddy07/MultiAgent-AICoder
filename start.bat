@echo off
REM AI Coder Startup Script for Windows

echo ╔═══════════════════════════════════════════════════════════╗
echo ║                                                           ║
echo ║              AI Coder Multi-Agent System                  ║
echo ║                                                           ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

REM Check if .env exists
if not exist ".env" (
    echo ⚠️  Warning: .env file not found!
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo ⚠️  IMPORTANT: Please edit .env and add your OPENAI_API_KEY!
    echo    notepad .env
    echo.
    pause
)

REM Check if Python virtual environment exists
if not exist "backend\venv" (
    echo 📦 Creating Python virtual environment...
    cd backend
    python -m venv venv
    cd ..
)

REM Install backend dependencies
echo 📦 Installing backend dependencies...
cd backend
call venv\Scripts\activate.bat
pip install -r requirements.txt > nul 2>&1
cd ..

REM Install frontend dependencies if needed
if not exist "frontend\node_modules" (
    echo 📦 Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

echo.
echo ✅ Setup complete!
echo.
echo 🚀 Starting backend server on port 8000...
cd backend
start "AI Coder Backend" cmd /k "venv\Scripts\activate.bat && python main.py"
cd ..

echo ⏳ Waiting for backend to start...
timeout /t 3 /nobreak > nul

echo 🚀 Starting frontend server on port 3000...
cd frontend
start "AI Coder Frontend" cmd /k "npm start"
cd ..

echo.
echo ✅ AI Coder is running!
echo.
echo    Backend:  http://localhost:8000
echo    Frontend: http://localhost:3000
echo    API Docs: http://localhost:8000/docs
echo.
echo Close the terminal windows to stop the servers
echo.
pause
