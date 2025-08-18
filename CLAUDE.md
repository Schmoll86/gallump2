# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gallump is a modular AI-powered trading assistant with two distinct Claude AI integrations:
1. **Gallump Brain (Execution)**: Claude AI via API for trade execution decisions (brain.py)
2. **MCP Analytics (Read-Only)**: Claude Desktop MCP for market analysis and discovery (via stdio)

The system maintains strict separation between analysis (MCP) and execution (Brain).

## Critical Architecture Principles

### How The System Works (Simple Explanation)

Think of Gallump like a team where each person has ONE specific job:

- **brain.py**: The AI consultant who gives trading advice
- **broker.py**: The trader who actually places orders with IBKR
- **context_builder.py**: The researcher who gathers all market data
- **prompt_builder.py**: The translator who formats data for the AI
- **validators.py**: The compliance officer who checks all orders
- **risk.py**: The risk manager who sets limits
- **scanner.py**: The market watcher who finds opportunities
- **session_manager.py**: The secretary who remembers all conversations
- **storage.py**: The filing cabinet for permanent records
- **cache.py**: The notepad for quick temporary notes

**Analytics Team (MCP modules):**
- **analytics_engine.py**: The quant analyst with advanced math
- **analytics_context.py**: The editor who prioritizes information
- **analytics_feeds.py**: The data vendor with real-time feeds

Each module ONLY does its job and NEVER does another module's job.

### Data Flow Rules

**Execution Flow (Can Trade)**:
```
User Input → SessionManager → ContextBuilder → PromptBuilder → Brain → User Review → 
RED BUTTON (confirm) → Validators → Risk → Broker → IBKR
```

**Analytics Flow (Read-Only)**:
```
User Request → MCP Server (stdio) → IBKR Scanner API → Context Scoring → 
Analysis Results → User Display (NO EXECUTION PATH)
```

**MCP Analytics Flow (Read-Only)**:
```
User → MCP Tab → WebSocket (5002) → Bridge → MCP Server → IBKR
                                                 ↓
                                          Claude Desktop
```
- NO execution path from MCP
- Separate from Strategy Chat flow
- Uses Claude Desktop, not API

**Session Management Flow:**
1. SessionManager maintains conversation continuity across requests
2. ContextBuilder provides market data (prices, news, technicals)
3. PromptBuilder combines both session and market context
4. Brain processes with full context awareness

1. NO module directly calls another without going through proper flow
2. ALL data must pass through validators before risk/execution
3. Brain NEVER executes trades - only suggests strategies
4. User confirmation (RED BUTTON) is REQUIRED before ANY execution
5. Storage and Cache NEVER make decisions or contain business logic

## Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install flask flask-cors pyjwt
pip install ib_insync nest-asyncio
pip install anthropic
pip install python-dotenv
pip install redis
pip install pytz holidays  # For market hours awareness
pip install sqlite3  # Usually included with Python

# Environment variables (.env file)
ANTHROPIC_API_KEY=your-claude-api-key
ADMIN_PASSWORD=Snoop23
SECRET_KEY=your-secret-key-change-this
IBKR_HOST=127.0.0.1
IBKR_PORT=4001  # 4002 for paper trading

# Initialize database
python -c "from gallump.core.storage import Storage; Storage()"

# Run server (uses port 5001 on macOS to avoid AirPlay conflict)
python -m gallump.api.server
```

## Common Development Tasks

### Testing IBKR Connection
```bash
# Full diagnostic
python diagnose_ibkr.py

# Paper trading diagnostic
python diagnose_ibkr.py paper

# Quick connection test
python -c "from gallump.core.broker import Broker; b = Broker(); print(b.connect())"
```

### Testing API Endpoints
```bash
# Get JWT token
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password": "Snoop23"}'

# Test health check (use token from login)
curl http://localhost:5001/api/health \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test AI conversation (first request - creates new session)
curl -X POST http://localhost:5001/api/strategies/generate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "I think AAPL will bounce from support", "watchlist": ["AAPL"]}'

# Continue conversation (include session_id from first response)
curl -X POST http://localhost:5001/api/strategies/generate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What about a more conservative approach?", "session_id": "SESSION_ID_HERE", "watchlist": ["AAPL"]}'

# Test analytics endpoints (NEW)
curl http://localhost:5001/api/analytics/portfolio \
  -H "Authorization: Bearer YOUR_TOKEN"

curl http://localhost:5001/api/analytics/symbol/AAPL \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test pending orders endpoints
curl http://localhost:5001/api/orders/pending \
  -H "Authorization: Bearer YOUR_TOKEN"

curl http://localhost:5001/api/orders/brackets \
  -H "Authorization: Bearer YOUR_TOKEN"

curl http://localhost:5001/api/orders/stats \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Pending Orders System

The system includes comprehensive pending orders tracking that integrates with IBKR's live order management:

#### Key Features:
- **Full IBKR API Fidelity**: Tracks all order types (MKT, LMT, STP, TRAIL, etc.)
- **Bracket Order Support**: Groups parent, profit target, and stop loss orders
- **Multi-Layer Caching**: Redis/memory cache with database persistence
- **Real-Time Sync**: Live updates from IBKR with status tracking
- **OCO Management**: One-Cancels-All group handling

#### API Endpoints:
```bash
# Get all pending orders (supports filtering)
GET /api/orders/pending?symbol=AAPL&status=Submitted

# Get bracket order groups
GET /api/orders/brackets

# Cancel a specific order
POST /api/orders/cancel/{order_id}

# Get order statistics
GET /api/orders/stats
```

#### Data Flow:
```
IBKR Live Orders → broker.get_enhanced_open_orders() → 
Cache (30s TTL) → Database Sync → API Response
```

#### Database Schema:
- **pending_orders** table with 25+ IBKR-compliant fields
- Full order lifecycle tracking (PendingSubmit → Filled)
- Asset type support (STOCK, OPTION, FUTURE, FOREX)
- Time constraints (DAY, GTC, IOC, FOK, GAT, GTD)

#### Key Methods:
```python
# Broker methods
broker.get_enhanced_open_orders()  # Live IBKR orders
broker.place_bracket_order(symbol, action, qty, entry, target, stop)
broker.cancel_order(order_id)

# Storage methods  
storage.sync_pending_orders(live_orders)
storage.get_pending_orders(symbol=None, status=None)
storage.get_bracket_orders()

# Cache methods
cache.cache_pending_orders(orders, ttl=30)
cache.get_cached_pending_orders()
cache.invalidate_pending_orders()
```

### Adding New Features

When adding ANY new feature, ask yourself:
1. Which module's single responsibility does this belong to?
2. If it doesn't fit any module's responsibility, create a NEW module
3. Does the data flow follow: Context → Brain → User → Validation → Risk → Execution?
4. Is user confirmation enforced before any trade execution?

### Database Operations
```python
from gallump.core.storage import Storage
storage = Storage()

# Save annotation (for mistakes, insights, lessons)
storage.save_annotation(
    note_type="mistake",  # or "insight", "strategy_liked", "lesson"
    text="Entered position too close to market close",
    related_symbol="SPY",
    author="user",  # or "claude"
    importance="high"  # "low", "normal", "high", "critical"
)

# Query past mistakes for learning
mistakes = storage.get_mistakes(symbol="AAPL")
```

## Code Patterns to Follow

### API Endpoint Pattern
```python
@app.route('/api/endpoint', methods=['POST'])
@auth_required  # ALWAYS require authentication
def endpoint_name():
    # 1. Get and validate input
    data = request.json
    session_id = data.get('session_id')
    validated = validate_something(data)
    
    # 2. Get or create session
    session_id = session_manager.get_or_create_session(session_id)
    
    # 3. Build both session and market context
    session_context = session_manager.get_context(session_id, symbol)
    market_context = context_builder.build(...)
    
    # 4. Process with full context (but NEVER execute without confirmation)
    result = process_something(validated, session_context, market_context)
    
    # 5. Update session and return
    session_manager.add_message(session_id, 'assistant', result['response'], symbol)
    return jsonify({**result, 'session_id': session_id})
```

### Error Handling Pattern
```python
try:
    # Operation
    result = do_something()
    return jsonify({"success": True, "data": result})
except Exception as e:
    logger.error(f"Operation failed: {e}")
    return jsonify({"error": str(e), "details": "Technical details"}), 500
```

### Order Execution Flow (MUST follow exactly)
```python
# 1. User confirms strategy (RED BUTTON)
confirmed = request.json.get('confirmed', False)
if not confirmed:
    return jsonify({'error': 'User confirmation required'}), 400

# 2. Validate EVERY order
validated_orders = [validate_order(order) for order in orders]

# 3. Check risk for EVERY order
risk_result = risk_manager.evaluate(trade, portfolio)
if not risk_result.approved:
    return jsonify({'error': 'Failed risk checks', 'warnings': risk_result.warnings}), 400

# 4. ONLY NOW execute through broker
order_id = broker.place_order(...)

# 5. Log EVERYTHING
storage.save_trade(trade_details)
```

## IBKR Integration Notes

- **Port 4001**: Live trading
- **Port 4002**: Paper trading
- **Client ID**: Automatically managed (random selection to avoid conflicts)
- **Market Data**: Requires proper entitlements/subscriptions
- **After Hours**: Uses delayed data mode (reqMarketDataType(3))
- **Rate Limits**: 50-100 concurrent market data subscriptions
- **Connection**: Dynamic client ID retry on conflicts
- **Market Hours**: Full timezone awareness with pytz and holidays

## Testing Checklist

Before ANY live trading:

- [ ] Verify risk limits trigger correctly
- [ ] Confirm user authorization flow works
- [ ] Test market hours and after-hours behavior
- [ ] Verify all trades are logged to database
- [ ] Check that Brain NEVER executes directly
- [ ] Ensure validators catch malformed data
- [ ] Test error handling for IBKR disconnections
- [ ] Verify pending orders sync correctly with IBKR
- [ ] Test bracket order creation and management
- [ ] Confirm order cancellation works properly

## Common Issues and Solutions

### "Current Price: $0.00"
- Check market data entitlements in IBKR
- Verify symbol is correct and market is open
- Run: `python diagnose_ibkr.py` to check entitlements

### "Cannot connect to IBKR"
- Ensure IB Gateway/TWS is running
- Check API settings are enabled
- Verify port matches (4001 live, 4002 paper)
- Ensure Client ID is not already in use

### "Strategy execution failed"
- Check logs for validation errors
- Verify risk limits aren't exceeded
- Ensure broker is connected
- Confirm orders have all required fields

## Critical Safety Rules

1. **NEVER** allow Brain to execute trades directly
2. **ALWAYS** require user confirmation (RED BUTTON) before execution
3. **NEVER** skip validation or risk checks
4. **ALWAYS** log every trade attempt with full context
5. **NEVER** put business logic in storage.py or cache.py
6. **ALWAYS** maintain single responsibility per module
7. **NEVER** store secrets in code - use environment variables

## Frontend Implementation

A complete React frontend has been implemented in `gallump/frontend/` with proper integration to all backend endpoints.

### Frontend Setup

```bash
# Navigate to frontend directory
cd gallump/frontend

# Install dependencies
npm install

# Start development server (runs on port 3000, proxies to backend on 5001)
npm run dev

# Build for production
npm run build
```

### Frontend Architecture

- **React 18** with Vite for fast development
- **Tailwind CSS** for mobile-first styling
- **Zustand** for state management
- **Axios** for API calls with JWT interceptors
- **React Hot Toast** for notifications

### Key Frontend Features

1. **Session Management**: Properly maintains session_id for conversation continuity
2. **RED BUTTON**: Multi-stage confirmation (Review → Countdown → Execute)
3. **Health Monitoring**: Real-time system status bar
4. **Mobile Optimized**: Touch-friendly with bottom navigation
5. **Error Handling**: Global error boundary and user-friendly error messages
6. **Stale Data Detection**: Shows warnings when using cached prices

### Frontend-Backend Integration Points

- Uses `/api/strategies/generate` with session_id for continuity
- Uses `/api/strategies/{id}/confirm` for execution (NOT /api/execute)
- Handles actual response structure (recommendations, not strategies)
- Displays context statistics (token usage, message count)
- Shows market open/closed status from health endpoint

See `gallump/frontend/README.md` for detailed frontend documentation.
