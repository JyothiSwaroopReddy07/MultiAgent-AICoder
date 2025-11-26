#!/bin/bash

# AI Code Generator Startup Script

echo "🚀 Starting AI Code Generator..."
echo ""

# Check for API key
if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ ERROR: GEMINI_API_KEY not set!"
    echo ""
    echo "Please set your Gemini API key:"
    echo ""
    echo "  export GEMINI_API_KEY='AIzaSyD-xxxxx'"
    echo ""
    echo "Or create a .env file in backend/ with:"
    echo "  GEMINI_API_KEY=AIzaSyD-xxxxx"
    echo ""
    echo "Get your API key from: https://makersuite.google.com/app/apikey"
    exit 1
fi

echo "✅ API key found"
echo ""

# Kill existing processes
echo "🧹 Cleaning up old processes..."
pkill -f "main_enhanced.py" 2>/dev/null
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null
sleep 2

# Start backend
echo "🔧 Starting backend on http://localhost:8000..."
cd backend
nohup python main_enhanced.py > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend
sleep 5

# Check backend health
if curl -s http://localhost:8000/api/chat/health | grep -q "healthy"; then
    echo "✅ Backend is running"
else
    echo "❌ Backend failed to start. Check /tmp/backend.log"
    exit 1
fi

# Start frontend
echo "🎨 Starting frontend on http://localhost:3000..."
cd frontend
nohup npm start > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

sleep 8

echo ""
echo "=========================================="
echo "  🎉 AI Code Generator is Ready!"
echo "=========================================="
echo ""
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "  Backend logs:  tail -f /tmp/backend.log"
echo "  Frontend logs: tail -f /tmp/frontend.log"
echo ""
echo "  To stop:"
echo "    pkill -f main_enhanced.py"
echo "    pkill -f react-scripts"
echo ""
echo "=========================================="
echo ""
