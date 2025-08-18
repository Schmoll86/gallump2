# Gallump Trading Assistant - Technical Documentation

**📖 This Document**: Technical reference for developers. For quick start see [README.md](README.md). For frontend see [gallump/frontend/README.md](gallump/frontend/README.md).

## 🏗️ Project Structure

```
Gallump/
├── gallump/
│   ├── api/           # API server (Flask)
│   │   ├── server.py  # Main server, port 5001
│   │   └── routes.py  # All endpoints including analytics
│   ├── core/          # Business logic modules
│   │   ├── brain.py              # Claude AI integration
│   │   ├── broker.py             # IBKR trading interface
│   │   ├── context_builder.py    # Market data aggregation
│   │   ├── prompt_builder.py     # AI prompt formatting
│   │   ├── validators.py         # Order validation
│   │   ├── risk.py               # Risk management
│   │   ├── scanner.py            # IBKR market scanning
│   │   ├── session_manager.py    # Conversation memory
│   │   ├── storage.py            # Database (SQLite)
│   │   ├── cache.py              # Fast caching (Redis/memory)
│   │   ├── types.py              # Data type definitions
│   │   ├── analytics_engine.py   # Analytics engine
│   │   ├── analytics_context.py  # Smart data prioritization
│   │   └── analytics_feeds.py    # Real-time data feeds
│   └── frontend/      # React mobile app
├── mcp_enhanced_claude.py  # Claude Desktop integration
├── gallump_start.sh       # Start all services
├── gallump_stop.sh        # Stop all services
└── gallump_status.sh      # Check system status
```

## 🔐 Authentication Required

All endpoints except `/api/auth/login` require JWT authentication:
```
Authorization: Bearer YOUR_JWT_TOKEN
```

## 🎯 Core Architecture: Mobile-First Trading Assistant

### Two Access Points, One System:

1. **📱 Mobile App** (Primary)
   - Access from anywhere via Tailscale VPN
   - Single API endpoint (port 5001)
   - Full trading + analytics capabilities
   - RED BUTTON confirmation for all trades

2. **🖥️ Claude Desktop** (Secondary)
   - Local analysis via MCP protocol
   - Read-only access (no trading)
   - Uses same analytics engine
   - For desktop-based research

### Data Flow:
```
Mobile Phone → Tailscale → API:5001 → IBKR Gateway
                              ↓
                    [Trading + Analytics + Sessions]
                              ↓
                    Same Analytics Engine Used By:
                              ↓
                    Claude Desktop (MCP)
```

## 📋 Module Responsibilities (Single Purpose Each)

| Module | Purpose | Never Does |
|--------|---------|------------|
| **brain.py** | Talks to Claude AI | Fetch data or execute trades |
| **broker.py** | Executes IBKR trades | Make decisions or validate |
| **context_builder.py** | Gathers market data | Analyze or format data |
| **prompt_builder.py** | Formats AI prompts | Fetch data or call AI |
| **validators.py** | Validates orders | Execute or evaluate risk |
| **risk.py** | Evaluates risk | Execute or validate |
| **scanner.py** | Scans markets | Trade or analyze |
| **session_manager.py** | Manages conversations | Handle market data |
| **storage.py** | Saves to database | Make decisions or cache |
| **cache.py** | Fast data access | Persist or decide |
| **analytics_engine.py** | Advanced analytics | Execute trades |
| **analytics_context.py** | Prioritizes data | Fetch or analyze |
| **analytics_feeds.py** | Gets live data | Analyze or trade |

## 🔄 Complete API Flow (How It Works)

### 1. Conversational Analysis Phase

```
# First request (creates session)
POST /api/strategies/generate
{
  "prompt": "I think AAPL might bounce from support",
  "watchlist": ["AAPL", "MSFT", "GOOGL"]
}

# Continuing conversation (maintains context)
POST /api/strategies/generate
{
  "prompt": "What about a more conservative approach?",
  "session_id": "abc123def456",  # From previous response
  "watchlist": ["AAPL"]
}
```

**What happens:**
- Session Manager retrieves or creates conversation session
- Context Builder aggregates ALL market data (news, TA, options, scanner)
- Session context (conversation history + insights) is loaded
- Brain (Claude) analyzes with both market and session context
- Brain returns conversational response + strategy recommendations
- Conversation is saved to session for continuity
- Strategies are saved with status: `PENDING_USER_APPROVAL`
- **NO EXECUTION OCCURS**

**Response:**
```json
{
  "session_id": "abc123def456",  # Client must store for continuity
  "response": "Looking at AAPL's technical indicators...",
  "recommendations": [
    {
      "name": "Conservative Bull Call Spread",
      "reasoning": "Strong support at $180...",
      "orders": [...],
      "confidence": 0.75
    }
  ],
  "requires_confirmation": true,
  "context_stats": {
    "messages_in_session": 2,
    "relevant_history_loaded": 0,
    "insights_included": 5,
    "token_estimate": 2450
  }
}
```

### 2. User Review Phase

The frontend displays:
- Claude's conversational analysis
- Recommended strategies with full details
- Risk warnings and confidence levels
- "EXECUTE" button for each strategy (THE RED BUTTON)

### 2.5 Analytics Endpoints (NEW - Mobile App)

```
# Portfolio Analysis
POST /api/analytics/portfolio
Response: Current positions with enhanced context

# Single Symbol Analysis
GET /api/analytics/symbol/AAPL
Response: Deep analysis with technicals, news, options

# Market Analysis
POST /api/analytics/market
Body: { "symbols": ["AAPL", "MSFT"], "prompt": "compare these" }
Response: Multi-symbol comparison with scanner results

# Options Analysis
GET /api/analytics/options/SPY
Response: Options chain with Greeks, IV analysis
```

These endpoints use the same MCP analytics engine that Claude Desktop uses, giving the mobile app full parity with desktop analysis capabilities.

### 3. User Confirmation Phase (RED BUTTON)

```
POST /api/strategies/{strategy_id}/confirm
{
  "confirmed": true
}
```

**Only NOW does execution flow begin:**
1. Validators normalize all order data
2. Risk Manager checks portfolio limits
3. Broker executes the trade
4. Results returned to user

### 4. Conversation Continues

User can continue the conversation:
- "What about a more conservative approach?"
- "Show me bearish strategies instead"
- "What if we used a different expiration?"

Each generates new recommendations, requiring new confirmation.

## 🚀 Quick Start

```bash
# 1. Start everything
./gallump_start.sh

# 2. Check status
./gallump_status.sh

# 3. Access from mobile
# Connect via Tailscale to http://your-server:5001

# 4. Stop everything
./gallump_stop.sh
```

## 📊 Complete API Reference

### Authentication
- `POST /api/auth/login` - Get JWT token

### Core Trading Flow
- `POST /api/strategies/generate` - AI conversation and analysis
- `GET /api/strategies` - List pending strategies  
- `POST /api/strategies/{id}/confirm` - RED BUTTON (user confirmation)
- `DELETE /api/strategies/{id}` - Cancel/reject a strategy

### Portfolio & Market Data
- `GET /api/portfolio` - Current positions (read-only)
- `GET /api/positions` - Enhanced position data with prices
- `GET /api/watchlist` - Get watchlist
- `POST /api/watchlist` - Add to watchlist
- `DELETE /api/watchlist/{symbol}` - Remove from watchlist

### Analytics Endpoints (NEW)
- `POST /api/analytics/portfolio` - Enhanced portfolio analysis
- `GET /api/analytics/symbol/<symbol>` - Deep symbol analysis
- `POST /api/analytics/market` - Multi-symbol market analysis
- `GET /api/analytics/options/<symbol>` - Options Greeks and IV

### Market Analysis
- `GET /api/available_scanners` - List all IBKR scanner types
- `POST /api/run_scan` - Execute market scan
- `GET /api/diagnose/{symbol}` - Debug symbol data issues
- `GET /api/options/chain/{symbol}` - Get options chain

### System
- `GET /api/health` - System health check
- `POST /api/annotations` - Save notes/insights/mistakes

## 📈 Database Schema

```sql
-- Core Tables
strategies      -- AI-generated trading strategies
trades          -- Executed orders with fills
portfolios      -- Point-in-time snapshots
conversations   -- Chat history with Claude
annotations     -- Notes, insights, mistakes
watchlist       -- Monitored symbols
sessions        -- Conversation sessions with context
```

## 🔐 Security Architecture

1. **JWT Authentication**: All API endpoints require token
2. **Tailscale VPN**: Secure remote access
3. **RED BUTTON**: No trades without explicit confirmation
4. **Read-Only MCP**: Claude Desktop cannot execute trades
5. **Single Entry Point**: Port 5001 only

## Module Responsibilities in Flow

### Context Builder
- **ONLY** aggregates data
- No decisions, no filtering
- Provides complete market picture

### Brain (Claude AI)
- **ONLY** analyzes and recommends
- Never executes
- Maintains conversation context
- Returns suggestions for user review

### Validators
- **ONLY** validates data structure
- Normalizes field names
- Ensures type safety
- Runs AFTER user confirmation

### Risk Manager
- **ONLY** evaluates risk
- Checks portfolio limits
- Calculates position sizing
- Runs AFTER user confirmation

### Broker
- **ONLY** executes trades
- Interfaces with IBKR
- Returns execution results
- Runs LAST, after all checks

### Server/Routes
- Coordinates the flow
- Enforces confirmation requirement
- Never allows direct execution without user consent

## Security Features

1. **No Auto-Trading**: AI can NEVER execute without user confirmation
2. **Status Tracking**: Each strategy tracked as PENDING → CONFIRMED → EXECUTED
3. **Validation Gates**: Multiple validation points before execution
4. **Risk Limits**: Hard stops on position size, loss limits
5. **Audit Trail**: All conversations and decisions logged

## Example Conversation Flow

```
User: "I think oil stocks might rally"
AI: "Looking at the energy sector... XOM shows strong momentum... 
     Here are 3 strategies..."
User: Reviews strategies, clicks "EXECUTE" on Strategy A
System: Validates → Checks Risk → Executes → Returns result
User: "What about a hedge?"
AI: "For hedging your XOM position, consider these put spreads..."
User: Reviews, decides not to execute
User: "Show me tech stocks instead"
AI: "Switching focus to technology sector..."
```

## Key Endpoints

### Authentication
- `POST /api/auth/login` - Get JWT token

### Core Trading Flow
- `POST /api/strategies/generate` - AI conversation and analysis
- `GET /api/strategies` - List pending strategies  
- `POST /api/strategies/{id}/confirm` - RED BUTTON (user confirmation)
- `DELETE /api/strategies/{id}` - Cancel/reject a strategy

### Portfolio & Market Data
- `GET /api/portfolio` - Current positions (read-only)
- `GET /api/positions` - Enhanced position data with prices
- `GET /api/watchlist` - Get watchlist
- `POST /api/watchlist` - Add to watchlist
- `DELETE /api/watchlist/{symbol}` - Remove from watchlist

### Market Analysis
- `GET /api/available_scanners` - List all IBKR scanner types
- `POST /api/run_scan` - Execute market scan
- `GET /api/diagnose/{symbol}` - Debug symbol data issues
- `GET /api/options/chain/{symbol}` - Get options chain

### System
- `GET /api/health` - System health check
- `POST /api/annotations` - Save notes/insights/mistakes

## Important Notes

- The Brain module NEVER calls broker directly
- Execution ONLY happens through confirm endpoint
- User can have multiple conversations without executing anything
- Each strategy requires individual confirmation
- System designed for thoughtful, informed trading decisions
## Frontend Integration Update

The React frontend has been fully implemented and properly integrates with the backend API flow described above.

### Frontend Request Flow

1. **Authentication**
   ```javascript
   // Frontend: auth.js
   await axios.post('/api/auth/login', { password })
   // Stores JWT in sessionStorage
   ```

2. **Strategy Generation with Session**
   ```javascript
   // Frontend: api.js
   await axios.post('/api/strategies/generate', {
     prompt: userMessage,
     watchlist: ['AAPL', 'MSFT'],
     session_id: sessionId  // Maintains conversation
   })
   ```

3. **RED BUTTON Confirmation**
   ```javascript
   // Frontend: RedButton.jsx
   // Stage 1: Review (shows risk summary)
   // Stage 2: Countdown (3 seconds)
   // Stage 3: Ready (final confirmation)
   await axios.post(`/api/strategies/${id}/confirm`, {
     confirmed: true
   })
   ```

### Frontend Components Map to API Flow

- **ChatBox.jsx** → `/api/strategies/generate` (with session management)
- **RedButton.jsx** → `/api/strategies/{id}/confirm` (NOT /api/execute)
- **PortfolioPanel.jsx** → `/api/get_positions` and `/api/portfolio`
- **SystemHealth.jsx** → `/api/health` (every 10 seconds)
- **LoginModal.jsx** → `/api/auth/login`

### Session Management in Frontend

The frontend properly maintains the session_id:

```javascript
// session.js service
class SessionService {
  currentSessionId = null;
  
  setSessionId(sessionId) {
    this.currentSessionId = sessionId;
  }
  
  getSessionId() {
    return this.currentSessionId;
  }
}
```

Every call to `/api/strategies/generate` includes the session_id if available, ensuring conversation continuity across the three-tier memory system (HOT/WARM/COLD).

### Error Handling

The frontend properly handles all backend error responses:

```javascript
// Frontend error handling
catch (error) {
  if (error.response?.status === 400) {
    // Validation errors, risk check failures
    toast.error(error.response.data.error);
    error.response.data.warnings?.forEach(w => toast.warning(w));
  } else if (error.response?.status === 401) {
    // Authentication failure - logout
    authService.logout();
  }
}
```

### Data Freshness Indicators

The frontend shows when data is stale or unavailable:

```javascript
// PositionCard.jsx
if (position.price_source === 'cached') {
  // Shows yellow warning: "Using cached price"
}
if (position.price_source === 'unavailable') {
  // Shows red warning: "No price data available"
}
```

### Mobile-First Design

- Touch targets minimum 44px
- Bottom navigation for easy thumb access
- Safe area insets for modern phones
- Disabled pull-to-refresh to prevent conflicts
- Responsive layouts adapt to screen size

The frontend implementation strictly follows the API flow and never bypasses any safety mechanisms.
