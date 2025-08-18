from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os

from gallump.core.context_builder import build
from gallump.core.validators import validate_strategy, validate_order
from gallump.core.storage import Storage
from gallump.core.broker import Broker
from gallump.core.scanner import IBKRScanner
from gallump.core.cache import Cache
from gallump.core.session_manager import SessionManager
from gallump.api.routes import api

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Configuration - No auth needed on local secure network

storage = Storage()

# Initialize broker with environment settings
IBKR_HOST = os.getenv('IBKR_HOST', '127.0.0.1')
IBKR_PORT = int(os.getenv('IBKR_PORT', '4001'))  # 4001 for live, 4002 for paper
# Use Broker with automatic client ID management (None = dynamic)
broker = Broker(host=IBKR_HOST, port=IBKR_PORT, client_id=None)

# Try to connect to IBKR on startup
try:
    if broker.connect():
        print(f"✓ Connected to IBKR at {IBKR_HOST}:{IBKR_PORT}")
    else:
        print(f"✗ Failed to connect to IBKR at {IBKR_HOST}:{IBKR_PORT}")
except Exception as e:
    print(f"✗ IBKR connection error: {e}")

# Initialize scanner with same connection settings
scanner = IBKRScanner(host=IBKR_HOST, port=IBKR_PORT, client_id=2)  # Different client ID
cache = Cache(use_redis=True)  # Will fallback to in-memory if Redis not available
session_manager = SessionManager(cache=cache, storage=storage)

# Store broker and storage in app config so other modules can access them
app.config['broker'] = broker
app.config['storage'] = storage

# Initialize routes with component instances
from gallump.api.routes import init_routes, api
init_routes(broker, scanner, storage, cache)

# Register the API blueprint with all new routes
app.register_blueprint(api)

def auth_required(f):
    """No-op decorator - no authentication on local network"""
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Just pass through without authentication
        return f(*args, **kwargs)
    return wrapper

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login endpoint - always succeeds on local network"""
    # No authentication needed on local secure network
    return jsonify({
        'token': 'local_access_token',  # Dummy token for frontend compatibility  
        'username': 'local_user'
    })

@app.route('/api/strategies/generate', methods=['POST'])
@auth_required
def generate_strategy():
    """
    Generate strategies through AI conversation - NO EXECUTION
    This endpoint ONLY returns recommendations for user review
    Supports conversational continuity through session management
    """
    data = request.json
    user_prompt = data.get('prompt', '')
    watchlist = data.get('watchlist', [])
    session_id = data.get('session_id')  # Optional session ID from client
    
    # Get or create session for conversation continuity
    session_id = session_manager.get_or_create_session(session_id)
    
    # Extract primary symbol for context
    # Handle both simple string format and enhanced dict format
    if watchlist:
        first_item = watchlist[0]
        if isinstance(first_item, dict):
            # Enhanced watchlist format - extract symbol from dict
            symbol = first_item.get('symbol')
        else:
            # Simple string format
            symbol = first_item
    else:
        symbol = None
    print(f"DEBUG: Symbol type: {type(symbol)}, value: {symbol}")
    
    # Add user message to session
    session_manager.add_message(session_id, 'user', user_prompt, symbol)
    
    # Get session context (conversation history + insights)
    print(f"DEBUG: Getting context for session {session_id}, symbol {symbol}")
    session_context = session_manager.get_context(session_id, symbol)
    
    # Build market context with all data
    from gallump.core.context_builder import ContextBuilder
    from gallump.core.brain import Brain
    
    # Convert watchlist to simple symbols list for context builder
    if watchlist and isinstance(watchlist[0], dict):
        # Enhanced format - extract just the symbols
        symbols_list = [item.get('symbol') for item in watchlist if item.get('symbol')]
    else:
        # Simple format - use as is
        symbols_list = watchlist or []
    
    context_builder = ContextBuilder(broker=broker, cache=cache, scanner=scanner)
    market_context = context_builder.build(
        symbols=symbols_list,
        user_prompt=user_prompt,
        watchlist=symbols_list
    )
    
    # Initialize Brain with session awareness
    brain = Brain(session_id=session_id, session_manager=session_manager)
    
    # Get AI recommendations with both market and session context
    result = brain.converse(
        user_message=user_prompt,
        market_context=market_context,
        session_context=session_context
    )
    
    # Add assistant response to session
    session_manager.add_message(session_id, 'assistant', result['response'], symbol)
    
    # Save conversation to persistent storage
    storage.save_conversation(
        user_prompt=user_prompt,
        assistant_response=result['response'],
        symbol=symbol,
        session_id=session_id,
        strategies_count=len(result.get('recommendations', []))
    )
    
    # Save strategies for user review
    if result['recommendations']:
        for strategy in result['recommendations']:
            validated = validate_strategy(strategy)
            validated['status'] = 'PENDING_USER_APPROVAL'  # NOT executed
            validated['session_id'] = session_id  # Link to session
            storage.save_strategy(validated)
    
    # Return AI response with session ID for continuity
    return jsonify({
        'session_id': session_id,  # Client must store this for continuity
        'response': result['response'],  # AI conversation text
        'recommendations': result['recommendations'],  # Strategies to review
        'requires_confirmation': True,  # User must confirm before execution
        'context_stats': {
            'messages_in_session': len(session_context.current_messages),
            'relevant_history_loaded': len(session_context.relevant_history),
            'insights_included': len(session_context.insights),
            'token_estimate': session_context.token_estimate()
        }
    })

@app.route('/api/strategies/<strategy_id>/confirm', methods=['POST'])
@auth_required
def confirm_strategy(strategy_id):
    """
    USER CONFIRMATION REQUIRED - The "RED BUTTON"
    Only this endpoint can trigger actual execution
    """
    import logging
    from gallump.core.risk import RiskManager
    
    # User has reviewed and confirmed they want to execute
    confirmed = request.json.get('confirmed', False)
    
    if not confirmed:
        return jsonify({'error': 'User confirmation required'}), 400
    
    # Load the strategy
    strategy = storage.get_strategy(int(strategy_id))
    if not strategy:
        return jsonify({'error': 'Strategy not found'}), 404
    
    # Extract strategy details
    strategy_details = strategy.get('details', {})
    orders = strategy_details.get('orders', [])
    
    if not orders:
        return jsonify({'error': 'Strategy has no orders'}), 400
    
    # NOW we can proceed with execution flow:
    try:
        # 1. Validate each order
        validated_orders = []
        for order in orders:
            validated = validate_order(order)
            validated_orders.append(validated)
        
        # 2. Get current portfolio for risk check
        portfolio = broker.get_portfolio()
        
        # 3. Check risk limits for each order
        risk_manager = RiskManager()
        risk_approved = True
        risk_warnings = []
        
        for order in validated_orders:
            # Create a Trade object for risk evaluation
            from gallump.core.types import Trade
            trade = Trade(
                asset_type=order.get('asset_type', 'STOCK'),
                price=order.get('limit_price', 0),  # Use limit price or 0 for market
                quantity=order.get('quantity', 0)
            )
            
            # Evaluate risk
            from gallump.core.types import Portfolio as PortfolioType
            portfolio_obj = PortfolioType(
                total_value=portfolio.get('total_value', 0),
                positions=[]  # Simplified for now
            )
            
            risk_result = risk_manager.evaluate(trade, portfolio_obj)
            if not risk_result.approved:
                risk_approved = False
                risk_warnings.extend(risk_result.warnings)
        
        if not risk_approved:
            logging.warning(f"Strategy {strategy_id} failed risk checks: {risk_warnings}")
            return jsonify({
                'error': 'Strategy failed risk checks',
                'warnings': risk_warnings
            }), 400
        
        # 4. Execute through broker
        executed_orders = []
        failed_orders = []
        
        for order in validated_orders:
            try:
                # Log the order for audit
                logging.info(f"Executing order for strategy {strategy_id}: {order}")
                
                # Route to appropriate broker method based on order type
                order_type = order.get('order_type', 'MKT')
                
                if order_type == 'TRAIL':
                    # Handle trailing stop orders
                    order_id = broker.place_trailing_stop_order(
                        symbol=order['symbol'],
                        action=order['action'],
                        quantity=order['quantity'],
                        trail_amount=order.get('trail_amount'),
                        trail_percent=order.get('trail_percent')
                    )
                else:
                    # Handle regular orders
                    order_id = broker.place_order(
                        symbol=order['symbol'],
                        action=order['action'],
                        quantity=order['quantity'],
                        order_type=order_type,
                        limit_price=order.get('limit_price')
                    )
                
                if order_id:
                    executed_orders.append({
                        'order_id': order_id,
                        'symbol': order['symbol'],
                        'action': order['action'],
                        'quantity': order['quantity']
                    })
                    
                    # Save trade to storage
                    storage.save_trade({
                        'symbol': order['symbol'],
                        'action': order['action'],
                        'quantity': order['quantity'],
                        'order_type': order.get('order_type', 'MARKET'),
                        'limit_price': order.get('limit_price'),
                        'fill_status': 'submitted'
                    }, strategy_id=int(strategy_id))
                else:
                    failed_orders.append({
                        'symbol': order['symbol'],
                        'error': 'Failed to place order'
                    })
                    
            except Exception as e:
                logging.error(f"Failed to execute order: {e}")
                failed_orders.append({
                    'symbol': order.get('symbol', 'UNKNOWN'),
                    'error': str(e)
                })
        
        # 5. Update strategy status
        if executed_orders:
            storage.update_strategy_status(
                int(strategy_id), 
                'executed' if not failed_orders else 'partial',
                executed_at=datetime.now()
            )
        
        # Return execution results
        return jsonify({
            'status': 'executed' if not failed_orders else 'partial',
            'message': f'Strategy {strategy_id} executed',
            'executed_orders': executed_orders,
            'failed_orders': failed_orders
        })
        
    except Exception as e:
        logging.error(f"Strategy execution failed: {e}")
        return jsonify({
            'error': 'Strategy execution failed',
            'details': str(e)
        }), 500

@app.route('/api/execute', methods=['POST'])
def execute():
    """
    DEPRECATED - Use /confirm endpoint instead
    Execution should only happen after user confirmation
    """
    return jsonify({'error': 'Direct execution not allowed. Use /strategies/<id>/confirm'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Changed to 5001 to avoid conflict
