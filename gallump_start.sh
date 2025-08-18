#!/bin/bash

# Gallump Complete Startup Script
# Starts all components in the correct order

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}    Starting Gallump Trading System    ${NC}"
echo -e "${GREEN}========================================${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check for virtual environment
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Check for required environment variables
if [ ! -f ".env" ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo "Please create a .env file with the following:"
    echo "  ANTHROPIC_API_KEY=your-claude-api-key"
    echo "  ADMIN_PASSWORD=Snoop23"
    echo "  SECRET_KEY=your-secret-key"
    echo "  IBKR_HOST=127.0.0.1"
    echo "  IBKR_PORT=4001"
    exit 1
fi

# Function to check if a port is in use
check_port() {
    lsof -i :$1 > /dev/null 2>&1
    return $?
}

# Function to wait for service to be ready
wait_for_service() {
    local port=$1
    local service=$2
    local max_attempts=30
    local attempt=0
    
    echo -e "${YELLOW}Waiting for $service to be ready on port $port...${NC}"
    while [ $attempt -lt $max_attempts ]; do
        if check_port $port; then
            echo -e "${GREEN}✓ $service is ready${NC}"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    echo -e "${RED}✗ $service failed to start${NC}"
    return 1
}

# Kill any existing Gallump processes
echo -e "${YELLOW}Checking for existing Gallump processes...${NC}"
if pgrep -f "gallump.api.server" > /dev/null; then
    echo -e "${YELLOW}Found existing server processes. Shutting down...${NC}"
    pkill -f "gallump.api.server" || true
    sleep 2
fi

if pgrep -f "mcp_enhanced_claude.py" > /dev/null; then
    echo -e "${YELLOW}Found existing MCP processes. Shutting down...${NC}"
    pkill -f "mcp_enhanced_claude.py" || true
    sleep 1
fi


# Check if Redis is available (optional)
echo -e "${YELLOW}Checking Redis availability...${NC}"
if command -v redis-cli &> /dev/null; then
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis is available${NC}"
    else
        echo -e "${YELLOW}⚠ Redis not running. Starting Redis...${NC}"
        if command -v redis-server &> /dev/null; then
            redis-server --daemonize yes
            sleep 2
            if redis-cli ping > /dev/null 2>&1; then
                echo -e "${GREEN}✓ Redis started${NC}"
            else
                echo -e "${YELLOW}⚠ Redis unavailable (will use in-memory cache)${NC}"
            fi
        else
            echo -e "${YELLOW}⚠ Redis not installed (will use in-memory cache)${NC}"
        fi
    fi
else
    echo -e "${YELLOW}⚠ Redis not installed (will use in-memory cache)${NC}"
fi

# Check IBKR Gateway/TWS connection
echo -e "${YELLOW}Checking IBKR Gateway/TWS...${NC}"
IBKR_PORT=$(grep IBKR_PORT .env | cut -d '=' -f2 | tr -d ' ')
IBKR_PORT=${IBKR_PORT:-4001}

if check_port $IBKR_PORT; then
    echo -e "${GREEN}✓ IBKR Gateway/TWS detected on port $IBKR_PORT${NC}"
else
    echo -e "${RED}⚠ IBKR Gateway/TWS not detected on port $IBKR_PORT${NC}"
    echo -e "${YELLOW}  Please ensure IB Gateway or TWS is running${NC}"
    echo -e "${YELLOW}  Port 4001 = Live Trading, Port 4002 = Paper Trading${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Initialize database if needed
echo -e "${YELLOW}Checking database...${NC}"
if [ ! -f "data/trading.db" ]; then
    echo -e "${YELLOW}Initializing database...${NC}"
    python -c "from gallump.core.storage import Storage; Storage()" || {
        echo -e "${RED}✗ Failed to initialize database${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ Database initialized${NC}"
else
    echo -e "${GREEN}✓ Database exists${NC}"
fi

# Start main Gallump server
echo -e "${YELLOW}Starting Gallump API server...${NC}"
nohup python -m gallump.api.server > logs/server.log 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > .gallump_server.pid

# Wait for server to be ready
if wait_for_service 5001 "Gallump API server"; then
    echo -e "${GREEN}✓ Gallump API server started (PID: $SERVER_PID)${NC}"
else
    echo -e "${RED}✗ Failed to start Gallump API server${NC}"
    exit 1
fi

# Note: MCP Analytics is now integrated into the main API server
# Claude Desktop MCP runs separately via mcp_enhanced_claude.py

# Start Frontend (optional)
read -p "Start Frontend Development Server? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Starting Frontend...${NC}"
    cd gallump/frontend
    
    # Check if npm dependencies are installed
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Installing frontend dependencies...${NC}"
        npm install
    fi
    
    # Start frontend in background
    nohup npm run dev > ../../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../../.frontend.pid
    cd ../..
    
    if wait_for_service 3000 "Frontend dev server"; then
        echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
    else
        echo -e "${YELLOW}⚠ Frontend failed to start (check logs/frontend.log)${NC}"
    fi
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}       Gallump System Started!          ${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo -e "Services running:"
echo -e "  ${GREEN}✓${NC} Gallump API: http://localhost:5001"
[ -f .frontend.pid ] && echo -e "  ${GREEN}✓${NC} Frontend: http://localhost:3000"
echo
echo -e "Logs available in:"
echo -e "  • logs/server.log (API server)"
[ -f .frontend.pid ] && echo -e "  • logs/frontend.log (Frontend)"
echo
echo -e "To stop all services, run: ${YELLOW}./gallump_stop.sh${NC}"