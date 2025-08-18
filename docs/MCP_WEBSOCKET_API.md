# MCP Bridge WebSocket API Documentation

## Overview

The MCP Bridge provides WebSocket connectivity between the Gallump frontend and Claude Desktop's MCP capabilities. This document describes the WebSocket API for the bridge service running on port 5002.

## Connection

### WebSocket Endpoint
```
ws://localhost:5002/ws
```

### Connection Example (JavaScript)
```javascript
const ws = new WebSocket('ws://localhost:5002/ws');

ws.onopen = () => {
  console.log('Connected to MCP Bridge');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  handleMessage(data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected from MCP Bridge');
  // Implement reconnection logic
};
```

## Message Protocol

All messages are JSON-encoded with a `type` field indicating the message type.

## Client → Server Messages

### 1. Analysis Request
Analyze market data or answer questions using Claude Desktop's MCP tools.

**Request:**
```json
{
  "type": "analyze",
  "prompt": "What's the options flow for AAPL?",
  "symbols": ["AAPL", "SPY"],
  "id": 1705320600000
}
```

**Fields:**
- `type` (string, required): Must be "analyze"
- `prompt` (string, required): The analysis question
- `symbols` (array, optional): Stock symbols mentioned
- `id` (number, optional): Request identifier

**Response:**
```json
{
  "type": "analysis_result",
  "data": {
    "content": [{
      "text": "Based on the options flow analysis for AAPL..."
    }],
    "tools_used": ["get_options_chain", "analyze_flow"]
  }
}
```

### 2. Portfolio Request
Get current portfolio status and analysis.

**Request:**
```json
{
  "type": "get_portfolio"
}
```

**Response:**
```json
{
  "type": "portfolio_data",
  "data": {
    "content": [{
      "text": "Portfolio Summary:\n- Total Value: $50,000\n- P&L: +$2,500..."
    }],
    "positions": [
      {"symbol": "AAPL", "quantity": 100, "pnl": 500}
    ]
  }
}
```

### 3. Market Data Request
Get specific market data for a symbol.

**Request:**
```json
{
  "type": "get_market_data",
  "symbol": "AAPL"
}
```

**Fields:**
- `type` (string, required): Must be "get_market_data"
- `symbol` (string, required): Stock symbol

**Response:**
```json
{
  "type": "market_data",
  "symbol": "AAPL",
  "data": {
    "content": [{
      "text": "AAPL Market Data:\n- Price: $180.50\n- Volume: 45M..."
    }],
    "raw_data": {
      "last": 180.50,
      "volume": 45000000,
      "bid": 180.49,
      "ask": 180.51
    }
  }
}
```

## Server → Client Messages

### 1. Analysis Result
Response to an analysis request.

```json
{
  "type": "analysis_result",
  "data": {
    "content": [{
      "text": "Analysis text here..."
    }],
    "confidence": 0.85,
    "tools_used": ["tool1", "tool2"]
  }
}
```

### 2. Portfolio Data
Response to portfolio request.

```json
{
  "type": "portfolio_data",
  "data": {
    "content": [{
      "text": "Portfolio details..."
    }],
    "total_value": 50000,
    "total_pnl": 2500
  }
}
```

### 3. Market Data
Response to market data request.

```json
{
  "type": "market_data",
  "symbol": "AAPL",
  "data": {
    "content": [{
      "text": "Market data details..."
    }],
    "price": 180.50,
    "change": 2.5
  }
}
```

### 4. Error Message
Error response for any failed request.

```json
{
  "type": "error",
  "message": "Failed to get analysis from MCP",
  "details": "MCP process not responding",
  "request_id": 1705320600000
}
```

### 5. System Message
System status or informational messages.

```json
{
  "type": "system",
  "content": "🟢 Connected to Claude Desktop MCP",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Health Check Endpoint

### HTTP GET /health
Check the health of the MCP Bridge service.

**Request:**
```
GET http://localhost:5002/health
```

**Response:**
```json
{
  "status": "healthy",
  "mcp_running": true,
  "websocket_clients": 2
}
```

## Error Handling

### Connection Errors
If the WebSocket connection fails, the client should:
1. Display connection error to user
2. Attempt reconnection with exponential backoff
3. Max retry attempts: 5
4. Max delay: 30 seconds

### Message Errors
If a message fails to process:
1. Server sends error message with details
2. Client should display error to user
3. Client can retry with same request ID

## Rate Limiting

**Current Implementation:** None (⚠️ TODO)

**Recommended Limits:**
- 10 requests per minute per connection
- 1MB max message size
- 100 concurrent connections max

## Authentication

**Current Implementation:** None (⚠️ TODO)

**Recommended Implementation:**
```javascript
// Client should send auth on connection
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: localStorage.getItem('jwt_token')
  }));
};
```

## Example Usage

### Complete Client Implementation
```javascript
class MCPBridgeClient {
  constructor() {
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
  }

  connect() {
    this.ws = new WebSocket('ws://localhost:5002/ws');
    
    this.ws.onopen = () => {
      console.log('Connected to MCP Bridge');
      this.reconnectAttempts = 0;
      this.reconnectDelay = 1000;
    };
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    this.ws.onclose = () => {
      console.log('Disconnected from MCP Bridge');
      this.attemptReconnect();
    };
  }
  
  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => {
        console.log(`Reconnect attempt ${this.reconnectAttempts + 1}`);
        this.reconnectAttempts++;
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
        this.connect();
      }, this.reconnectDelay);
    }
  }
  
  sendAnalysis(prompt, symbols = []) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'analyze',
        prompt: prompt,
        symbols: symbols,
        id: Date.now()
      }));
    }
  }
  
  getPortfolio() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'get_portfolio'
      }));
    }
  }
  
  getMarketData(symbol) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'get_market_data',
        symbol: symbol
      }));
    }
  }
  
  handleMessage(data) {
    switch(data.type) {
      case 'analysis_result':
        this.onAnalysisResult(data.data);
        break;
      case 'portfolio_data':
        this.onPortfolioData(data.data);
        break;
      case 'market_data':
        this.onMarketData(data.symbol, data.data);
        break;
      case 'error':
        this.onError(data.message);
        break;
      case 'system':
        this.onSystemMessage(data.content);
        break;
    }
  }
  
  // Override these methods in your implementation
  onAnalysisResult(data) {}
  onPortfolioData(data) {}
  onMarketData(symbol, data) {}
  onError(message) {}
  onSystemMessage(content) {}
}
```

## Testing

### Using wscat
```bash
# Install wscat
npm install -g wscat

# Connect to bridge
wscat -c ws://localhost:5002/ws

# Send analysis request
{"type":"analyze","prompt":"What is AAPL doing?","symbols":["AAPL"]}

# Get portfolio
{"type":"get_portfolio"}

# Get market data
{"type":"get_market_data","symbol":"SPY"}
```

### Using curl for health check
```bash
curl http://localhost:5002/health
```

## Troubleshooting

### "Connection refused"
- Check if MCP Bridge is running: `ps aux | grep mcp_bridge`
- Start bridge: `python mcp_bridge_service.py`
- Check port 5002 is not in use: `lsof -i :5002`

### "MCP not responding"
- Check MCP server logs: `/tmp/mcp_enhanced.log`
- Restart MCP bridge service
- Verify IBKR Gateway is connected

### "No data received"
- Check if market is open
- Verify symbol is valid
- Check IBKR data subscriptions

---

**API Version**: 1.0.0
**Last Updated**: 2024-01-15
**Status**: ACTIVE WITH LIMITATIONS