"""
Flask API Routes - Enhanced endpoints for IBKR trading assistant
Implements scanner, health check, and improved position endpoints from Gallump.md
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any, List
import logging
from datetime import datetime

# Import core modules
from gallump.core.scanner import IBKRScanner
from gallump.core.storage import Storage
from gallump.core.cache import Cache
from gallump.core.context_builder import build
from gallump.core.validators import validate_strategy

# Create blueprint
api = Blueprint('api', __name__)

logger = logging.getLogger(__name__)

# Components will be initialized by server.py
broker = None
scanner = None
storage = None
cache = None

def init_routes(broker_instance, scanner_instance, storage_instance, cache_instance):
    """Initialize routes with component instances from server"""
    global broker, scanner, storage, cache
    broker = broker_instance
    scanner = scanner_instance
    storage = storage_instance
    cache = cache_instance
    
    # Load watchlist from database
    load_watchlist_from_db()

# Track watched symbols for health checks
WATCHED_SYMBOLS = []

def load_watchlist_from_db():
    """Load watchlist from database on startup"""
    global WATCHED_SYMBOLS
    try:
        if storage:
            # Get symbols from database
            cursor = storage.conn.cursor()
            cursor.execute("SELECT symbol FROM watchlist ORDER BY added_at DESC")
            symbols = [row[0] for row in cursor.fetchall()]
            WATCHED_SYMBOLS = symbols
            logger.info(f"Loaded {len(symbols)} symbols from watchlist database: {symbols}")
    except Exception as e:
        logger.error(f"Failed to load watchlist from database: {e}")
        WATCHED_SYMBOLS = []

def save_watchlist_to_db(symbols):
    """Save watchlist to database"""
    try:
        if storage:
            cursor = storage.conn.cursor()
            
            # Clear existing watchlist
            cursor.execute("DELETE FROM watchlist")
            
            # Add new symbols
            for symbol in symbols:
                cursor.execute(
                    "INSERT INTO watchlist (symbol) VALUES (?)",
                    (symbol.upper(),)
                )
            
            storage.conn.commit()
            logger.info(f"Saved watchlist to database: {symbols}")
    except Exception as e:
        logger.error(f"Failed to save watchlist to database: {e}")


@api.route('/api/health', methods=['GET'])
def health_check():
    """
    System health check endpoint.
    Returns status of all critical components.
    """
    results = {
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'healthy',
        'components': {}
    }
    
    try:
        # Check IBKR broker connection
        if broker:
            ibkr_connected = broker.is_connected()
            # Get detailed health metrics if using EnhancedBroker
            if hasattr(broker, 'get_connection_health'):
                health_metrics = broker.get_connection_health()
                results['components']['ibkr_connection'] = {
                    'status': 'connected' if ibkr_connected else 'disconnected',
                    'healthy': ibkr_connected,
                    'client_id': health_metrics.get('client_id'),
                    'connection_ready': health_metrics.get('connection_ready'),
                    'success_rate': health_metrics.get('success_rate'),
                    'market_status': health_metrics.get('market_status', {})
                }
            else:
                results['components']['ibkr_connection'] = {
                    'status': 'connected' if ibkr_connected else 'disconnected',
                    'healthy': ibkr_connected
                }
        else:
            results['components']['ibkr_connection'] = {
                'status': 'not_initialized',
                'healthy': False
            }
        
        # Check scanner connection
        scanner_connected = scanner._connected if hasattr(scanner, '_connected') else False
        results['components']['scanner'] = {
            'status': 'connected' if scanner_connected else 'disconnected',
            'healthy': scanner_connected
        }
        
        # Check cache status
        cache_status = cache.is_healthy() if hasattr(cache, 'is_healthy') else True
        results['components']['cache'] = {
            'status': 'active' if cache_status else 'inactive',
            'healthy': cache_status
        }
        
        # Check storage/database
        storage_status = storage.is_connected() if hasattr(storage, 'is_connected') else True
        results['components']['storage'] = {
            'status': 'connected' if storage_status else 'disconnected',
            'healthy': storage_status
        }
        
        # Check market data entitlements for watched symbols
        if WATCHED_SYMBOLS and scanner_connected:
            market_data_checks = {}
            for symbol in WATCHED_SYMBOLS[:5]:  # Check first 5 to avoid timeout
                check_result = scanner.check_symbol(symbol)
                market_data_checks[symbol] = {
                    'has_data': check_result.get('has_data', False),
                    'errors': check_result.get('errors', [])
                }
            results['components']['market_data'] = market_data_checks
        
        # Check pending orders status
        pending_orders_status = {'healthy': True, 'count': 0, 'working_orders': 0}
        try:
            if broker and hasattr(broker, 'get_enhanced_open_orders'):
                pending_orders = broker.get_enhanced_open_orders()
                working_orders = [o for o in pending_orders if o.is_working_order()]
                pending_orders_status = {
                    'healthy': True,
                    'count': len(pending_orders),
                    'working_orders': len(working_orders),
                    'status': 'active' if pending_orders else 'no_orders'
                }
            elif storage and hasattr(storage, 'get_pending_orders'):
                # Fallback to database if broker not available
                db_orders = storage.get_pending_orders()
                working_orders = [o for o in db_orders if o.is_working_order()]
                pending_orders_status = {
                    'healthy': True,
                    'count': len(db_orders),
                    'working_orders': len(working_orders),
                    'status': 'database_only'
                }
        except Exception as e:
            logger.warning(f"Failed to check pending orders status: {e}")
            pending_orders_status = {
                'healthy': False,
                'error': str(e),
                'status': 'error'
            }
        
        results['components']['pending_orders'] = pending_orders_status
        
        # Set overall health status
        all_healthy = all(
            comp.get('healthy', True) 
            for comp in results['components'].values() 
            if isinstance(comp, dict)
        )
        results['status'] = 'healthy' if all_healthy else 'degraded'
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        results['status'] = 'error'
        results['error'] = str(e)
        return jsonify(results), 500
    
    # Return 200 for healthy or degraded, 503 only for error
    status_code = 503 if results['status'] == 'error' else 200
    return jsonify(results), status_code


@api.route('/api/get_positions', methods=['GET'])
def get_positions():
    """
    Get current positions with enhanced price fetching.
    Implements batch price fetching and fallback to cached prices.
    """
    try:
        # Get positions from broker
        positions = broker.get_positions() if hasattr(broker, 'get_positions') else []
        
        if not positions:
            return jsonify({'positions': [], 'message': 'No open positions'})
        
        # Extract symbols for batch price fetch
        symbols = [pos.get('symbol') for pos in positions if pos.get('symbol')]
        
        # Batch fetch current prices
        current_prices = {}
        if hasattr(broker, 'get_last_prices'):
            try:
                print(f"DEBUG: Fetching prices for symbols: {symbols}")
                current_prices = broker.get_last_prices(symbols)
                print(f"DEBUG: Got prices: {current_prices}")
            except Exception as e:
                logger.warning(f"Failed to fetch live prices: {e}")
                print(f"DEBUG: Price fetch error: {e}")
        
        # Enhance positions with prices
        enhanced_positions = []
        for pos in positions:
            symbol = pos.get('symbol')
            
            # Try to get current price
            current_price = current_prices.get(symbol)
            
            # Fallback to cached price if no live price
            if not current_price or current_price == 0:
                cached_price = cache.get_last_price(symbol) if hasattr(cache, 'get_last_price') else None
                if cached_price:
                    current_price = cached_price
                    pos['price_source'] = 'cached'
                    pos['stale_data'] = True
                else:
                    pos['price_source'] = 'unavailable'
                    pos['error'] = f"No price data for {symbol} - check entitlement"
            else:
                pos['price_source'] = 'live'
                pos['stale_data'] = False
            
            pos['currentPrice'] = current_price
            
            # Calculate P&L if we have price
            if current_price and pos.get('avgCost'):
                pos['unrealizedPnL'] = (current_price - pos['avgCost']) * pos.get('quantity', 0)
                pos['unrealizedPnLPercent'] = ((current_price / pos['avgCost']) - 1) * 100 if pos['avgCost'] > 0 else 0
            
            enhanced_positions.append(pos)
        
        return jsonify({
            'positions': enhanced_positions,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching positions/prices: {e}")
        return jsonify({'error': str(e), 'positions': []}), 500


@api.route('/api/available_scanners', methods=['GET'])
def get_available_scanners():
    """
    Get all available IBKR scanner types and parameters.
    Returns instruments, locations, scan codes, and filters.
    """
    try:
        # Ensure scanner is connected
        if not scanner._connected:
            scanner.connect()
        
        # Get scanner parameters (uses cache if available)
        params = scanner.get_scanner_parameters()
        
        if 'error' in params:
            return jsonify(params), 500
        
        # Add popular scans with enhanced categorization
        params['popular'] = scanner.get_popular_scans()
        params['popular_codes'] = scanner.get_popular_scan_codes()
        
        # Add category breakdown
        params['categories'] = {
            'momentum': scanner.get_scans_by_category('momentum'),
            'volume': scanner.get_scans_by_category('volume'),
            'technical': scanner.get_scans_by_category('technical'),
            'options': scanner.get_scans_by_category('options')
        }
        
        return jsonify(params)
        
    except Exception as e:
        logger.error(f"Error fetching scanner parameters: {e}")
        return jsonify({'error': str(e)}), 500


@api.route('/api/run_scan', methods=['POST'])
def run_scan():
    """
    Execute an IBKR scanner with specified parameters.
    
    Expected JSON body:
    {
        "scan_code": "TOP_PERC_GAIN",
        "instrument": "STK",
        "location": "STK.US.MAJOR",
        "filters": {"priceAbove": 5, "volumeAbove": 1000000},
        "limit": 50
    }
    """
    try:
        body = request.json
        
        # Extract parameters
        scan_code = body.get('scan_code')
        instrument = body.get('instrument', 'STK')
        location = body.get('location', 'STK.US.MAJOR')
        filters = body.get('filters', {})
        limit = body.get('limit', 50)
        
        # Validate required parameters
        if not scan_code:
            return jsonify({'error': 'scan_code is required'}), 400
        
        # Ensure scanner is connected
        if not scanner._connected:
            scanner.connect()
        
        # Check if this is a popular scan for optimized execution
        if scan_code in scanner.get_popular_scan_codes():
            logger.info(f"Using optimized popular scan for {scan_code}")
            results = scanner.run_popular_scan(scan_code=scan_code, limit=limit)
        else:
            # Run regular scan with provided parameters
            results = scanner.run_scan(
                scan_code=scan_code,
                instrument=instrument,
                location=location,
                filters=filters,
                limit=limit
            )
        
        # Convert results to dict format
        results_dict = [r.to_dict() for r in results]
        
        # Add scan metadata
        scan_info = scanner.get_scan_info(scan_code)
        metadata = {
            'scan_name': scan_info.get('name', scan_code) if scan_info else scan_code,
            'category': scan_info.get('category', 'unknown') if scan_info else 'unknown',
            'description': scan_info.get('description', '') if scan_info else '',
            'optimized': scan_code in scanner.get_popular_scan_codes()
        }
        
        # Cache results if needed
        if hasattr(cache, 'set_scanner_results'):
            cache.set_scanner_results(scan_code, results_dict)
        
        return jsonify({
            'results': results_dict,
            'count': len(results_dict),
            'scan_code': scan_code,
            'metadata': metadata,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error running scan: {e}")
        return jsonify({'error': str(e), 'results': []}), 500


@api.route('/api/diagnose/<symbol>', methods=['GET'])
def diagnose_symbol(symbol: str):
    """
    Diagnostic endpoint for checking symbol data issues.
    Useful when positions show zero prices.
    """
    try:
        symbol = symbol.upper()
        
        # Ensure scanner is connected for diagnostics
        if not scanner._connected:
            scanner.connect()
        
        # Run symbol check
        result = scanner.check_symbol(symbol)
        
        # Add additional diagnostic info
        result['cached_price'] = cache.get_last_price(symbol) if hasattr(cache, 'get_last_price') else None
        result['in_watchlist'] = symbol in WATCHED_SYMBOLS
        result['timestamp'] = datetime.utcnow().isoformat()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error diagnosing symbol {symbol}: {e}")
        return jsonify({
            'symbol': symbol,
            'error': str(e)
        }), 500


@api.route('/api/refresh/prices', methods=['POST'])
def refresh_prices():
    """
    Manually refresh prices for watchlist and positions
    """
    try:
        symbols = request.json.get('symbols', [])
        
        # If no symbols provided, use watchlist + positions
        if not symbols:
            symbols = list(WATCHED_SYMBOLS)
            
            # Add position symbols
            if broker:
                positions = broker.get_positions()
                for pos in positions:
                    if pos.get('symbol') and pos['symbol'] not in symbols:
                        symbols.append(pos['symbol'])
        
        refreshed = {}
        
        if broker and symbols:
            # Force fresh market data fetch
            prices = broker.get_last_prices(symbols, timeout=5)
            
            # Cache with appropriate source
            market_open = broker.is_market_open() if hasattr(broker, 'is_market_open') else False
            source = 'live' if market_open else 'after_hours'
            
            for symbol, price in prices.items():
                if price > 0 and cache:
                    cache.set_price(symbol, price, source)
                refreshed[symbol] = {
                    'price': price,
                    'source': source,
                    'timestamp': datetime.utcnow().isoformat()
                }
        
        return jsonify({
            'success': True,
            'refreshed': refreshed,
            'count': len(refreshed)
        })
        
    except Exception as e:
        logger.error(f"Error refreshing prices: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/api/watchlist/sync', methods=['POST'])
def sync_watchlist():
    """
    Sync watchlist symbols for health monitoring.
    Supports both simple array and enhanced object format.
    """
    global WATCHED_SYMBOLS
    
    try:
        body = request.json
        watchlist_data = body.get('symbols', body.get('watchlist', []))
        
        # Detect format and normalize
        if watchlist_data and isinstance(watchlist_data[0], dict):
            # Enhanced format with metadata
            WATCHED_SYMBOLS = []
            for item in watchlist_data:
                symbol = item.get('symbol')
                if symbol:
                    WATCHED_SYMBOLS.append(symbol.upper())
                    # Save with enhanced metadata
                    storage.add_to_watchlist(
                        symbol=symbol,
                        thesis=item.get('thesis'),
                        is_primary=item.get('is_primary', False),
                        category=item.get('category', 'Long')
                    )
        else:
            # Simple array format (backward compatible)
            WATCHED_SYMBOLS = [s.upper() for s in watchlist_data if s]
            save_watchlist_to_db(WATCHED_SYMBOLS)
        
        logger.info(f"Updated watched symbols: {WATCHED_SYMBOLS}")
        
        return jsonify({
            'success': True,
            'watched_symbols': WATCHED_SYMBOLS
        })
        
    except Exception as e:
        logger.error(f"Error syncing watchlist: {e}")
        return jsonify({'error': str(e)}), 500


@api.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    """Get current portfolio summary"""
    try:
        if not broker:
            return jsonify({'error': 'Broker not initialized'}), 500
        
        portfolio = broker.get_portfolio()
        return jsonify(portfolio)
        
    except Exception as e:
        logger.error(f"Error fetching portfolio: {e}")
        return jsonify({'error': str(e)}), 500


@api.route('/api/positions', methods=['GET'])
def get_current_positions():
    """Get all current positions"""
    try:
        if not broker:
            return jsonify({'error': 'Broker not initialized'}), 500
        
        positions = broker.get_positions()
        
        # Add current prices if available
        if positions and hasattr(broker, 'get_last_prices'):
            symbols = [p['symbol'] for p in positions if 'symbol' in p]
            prices = broker.get_last_prices(symbols)
            
            for pos in positions:
                symbol = pos.get('symbol')
                if symbol and symbol in prices:
                    pos['current_price'] = prices[symbol]
        
        return jsonify(positions)
        
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        return jsonify({'error': str(e)}), 500


@api.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    """
    Get current watchlist
    Returns enhanced format if available, falls back to simple array
    """
    try:
        # Try to get enhanced watchlist from storage
        if storage and hasattr(storage, 'get_enhanced_watchlist'):
            enhanced = storage.get_enhanced_watchlist()
            if enhanced:
                return jsonify({
                    'watchlist': enhanced,
                    'format': 'enhanced',
                    'primary': storage.get_primary_symbol()
                })
        
        # Fallback to simple array
        return jsonify({
            'watchlist': WATCHED_SYMBOLS,
            'format': 'simple'
        })
    except Exception as e:
        logger.error(f"Error getting watchlist: {e}")
        # Return simple format on error
        return jsonify({
            'watchlist': WATCHED_SYMBOLS,
            'format': 'simple'
        })

@api.route('/api/watchlist/<symbol>', methods=['PATCH'])
def update_watchlist_item(symbol):
    """Update specific watchlist item metadata"""
    try:
        updates = request.json
        
        if storage and hasattr(storage, 'update_watchlist_item'):
            success = storage.update_watchlist_item(symbol, **updates)
            
            if success:
                # Reload watchlist if primary changed
                if 'is_primary' in updates:
                    load_watchlist_from_db()
                
                return jsonify({'success': True, 'symbol': symbol})
            else:
                return jsonify({'error': 'Symbol not found in watchlist'}), 404
        else:
            return jsonify({'error': 'Enhanced watchlist not available'}), 501
            
    except Exception as e:
        logger.error(f"Error updating watchlist item: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Analytics Endpoints - Provides MCP-style analysis for mobile app
# ============================================================================

# Import simplified analytics that actually works
from gallump.api.analytics_simplified import analytics_bp
api.register_blueprint(analytics_bp)

@api.route('/api/analytics/portfolio', methods=['POST'])
def analyze_portfolio():
    """
    Enhanced portfolio analysis endpoint
    Provides same capabilities as MCP enhanced_portfolio_analysis tool
    """
    try:
        # Import MCP modules
        from gallump.core.analytics_engine import EnhancedMCPAnalytics
        from gallump.core.analytics_context import IntelligentContextManager
        
        # Initialize analytics with broker's IB connection
        analytics = EnhancedMCPAnalytics(ib_connection=broker.ib if broker else None)
        context_manager = IntelligentContextManager()
        
        # Get portfolio data
        if not broker:
            return jsonify({'error': 'Broker not initialized'}), 500
            
        positions = broker.get_positions()
        
        # Build enhanced context
        portfolio_context = analytics.get_portfolio_context()
        prioritized_data = context_manager.prioritize_for_response(portfolio_context)
        
        return jsonify({
            'positions': positions,
            'context': prioritized_data,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'analytics_api'
        })
        
    except ImportError as e:
        logger.error(f"MCP modules not available: {e}")
        # Fallback to basic portfolio data
        if broker:
            positions = broker.get_positions()
            return jsonify({
                'positions': positions,
                'enhanced': False,
                'timestamp': datetime.utcnow().isoformat()
            })
        return jsonify({'error': 'Analytics not available'}), 503
    except Exception as e:
        logger.error(f"Portfolio analysis error: {e}")
        return jsonify({'error': str(e)}), 500


@api.route('/api/analytics/symbol/<symbol>', methods=['GET'])
def analyze_symbol(symbol):
    """
    Enhanced symbol analysis endpoint
    Provides same capabilities as MCP enhanced_symbol_analysis tool
    """
    try:
        # Import MCP modules
        from gallump.core.analytics_engine import EnhancedMCPAnalytics
        from gallump.core.analytics_feeds import MCPDataFeeds
        from gallump.core.broker import Broker
        
        # Use existing broker connection for data feeds
        if not broker:
            return jsonify({'error': 'Broker not initialized'}), 500
        
        # Initialize analytics with existing IBKR connection
        analytics = EnhancedMCPAnalytics(ib_connection=broker.ib if broker else None)
        data_feeds = MCPDataFeeds(ib_connection=broker.ib)
        
        # Get analysis type from query params
        analysis_type = request.args.get('type', 'comprehensive')
        
        # Get enhanced market data
        market_data = analytics.get_enhanced_market_data(symbol)
        
        # Add real-time feeds if available (no need to call connect, just check if ib is connected)
        if broker.ib and broker.ib.isConnected():
            # Start feeds for this symbol
            data_feeds.start_feeds([symbol], include_options=False, include_news=False)
            # Note: Level2 data would require additional implementation
        
        return jsonify({
            'symbol': symbol,
            'analysis': market_data,
            'type': analysis_type,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'analytics_api'
        })
        
    except ImportError:
        # Fallback to basic context builder
        context = build(symbol, storage=storage, cache=cache)
        return jsonify({
            'symbol': symbol,
            'context': context.__dict__ if hasattr(context, '__dict__') else str(context),
            'enhanced': False,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Symbol analysis error: {e}")
        return jsonify({'error': str(e)}), 500


@api.route('/api/analytics/market', methods=['POST'])
def analyze_market():
    """
    Enhanced market analysis endpoint
    Provides same capabilities as MCP enhanced_market_analysis tool
    """
    try:
        data = request.json
        symbols = data.get('symbols', [])
        prompt = data.get('prompt', '')
        
        # Import analytics modules
        from gallump.core.analytics_engine import EnhancedMCPAnalytics
        
        # Initialize analytics with broker's IB connection
        analytics = EnhancedMCPAnalytics(ib_connection=broker.ib if broker else None)
        
        # Run market analysis
        analysis = {}
        for symbol in symbols[:10]:  # Limit to 10 symbols
            analysis[symbol] = analytics.get_enhanced_market_data(symbol)
        
        # Add scanner results if requested
        if 'scan' in prompt.lower() and scanner:
            scan_results = scanner.scan_market('TOP_PERC_GAIN')[:10]
            analysis['scan_results'] = scan_results
        
        return jsonify({
            'symbols': symbols,
            'analysis': analysis,
            'prompt': prompt,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'analytics_api'
        })
        
    except ImportError:
        # Fallback to basic scanner
        if scanner:
            results = scanner.run_scan('TOP_PERC_GAIN', limit=10)
            return jsonify({
                'scan_results': results,
                'enhanced': False,
                'timestamp': datetime.utcnow().isoformat()
            })
        return jsonify({'error': 'Analytics not available'}), 503
    except Exception as e:
        logger.error(f"Market analysis error: {e}")
        return jsonify({'error': str(e)}), 500


@api.route('/api/analytics/options/<symbol>', methods=['GET'])
def analyze_options(symbol):
    """
    Enhanced options analysis endpoint
    Provides same capabilities as MCP enhanced_options_analysis tool
    """
    try:
        # Import MCP modules
        from gallump.core.analytics_engine import EnhancedMCPAnalytics
        from gallump.core.analytics_feeds import MCPDataFeeds
        from gallump.core.broker import Broker
        
        # Use existing broker connection for data feeds
        if not broker:
            return jsonify({'error': 'Broker not initialized'}), 500
        
        # Initialize analytics with existing IBKR connection
        analytics = EnhancedMCPAnalytics(ib_connection=broker.ib if broker else None)
        data_feeds = MCPDataFeeds(ib_connection=broker.ib)
        
        # Get strategy type from query params
        strategy_type = request.args.get('strategy', 'overview')
        
        # Get options data
        options_data = {}
        
        if broker.ib and broker.ib.isConnected():
            # Start options feeds for this symbol
            data_feeds.start_feeds([symbol], include_options=True, include_news=False)
            # Note: Getting options chain would require additional implementation
            if chain:
                options_data['chain'] = chain
                options_data['iv_analysis'] = analytics.analyze_implied_volatility(chain)
                options_data['unusual_activity'] = analytics.detect_unusual_options_activity(chain)
        
        return jsonify({
            'symbol': symbol,
            'options': options_data,
            'strategy_type': strategy_type,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'analytics_api'
        })
        
    except ImportError:
        # Fallback - return basic message
        return jsonify({
            'symbol': symbol,
            'message': 'Options analysis requires MCP modules',
            'enhanced': False,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Options analysis error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Pending Orders Endpoints - Full IBKR order management with bracket support
# ============================================================================

@api.route('/api/orders/pending', methods=['GET'])
def get_pending_orders():
    """
    Get all pending orders with enhanced details and caching
    Supports filtering by symbol, status, or bracket group
    """
    try:
        # Get query parameters
        symbol = request.args.get('symbol')
        status = request.args.get('status')
        oca_group = request.args.get('oca_group')
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        # Try cache first unless force refresh
        if not force_refresh:
            cached_orders = cache.get_cached_pending_orders()
            if cached_orders:
                # Apply filters if requested
                filtered_orders = cached_orders
                if symbol:
                    filtered_orders = [o for o in filtered_orders if o.symbol == symbol.upper()]
                if status:
                    filtered_orders = [o for o in filtered_orders if o.status == status]
                if oca_group:
                    filtered_orders = [o for o in filtered_orders if o.oca_group == oca_group]
                
                return jsonify({
                    'orders': [order.to_dict() for order in filtered_orders],
                    'total': len(filtered_orders),
                    'source': 'cache',
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        # Get live orders from IBKR
        if broker and hasattr(broker, 'get_enhanced_open_orders'):
            live_orders = broker.get_enhanced_open_orders()
            
            # Sync with database for persistence
            if storage and hasattr(storage, 'sync_pending_orders'):
                storage.sync_pending_orders(live_orders)
            
            # Cache results for next request
            if cache and hasattr(cache, 'cache_pending_orders'):
                cache.cache_pending_orders(live_orders, ttl=30)
            
            # Apply filters if requested
            filtered_orders = live_orders
            if symbol:
                filtered_orders = [o for o in filtered_orders if o.symbol == symbol.upper()]
            if status:
                filtered_orders = [o for o in filtered_orders if o.status == status]
            if oca_group:
                filtered_orders = [o for o in filtered_orders if o.oca_group == oca_group]
            
            return jsonify({
                'orders': [order.to_dict() for order in filtered_orders],
                'total': len(filtered_orders),
                'source': 'live_ibkr',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Fallback to database if IBKR not available
        if storage and hasattr(storage, 'get_pending_orders'):
            db_orders = storage.get_pending_orders(symbol=symbol, status=status, oca_group=oca_group)
            return jsonify({
                'orders': [order.to_dict() for order in db_orders],
                'total': len(db_orders),
                'source': 'database',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return jsonify({
            'orders': [],
            'total': 0,
            'source': 'none',
            'error': 'No data source available',
            'timestamp': datetime.utcnow().isoformat()
        }), 503
        
    except Exception as e:
        logger.error(f"Error fetching pending orders: {e}")
        return jsonify({
            'error': str(e),
            'orders': [],
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@api.route('/api/orders/brackets', methods=['GET'])
def get_bracket_orders():
    """Get all bracket order groups with enhanced formatting"""
    try:
        # Try cache first
        cached_brackets = cache.get_cached_bracket_orders() if cache else []
        if cached_brackets:
            return jsonify({
                'brackets': [
                    {
                        'oca_group': bracket.oca_group,
                        'main_order': bracket.main_order.to_dict(),
                        'profit_target': bracket.profit_target.to_dict() if bracket.profit_target else None,
                        'stop_loss': bracket.stop_loss.to_dict() if bracket.stop_loss else None,
                        'status': bracket.get_status(),
                        'is_complete': bracket.is_complete()
                    }
                    for bracket in cached_brackets
                ],
                'count': len(cached_brackets),
                'source': 'cache',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Get from database
        if storage and hasattr(storage, 'get_bracket_orders'):
            brackets = storage.get_bracket_orders()
            
            # Cache results
            if cache and hasattr(cache, 'cache_bracket_orders'):
                cache.cache_bracket_orders(brackets, ttl=60)
            
            return jsonify({
                'brackets': [
                    {
                        'oca_group': bracket.oca_group,
                        'main_order': bracket.main_order.to_dict(),
                        'profit_target': bracket.profit_target.to_dict() if bracket.profit_target else None,
                        'stop_loss': bracket.stop_loss.to_dict() if bracket.stop_loss else None,
                        'status': bracket.get_status(),
                        'is_complete': bracket.is_complete()
                    }
                    for bracket in brackets
                ],
                'count': len(brackets),
                'source': 'database',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return jsonify({
            'brackets': [],
            'count': 0,
            'source': 'none',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching bracket orders: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/api/orders/cancel/<order_id>', methods=['POST'])
def cancel_order(order_id):
    """Cancel a pending order"""
    try:
        if not broker:
            return jsonify({'error': 'Broker not initialized'}), 500
        
        # Cancel order via IBKR
        success = broker.cancel_order(order_id)
        
        if success:
            # Update database status
            if storage and hasattr(storage, 'update_order_status'):
                storage.update_order_status(order_id, 'Cancelled')
            
            # Invalidate cache to force refresh
            if cache and hasattr(cache, 'invalidate_pending_orders'):
                cache.invalidate_pending_orders()
            
            return jsonify({
                'success': True,
                'order_id': order_id,
                'status': 'cancelled',
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'error': 'Failed to cancel order',
                'order_id': order_id
            }), 400
            
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/api/orders/stats', methods=['GET'])
def get_pending_orders_stats():
    """Get statistics about pending orders"""
    try:
        if cache and hasattr(cache, 'get_pending_orders_stats'):
            stats = cache.get_pending_orders_stats()
            return jsonify({
                'stats': stats,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return jsonify({
            'stats': {'total': 0, 'by_status': {}, 'by_type': {}},
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting order stats: {e}")
        return jsonify({'error': str(e)}), 500