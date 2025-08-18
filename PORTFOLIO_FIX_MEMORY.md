# Portfolio Display Fix - IMPORTANT MEMORY
**Date**: August 18, 2025
**Fixed By**: Claude

## The Problem
Portfolio page was showing $0.00 for all positions and P&L calculations, even though the backend was fetching correct prices from IBKR.

## Root Cause
The frontend `PortfolioPanel.jsx` was using TWO different API calls:
1. `api.getPortfolio()` - Returns positions with `marketPrice` field
2. `api.getPositions()` - Returns positions with `currentPrice` field

The component was displaying data from `getPositions()` but the `PositionCard.jsx` expected `marketPrice` field, causing all prices to show as $0.00.

## The Solution

### Backend Fix (broker.py)
Modified `get_portfolio()` method to fetch current prices and calculate P&L:
```python
# Get positions
positions = self.get_positions()

# Add current prices to positions
if positions:
    symbols = [p['symbol'] for p in positions if 'symbol' in p]
    try:
        prices = self.get_last_prices(symbols)
        for pos in positions:
            symbol = pos.get('symbol')
            if symbol and symbol in prices:
                pos['currentPrice'] = prices[symbol]
                pos['marketPrice'] = prices[symbol]
                pos['marketValue'] = prices[symbol] * pos.get('position', 0)
                # Calculate unrealized P&L
                avg_cost = pos.get('averageCost', 0)
                position_size = pos.get('position', 0)
                if avg_cost and position_size:
                    pos['unrealizedPnL'] = (prices[symbol] - avg_cost) * position_size
    except Exception as e:
        logger.warning(f"Could not fetch current prices: {e}")
```

### Frontend Fix (PortfolioPanel.jsx)
Simplified to use ONLY portfolio data:
```javascript
const fetchData = async () => {
  setLoading(true);
  try {
    const portfolioData = await api.getPortfolio();
    
    setPortfolio(portfolioData);
    // Use positions from portfolio data which has the correct price fields
    setPositions(portfolioData.positions || []);
  } catch (error) {
    toast.error('Failed to fetch portfolio data');
    console.error(error);
  } finally {
    setLoading(false);
  }
};
```

## Key Learnings
1. **Always use consistent field names** - Don't mix `currentPrice` and `marketPrice`
2. **Single source of truth** - Use ONE API endpoint for related data
3. **Backend should provide complete data** - Don't rely on frontend to merge data from multiple endpoints
4. **Test the entire data flow** - From IBKR → Backend → API → Frontend → Display

## Testing Confirmation
Portfolio now correctly shows:
- Current prices for all positions
- Unrealized P&L calculations
- Market values
- Proper percentage gains/losses

## Related Files
- `/gallump/core/broker.py` - `get_portfolio()` method
- `/gallump/frontend/src/components/Portfolio/PortfolioPanel.jsx` - Main portfolio component
- `/gallump/frontend/src/components/Portfolio/PositionCard.jsx` - Individual position display