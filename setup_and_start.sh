#!/bin/bash

echo "=========================================="
echo "  AI Code Generator - Setup & Start"
echo "=========================================="
echo ""

# Check if API key is already set
if [ -n "$OPENAI_API_KEY" ]; then
    echo "✅ API key found in environment"
elif [ -f "backend/.env" ] && grep -q "OPENAI_API_KEY" backend/.env; then
    echo "✅ API key found in .env file"
else
    echo "🔑 OpenAI API key is required"
    echo ""
    echo "Please enter your OpenAI API key:"
    echo "(Get it from: https://platform.openai.com/api-keys)"
    echo ""
    read -p "API Key: " api_key
    
    if [ -z "$api_key" ]; then
        echo "❌ No API key provided. Exiting."
        exit 1
    fi
    
    # Save to .env file
    echo "Saving API key to backend/.env..."
    cat > backend/.env << EOF
OPENAI_API_KEY=$api_key
OPENAI_MODEL=gpt-4o
TEMPERATURE=0.7
MAX_TOKENS=4000
BACKEND_PORT=8000
DEBUG=True
EOF
    
    echo "✅ API key saved"
fi

echo ""
echo "🧹 Cleaning up old processes..."
pkill -f "main_enhanced.py" 2>/dev/null
lsof -ti:8000 | xargs kill -9 2>/dev/null
sleep 2

echo "🔧 Starting backend..."
cd backend
python main_enhanced.py > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
cd ..

echo "⏳ Waiting for backend to start..."
for i in {1..15}; do
    if curl -s http://localhost:8000/api/chat/health | grep -q "healthy"; then
        echo "✅ Backend is running!"
        break
    fi
    sleep 1
    echo -n "."
done

echo ""
echo ""
echo "=========================================="
echo "  🎉 Application is Ready!"
echo "=========================================="
echo ""
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "  The frontend is already running."
echo "  Just refresh your browser!"
echo ""
echo "  Logs:"
echo "    Backend:  tail -f /tmp/backend.log"
echo ""
echo "=========================================="

