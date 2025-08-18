# MCP Tools Enhancement Plan

## Current State vs. Desired State

### What We Have Now
The MCP server has 4 basic tools that mostly query the database:
- Portfolio analysis (database query)
- Symbol analysis (basic market data)
- Market analysis (multiple symbols)
- Options analysis (basic chain)

### What We Need for Full IBKR Exploitation

## Required MCP Tool Additions

### 1. Scanner Tools
```python
def run_ibkr_scanner(scanner_type, filters):
    """
    Access IBKR's 50+ scanners:
    - TOP_PERC_GAIN - Top gainers
    - TOP_PERC_LOSE - Top losers  
    - MOST_ACTIVE - Highest volume
    - HOT_BY_VOLUME - Unusual volume
    - TOP_TRADE_COUNT - Most trades
    - OPTION_VOLUME_MOST_ACTIVE - Options activity
    - HIGH_VS_13W_HL - Near 52-week high
    - LOW_VS_13W_HL - Near 52-week low
    """
```

### 2. Options Greeks & Flow
```python
def get_options_with_greeks(symbol):
    """
    Get FULL options data:
    - All expirations
    - All strikes
    - Real-time Greeks (delta, gamma, theta, vega, rho)
    - Implied volatility
    - Open interest
    - Volume
    - Unusual activity detection
    """
```

### 3. Level 2 Market Depth
```python
def get_market_depth(symbol, levels=10):
    """
    Get order book:
    - Bid levels with size
    - Ask levels with size
    - Cumulative volume
    - Price pressure analysis
    """
```

### 4. News & Sentiment
```python
def get_news_feed(symbol=None, hours=24):
    """
    Get IBKR news:
    - Real-time news headlines
    - Full articles
    - Sentiment scoring
    - Source credibility
    - Related symbols
    """
```

### 5. Historical Data
```python
def get_historical_bars(symbol, period, bar_size):
    """
    Get historical data:
    - 1min, 5min, 15min, 1hour, 1day bars
    - OHLCV data
    - Up to 1 year history
    - After-hours data
    """
```

### 6. Fundamentals
```python
def get_fundamentals(symbol):
    """
    Get company data:
    - Market cap
    - P/E ratio
    - EPS
    - Revenue
    - Earnings dates
    - Dividend info
    """
```

### 7. Technical Indicators
```python
def calculate_technicals(symbol, indicators):
    """
    Calculate indicators:
    - Moving averages (SMA, EMA)
    - RSI
    - MACD
    - Bollinger Bands
    - Volume indicators
    - Support/Resistance
    """
```

## Implementation Priority

### Phase 1 (High Value, Easy)
1. **Scanner Access** - Just need to call broker.run_scanner()
2. **Full Options Chain** - broker.get_options_chain() with Greeks
3. **News Feed** - broker.get_news()

### Phase 2 (High Value, Medium)
4. **Level 2 Data** - broker.get_market_depth()
5. **Historical Bars** - broker.get_historical_data()
6. **Fundamentals** - broker.get_fundamentals()

### Phase 3 (Nice to Have)
7. **Technical Calculations** - Can calculate from historical data
8. **Options Flow Detection** - Requires analysis logic
9. **Custom Scanners** - Build on top of IBKR scanners

## Code Changes Needed

### 1. Update mcp_enhanced_claude.py
Add new tool definitions in list_tools() and implement in call_tool()

### 2. Update broker.py
Ensure all IBKR methods are exposed:
- run_scanner()
- get_options_chain_with_greeks()
- get_market_depth()
- get_news()
- get_historical_bars()
- get_fundamentals()

### 3. Update analytics_feeds.py
Actually connect to IBKR for real-time data instead of just having the structure

## Why This Matters

Without these tools, Claude Desktop can only:
- Look at your portfolio
- Get basic quotes
- Do simple analysis

With these tools, Claude Desktop can:
- Find trading opportunities (scanners)
- Analyze options flow for institutional activity
- See order book imbalances
- Read breaking news and gauge sentiment
- Backtest strategies with historical data
- Compare fundamentals across sectors
- Calculate complex technical indicators

## No New Dependencies Needed

All these features are already available through ib_insync:
- No numpy needed
- No pandas needed  
- No TA-lib needed
- Just proper IBKR API calls

## Testing Checklist

- [ ] Scanner returns results for TOP_PERC_GAIN
- [ ] Options chain includes all Greeks
- [ ] Level 2 shows bid/ask depth
- [ ] News feed returns recent articles
- [ ] Historical data returns correct bars
- [ ] Fundamentals show P/E, EPS, etc.
- [ ] Technical indicators calculate correctly

---

This would give you the full power of IBKR through Claude Desktop!