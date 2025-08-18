# MCP Implementation Tasks for Claude Desktop

## Priority 1: Critical Fixes (Do These First!)

### 1. Fix WeakSet Issue in mcp_bridge_service.py
**Line 33**: Change `self.websockets = weakref.WeakSet()` to `self.websockets = set()`
**Line 113**: Add proper cleanup in finally block
```python
finally:
    self.websockets.discard(ws)  # This already exists, just verify it works
```

### 2. Add Process Monitoring for MCP Server
In `mcp_bridge_service.py`, add monitoring for the subprocess:
```python
async def monitor_mcp_process(self):
    """Monitor MCP process and restart if it dies"""
    while True:
        if self.mcp_process and self.mcp_process.returncode is not None:
            logger.error("MCP process died, restarting...")
            await self.start_mcp_server()
        await asyncio.sleep(5)
```

### 3. Add Basic Caching Layer
Create simple in-memory cache with TTL:
```python
class SimpleCache:
    def __init__(self):
        self.cache = {}
    
    def get(self, key):
        if key in self.cache:
            data, expiry = self.cache[key]
            if time.time() < expiry:
                return data
        return None
    
    def set(self, key, value, ttl=60):
        self.cache[key] = (value, time.time() + ttl)
```

## Priority 2: Add IBKR Tools to MCP Server

### Update mcp_enhanced_claude.py

Add these tool definitions to `list_tools()`:

```python
{
    'name': 'run_scanner',
    'description': 'Run IBKR market scanner (top gainers, unusual volume, etc.)',
    'inputSchema': {
        'type': 'object',
        'properties': {
            'scanner_type': {'type': 'string', 'description': 'Scanner type: TOP_PERC_GAIN, MOST_ACTIVE, etc.'},
            'limit': {'type': 'number', 'description': 'Number of results'}
        },
        'required': ['scanner_type']
    }
},
{
    'name': 'get_options_chain_full',
    'description': 'Get complete options chain with Greeks',
    'inputSchema': {
        'type': 'object',
        'properties': {
            'symbol': {'type': 'string', 'description': 'Stock symbol'},
            'expiry': {'type': 'string', 'description': 'Optional specific expiry date'}
        },
        'required': ['symbol']
    }
},
{
    'name': 'get_market_depth',
    'description': 'Get Level 2 order book data',
    'inputSchema': {
        'type': 'object',
        'properties': {
            'symbol': {'type': 'string', 'description': 'Stock symbol'},
            'levels': {'type': 'number', 'description': 'Number of price levels'}
        },
        'required': ['symbol']
    }
},
{
    'name': 'get_news',
    'description': 'Get news for symbol or market',
    'inputSchema': {
        'type': 'object',
        'properties': {
            'symbol': {'type': 'string', 'description': 'Optional symbol filter'},
            'hours': {'type': 'number', 'description': 'Hours of history'}
        }
    }
}
```

### Implement the tools in call_tool():

```python
elif tool_name == 'run_scanner':
    scanner_type = arguments.get('scanner_type', 'TOP_PERC_GAIN')
    limit = arguments.get('limit', 20)
    
    broker = Broker()
    if broker.connect():
        results = broker.scanner.run_scan(scanner_type, limit)
        return self._format_scanner_results(results)
        
elif tool_name == 'get_options_chain_full':
    symbol = arguments['symbol']
    
    broker = Broker()
    if broker.connect():
        chain = broker.get_options_chain(symbol)
        # Include Greeks calculation
        for option in chain:
            option['greeks'] = broker.calculate_greeks(option)
        return self._format_options_chain(chain)
```

## Priority 3: Update Frontend for Rich Data Display

### Update ClaudeDesktopTab.jsx

Add formatters for new data types:

```javascript
const formatScannerResults = (data) => {
  if (!data.results) return "No scanner results";
  
  let output = "Scanner Results:\n\n";
  data.results.forEach(item => {
    output += `${item.symbol}: ${item.change}% | Vol: ${item.volume}\n`;
  });
  return output;
};

const formatOptionsChain = (data) => {
  if (!data.chain) return "No options data";
  
  let output = "Options Chain:\n\n";
  data.chain.forEach(option => {
    output += `${option.strike} ${option.type}: `;
    output += `Bid: ${option.bid} Ask: ${option.ask} `;
    output += `Delta: ${option.delta} IV: ${option.iv}\n`;
  });
  return output;
};
```

## Priority 4: Clean Up Deprecated Code

### Remove or Rename:
1. **DON'T DELETE YET** - Keep `AnalyticsChat.jsx` as it's still used by scanner tab
2. **RENAME** - Change "scanner" tab to "API Analytics" to differentiate from MCP
3. **COMMENT** - Add clear comments about which is which

## Priority 5: Documentation Updates

### Update README.md
Add section about MCP tab:
```markdown
## 🧠 Claude Desktop Integration (MCP Tab)

Access Claude Desktop's powerful analysis from your phone:

1. **Start MCP Bridge**: `python mcp_bridge_service.py`
2. **Open App**: Navigate to purple MCP tab
3. **Ask Questions**: 
   - "Run top gainers scanner"
   - "Show AAPL options chain with Greeks"
   - "Get market depth for SPY"

**Note**: MCP tab is READ-ONLY analysis via Claude Desktop (free, unlimited context)
Different from Strategy Chat (blue tab) which can execute trades.
```

### Update CLAUDE.md
Add MCP bridge to data flow:
```markdown
## MCP Analytics Flow (Read-Only)
User Phone → MCP Tab → WebSocket (5002) → MCP Bridge → Claude Desktop → IBKR
```

## Checklist for Claude Desktop to Implement:

- [ ] Fix WeakSet to regular set()
- [ ] Add process monitoring
- [ ] Add basic caching
- [ ] Add scanner tool to MCP
- [ ] Add full options chain tool
- [ ] Add market depth tool
- [ ] Add news tool
- [ ] Update frontend formatters
- [ ] Update README.md
- [ ] Update CLAUDE.md
- [ ] Test each new tool
- [ ] Verify WebSocket stability

## Testing After Implementation:

1. **Test Scanner**: "Run top gainers scanner"
2. **Test Options**: "Show AAPL options chain"
3. **Test Market Depth**: "Get Level 2 for SPY"
4. **Test News**: "Show latest news for TSLA"
5. **Test Cache**: Request same data twice, should be faster
6. **Test Recovery**: Kill MCP process, should auto-restart

## What NOT to Change:

1. **Keep authentication as-is** (Tailscale is enough)
2. **Skip rate limiting** (single user)
3. **Don't add metrics yet** (not needed)
4. **Keep existing Strategy Chat** (it works fine)
5. **Don't modify broker.py** (already has the methods)

---

**Give this document to Claude Desktop and have it work through the checklist!**