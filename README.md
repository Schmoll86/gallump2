# Gallump2 - AI-Powered Trading Assistant

A modular trading system with AI-powered strategy generation and IBKR integration.

## Features

- **AI Strategy Generation**: Claude AI generates trading strategies based on market analysis
- **RED BUTTON Confirmation**: Multi-stage confirmation for trade execution
- **Portfolio Management**: Real-time portfolio tracking with P&L
- **IBKR Integration**: Direct connection to Interactive Brokers
- **Modular Architecture**: Clean separation of concerns with single-responsibility modules

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Interactive Brokers Gateway/TWS
- Anthropic API key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gallump2.git
cd gallump2
```

2. Set up Python environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up frontend:
```bash
cd gallump/frontend
npm install
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

### Running the Application

1. Start IBKR Gateway/TWS (port 4001 for live, 4002 for paper)

2. Start the backend:
```bash
python -m gallump.api.server
```

3. Start the frontend:
```bash
cd gallump/frontend
npm run dev
```

4. Open http://localhost:3000 in your browser

## Architecture

### Modular Design
- **Core**: Connection management, types
- **Market Data**: Price fetching
- **Execution**: Order validation and execution
- **Portfolio**: Position tracking
- **Strategy**: AI-powered strategy generation

### MCP Integration
Includes MCP server for Claude Desktop integration (mcp_ibkr_server.py)

## License

MIT