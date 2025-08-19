# Gallump2 - Clean Trading Architecture

Two separate projects in one repository:

## 1. MCP Server for Claude Desktop
**File:** `mcp_ibkr_server.py`

Provides IBKR trading tools to Claude Desktop:
- Get quotes and market data
- View positions and orders
- Run market scanners
- Get historical data

**Usage:**
```bash
python mcp_ibkr_server.py
```

## 2. Gallump2 Trading System
**Folder:** `gallump2_trading/`

Clean modular architecture with single-responsibility modules:
- Connection management with auto-reconnect
- Connection pooling for efficiency
- Market data fetching
- Order validation
- Position tracking

**Structure:**
```
gallump2_trading/
├── core/           # Connection management, types
├── market_data/    # Price fetching
├── execution/      # Order validation
└── portfolio/      # Position tracking
```

## Requirements
- Python 3.9+
- Interactive Brokers Gateway
- `pip install -r requirements.txt`

## Environment Setup
Copy `.env.example` to `.env` and configure:
- ANTHROPIC_API_KEY
- IBKR_HOST and IBKR_PORT

## License
MIT