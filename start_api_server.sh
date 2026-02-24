#!/bin/bash

# STT API Server Startup Script
# This script starts the STT API server in the foreground to view logs

echo "=================================="
echo "STT API Server Startup Script"
echo "=================================="
echo ""

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📂 Working Directory: $SCRIPT_DIR"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found"
    exit 1
fi

echo "🐍 Python Version: $(python3 --version)"
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "✅ Virtual environment found: venv/"
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
    echo "✅ Virtual environment activated"
elif [ -d ".venv" ]; then
    echo "✅ Virtual environment found: .venv/"
    echo "🔄 Activating virtual environment..."
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  No virtual environment found, using system Python"
fi

echo ""
echo "🚀 Starting STT API Server..."
echo "📡 Default Port: 8003"
echo "📖 API Docs: http://0.0.0.0:8003/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================="
echo ""

# Start the API server
python3 api_server.py

# Capture exit code
EXIT_CODE=$?

echo ""
echo "=================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Server stopped gracefully"
else
    echo "❌ Server stopped with error code: $EXIT_CODE"
fi
echo "=================================="

exit $EXIT_CODE
