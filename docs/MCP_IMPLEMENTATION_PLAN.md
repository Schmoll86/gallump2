# MCP Implementation Plan - Detailed File Changes

## Executive Summary
Claude Desktop will implement these changes to complete the MCP integration. Each section specifies exact files and changes needed.

---

## PHASE 1: Critical Fixes (Do First!)

### 📄 File: `/mcp_bridge_service.py`

#### Change 1: Fix WeakSet Issue
**Line 33** - Replace:
```python
self.websockets = weakref.WeakSet()
```
With:
```python
self.websockets = set()
```

#### Change 2: Add Process Monitoring
**After line 89** - Add new method:
```python
async def monitor_mcp_process(self):
    """Monitor MCP process and restart if it dies"""
    while self.running:
        if self.mcp_process and self.mcp_process.returncode is not None:
            logger.error(f"MCP process died with code {self.mcp_process.returncode}, restarting...")
            await self.start_mcp_server()
        await asyncio.sleep(5)
```

**In start() method around line 253** - Add:
```python
async def start(self):
    """Start the bridge service"""
    self.running = True
    await self.start_mcp_server()
    
    # Start monitoring task
    asyncio.create_task(self.monitor_mcp_process())
    
    # Rest of existing code...
```

#### Change 3: Add Simple Cache
**After line 31** - Add:
```python
def __init__(self):
    self.app = web.Application()
    self.websockets = set()  # Changed from WeakSet
    self.mcp_process: Optional[subprocess.Popen] = None
    self.cache = {}  # Simple cache
    self.running = False
    self.setup_routes()
    self.setup_cors()

def get_cached(self, key: str):
    """Get cached value if not expired"""
    if key in self.cache:
        value, expiry = self.cache[key]
        if time.time() < expiry:
            return value
    return None

def set_cached(self, key: str, value: Any, ttl: int = 60):
    """Cache value with TTL in seconds"""
    self.cache[key] = (value, time.time() + ttl)
```

**Add import at top**:
```python
import time
```

---

## PHASE 2: MCP Server Tool Enhancements

### 📄 File: `/mcp_enhanced_claude.py`

#### Change 1: Add New Tool Definitions
**In list_tools() method around line 144** - Add after existing tools:
```python
{
    'name': 'run_scanner',
    'description': 'Run IBKR market scanner to find stocks matching criteria (top gainers, most active, unusual volume, etc.)',
    'inputSchema': {
        'type': 'object',
        'properties': {
            'scanner_type': {
                'type': 'string',
                'description': 'Scanner type: TOP_PERC_GAIN, TOP_PERC_LOSE, MOST_ACTIVE, HOT_BY_VOLUME, TOP_TRADE_COUNT',
                'enum': ['TOP_PERC_GAIN', 'TOP_PERC_LOSE', 'MOST_ACTIVE', 'HOT_BY_VOLUME', 'TOP_TRADE_COUNT']
            },
            'limit': {
                'type': 'number',
                'description': 'Number of results (default 20)',
                'default': 20
            }
        },
        'required': ['scanner_type']
    }
},
{
    'name': 'get_full_options_chain',
    'description': 'Get complete options chain with Greeks, IV, and unusual activity for a symbol',
    'inputSchema': {
        'type': 'object',
        'properties': {
            'symbol': {'type': 'string', 'description': 'Stock symbol'},
            'include_greeks': {'type': 'boolean', 'default': True},
            'min_volume': {'type': 'number', 'description': 'Minimum volume filter', 'default': 0}
        },
        'required': ['symbol']
    }
},
{
    'name': 'get_market_depth',
    'description': 'Get Level 2 order book data showing bid/ask depth',
    'inputSchema': {
        'type': 'object',
        'properties': {
            'symbol': {'type': 'string', 'description': 'Stock symbol'},
            'levels': {'type': 'number', 'description': 'Number of price levels', 'default': 10}
        },
        'required': ['symbol']
    }
},
{
    'name': 'get_news_feed',
    'description': 'Get recent news for symbol or market with sentiment analysis',
    'inputSchema': {
        'type': 'object',
        'properties': {
            'symbol': {'type': 'string', 'description': 'Optional symbol filter'},
            'hours': {'type': 'number', 'description': 'Hours of history', 'default': 24},
            'include_sentiment': {'type': 'boolean', 'default': True}
        }
    }
},
{
    'name': 'get_historical_data',
    'description': 'Get historical price data for technical analysis',
    'inputSchema': {
        'type': 'object',
        'properties': {
            'symbol': {'type': 'string', 'description': 'Stock symbol'},
            'period': {'type': 'string', 'description': '1d, 1w, 1m, 3m, 1y', 'default': '1m'},
            'bar_size': {'type': 'string', 'description': '1min, 5min, 15min, 1hour, 1day', 'default': '1day'}
        },
        'required': ['symbol']
    }
}
```

#### Change 2: Implement Tool Handlers
**In call_tool() method around line 210** - Add cases for new tools:
```python
elif tool_name == 'run_scanner':
    return self._run_scanner(arguments)
elif tool_name == 'get_full_options_chain':
    return self._get_full_options_chain(arguments)
elif tool_name == 'get_market_depth':
    return self._get_market_depth(arguments)
elif tool_name == 'get_news_feed':
    return self._get_news_feed(arguments)
elif tool_name == 'get_historical_data':
    return self._get_historical_data(arguments)
```

#### Change 3: Add Implementation Methods
**After the call_tool() method** - Add:
```python
def _run_scanner(self, args):
    """Run IBKR scanner"""
    scanner_type = args.get('scanner_type', 'TOP_PERC_GAIN')
    limit = args.get('limit', 20)
    
    try:
        if IBKR_AVAILABLE:
            from gallump.core.scanner import Scanner
            from gallump.core.broker import Broker
            
            broker = Broker()
            if broker.connect():
                scanner = Scanner(broker=broker)
                results = scanner.scan(scanner_type, limit=limit)
                
                # Format results
                output = f"Scanner Results: {scanner_type}\\n\\n"
                for i, item in enumerate(results[:limit], 1):
                    output += f"{i}. {item.get('symbol', 'N/A')}: "
                    output += f"Change: {item.get('change_percent', 0):.2f}% "
                    output += f"Volume: {item.get('volume', 0):,}\\n"
                
                return {'content': [{'text': output}]}
        
        # Fallback to sample data
        return {'content': [{'text': 'Scanner not available - market closed'}]}
        
    except Exception as e:
        logger.error(f"Scanner error: {e}")
        return {'content': [{'text': f'Scanner error: {str(e)}'}]}

def _get_full_options_chain(self, args):
    """Get complete options chain with Greeks"""
    symbol = args['symbol']
    include_greeks = args.get('include_greeks', True)
    
    try:
        if IBKR_AVAILABLE:
            from gallump.core.broker import Broker
            
            broker = Broker()
            if broker.connect():
                # Get options chain
                chain = broker.get_options_chain(symbol)
                
                if not chain:
                    return {'content': [{'text': f'No options data for {symbol}'}]}
                
                # Format output
                output = f"Options Chain for {symbol}\\n\\n"
                
                # Group by expiration
                by_expiry = {}
                for option in chain:
                    expiry = option.get('expiration', 'Unknown')
                    if expiry not in by_expiry:
                        by_expiry[expiry] = []
                    by_expiry[expiry].append(option)
                
                for expiry in sorted(by_expiry.keys())[:3]:  # Show first 3 expirations
                    output += f"\\nExpiration: {expiry}\\n"
                    output += "-" * 40 + "\\n"
                    
                    for opt in by_expiry[expiry][:10]:  # Show first 10 strikes
                        output += f"{opt['strike']} {opt['type']}: "
                        output += f"Bid: {opt.get('bid', 0):.2f} "
                        output += f"Ask: {opt.get('ask', 0):.2f} "
                        
                        if include_greeks and 'greeks' in opt:
                            output += f"Delta: {opt['greeks'].get('delta', 0):.3f} "
                            output += f"IV: {opt['greeks'].get('iv', 0):.2%}"
                        
                        output += "\\n"
                
                return {'content': [{'text': output}]}
        
        return {'content': [{'text': 'Options data not available'}]}
        
    except Exception as e:
        logger.error(f"Options chain error: {e}")
        return {'content': [{'text': f'Options error: {str(e)}'}]}

def _get_market_depth(self, args):
    """Get Level 2 market depth"""
    symbol = args['symbol']
    levels = args.get('levels', 10)
    
    try:
        if IBKR_AVAILABLE:
            from gallump.core.broker import Broker
            
            broker = Broker()
            if broker.connect():
                # Get market depth
                depth = broker.reqMktDepth(symbol, numRows=levels)
                
                output = f"Market Depth for {symbol}\\n\\n"
                output += "BIDS:\\n"
                for bid in depth.get('bids', [])[:levels]:
                    output += f"  ${bid['price']:.2f} x {bid['size']:,}\\n"
                
                output += "\\nASKS:\\n"
                for ask in depth.get('asks', [])[:levels]:
                    output += f"  ${ask['price']:.2f} x {ask['size']:,}\\n"
                
                return {'content': [{'text': output}]}
        
        return {'content': [{'text': 'Market depth not available'}]}
        
    except Exception as e:
        logger.error(f"Market depth error: {e}")
        return {'content': [{'text': f'Market depth error: {str(e)}'}]}

def _get_news_feed(self, args):
    """Get news with sentiment"""
    symbol = args.get('symbol')
    hours = args.get('hours', 24)
    
    try:
        # For now, return from database
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        query = "SELECT * FROM annotations WHERE note_type = 'news' "
        if symbol:
            query += f"AND related_symbol = '{symbol}' "
        query += "ORDER BY created_at DESC LIMIT 10"
        
        c.execute(query)
        news = c.fetchall()
        conn.close()
        
        if news:
            output = f"Recent News"
            if symbol:
                output += f" for {symbol}"
            output += ":\\n\\n"
            
            for item in news:
                output += f"• {item[2]}\\n"  # text field
                output += f"  {item[7]}\\n\\n"  # timestamp
        else:
            output = "No recent news available"
        
        return {'content': [{'text': output}]}
        
    except Exception as e:
        logger.error(f"News error: {e}")
        return {'content': [{'text': f'News error: {str(e)}'}]}

def _get_historical_data(self, args):
    """Get historical price data"""
    symbol = args['symbol']
    period = args.get('period', '1m')
    bar_size = args.get('bar_size', '1day')
    
    try:
        if IBKR_AVAILABLE:
            from gallump.core.broker import Broker
            
            broker = Broker()
            if broker.connect():
                # Get historical data
                bars = broker.get_historical_data(symbol, period, bar_size)
                
                if not bars:
                    return {'content': [{'text': f'No historical data for {symbol}'}]}
                
                output = f"Historical Data for {symbol} ({period})\\n\\n"
                
                # Show last 10 bars
                for bar in bars[-10:]:
                    output += f"{bar['date']}: "
                    output += f"O:{bar['open']:.2f} "
                    output += f"H:{bar['high']:.2f} "
                    output += f"L:{bar['low']:.2f} "
                    output += f"C:{bar['close']:.2f} "
                    output += f"V:{bar['volume']:,}\\n"
                
                return {'content': [{'text': output}]}
        
        return {'content': [{'text': 'Historical data not available'}]}
        
    except Exception as e:
        logger.error(f"Historical data error: {e}")
        return {'content': [{'text': f'Historical data error: {str(e)}'}]}
```

---

## PHASE 3: Cache Layer Enhancement

### 📄 File: `/gallump/core/cache.py`

#### Add Scanner Caching Methods
**After existing methods** - Add:
```python
def cache_scanner_results(self, scanner_type: str, results: List, ttl: int = 300):
    """Cache scanner results for 5 minutes"""
    key = f"scanner:{scanner_type}"
    self.set(key, results, expire_seconds=ttl)
    logger.info(f"Cached {len(results)} results for scanner {scanner_type}")

def get_cached_scanner(self, scanner_type: str) -> Optional[List]:
    """Get cached scanner results if available"""
    key = f"scanner:{scanner_type}"
    return self.get(key)

def cache_options_chain(self, symbol: str, chain: Dict, ttl: int = 300):
    """Cache options chain for 5 minutes"""
    key = f"options:{symbol}"
    self.set(key, chain, expire_seconds=ttl)

def get_cached_options(self, symbol: str) -> Optional[Dict]:
    """Get cached options chain if available"""
    key = f"options:{symbol}"
    return self.get(key)

def cache_market_depth(self, symbol: str, depth: Dict, ttl: int = 30):
    """Cache market depth for 30 seconds"""
    key = f"depth:{symbol}"
    self.set(key, depth, expire_seconds=ttl)

def get_cached_depth(self, symbol: str) -> Optional[Dict]:
    """Get cached market depth if available"""
    key = f"depth:{symbol}"
    return self.get(key)

def cache_news(self, key: str, news: List, ttl: int = 600):
    """Cache news for 10 minutes"""
    cache_key = f"news:{key}"
    self.set(cache_key, news, expire_seconds=ttl)

def get_cached_news(self, key: str) -> Optional[List]:
    """Get cached news if available"""
    cache_key = f"news:{key}"
    return self.get(cache_key)
```

---

## PHASE 4: Frontend Enhancement

### 📄 File: `/gallump/frontend/src/components/ClaudeDesktopTab.jsx`

#### Add Data Formatters
**After line 115** - Add new formatting functions:
```javascript
const formatScannerResults = (data) => {
  if (!data || !data.content) return "No scanner results";
  
  // If it's already formatted text, return as is
  if (data.content[0] && data.content[0].text) {
    return data.content[0].text;
  }
  
  // Otherwise format the raw data
  let output = "📊 Scanner Results:\\n\\n";
  if (data.results && Array.isArray(data.results)) {
    data.results.forEach((item, idx) => {
      output += `${idx + 1}. ${item.symbol}: `;
      output += `${item.change_percent > 0 ? '📈' : '📉'} ${item.change_percent}% `;
      output += `Vol: ${item.volume?.toLocaleString() || 'N/A'}\\n`;
    });
  }
  return output;
};

const formatOptionsChain = (data) => {
  if (!data || !data.content) return "No options data";
  
  if (data.content[0] && data.content[0].text) {
    return data.content[0].text;
  }
  
  let output = "📊 Options Chain:\\n\\n";
  // Format options data if raw
  return output;
};

const formatMarketDepth = (data) => {
  if (!data || !data.content) return "No market depth";
  
  if (data.content[0] && data.content[0].text) {
    return data.content[0].text;
  }
  
  let output = "📊 Market Depth:\\n\\n";
  // Format depth data if raw
  return output;
};

const formatNewsItems = (data) => {
  if (!data || !data.content) return "No news available";
  
  if (data.content[0] && data.content[0].text) {
    return data.content[0].text;
  }
  
  let output = "📰 Recent News:\\n\\n";
  // Format news if raw
  return output;
};
```

#### Update Message Handling
**In handleBridgeMessage() around line 70** - Add cases:
```javascript
case 'scanner_results':
  setMessages(prev => [...prev, {
    type: 'assistant',
    content: formatScannerResults(data.data)
  }]);
  break;
  
case 'options_chain':
  setMessages(prev => [...prev, {
    type: 'assistant',
    content: formatOptionsChain(data.data)
  }]);
  break;
  
case 'market_depth':
  setMessages(prev => [...prev, {
    type: 'assistant',
    content: formatMarketDepth(data.data)
  }]);
  break;
  
case 'news_feed':
  setMessages(prev => [...prev, {
    type: 'assistant',
    content: formatNewsItems(data.data)
  }]);
  break;
```

#### Add Quick Action Buttons
**After line 250 (in the input area)** - Add:
```javascript
{/* Quick action buttons */}
<div className="flex gap-2 mt-2">
  <button
    onClick={() => sendMessage('Run top gainers scanner')}
    className="px-3 py-1 bg-purple-700 hover:bg-purple-600 text-white text-sm rounded"
  >
    🔍 Top Gainers
  </button>
  <button
    onClick={() => sendMessage('Show my portfolio')}
    className="px-3 py-1 bg-purple-700 hover:bg-purple-600 text-white text-sm rounded"
  >
    📊 Portfolio
  </button>
  <button
    onClick={() => sendMessage('Get market overview')}
    className="px-3 py-1 bg-purple-700 hover:bg-purple-600 text-white text-sm rounded"
  >
    📈 Market
  </button>
</div>
```

---

## PHASE 5: Documentation Updates

### 📄 File: `/README.md`

#### Add MCP Section
**After the Features section** - Add:
```markdown
## 🧠 Claude Desktop Integration (MCP Tab)

The purple MCP tab provides free, unlimited analysis using Claude Desktop:

### Starting the MCP Bridge
```bash
# In a separate terminal
python mcp_bridge_service.py
```

### Available Commands
- **Scanners**: "Run top gainers scanner", "Show most active stocks"
- **Options**: "Get AAPL options chain with Greeks"
- **Market Depth**: "Show Level 2 for SPY"
- **News**: "Get latest news for TSLA"
- **Historical**: "Show AAPL price history"

### Key Differences
- **MCP Tab (Purple)**: Free analysis via Claude Desktop, read-only
- **Strategy Chat (Blue)**: Trade execution via API, costs tokens
```

### 📄 File: `/CLAUDE.md`

#### Add MCP Flow
**In the Data Flow Rules section** - Add:
```markdown
**MCP Analytics Flow (Read-Only)**:
```
User → MCP Tab → WebSocket (5002) → Bridge → MCP Server → IBKR
                                                 ↓
                                          Claude Desktop
```
- NO execution path from MCP
- Separate from Strategy Chat flow
- Uses Claude Desktop, not API
```

---

## PHASE 6: Optional Database Enhancement

### 📄 File: `/gallump/core/storage.py`

#### Add Scanner History Table
**In __init__() method around line 127** - Add:
```python
CREATE TABLE IF NOT EXISTS scanner_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scanner_type TEXT NOT NULL,
    symbol TEXT NOT NULL,
    change_percent REAL,
    volume INTEGER,
    rank INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_scanner_timestamp (timestamp),
    INDEX idx_scanner_symbol (symbol)
)
```

#### Add Methods
**After existing methods** - Add:
```python
def save_scanner_result(self, scanner_type: str, symbol: str, 
                        change_percent: float, volume: int, rank: int):
    """Save scanner result for history tracking"""
    conn = self.get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO scanner_results 
        (scanner_type, symbol, change_percent, volume, rank)
        VALUES (?, ?, ?, ?, ?)
    """, (scanner_type, symbol, change_percent, volume, rank))
    conn.commit()
    conn.close()

def get_scanner_history(self, scanner_type: str = None, days: int = 7) -> List[Dict]:
    """Get scanner history for pattern analysis"""
    conn = self.get_connection()
    c = conn.cursor()
    
    query = """
        SELECT * FROM scanner_results 
        WHERE timestamp > datetime('now', '-{} days')
    """.format(days)
    
    if scanner_type:
        query += f" AND scanner_type = '{scanner_type}'"
    
    query += " ORDER BY timestamp DESC"
    
    c.execute(query)
    results = c.fetchall()
    conn.close()
    
    return [self._row_to_dict(c, row) for row in results]
```

---

## Testing Checklist

After implementation, test these commands in the MCP tab:

1. ✅ "Run top gainers scanner"
2. ✅ "Show AAPL options chain with Greeks"
3. ✅ "Get market depth for SPY"
4. ✅ "Show latest news"
5. ✅ "Get TSLA historical data"
6. ✅ Kill mcp_bridge_service.py and verify auto-restart
7. ✅ Request same data twice to test caching

---

## Files Summary

**Files to Modify (8 total):**
1. `/mcp_bridge_service.py` - Add monitoring, caching, fix WeakSet
2. `/mcp_enhanced_claude.py` - Add 5 new tools and implementations
3. `/gallump/core/cache.py` - Add caching methods
4. `/gallump/frontend/src/components/ClaudeDesktopTab.jsx` - Add formatters
5. `/README.md` - Add MCP documentation
6. `/CLAUDE.md` - Add MCP flow
7. `/gallump/core/storage.py` - Add scanner history (optional)
8. `/gallump/core/broker.py` - Verify methods exist (no changes needed)

**Files to Leave Alone:**
- `brain.py` - Already gets scanner data through Context
- `context_builder.py` - Already includes scanner_alerts
- All Strategy Chat components - Working fine

---

**Give this document to Claude Desktop to implement step by step!**