# Setting Up Claude Desktop with Gallump MCP

## What is MCP?
MCP (Model Context Protocol) allows Claude Desktop to access external tools and data sources. Your Gallump system has an MCP server that can provide IBKR market data to Claude Desktop.

## Setup Instructions

### 1. Locate Claude Desktop Config
Find your Claude Desktop configuration file:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

### 2. Add Gallump MCP Server
Edit the config file and add:

```json
{
  "mcpServers": {
    "gallump-trading": {
      "command": "python",
      "args": ["/Users/schmoll/Desktop/Gallump/mcp_enhanced_claude.py"],
      "env": {
        "PYTHONPATH": "/Users/schmoll/Desktop/Gallump"
      }
    }
  }
}
```

### 3. Restart Claude Desktop
Close and reopen Claude Desktop

### 4. Test in Claude Desktop
In Claude Desktop (not the web), type:
- "Use the gallump-trading tools to analyze my portfolio"
- "Get current price for AAPL using gallump-trading"
- "Run a market scanner for top gainers"

## How It Works
```
You in Claude Desktop → Claude AI → MCP Server → IBKR → Market Data
                           ↓
                    AI Analysis with full context
```

## Available MCP Tools in Claude Desktop
Once configured, Claude Desktop will have access to:
- `enhanced_portfolio_analysis` - Analyze your portfolio
- `enhanced_symbol_analysis` - Deep dive on specific stocks
- `enhanced_market_analysis` - Market overview and trends
- `enhanced_options_analysis` - Options strategies
- `run_scanner` - Find trading opportunities
- `get_market_depth` - Level 2 data
- `get_news_feed` - Real-time news

## Important Notes
1. This gives Claude Desktop LIVE access to your IBKR account
2. Claude Desktop will be able to SEE your positions but NOT execute trades
3. The MCP server is READ-ONLY - it cannot place orders
4. Use the Strategy Chat in the web app for actual trading

## Troubleshooting
If Claude Desktop doesn't see the tools:
1. Check the config file syntax (valid JSON)
2. Ensure Python path is correct
3. Make sure IBKR Gateway/TWS is running
4. Check Claude Desktop logs for errors