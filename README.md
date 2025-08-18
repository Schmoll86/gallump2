# Gallump2 - AI Trading Assistant

## What It Does
- Chat with AI about trading ideas
- Get trade suggestions from Claude
- Execute trades on Interactive Brokers
- Track your portfolio in real-time

## Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
cd gallump/frontend && npm install
```

2. **Set up .env file:**
```bash
ANTHROPIC_API_KEY=your-claude-api-key
ADMIN_PASSWORD=Snoop23
IBKR_PORT=4001  # or 4002 for paper trading
```

3. **Start everything:**
```bash
# Terminal 1: Start IBKR Gateway

# Terminal 2: Backend
python -m gallump.api.server

# Terminal 3: Frontend
cd gallump/frontend && npm run dev
```

4. **Open browser:** http://localhost:3000

## How to Use

1. **Chat Tab**: Talk to Claude about trading ideas
2. **Portfolio Tab**: See your positions and P&L
3. **Analytics Tab**: Basic market analysis
4. **RED BUTTON**: Confirm trades before execution

## Project Structure

```
gallump2/
├── gallump/
│   ├── core/           # Trading logic
│   ├── api/            # REST API
│   └── frontend/       # React app
├── gallump_next/       # New modular architecture
└── mcp_ibkr_server.py  # Claude Desktop tools
```

## Safety Features
- No trades without confirmation
- Risk limits enforced
- All trades logged

## Requirements
- Python 3.9+
- Node.js 18+
- Interactive Brokers account
- Claude API key

## Support
This is experimental software. Use at your own risk.