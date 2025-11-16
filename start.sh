#!/bin/bash

# AI Coder Startup Script

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║              AI Coder Multi-Agent System                  ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and add your OPENAI_API_KEY!"
    echo "   nano .env"
    echo ""
    read -p "Press Enter after adding your API key..."
fi

# Check if Python virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo "📦 Creating Python virtual environment..."
    cd backend
    python3 -m venv venv
    cd ..
fi

# Activate virtual environment and install backend dependencies
echo "📦 Installing backend dependencies..."
cd backend
source venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1
cd ..

# Install frontend dependencies if needed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Starting backend server on port 8000..."
cd backend
source venv/bin/activate
python main.py &
BACKEND_PID=$!
cd ..

echo "⏳ Waiting for backend to start..."
sleep 3

echo "🚀 Starting frontend server on port 3000..."
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ AI Coder is running!"
echo ""
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
