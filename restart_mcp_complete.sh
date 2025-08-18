#!/bin/bash
# Complete restart of MCP Bridge Service with fixes

echo "🛑 Stopping existing MCP Bridge..."
# Kill existing process on port 5002
lsof -ti:5002 | xargs kill -9 2>/dev/null

# Also kill any orphaned mcp_enhanced_claude processes
pkill -f mcp_enhanced_claude 2>/dev/null

echo "⏳ Waiting for cleanup..."
sleep 3

echo "🚀 Starting MCP Bridge Service with fixes..."
cd /Users/schmoll/Desktop/Gallump
source venv/bin/activate

# Start with more verbose logging
export PYTHONUNBUFFERED=1
python3 -u mcp_bridge_service.py 2>&1 | tee /tmp/mcp_bridge.log &

echo "✅ MCP Bridge started!"
echo ""
echo "📊 Checking status in 3 seconds..."
sleep 3

# Check if it's running
if lsof -i :5002 > /dev/null 2>&1; then
    echo "✅ Port 5002 is active"
    
    # Check health
    health=$(curl -s http://localhost:5002/health)
    echo "📡 Health check: $health"
    
    # Check if MCP subprocess is running
    if echo "$health" | grep -q '"mcp_running":true'; then
        echo "✅ MCP subprocess is running!"
    else
        echo "⚠️ MCP subprocess not running - check /tmp/mcp_bridge.log for errors"
    fi
else
    echo "❌ Bridge failed to start - check /tmp/mcp_bridge.log"
fi

echo ""
echo "📝 Logs available at:"
echo "  - Bridge: /tmp/mcp_bridge.log"
echo "  - MCP: /tmp/mcp_enhanced.log"
echo ""
echo "To test: python3 test_mcp_bridge.py"
