#!/bin/bash
# Restart MCP Bridge Service with the fix

echo "🛑 Stopping existing MCP Bridge..."
# Kill existing process on port 5002
lsof -ti:5002 | xargs kill -9 2>/dev/null

echo "⏳ Waiting for port to be free..."
sleep 2

echo "🚀 Starting MCP Bridge Service..."
cd /Users/schmoll/Desktop/Gallump
source venv/bin/activate
python3 mcp_bridge_service.py &

echo "✅ MCP Bridge restarted with python3 fix!"
echo "📡 Service should be running on port 5002"
echo ""
echo "To check status:"
echo "  curl http://localhost:5002/health"
