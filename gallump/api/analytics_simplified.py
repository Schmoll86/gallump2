"""
Simplified Analytics Routes - Actually works with current system
"""
from flask import Blueprint, jsonify, request
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

analytics_bp = Blueprint('analytics', __name__)

# Import what we actually have
try:
    from gallump.core.broker import Broker
    from gallump.core.storage import Storage
except ImportError:
    # Try relative imports if package imports fail
    from ..core.broker import Broker
    from ..core.storage import Storage

@analytics_bp.route('/api/analytics/chat', methods=['POST'])
def analytics_chat():
    """
    Simple analytics chat that provides basic market analysis
    """
    try:
        data = request.json
        prompt = data.get('prompt', '')
        symbols = data.get('symbols', [])
        
        # Use the global broker instance from routes.py instead of creating new ones!
        from flask import current_app
        broker = current_app.config.get('broker')
        storage = current_app.config.get('storage')
        
        # Build response based on prompt
        response = {
            'prompt': prompt,
            'symbols': symbols,
            'analysis': '',
            'timestamp': datetime.now().isoformat()
        }
        
        # Check if broker exists and is connected
        if not broker or not broker.is_connected():
            response['analysis'] = "⚠️ Cannot connect to IBKR for live data. Limited analysis available."
            return jsonify(response)
        
        # Handle different types of requests
        prompt_lower = prompt.lower()
        
        if 'portfolio' in prompt_lower:
            # Get portfolio data
            portfolio = broker.get_portfolio()
            response['analysis'] = f"""📊 **Portfolio Analysis**
            
Total Value: ${portfolio.get('total_value', 0):,.2f}
Cash: ${portfolio.get('cash', 0):,.2f}
Buying Power: ${portfolio.get('buying_power', 0):,.2f}

**Positions:**
"""
            for pos in portfolio.get('positions', []):
                symbol = pos.get('symbol')
                qty = pos.get('position', 0)
                price = pos.get('marketPrice', 0)
                pnl = pos.get('unrealizedPnL', 0)
                response['analysis'] += f"\n• {symbol}: {qty} shares @ ${price:.2f} (P&L: ${pnl:+.2f})"
        
        elif symbols:
            # Analyze specific symbols
            response['analysis'] = f"📈 **Market Analysis for {', '.join(symbols)}**\n\n"
            
            # Get prices for symbols
            prices = broker.get_last_prices(symbols)
            
            for symbol in symbols:
                price = prices.get(symbol, 0)
                response['analysis'] += f"**{symbol}**: ${price:.2f}\n"
                
                # Add some basic analysis
                if price > 0:
                    # Get positions if any
                    positions = broker.get_positions()
                    for pos in positions:
                        if pos.get('symbol') == symbol:
                            avg_cost = pos.get('averageCost', 0)
                            if avg_cost > 0:
                                pct_change = ((price / avg_cost) - 1) * 100
                                response['analysis'] += f"  • Your position: {pct_change:+.2f}% from cost basis\n"
                            break
                    
                    # Add basic technical levels (simplified)
                    response['analysis'] += f"  • Support: ${price * 0.95:.2f}\n"
                    response['analysis'] += f"  • Resistance: ${price * 1.05:.2f}\n"
                    response['analysis'] += "\n"
        
        elif 'market' in prompt_lower or 'scan' in prompt_lower:
            # Market overview
            response['analysis'] = """📊 **Market Overview**
            
Market Status: Open (Regular Hours)

**Top Movers** (if scanner available):
• Feature requires scanner to be configured

**Suggested Actions:**
• Review your portfolio positions
• Check for any pending orders
• Monitor key support/resistance levels
"""
        
        else:
            # Generic response
            response['analysis'] = f"""💬 **Analysis Request**

Your prompt: "{prompt}"

To get specific analysis, try:
• "analyze AAPL" - for symbol analysis
• "portfolio analysis" - for portfolio review  
• "market overview" - for market summary
• Include ticker symbols in your message

Example: "analyze TSLA and NVDA"
"""
        
        # Don't disconnect the global broker!
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Analytics chat error: {e}")
        return jsonify({
            'error': str(e),
            'analysis': f'Error: {str(e)}'
        }), 500