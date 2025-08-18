#!/usr/bin/env python3
"""
Enhanced MCP Server for Claude Desktop - FIXED VERSION
Implements FULL MCP protocol with all required methods
"""

import asyncio
import json
import logging
import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# Setup logging to stderr for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/mcp_enhanced.log'),
        logging.StreamHandler(sys.stderr)  # This will appear in Claude Desktop logs
    ]
)
logger = logging.getLogger(__name__)

# Add gallump to path
sys.path.insert(0, str(Path(__file__).parent))

# Import enhanced components
try:
    from gallump.core.analytics_context import IntelligentContextManager
    from gallump.core.analytics_feeds import MCPDataFeeds
    from gallump.core.analytics_engine import EnhancedMCPAnalytics
    ENHANCED_AVAILABLE = True
    logger.info("✅ Enhanced components loaded successfully")
except ImportError as e:
    logger.error(f"❌ Enhanced components failed to load: {e}")
    ENHANCED_AVAILABLE = False

# Check for ib_insync
try:
    from ib_insync import IB, Stock, Option
    IBKR_AVAILABLE = True
    logger.info("✅ ib_insync available for live market data")
except ImportError:
    IBKR_AVAILABLE = False
    logger.info("⚠️ ib_insync not available - using cached data only")

class EnhancedMCPForClaude:
    """Enhanced MCP server specifically for Claude Desktop"""
    
    def __init__(self):
        self.db_path = os.getenv('GALLUMP_DB_PATH', 
                                str(Path(__file__).parent / 'data' / 'trading.db'))
        
        logger.info(f"Database path: {self.db_path}")
        
        # Initialize components if available
        if ENHANCED_AVAILABLE:
            self.context_manager = IntelligentContextManager()
            self.analytics = EnhancedMCPAnalytics()
            logger.info("Enhanced analytics components initialized")
        else:
            self.context_manager = None
            self.analytics = None
            logger.warning("Running in basic mode")
    
    def handle_request(self, request_data):
        """Handle MCP protocol requests"""
        try:
            method = request_data.get('method', '')
            params = request_data.get('params', {})
            
            logger.info(f"Handling method: {method}")
            
            # Core MCP protocol methods
            if method == 'initialize':
                return self.initialize(params)
            elif method == 'initialized':
                return self.handle_initialized(params)
            elif method == 'shutdown':
                return self.handle_shutdown()
            elif method == 'notifications/cancelled':
                return self.handle_cancelled(params)
            # Tool methods
            elif method == 'tools/list':
                return self.list_tools()
            elif method == 'tools/call':
                return self.call_tool(params)
            else:
                logger.warning(f"Unknown method: {method}")
                return {
                    'error': {
                        'code': -32601,
                        'message': f'Method not found: {method}'
                    }
                }
        
        except Exception as e:
            logger.error(f"Request handling error: {e}", exc_info=True)
            return {
                'error': {
                    'code': -32603,
                    'message': f'Internal error: {str(e)}'
                }
            }
    
    def initialize(self, params):
        """Handle MCP initialization handshake"""
        logger.info("Initializing MCP server")
        return {
            'protocolVersion': '2025-06-18',
            'capabilities': {},
            'serverInfo': {
                'name': 'gallump-enhanced-analytics',
                'version': '1.0.0'
            }
        }
    
    def handle_initialized(self, params):
        """Handle initialized notification from client"""
        logger.info("Client initialized successfully")
        # This is a notification, no response needed
        return None
    
    def handle_shutdown(self):
        """Handle shutdown request"""
        logger.info("Shutdown requested")
        # Cleanup if needed
        return {}
    
    def handle_cancelled(self, params):
        """Handle cancelled notification"""
        request_id = params.get('requestId')
        reason = params.get('reason')
        logger.info(f"Request {request_id} cancelled: {reason}")
        # This is a notification, no response needed
        return None
    
    def list_tools(self):
        """List available MCP tools"""
        if ENHANCED_AVAILABLE:
            tools = [
                {
                    'name': 'enhanced_portfolio_analysis',
                    'description': 'Use this tool when user asks about: portfolio, positions, holdings, P&L, profits, losses, current investments, what they own, portfolio value, account balance, trading performance, or "show my portfolio"',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {},
                        'required': []
                    }
                },
                {
                    'name': 'enhanced_symbol_analysis',
                    'description': 'Use this tool when user mentions specific stock symbols (AAPL, MSFT, SPY, etc.) or asks to: analyze a stock, check a ticker, review a symbol, get stock details, show stock analysis, evaluate a company, or says "what about [symbol]" or "analyze [symbol]"',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'symbol': {'type': 'string', 'description': 'Stock symbol to analyze (e.g., AAPL, MSFT, SPY)'},
                            'analysis_type': {'type': 'string', 'description': 'Type: basic, options, risk, technical'}
                        },
                        'required': ['symbol']
                    }
                },
                {
                    'name': 'enhanced_market_analysis',
                    'description': 'Use this tool when user asks about: market conditions, sector analysis, multiple stocks comparison, market trends, "what\'s moving", market overview, sector rotation, market breadth, or comparing multiple symbols like "compare AAPL and MSFT"',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'prompt': {'type': 'string', 'description': 'Market analysis request or question'},
                            'symbols': {'type': 'array', 'description': 'List of symbols to analyze (optional)'}
                        },
                        'required': ['prompt']
                    }
                },
                {
                    'name': 'enhanced_options_analysis',
                    'description': 'Use this tool when user asks about: options, calls, puts, strikes, expiration, Greeks (delta, gamma, theta, vega), IV (implied volatility), options chains, covered calls, spreads, or says "options for [symbol]" or "show me options"',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'symbol': {'type': 'string', 'description': 'Underlying stock symbol'},
                            'strategy_type': {'type': 'string', 'description': 'Options strategy type (covered_call, spread, etc.)'}
                        },
                        'required': ['symbol']
                    }
                },
                {
                    'name': 'run_scanner',
                    'description': 'Run IBKR market scanner to find stocks matching criteria (gainers/losers, volume, technical patterns, options activity)',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'scanner_type': {
                                'type': 'string',
                                'description': 'Scanner type - includes momentum, volume, technical, and options scanners',
                                'enum': ['TOP_PERC_GAIN', 'TOP_PERC_LOSE', 'MOST_ACTIVE', 'HOT_BY_VOLUME', 'TOP_TRADE_COUNT', 
                                        'HIGH_VS_13W_HL', 'LOW_VS_13W_HL', 'HIGH_OPT_IMP_VOLAT', 'OPT_VOLUME_MOST_ACTIVE', 'HOT_BY_OPT_VOLUME']
                            },
                            'limit': {
                                'type': 'number',
                                'description': 'Number of results (default 20)',
                                'default': 20
                            },
                            'category': {
                                'type': 'string',
                                'description': 'Filter by scanner category: momentum, volume, technical, options',
                                'enum': ['momentum', 'volume', 'technical', 'options']
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
            ]
        else:
            # Fallback basic tools
            tools = [
                {
                    'name': 'get_portfolio',
                    'description': 'Use this tool when user asks about portfolio, positions, or holdings',
                    'inputSchema': {'type': 'object', 'properties': {}, 'required': []}
                },
                {
                    'name': 'get_watchlist',
                    'description': 'Use this tool when user asks about watchlist or tracked symbols',
                    'inputSchema': {'type': 'object', 'properties': {}, 'required': []}
                }
            ]
        
        return {'tools': tools}
    
    def call_tool(self, params):
        """Execute tool calls"""
        tool_name = params.get('name', '')
        arguments = params.get('arguments', {})
        
        logger.info(f"Calling tool: {tool_name}")
        
        try:
            if ENHANCED_AVAILABLE and self.analytics:
                # Enhanced tool calls
                if tool_name == 'enhanced_portfolio_analysis':
                    result = self._enhanced_portfolio_analysis()
                elif tool_name == 'enhanced_symbol_analysis':
                    symbol = arguments.get('symbol', '').upper()
                    analysis_type = arguments.get('analysis_type', 'basic')
                    result = self._enhanced_symbol_analysis(symbol, analysis_type)
                elif tool_name == 'enhanced_market_analysis':
                    prompt = arguments.get('prompt', '')
                    symbols = arguments.get('symbols', [])
                    result = self._enhanced_market_analysis(prompt, symbols)
                elif tool_name == 'enhanced_options_analysis':
                    symbol = arguments.get('symbol', '').upper()
                    strategy_type = arguments.get('strategy_type', 'general')
                    result = self._enhanced_options_analysis(symbol, strategy_type)
                elif tool_name == 'run_scanner':
                    result = self._run_scanner(arguments)
                elif tool_name == 'get_full_options_chain':
                    result = self._get_full_options_chain(arguments)
                elif tool_name == 'get_market_depth':
                    result = self._get_market_depth(arguments)
                elif tool_name == 'get_news_feed':
                    result = self._get_news_feed(arguments)
                elif tool_name == 'get_historical_data':
                    result = self._get_historical_data(arguments)
                else:
                    result = self._basic_tool_call(tool_name, arguments)
            else:
                # Basic tool calls
                result = self._basic_tool_call(tool_name, arguments)
            
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': self._format_result(result)
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Tool execution error: {e}", exc_info=True)
            return {
                'error': {
                    'code': -32603,
                    'message': f'Tool execution failed: {str(e)}'
                }
            }
    
    def _enhanced_portfolio_analysis(self):
        """Enhanced portfolio analysis"""
        try:
            # Get portfolio data from database
            portfolio_data = self._get_portfolio_from_db()
            
            # Add enhanced analysis if available
            if self.analytics:
                enhanced_context = self.analytics.get_portfolio_context()
                portfolio_data.update(enhanced_context)
            
            return {
                'type': 'enhanced_portfolio',
                'data': portfolio_data,
                'capabilities': {
                    'ibkr_integration': IBKR_AVAILABLE,
                    'intelligent_context': True,
                    'options_analysis': True
                }
            }
        except Exception as e:
            logger.error(f"Portfolio analysis error: {e}")
            return {'error': f'Portfolio analysis failed: {e}'}
    
    def _enhanced_symbol_analysis(self, symbol: str, analysis_type: str):
        """Enhanced symbol analysis"""
        try:
            result = {
                'symbol': symbol,
                'analysis_type': analysis_type,
                'portfolio_context': self._get_symbol_portfolio_context(symbol),
                'timestamp': datetime.now().isoformat()
            }
            
            # Add enhanced market data if available
            if self.analytics and IBKR_AVAILABLE:
                market_data = self.analytics.get_enhanced_market_data(symbol)
                result['market_data'] = market_data
                
                if 'options' in analysis_type.lower():
                    options_data = self.analytics.get_options_analysis(symbol)
                    result['options_analysis'] = options_data
            
            return result
        except Exception as e:
            logger.error(f"Symbol analysis error: {e}")
            return {'error': f'Symbol analysis failed: {e}'}
    
    def _enhanced_market_analysis(self, prompt: str, symbols: list):
        """Enhanced market analysis"""
        try:
            result = {
                'prompt': prompt,
                'symbols': symbols,
                'analysis': f"Enhanced market analysis for: {', '.join(symbols)}" if symbols else "General market analysis",
                'timestamp': datetime.now().isoformat()
            }
            
            # Add context management
            if self.context_manager:
                context = self.context_manager.get_context_for_claude(prompt, symbols)
                result['intelligent_context'] = context
            
            return result
        except Exception as e:
            logger.error(f"Market analysis error: {e}")
            return {'error': f'Market analysis failed: {e}'}
    
    def _enhanced_options_analysis(self, symbol: str, strategy_type: str):
        """Enhanced options analysis"""
        try:
            result = {
                'symbol': symbol,
                'strategy_type': strategy_type,
                'portfolio_impact': self._get_symbol_portfolio_context(symbol),
                'timestamp': datetime.now().isoformat()
            }
            
            if self.analytics and IBKR_AVAILABLE:
                options_data = self.analytics.get_options_analysis(symbol)
                result['options_data'] = options_data
            else:
                result['note'] = 'Install ib_insync for live options data'
            
            return result
        except Exception as e:
            logger.error(f"Options analysis error: {e}")
            return {'error': f'Options analysis failed: {e}'}
    
    def _run_scanner(self, args):
        """Run IBKR scanner with enhanced popular scan support"""
        scanner_type = args.get('scanner_type', 'TOP_PERC_GAIN')
        limit = args.get('limit', 20)
        category = args.get('category')
        
        try:
            if IBKR_AVAILABLE:
                from gallump.core.scanner import IBKRScanner
                
                scanner = IBKRScanner()
                if scanner.connect():
                    # Use the enhanced popular scan method for better optimization
                    results = scanner.run_popular_scan(scanner_type, limit=limit)
                    
                    # Get scan info for better formatting
                    scan_info = scanner.get_scan_info(scanner_type)
                    scan_name = scan_info.get('name', scanner_type) if scan_info else scanner_type
                    scan_category = scan_info.get('category', 'unknown') if scan_info else 'unknown'
                    
                    # Format results with enhanced information
                    output = f"📊 **{scan_name}** Scanner Results\n"
                    output += f"Category: {scan_category.title()} | Count: {len(results)}\n\n"
                    
                    if not results:
                        output += "No results found for current market conditions.\n"
                    else:
                        for i, item in enumerate(results[:limit], 1):
                            symbol = item.symbol if hasattr(item, 'symbol') else item.get('symbol', 'N/A')
                            distance = item.distance if hasattr(item, 'distance') else item.get('distance', 'N/A')
                            
                            output += f"{i:2d}. **{symbol}**: {distance}"
                            
                            # Add category-specific formatting
                            if scan_category == 'momentum':
                                output += f" change"
                            elif scan_category == 'volume':
                                output += f" volume"
                            elif scan_category == 'technical':
                                output += f" vs target"
                            elif scan_category == 'options':
                                output += f" activity"
                            
                            output += "\n"
                        
                        # Add category explanation
                        if scan_info:
                            output += f"\n💡 **About {scan_name}**: {scan_info.get('description', '')}\n"
                    
                    return {'content': [{'text': output}]}
            
            # Enhanced fallback with category info
            fallback_msg = f"Scanner '{scanner_type}' not available - "
            if category:
                fallback_msg += f"check {category} scanners when market opens"
            else:
                fallback_msg += "market closed or connection unavailable"
            
            return {'content': [{'text': fallback_msg}]}
            
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
                    output = f"Options Chain for {symbol}\n\n"
                    
                    # Group by expiration
                    by_expiry = {}
                    for option in chain:
                        expiry = option.get('expiration', 'Unknown')
                        if expiry not in by_expiry:
                            by_expiry[expiry] = []
                        by_expiry[expiry].append(option)
                    
                    for expiry in sorted(by_expiry.keys())[:3]:  # Show first 3 expirations
                        output += f"\nExpiration: {expiry}\n"
                        output += "-" * 40 + "\n"
                        
                        for opt in by_expiry[expiry][:10]:  # Show first 10 strikes
                            output += f"{opt['strike']} {opt['type']}: "
                            output += f"Bid: {opt.get('bid', 0):.2f} "
                            output += f"Ask: {opt.get('ask', 0):.2f} "
                            
                            if include_greeks and 'greeks' in opt:
                                output += f"Delta: {opt['greeks'].get('delta', 0):.3f} "
                                output += f"IV: {opt['greeks'].get('iv', 0):.2%}"
                            
                            output += "\n"
                    
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
                    
                    output = f"Market Depth for {symbol}\n\n"
                    output += "BIDS:\n"
                    for bid in depth.get('bids', [])[:levels]:
                        output += f"  ${bid['price']:.2f} x {bid['size']:,}\n"
                    
                    output += "\nASKS:\n"
                    for ask in depth.get('asks', [])[:levels]:
                        output += f"  ${ask['price']:.2f} x {ask['size']:,}\n"
                    
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
                output += ":\n\n"
                
                for item in news:
                    output += f"• {item[2]}\n"  # text field
                    output += f"  {item[7]}\n\n"  # timestamp
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
                    
                    output = f"Historical Data for {symbol} ({period})\n\n"
                    
                    # Show last 10 bars
                    for bar in bars[-10:]:
                        output += f"{bar['date']}: "
                        output += f"O:{bar['open']:.2f} "
                        output += f"H:{bar['high']:.2f} "
                        output += f"L:{bar['low']:.2f} "
                        output += f"C:{bar['close']:.2f} "
                        output += f"V:{bar['volume']:,}\n"
                    
                    return {'content': [{'text': output}]}
            
            return {'content': [{'text': 'Historical data not available'}]}
            
        except Exception as e:
            logger.error(f"Historical data error: {e}")
            return {'content': [{'text': f'Historical data error: {str(e)}'}]}
    
    def _basic_tool_call(self, tool_name: str, arguments: dict):
        """Handle basic tool calls"""
        if tool_name == 'get_portfolio':
            return self._get_portfolio_from_db()
        elif tool_name == 'get_watchlist':
            return self._get_watchlist_from_db()
        else:
            return {'error': f'Unknown tool: {tool_name}'}
    
    def _get_portfolio_from_db(self):
        """Get portfolio data from database"""
        try:
            if not os.path.exists(self.db_path):
                logger.warning(f"Database not found at {self.db_path}")
                return {'status': 'no_database', 'positions': []}
            
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Try to get positions from portfolios table (JSON format)
            try:
                cursor.execute("""
                    SELECT positions, total_value, cash, buying_power, daily_pnl, total_pnl
                    FROM portfolios 
                    ORDER BY snapshot_time DESC
                    LIMIT 1
                """)
                portfolio_row = cursor.fetchone()
                
                if portfolio_row:
                    positions_json = portfolio_row['positions']
                    if positions_json:
                        import json
                        positions = json.loads(positions_json) if isinstance(positions_json, str) else []
                    else:
                        positions = []
                    
                    conn.close()
                    return {
                        'status': 'success',
                        'positions': positions,
                        'total_value': portfolio_row['total_value'],
                        'cash': portfolio_row['cash'],
                        'buying_power': portfolio_row['buying_power'],
                        'daily_pnl': portfolio_row['daily_pnl'],
                        'total_pnl': portfolio_row['total_pnl']
                    }
            except sqlite3.OperationalError as e:
                logger.warning(f"Portfolios table query failed: {e}")
            
            conn.close()
            
            # No cached data - try to get live data from IBKR
            logger.info("No cached portfolio data found, attempting live IBKR connection")
            try:
                if IBKR_AVAILABLE:
                    from gallump.core.broker import Broker
                    broker = Broker()
                    if broker.connect():
                        positions = broker.get_positions()
                        portfolio_summary = broker.get_portfolio_summary()
                        
                        # Format for MCP response
                        formatted_positions = []
                        for pos in positions:
                            formatted_positions.append({
                                'symbol': pos.get('symbol', 'N/A'),
                                'position': pos.get('position', 0),
                                'averageCost': pos.get('averageCost', 0),
                                'unrealizedPnL': pos.get('unrealizedPnL', 0),
                                'marketPrice': pos.get('marketPrice', 0)
                            })
                        
                        return {
                            'status': 'success',
                            'positions': formatted_positions,
                            'source': 'live_ibkr',
                            'total_value': portfolio_summary.get('total_value', 0),
                            'cash': portfolio_summary.get('cash', 0),
                            'buying_power': portfolio_summary.get('buying_power', 0),
                            'daily_pnl': portfolio_summary.get('daily_pnl', 0),
                            'total_pnl': sum(pos.get('unrealizedPnL', 0) for pos in formatted_positions)
                        }
            except Exception as e:
                logger.error(f"Failed to get live IBKR data: {e}")
            
            return {'status': 'no_positions', 'positions': []}
            
        except Exception as e:
            logger.error(f"Portfolio DB error: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}
    
    def _get_watchlist_from_db(self):
        """Get watchlist from database"""
        try:
            if not os.path.exists(self.db_path):
                return {'status': 'no_database', 'symbols': []}
            
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            
            cursor.execute("SELECT symbol FROM watchlist ORDER BY added_at DESC")
            symbols = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                'status': 'success',
                'symbols': symbols,
                'count': len(symbols)
            }
            
        except Exception as e:
            logger.error(f"Watchlist DB error: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _get_symbol_portfolio_context(self, symbol: str):
        """Get portfolio context for a specific symbol"""
        portfolio = self._get_portfolio_from_db()
        positions = portfolio.get('positions', [])
        
        for pos in positions:
            if pos.get('symbol') == symbol:
                return {
                    'has_position': True,
                    'position': pos.get('position'),
                    'avg_cost': pos.get('averageCost'),
                    'unrealized_pnl': pos.get('unrealizedPnL'),
                    'market_price': pos.get('marketPrice')
                }
        
        return {'has_position': False}
    
    def _format_result(self, result):
        """Format result for display"""
        if isinstance(result, dict) and 'error' in result:
            return f"❌ {result['error']}"
        
        if isinstance(result, dict):
            if result.get('type') == 'enhanced_portfolio':
                return self._format_portfolio_result(result)
            elif 'symbol' in result:
                return self._format_symbol_result(result)
            elif 'symbols' in result:
                return self._format_market_result(result)
            else:
                return self._format_generic_result(result)
        
        return str(result)
    
    def _format_portfolio_result(self, result):
        """Format portfolio analysis result"""
        data = result.get('data', {})
        positions = data.get('positions', [])
        
        if not positions:
            return "📊 **Portfolio Analysis**\n\nNo active positions found."
        
        lines = ["🚀 **Enhanced Portfolio Analysis**", "=" * 40]
        lines.append(f"📊 **Positions**: {len(positions)}")
        lines.append(f"💰 **Total P&L**: ${data.get('total_pnl', 0):+,.2f}")
        
        lines.append("\n**Top Positions**:")
        for pos in positions[:5]:
            pnl = pos.get('unrealizedPnL', 0)
            lines.append(f"• {pos.get('symbol', 'N/A')}: {pos.get('position', 0)} shares (${pnl:+,.2f})")
        
        capabilities = result.get('capabilities', {})
        lines.append(f"\n🔧 **Enhanced Features**:")
        for feature, enabled in capabilities.items():
            status = "✅" if enabled else "⚠️"
            lines.append(f"{status} {feature.replace('_', ' ').title()}")
        
        return "\n".join(lines)
    
    def _format_symbol_result(self, result):
        """Format symbol analysis result"""
        symbol = result['symbol']
        lines = [f"📈 **Enhanced Analysis: {symbol}**", "=" * 40]
        
        # Portfolio context
        portfolio_ctx = result.get('portfolio_context', {})
        if portfolio_ctx.get('has_position'):
            pos = portfolio_ctx['position']
            pnl = portfolio_ctx.get('unrealized_pnl', 0)
            lines.append(f"🎯 **Position**: {pos} shares (${pnl:+,.2f})")
        else:
            lines.append("📋 **Position**: Not currently held")
        
        # Market data
        market_data = result.get('market_data', {})
        if market_data:
            lines.append(f"💹 **Market Data**: Live data available")
        
        # Options analysis
        options_data = result.get('options_analysis', {})
        if options_data:
            lines.append(f"⚡ **Options**: Analysis available")
        
        return "\n".join(lines)
    
    def _format_market_result(self, result):
        """Format market analysis result"""
        symbols = result.get('symbols', [])
        lines = ["🌍 **Enhanced Market Analysis**", "=" * 40]
        lines.append(f"📊 **Symbols**: {', '.join(symbols)}" if symbols else "General market analysis")
        lines.append(f"🎯 **Request**: {result.get('prompt', 'N/A')}")
        
        context = result.get('intelligent_context', {})
        if context:
            lines.append(f"🧠 **Context Items**: {context.get('context_stats', {}).get('total_items', 0)}")
        
        return "\n".join(lines)
    
    def _format_generic_result(self, result):
        """Format generic result"""
        if result.get('status') == 'success':
            if 'positions' in result:
                return f"📊 Portfolio: {len(result.get('positions', []))} positions"
            elif 'symbols' in result:
                return f"👀 Watchlist: {result.get('count', 0)} symbols"
        
        return json.dumps(result, indent=2)

async def main():
    """Main entry point for Claude Desktop MCP protocol"""
    logger.info("🔌 Starting Enhanced MCP Server for Claude Desktop")
    logger.info(f"Enhanced features: {ENHANCED_AVAILABLE}")
    logger.info(f"IBKR integration: {IBKR_AVAILABLE}")
    
    server = EnhancedMCPForClaude()
    
    try:
        # Read from stdin and write to stdout (MCP protocol)
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
                logger.info(f"Received request: {request.get('method', 'unknown')}")
                
                response = server.handle_request(request)
                
                # Skip response for notifications (they return None)
                if response is None:
                    continue
                
                # Ensure proper JSON-RPC format
                formatted_response = {
                    'jsonrpc': '2.0',
                    'id': request.get('id')
                }
                
                # Wrap success responses in 'result' field
                if 'error' in response:
                    formatted_response['error'] = response['error']
                else:
                    formatted_response['result'] = response
                
                output = json.dumps(formatted_response)
                print(output, flush=True)
                logger.info(f"Sent response for request {request.get('id')}")
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                error_response = {
                    'jsonrpc': '2.0',
                    'id': None,
                    'error': {
                        'code': -32700,
                        'message': f'Parse error: {str(e)}'
                    }
                }
                print(json.dumps(error_response), flush=True)
    
    except KeyboardInterrupt:
        logger.info("MCP server stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

if __name__ == '__main__':
    # Run the async main function
    asyncio.run(main())
