# MCP API Specification

## Overview

This document specifies the API endpoints for the MCP (Model Context Protocol) integration that enables remote access to Claude Desktop's analysis capabilities.

## Base URL

```
Development: http://localhost:5001/api/mcp
Production: https://your-domain.com/api/mcp
```

## Authentication

All endpoints require JWT authentication token in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

## Endpoints

### 1. Send Query to Claude Desktop

**Endpoint**: `POST /api/mcp/query`

**Description**: Send an analysis query to Claude Desktop via MCP

**Request Headers**:
```
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

**Request Body**:
```json
{
  "query": "string",           // Required: The analysis question
  "context": {                 // Optional: Additional context
    "symbols": ["AAPL", "TSLA"],
    "include_positions": true,
    "include_history": true,
    "include_technicals": true,
    "include_options": true,
    "time_range": "1D"        // 1D, 1W, 1M, 3M, 1Y
  },
  "session_id": "string"       // Optional: For context continuity
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "analysis": {
    "content": "Based on my analysis of AAPL...",
    "confidence": 0.85,
    "key_points": [
      "Strong bullish momentum",
      "Options flow indicates institutional buying"
    ]
  },
  "tools_used": [
    {
      "tool": "get_options_chain",
      "symbol": "AAPL",
      "timestamp": "2024-01-15T10:30:00Z"
    },
    {
      "tool": "analyze_options_flow",
      "symbol": "AAPL",
      "timestamp": "2024-01-15T10:30:01Z"
    }
  ],
  "metadata": {
    "query_id": "q_123456",
    "session_id": "s_789012",
    "processing_time_ms": 1250,
    "data_points_analyzed": 47,
    "timestamp": "2024-01-15T10:30:02Z"
  }
}
```

**Error Response** (400/500):
```json
{
  "success": false,
  "error": "Claude Desktop not connected",
  "details": "The MCP server cannot reach Claude Desktop",
  "suggestions": [
    "Check if Claude Desktop is running",
    "Verify MCP server configuration",
    "Use Strategy Chat as alternative"
  ]
}
```

### 2. Check MCP Status

**Endpoint**: `GET /api/mcp/status`

**Description**: Check the status of MCP server and Claude Desktop connection

**Response** (200 OK):
```json
{
  "status": {
    "mcp_server": "running",           // running, stopped, error
    "claude_desktop": "connected",      // connected, disconnected, unknown
    "ibkr_connection": "active",       // active, inactive, error
    "last_heartbeat": "2024-01-15T10:30:00Z"
  },
  "capabilities": {
    "available_tools": 24,
    "max_context_size": "unlimited",
    "supports_streaming": true,
    "supports_images": false
  },
  "statistics": {
    "queries_today": 42,
    "avg_response_time_ms": 1500,
    "last_query": "2024-01-15T10:25:00Z",
    "uptime_seconds": 3600
  }
}
```

### 3. List Available Tools

**Endpoint**: `GET /api/mcp/tools`

**Description**: Get list of available MCP tools and their capabilities

**Response** (200 OK):
```json
{
  "tools": [
    {
      "name": "get_quote",
      "category": "market_data",
      "description": "Get real-time quote for a symbol",
      "parameters": {
        "symbol": "string (required)",
        "include_extended": "boolean (optional)"
      },
      "example": {
        "symbol": "AAPL",
        "include_extended": true
      }
    },
    {
      "name": "get_options_chain",
      "category": "options",
      "description": "Get full options chain with Greeks",
      "parameters": {
        "symbol": "string (required)",
        "expiration": "string (optional)",
        "strike_range": "number (optional)"
      }
    },
    {
      "name": "analyze_options_flow",
      "category": "analysis",
      "description": "Detect unusual options activity",
      "parameters": {
        "symbol": "string (required)",
        "min_volume": "number (optional)",
        "min_oi": "number (optional)"
      }
    }
  ],
  "categories": {
    "market_data": 6,
    "options": 5,
    "portfolio": 4,
    "analysis": 7,
    "scanner": 2
  },
  "total_tools": 24
}
```

### 4. Get Analysis History

**Endpoint**: `GET /api/mcp/history`

**Description**: Retrieve past Claude Desktop analyses

**Query Parameters**:
- `session_id` (optional): Filter by session
- `symbol` (optional): Filter by symbol
- `limit` (optional, default: 10): Number of results
- `offset` (optional, default: 0): Pagination offset

**Response** (200 OK):
```json
{
  "history": [
    {
      "query_id": "q_123456",
      "session_id": "s_789012",
      "query": "Analyze AAPL options flow",
      "summary": "Bullish unusual activity detected",
      "symbols": ["AAPL"],
      "tools_used": ["get_options_chain", "analyze_options_flow"],
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "total": 42,
    "limit": 10,
    "offset": 0,
    "has_more": true
  }
}
```

### 5. Stream Analysis (WebSocket)

**Endpoint**: `WS /api/mcp/stream`

**Description**: Stream real-time analysis from Claude Desktop

**Connection**:
```javascript
const ws = new WebSocket('ws://localhost:5001/api/mcp/stream');
ws.send(JSON.stringify({
  type: 'auth',
  token: 'jwt_token'
}));
```

**Message Types**:

**Query Message**:
```json
{
  "type": "query",
  "query": "Monitor AAPL options flow",
  "stream": true
}
```

**Progress Message** (from server):
```json
{
  "type": "progress",
  "tool": "get_options_chain",
  "status": "fetching",
  "progress": 0.5
}
```

**Data Message** (from server):
```json
{
  "type": "data",
  "content": "Detected large call sweep...",
  "partial": true
}
```

**Complete Message** (from server):
```json
{
  "type": "complete",
  "analysis": "Full analysis text...",
  "tools_used": ["get_options_chain"],
  "query_id": "q_123456"
}
```

### 6. Execute MCP Tool Directly

**Endpoint**: `POST /api/mcp/tool`

**Description**: Execute a specific MCP tool (for debugging/testing)

**Request Body**:
```json
{
  "tool": "get_quote",
  "parameters": {
    "symbol": "AAPL"
  }
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "result": {
    "symbol": "AAPL",
    "last": 180.50,
    "bid": 180.49,
    "ask": 180.51,
    "volume": 45000000,
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "execution_time_ms": 125
}
```

## Error Codes

| Code | Message | Description |
|------|---------|-------------|
| 400 | Bad Request | Invalid query or parameters |
| 401 | Unauthorized | Invalid or missing JWT token |
| 403 | Forbidden | User lacks permission for MCP |
| 404 | Not Found | Tool or resource not found |
| 408 | Request Timeout | Claude Desktop took too long |
| 500 | Internal Server Error | Server error |
| 502 | Bad Gateway | MCP server unreachable |
| 503 | Service Unavailable | Claude Desktop not connected |

## Rate Limiting

- **Queries**: 60 per minute per user
- **Status checks**: 120 per minute per user
- **Tool execution**: 30 per minute per user

Headers returned:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1705320600
```

## Best Practices

### 1. Context Management
```javascript
// Include relevant context for better analysis
const query = {
  query: "Should I hedge my AAPL position?",
  context: {
    symbols: ["AAPL"],
    include_positions: true,  // Claude sees your position
    include_history: true     // Claude sees recent trades
  }
};
```

### 2. Session Continuity
```javascript
// Maintain conversation context
let sessionId = null;

async function askClaude(question) {
  const response = await fetch('/api/mcp/query', {
    method: 'POST',
    body: JSON.stringify({
      query: question,
      session_id: sessionId  // Pass previous session
    })
  });
  
  const data = await response.json();
  sessionId = data.metadata.session_id;  // Store for next query
  return data;
}
```

### 3. Error Handling
```javascript
try {
  const analysis = await queryMCP(question);
} catch (error) {
  if (error.code === 503) {
    // Claude Desktop not available, fallback
    console.log("Switching to Strategy Chat...");
    const fallback = await queryStrategyAPI(question);
  }
}
```

### 4. Tool Usage Monitoring
```javascript
// Display which tools Claude is using
response.tools_used.forEach(tool => {
  console.log(`Claude used: ${tool.tool} for ${tool.symbol}`);
});
```

## Testing

### Test Query
```bash
# Get auth token
TOKEN=$(curl -s -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password": "Snoop23"}' | jq -r .token)

# Send analysis query
curl -X POST http://localhost:5001/api/mcp/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze unusual options activity for AAPL",
    "context": {
      "symbols": ["AAPL"],
      "include_options": true
    }
  }'
```

### Check Status
```bash
curl -X GET http://localhost:5001/api/mcp/status \
  -H "Authorization: Bearer $TOKEN"
```

### List Tools
```bash
curl -X GET http://localhost:5001/api/mcp/tools \
  -H "Authorization: Bearer $TOKEN"
```

## Frontend Integration Example

```javascript
// ClaudeDesktopService.js
class ClaudeDesktopService {
  async query(question, context = {}) {
    const response = await fetch('/api/mcp/query', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        query: question,
        context: context,
        session_id: this.sessionId
      })
    });
    
    if (!response.ok) {
      throw new Error(`MCP Error: ${response.statusText}`);
    }
    
    const data = await response.json();
    this.sessionId = data.metadata.session_id;
    return data;
  }
  
  async getStatus() {
    const response = await fetch('/api/mcp/status', {
      headers: {
        'Authorization': `Bearer ${this.token}`
      }
    });
    return response.json();
  }
}
```

## Migration from Analytics Tab

The current Analytics tab will be replaced with the Claude Desktop tab:

1. **Before**: Analytics tab tried to use MCP modules directly
2. **After**: Claude Desktop tab uses actual Claude Desktop via MCP

No data migration needed - this is a complete replacement.

---

**Document Version**: 1.0.0
**Last Updated**: 2024-01-15
**Status**: DRAFT - Awaiting Implementation