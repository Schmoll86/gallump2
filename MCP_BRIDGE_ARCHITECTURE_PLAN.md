# MCP IBKR Tools & Bidirectional Bridge - Complete Architecture Plan

## Phase 1: Perfect the MCP Tools (DO THIS FIRST)
**Timeline: 1-2 weeks**
**Goal: Claude Desktop becomes your ultimate trading analysis companion**

### 1.1 Core MCP Tools to Implement

```python
# mcp_ibkr_server.py - The complete MCP server

class IBKRMCPServer:
    """MCP server that Claude Desktop will use"""
    
    tools = [
        # Market Data Tools
        "get_quote",           # Real-time price, bid/ask, volume
        "get_market_depth",    # Level 2 data, order book
        "get_historical_bars", # OHLCV data for charting
        "get_tick_data",       # Tick-by-tick trades
        
        # Portfolio Tools
        "get_positions",       # Current holdings with P&L
        "get_orders",          # Open orders
        "get_executions",      # Recent trades
        "get_account_summary", # Buying power, margin, etc.
        
        # Analytics Tools
        "scan_market",         # Top gainers, unusual volume, etc.
        "get_options_chain",   # Full options data with Greeks
        "get_fundamentals",    # P/E, market cap, financials
        "get_news",           # Real-time news for symbols
        
        # Advanced Tools
        "calculate_risk",      # Portfolio risk metrics
        "find_correlations",   # Symbol correlation analysis
        "get_sector_data",     # Sector performance
        "get_market_calendar", # Earnings, dividends, splits
    ]
```

### 1.2 Testing Framework

```python
# test_mcp_tools.py
def test_all_tools():
    """Ensure each tool works perfectly with Claude Desktop"""
    
    test_cases = {
        "get_quote": ["AAPL", "TSLA", "SPY"],
        "get_positions": [],
        "scan_market": ["TOP_PERC_GAIN", "UNUSUAL_VOLUME"],
        "get_options_chain": ["SPY", "2024-12-20"],
    }
    
    for tool, params in test_cases.items():
        result = mcp_server.call_tool(tool, params)
        assert result.status == "success"
        assert result.data is not None
```

### 1.3 Claude Desktop Configuration

```json
{
  "mcpServers": {
    "ibkr-trading": {
      "command": "python",
      "args": ["/Users/schmoll/Desktop/Gallump/mcp_ibkr_server.py"],
      "env": {
        "IBKR_HOST": "127.0.0.1",
        "IBKR_PORT": "4001",
        "IBKR_CLIENT_ID": "999"
      }
    }
  }
}
```

### 1.4 Success Criteria
- [ ] All tools return data within 2 seconds
- [ ] Claude Desktop can access all tools
- [ ] Error handling for market closed, invalid symbols
- [ ] Caching for expensive operations
- [ ] Rate limiting to avoid IBKR throttling

---

## Phase 2: Design the Bridge Architecture
**Timeline: 1 week planning**
**Goal: Clear blueprint for bidirectional communication**

### 2.1 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Mobile App (React)                       │
├─────────────────────────────────────────────────────────────┤
│  • Strategy Chat (Execution)                                 │
│  • Analytics Request (Queue analysis for Claude Desktop)     │
│  • Results Viewer (See Claude Desktop analysis)              │
└────────────────────┬───────────────────────────────────────┘
                     │ WebSocket
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Bridge Server (Python - Port 5002)              │
├─────────────────────────────────────────────────────────────┤
│  • Request Queue Manager                                     │
│  • WebSocket Handler                                         │
│  • Result Cache                                              │
│  • Session Manager                                           │
└────────┬──────────────────────────┬────────────────────────┘
         │ HTTP Polling              │ HTTP POST
         ▼                           ▼
┌─────────────────────────────────────────────────────────────┐
│          Request Queue (Redis/SQLite)                        │
├─────────────────────────────────────────────────────────────┤
│  • Pending requests                                          │
│  • Processing requests                                       │
│  • Completed analyses                                        │
└────────────────────┬───────────────────────────────────────┘
                     │ Polling every 2s
                     ▼
┌─────────────────────────────────────────────────────────────┐
│      Claude Desktop Processor (Python - Background)          │
├─────────────────────────────────────────────────────────────┤
│  • Poll for requests                                         │
│  • Format for Claude                                         │
│  • Capture responses                                         │
│  • Submit results                                            │
└────────────────────┬───────────────────────────────────────┘
                     │ AppleScript/Automation
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Claude Desktop (with MCP Tools)                 │
├─────────────────────────────────────────────────────────────┤
│  • Receives formatted prompts                                │
│  • Uses MCP tools for data                                   │
│  • Generates analysis                                        │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow Sequences

#### Sequence 1: Mobile Analysis Request
```
1. User in mobile: "Analyze NVDA for swing trade opportunity"
2. Mobile → Bridge: {type: "analysis_request", prompt: "...", symbols: ["NVDA"]}
3. Bridge → Queue: Store with unique request_id
4. Bridge → Mobile: {type: "queued", request_id: "abc123", eta: 30}
5. Mobile shows: "⏳ Analysis queued... (ID: abc123)"
```

#### Sequence 2: Claude Desktop Processing
```
1. Processor → Queue: GET /pending_request
2. Queue → Processor: {id: "abc123", prompt: "...", symbols: [...]}
3. Processor formats prompt with context
4. Processor → Claude Desktop: (via automation)
   "Use the ibkr-trading MCP tools to analyze NVDA for swing trade opportunity.
    Include: current price, options flow, technical levels, and risk assessment."
5. Claude Desktop executes with MCP tools
6. Processor captures response
7. Processor → Bridge: POST /submit_result {request_id: "abc123", analysis: "..."}
```

#### Sequence 3: Mobile Receives Result
```
1. Bridge → Queue: Mark request completed
2. Bridge → Mobile: (via WebSocket) {type: "analysis_complete", request_id: "abc123", analysis: "..."}
3. Mobile displays formatted analysis
4. Mobile stores in local cache
```

### 2.3 Database Schema

```sql
-- requests table
CREATE TABLE analysis_requests (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    prompt TEXT NOT NULL,
    symbols TEXT, -- JSON array
    status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    processor_id TEXT,
    retry_count INTEGER DEFAULT 0,
    priority INTEGER DEFAULT 0
);

-- results table  
CREATE TABLE analysis_results (
    request_id TEXT PRIMARY KEY,
    analysis TEXT NOT NULL,
    tokens_used INTEGER,
    processing_time_ms INTEGER,
    mcp_tools_used TEXT, -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES analysis_requests(id)
);

-- session tracking
CREATE TABLE processor_sessions (
    id TEXT PRIMARY KEY,
    claude_desktop_version TEXT,
    status TEXT, -- active, idle, disconnected
    last_heartbeat TIMESTAMP,
    requests_processed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.4 API Endpoints

```python
# Bridge Server API

# For Mobile App
POST   /api/bridge/request    - Submit analysis request
GET    /api/bridge/status/:id - Check request status  
GET    /api/bridge/result/:id - Get analysis result
DELETE /api/bridge/cancel/:id - Cancel pending request
WS     /ws/bridge             - Real-time updates

# For Claude Desktop Processor
GET    /api/processor/next    - Get next pending request
POST   /api/processor/claim   - Claim request for processing
POST   /api/processor/result  - Submit analysis result
POST   /api/processor/heartbeat - Keep session alive
POST   /api/processor/error   - Report processing error

# Admin/Monitoring
GET    /api/bridge/stats      - Queue statistics
GET    /api/bridge/health     - System health check
```

---

## Phase 3: Build the Bridge
**Timeline: 2-3 weeks**
**Goal: Working bidirectional system**

### 3.1 Implementation Order

1. **Week 1: Core Infrastructure**
   - Request queue with Redis/SQLite
   - Basic Bridge Server
   - Database models
   - API endpoints

2. **Week 2: Claude Desktop Integration**
   - Processor script
   - Claude Desktop automation (AppleScript/Python)
   - Response capture
   - Error handling

3. **Week 3: Mobile Integration**
   - Update MCP tab to use queue
   - WebSocket real-time updates
   - Result display formatting
   - Offline handling

### 3.2 Configuration Files

```yaml
# bridge_config.yaml
bridge:
  host: 0.0.0.0
  port: 5002
  max_queue_size: 100
  request_timeout: 60
  
processor:
  poll_interval: 2
  max_retries: 3
  claude_desktop_timeout: 30
  
redis:
  host: localhost
  port: 6379
  db: 0
  
monitoring:
  enable_metrics: true
  log_level: INFO
```

### 3.3 Error Handling Strategy

```python
class BridgeErrorHandler:
    def handle_error(self, error_type, request_id):
        strategies = {
            "claude_desktop_not_running": self.queue_for_later,
            "mcp_tool_error": self.retry_with_fallback,
            "timeout": self.notify_user_timeout,
            "rate_limit": self.add_to_backoff_queue,
        }
        return strategies[error_type](request_id)
```

---

## Phase 4: Testing & Optimization
**Timeline: 1 week**
**Goal: Production-ready system**

### 4.1 Test Scenarios

1. **Load Testing**
   - 50 concurrent analysis requests
   - Queue overflow handling
   - Memory leak detection

2. **Failure Testing**
   - Claude Desktop crashes
   - Network interruption
   - IBKR disconnection
   - Redis failure

3. **Performance Testing**
   - End-to-end latency < 30 seconds
   - Queue processing rate
   - WebSocket connection stability

### 4.2 Monitoring & Metrics

```python
metrics = {
    "queue_depth": lambda: len(pending_requests),
    "avg_processing_time": lambda: sum(times)/len(times),
    "success_rate": lambda: successful/total,
    "claude_desktop_uptime": lambda: time_since_last_heartbeat,
    "active_websockets": lambda: len(ws_connections),
}
```

---

## Phase 5: Future Enhancements

### 5.1 Advanced Features
- Priority queue for premium users
- Batch processing for related requests
- Analysis caching and similarity matching
- Multi-Claude Desktop instance support
- Scheduled/recurring analyses

### 5.2 AI Improvements
- Fine-tuned prompts for different analysis types
- Context memory across requests
- Learning from user feedback
- Automatic insight extraction

---

## Decision Point: Should You Build This?

### Build If:
- You need deep, AI-powered analysis on mobile
- You're willing to maintain complex infrastructure
- Latency of 10-30 seconds is acceptable
- You want cutting-edge integration

### Don't Build If:
- Current Strategy Chat is sufficient
- You need real-time responses
- Maintenance complexity is a concern
- Simple analysis is enough

### Alternative: Enhanced API-Based Analytics
Instead of the bridge, enhance your Analytics tab to use Claude API directly with:
- Pre-built analysis templates
- Direct IBKR data integration
- Real-time response (2-3 seconds)
- No Claude Desktop dependency

## Recommended Path Forward

1. **First**: Perfect the MCP tools (2 weeks)
2. **Test**: Use Claude Desktop manually with perfect tools (1 week)
3. **Evaluate**: Is manual use sufficient? 
4. **Decide**: Build bridge only if automation is critical
5. **Alternative**: Enhance Analytics tab with Claude API

The MCP tools alone will make Claude Desktop incredibly powerful for trading analysis. The bridge adds automation but significant complexity.