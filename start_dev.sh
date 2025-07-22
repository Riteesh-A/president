#!/bin/bash

# President Game Development Startup Script
echo "🃏 Starting President Game Development Environment"
echo "=================================================="

# Check if we're in the right directory
if [ ! -d "engine_py" ] || [ ! -d "frontend" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Function to cleanup processes on exit
cleanup() {
    echo ""
    echo "🧹 Shutting down servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Start backend
echo "🔧 Starting backend server..."
cd engine_py
pip install -e . > /dev/null 2>&1
python -m uvicorn src.president_engine.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 2

# Start frontend
echo "🎨 Starting frontend server..."
cd frontend
npm install > /dev/null 2>&1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for both servers to be ready
echo "⏳ Waiting for servers to start..."
sleep 3

echo ""
echo "✅ Development environment ready!"
echo "🔗 Frontend: http://localhost:3000"
echo "🔗 Backend:  http://localhost:8000"
echo "🔗 Health:   http://localhost:8000/health"
echo "🔗 WebSocket: ws://localhost:8000/ws"
echo ""
echo "💡 Press Ctrl+C to stop both servers"
echo "🎮 Open http://localhost:3000 to start playing!"

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID 