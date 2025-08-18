#!/bin/bash

# Gallump System Status Check
# Shows the status of all Gallump components

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    Gallump System Status Check         ${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Function to check if a port is in use
check_port() {
    lsof -i :$1 > /dev/null 2>&1
    return $?
}

# Function to check service status
check_service() {
    local port=$1
    local service=$2
    local url=$3
    
    if check_port $port; then
        echo -e "${GREEN}✓${NC} $service is running on port $port"
        if [ ! -z "$url" ]; then
            echo -e "  URL: ${BLUE}$url${NC}"
        fi
        # Show process info
        PID=$(lsof -ti :$port | head -1)
        if [ ! -z "$PID" ]; then
            echo -e "  PID: $PID"
        fi
    else
        echo -e "${RED}✗${NC} $service is not running (port $port)"
    fi
}

# Check main services
echo -e "${YELLOW}Core Services:${NC}"
echo -e "─────────────────────────────────"
check_service 5001 "Gallump API Server" "http://localhost:5001"
check_service 3000 "Frontend Dev Server" "http://localhost:3000"
# MCP Analytics now integrated into main API server
echo

# Check IBKR Gateway
echo -e "${YELLOW}External Services:${NC}"
echo -e "─────────────────────────────────"
IBKR_LIVE=4001
IBKR_PAPER=4002

if check_port $IBKR_LIVE; then
    echo -e "${GREEN}✓${NC} IBKR Gateway/TWS (LIVE) on port $IBKR_LIVE"
elif check_port $IBKR_PAPER; then
    echo -e "${GREEN}✓${NC} IBKR Gateway/TWS (PAPER) on port $IBKR_PAPER"
else
    echo -e "${RED}✗${NC} IBKR Gateway/TWS not detected"
fi

# Check Redis
if command -v redis-cli &> /dev/null; then
    if redis-cli ping > /dev/null 2>&1; then
        REDIS_VERSION=$(redis-cli --version | awk '{print $2}')
        echo -e "${GREEN}✓${NC} Redis is running (v$REDIS_VERSION)"
    else
        echo -e "${YELLOW}⚠${NC} Redis is installed but not running"
    fi
else
    echo -e "${YELLOW}⚠${NC} Redis not installed (using in-memory cache)"
fi
echo

# Check Python processes
echo -e "${YELLOW}Gallump Python Processes:${NC}"
echo -e "─────────────────────────────────"
PROCESSES=$(ps aux | grep -E "gallump|mcp_" | grep -v grep | grep python)
if [ -z "$PROCESSES" ]; then
    echo -e "${YELLOW}No Gallump Python processes running${NC}"
else
    echo "$PROCESSES" | while read line; do
        PID=$(echo $line | awk '{print $2}')
        CMD=$(echo $line | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}')
        echo -e "  PID $PID: $CMD" | head -c 80
        echo
    done
fi
echo

# Check PID files
echo -e "${YELLOW}PID Files:${NC}"
echo -e "─────────────────────────────────"
for pidfile in .gallump_server.pid .frontend.pid; do
    if [ -f "$pidfile" ]; then
        PID=$(cat "$pidfile")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} $pidfile: Process $PID is running"
        else
            echo -e "${RED}✗${NC} $pidfile: Process $PID is not running (stale)"
        fi
    fi
done
echo

# Check logs
echo -e "${YELLOW}Recent Log Activity:${NC}"
echo -e "─────────────────────────────────"
if [ -d "logs" ]; then
    for logfile in logs/*.log; do
        if [ -f "$logfile" ]; then
            BASENAME=$(basename "$logfile")
            if [ -s "$logfile" ]; then
                LAST_MOD=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$logfile" 2>/dev/null || stat -c "%y" "$logfile" 2>/dev/null | cut -d' ' -f1-2)
                SIZE=$(ls -lh "$logfile" | awk '{print $5}')
                echo -e "  $BASENAME: $SIZE (last modified: $LAST_MOD)"
                
                # Show last error if any
                LAST_ERROR=$(grep -i "error\|exception\|failed" "$logfile" | tail -1)
                if [ ! -z "$LAST_ERROR" ]; then
                    echo -e "    ${RED}Last error: $(echo $LAST_ERROR | head -c 60)...${NC}"
                fi
            else
                echo -e "  $BASENAME: Empty"
            fi
        fi
    done
else
    echo -e "${YELLOW}No logs directory found${NC}"
fi
echo

# API Health Check
echo -e "${YELLOW}API Health Check:${NC}"
echo -e "─────────────────────────────────"
if check_port 5001; then
    # Try to get health status without auth (if endpoint allows)
    HEALTH_RESPONSE=$(curl -s http://localhost:5001/api/health 2>/dev/null)
    if [ ! -z "$HEALTH_RESPONSE" ]; then
        if echo "$HEALTH_RESPONSE" | grep -q "error"; then
            echo -e "${YELLOW}API requires authentication for health check${NC}"
        else
            echo -e "${GREEN}API Health Response:${NC}"
            echo "$HEALTH_RESPONSE" | python -m json.tool 2>/dev/null | head -10 || echo "$HEALTH_RESPONSE"
        fi
    else
        echo -e "${YELLOW}Could not fetch health status${NC}"
    fi
else
    echo -e "${RED}API server not running${NC}"
fi
echo

# Summary
echo -e "${BLUE}========================================${NC}"
RUNNING_COUNT=0
[ $(check_port 5001; echo $?) -eq 0 ] && RUNNING_COUNT=$((RUNNING_COUNT + 1))
[ $(check_port 3000; echo $?) -eq 0 ] && RUNNING_COUNT=$((RUNNING_COUNT + 1))

if [ $RUNNING_COUNT -eq 2 ]; then
    echo -e "${GREEN}All services are running!${NC}"
elif [ $RUNNING_COUNT -gt 0 ]; then
    echo -e "${YELLOW}$RUNNING_COUNT/2 services are running${NC}"
else
    echo -e "${RED}No services are running${NC}"
    echo -e "Run ${YELLOW}./gallump_start.sh${NC} to start the system"
fi
echo -e "${BLUE}========================================${NC}"