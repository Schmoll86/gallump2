#!/bin/bash

# Gallump Complete Shutdown Script
# Stops all components cleanly

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}    Stopping Gallump Trading System     ${NC}"
echo -e "${YELLOW}========================================${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to stop a service by PID file
stop_service() {
    local pid_file=$1
    local service_name=$2
    
    if [ -f "$pid_file" ]; then
        PID=$(cat "$pid_file")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}Stopping $service_name (PID: $PID)...${NC}"
            kill $PID 2>/dev/null
            sleep 1
            
            # Force kill if still running
            if ps -p $PID > /dev/null 2>&1; then
                echo -e "${YELLOW}Force stopping $service_name...${NC}"
                kill -9 $PID 2>/dev/null
            fi
            echo -e "${GREEN}✓ $service_name stopped${NC}"
        else
            echo -e "${YELLOW}$service_name not running (stale PID file)${NC}"
        fi
        rm -f "$pid_file"
    else
        echo -e "${YELLOW}$service_name PID file not found${NC}"
    fi
}

# Stop Frontend if running
stop_service ".frontend.pid" "Frontend server"

# Stop main Gallump server
stop_service ".gallump_server.pid" "Gallump API server"

# Kill any remaining Gallump processes
echo -e "${YELLOW}Checking for remaining Gallump processes...${NC}"

# Kill by process name patterns
PROCESSES=(
    "gallump.api.server"
    "mcp_enhanced_claude.py"
)

for process in "${PROCESSES[@]}"; do
    if pgrep -f "$process" > /dev/null; then
        echo -e "${YELLOW}Stopping remaining $process processes...${NC}"
        pkill -f "$process" 2>/dev/null || true
        sleep 0.5
        
        # Force kill if still running
        if pgrep -f "$process" > /dev/null; then
            pkill -9 -f "$process" 2>/dev/null || true
        fi
    fi
done

# Kill npm dev server if running on port 3000
if lsof -i :3000 > /dev/null 2>&1; then
    echo -e "${YELLOW}Stopping process on port 3000...${NC}"
    lsof -ti :3000 | xargs kill -9 2>/dev/null || true
fi


# Kill API server if running on port 5001
if lsof -i :5001 > /dev/null 2>&1; then
    echo -e "${YELLOW}Stopping process on port 5001...${NC}"
    lsof -ti :5001 | xargs kill -9 2>/dev/null || true
fi

# Clean up any stale PID files
rm -f .gallump_server.pid .frontend.pid

# Optional: Stop Redis if it was started by us
read -p "Stop Redis server? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v redis-cli &> /dev/null; then
        if redis-cli ping > /dev/null 2>&1; then
            echo -e "${YELLOW}Stopping Redis...${NC}"
            redis-cli shutdown 2>/dev/null || true
            echo -e "${GREEN}✓ Redis stopped${NC}"
        else
            echo -e "${YELLOW}Redis not running${NC}"
        fi
    fi
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}     Gallump System Stopped!            ${NC}"
echo -e "${GREEN}========================================${NC}"

# Final check
echo
echo -e "${YELLOW}Verifying shutdown...${NC}"
ALL_STOPPED=true

if lsof -i :5001 > /dev/null 2>&1; then
    echo -e "${RED}⚠ Port 5001 still in use${NC}"
    ALL_STOPPED=false
fi

if lsof -i :3000 > /dev/null 2>&1; then
    echo -e "${RED}⚠ Port 3000 still in use${NC}"
    ALL_STOPPED=false
fi


if pgrep -f "gallump" > /dev/null; then
    echo -e "${RED}⚠ Some Gallump processes may still be running${NC}"
    echo "Run 'ps aux | grep gallump' to check"
    ALL_STOPPED=false
fi

if [ "$ALL_STOPPED" = true ]; then
    echo -e "${GREEN}✓ All Gallump services stopped successfully${NC}"
else
    echo -e "${YELLOW}Some services may still be running. Check manually if needed.${NC}"
fi