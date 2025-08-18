"""
Enhanced MCP Analytics - Minimal Complexity, Maximum Capability
Uses existing infrastructure with smart caching and context building
"""

import os
import time
import sqlite3
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class EnhancedMCPAnalytics:
    """
    Enhanced MCP Analytics with minimal complexity
    - Uses existing Gallump DB (read-only)
    - Temporary in-memory cache only
    - Same IBKR connection for live data
    - No additional persistent storage
    """
    
    def __init__(self, ib_connection=None):
        self.ib = ib_connection
        self.gallump_db_path = os.getenv('GALLUMP_DB_PATH', '/Users/schmoll/Desktop/Gallump/data/trading.db')
        
        # Simple in-memory cache (expires on restart)
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_ttl = {
            'market_data': 60,      # 1 minute
            'news': 900,            # 15 minutes  
            'technicals': 300,      # 5 minutes
            'options': 300,         # 5 minutes
            'sector_data': 1800     # 30 minutes
        }
        
        # Connect to Gallump DB (read-only)
        self._connect_to_gallump_db()
    
    def _connect_to_gallump_db(self):
        """Connect to existing Gallump database in read-only mode"""
        try:
            self.gallump_db = sqlite3.connect(f"file:{self.gallump_db_path}?mode=ro", uri=True)
            self.gallump_db.row_factory = sqlite3.Row
            logger.info("Connected to Gallump database (read-only)")
        except Exception as e:
            logger.error(f"Failed to connect to Gallump DB: {e}")
            self.gallump_db = None
    
    def _get_cached(self, key: str, data_type: str = 'market_data') -> Optional[Any]:
        """Get cached data if still valid"""
        if key not in self.cache:
            return None
        
        age = time.time() - self.cache_timestamps.get(key, 0)
        ttl = self.cache_ttl.get(data_type, 300)
        
        if age < ttl:
            return self.cache[key]
        else:
            # Expired - remove from cache
            self.cache.pop(key, None)
            self.cache_timestamps.pop(key, None)
            return None
    
    def _set_cached(self, key: str, value: Any, data_type: str = 'market_data'):
        """Cache data with timestamp"""
        self.cache[key] = value
        self.cache_timestamps[key] = time.time()
    
    def get_portfolio_context(self) -> Dict:
        """Get current portfolio from Gallump DB"""
        if not self.gallump_db:
            return {}
        
        try:
            cursor = self.gallump_db.cursor()
            
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
                else:
                    positions = []
            except sqlite3.OperationalError:
                # Fallback to old schema if needed
                try:
                    cursor.execute("""
                        SELECT symbol, position, averageCost, unrealizedPnL, marketPrice
                        FROM positions 
                        WHERE position != 0
                    """)
                    positions = [dict(row) for row in cursor.fetchall()]
                except sqlite3.OperationalError:
                    positions = []
            
            # Get recent strategies for context
            cursor.execute("""
                SELECT name, symbol, confidence, risk_level, created_at
                FROM strategies 
                WHERE created_at > datetime('now', '-7 days')
                ORDER BY created_at DESC
                LIMIT 10
            """)
            recent_strategies = [dict(row) for row in cursor.fetchall()]
            
            # Get watchlist
            cursor.execute("SELECT symbol, added_at FROM watchlist ORDER BY added_at DESC")
            watchlist = [dict(row) for row in cursor.fetchall()]
            
            return {
                'positions': positions,
                'recent_strategies': recent_strategies,
                'watchlist': watchlist,
                'total_positions': len(positions),
                'context_loaded_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio context: {e}")
            return {}
    
    def get_enhanced_market_data(self, symbol: str) -> Dict:
        """Get comprehensive market data with caching"""
        cache_key = f"market_data_{symbol}"
        cached = self._get_cached(cache_key, 'market_data')
        if cached:
            return cached
        
        try:
            # This would integrate with your existing IBKR connection
            market_data = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'price_data': self._get_price_data(symbol),
                'volume_analysis': self._get_volume_analysis(symbol),
                'technical_indicators': self._get_technical_indicators(symbol),
                'support_resistance': self._get_support_resistance(symbol)
            }
            
            self._set_cached(cache_key, market_data, 'market_data')
            return market_data
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return {'error': str(e), 'symbol': symbol}
    
    def get_options_analysis(self, symbol: str) -> Dict:
        """Get options analysis with caching"""
        cache_key = f"options_{symbol}"
        cached = self._get_cached(cache_key, 'options')
        if cached:
            return cached
        
        try:
            options_data = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'iv_analysis': self._get_iv_analysis(symbol),
                'options_flow': self._get_options_flow(symbol),
                'greeks_summary': self._get_greeks_summary(symbol),
                'unusual_activity': self._detect_unusual_options_activity(symbol)
            }
            
            self._set_cached(cache_key, options_data, 'options')
            return options_data
            
        except Exception as e:
            logger.error(f"Error getting options data for {symbol}: {e}")
            return {'error': str(e), 'symbol': symbol}
    
    def get_news_sentiment(self, symbol: str, hours: int = 24) -> Dict:
        """Get news sentiment with caching"""
        cache_key = f"news_{symbol}_{hours}h"
        cached = self._get_cached(cache_key, 'news')
        if cached:
            return cached
        
        try:
            news_data = {
                'symbol': symbol,
                'timeframe_hours': hours,
                'timestamp': datetime.now().isoformat(),
                'news_articles': self._get_recent_news(symbol, hours),
                'sentiment_score': self._calculate_sentiment_score(symbol),
                'key_themes': self._extract_news_themes(symbol)
            }
            
            self._set_cached(cache_key, news_data, 'news')
            return news_data
            
        except Exception as e:
            logger.error(f"Error getting news for {symbol}: {e}")
            return {'error': str(e), 'symbol': symbol}
    
    def analyze_with_full_context(self, prompt: str, symbols: List[str]) -> Dict:
        """Comprehensive analysis using all available context"""
        
        # Build context from multiple sources
        context = {
            'timestamp': datetime.now().isoformat(),
            'portfolio': self.get_portfolio_context(),
            'symbols_analysis': {}
        }
        
        # Get enhanced data for each symbol
        for symbol in symbols:
            context['symbols_analysis'][symbol] = {
                'market_data': self.get_enhanced_market_data(symbol),
                'options': self.get_options_analysis(symbol),
                'news_sentiment': self.get_news_sentiment(symbol),
                'correlation_analysis': self._get_correlation_analysis(symbol, symbols)
            }
        
        # Add market-wide context
        context['market_context'] = {
            'sector_performance': self._get_sector_performance(),
            'market_breadth': self._get_market_breadth(),
            'vix_analysis': self._get_vix_analysis(),
            'economic_calendar': self._get_economic_events()
        }
        
        return {
            'analysis_type': 'comprehensive',
            'context_data': context,
            'cache_stats': self._get_cache_stats(),
            'mode': 'READ_ONLY',
            'can_execute': False  # Safety guarantee
        }
    
    def _get_cache_stats(self) -> Dict:
        """Get cache utilization stats"""
        return {
            'cached_items': len(self.cache),
            'cache_hit_rate': 'Not tracked (stateless)',
            'oldest_cache_entry': min(self.cache_timestamps.values()) if self.cache_timestamps else None,
            'memory_usage': 'Minimal (in-memory only)'
        }
    
    # Placeholder methods for actual implementation
    def _get_price_data(self, symbol: str) -> Dict:
        return {'current_price': 0, 'day_change': 0, 'volume': 0}
    
    def _get_volume_analysis(self, symbol: str) -> Dict:
        return {'avg_volume': 0, 'volume_spike': False, 'relative_volume': 1.0}
    
    def _get_technical_indicators(self, symbol: str) -> Dict:
        return {'rsi': 50, 'macd': 'neutral', 'bollinger_position': 'middle'}
    
    def _get_support_resistance(self, symbol: str) -> Dict:
        return {'support_levels': [], 'resistance_levels': [], 'key_levels': []}
    
    def _get_iv_analysis(self, symbol: str) -> Dict:
        return {'current_iv': 0, 'iv_percentile': 50, 'iv_rank': 'medium'}
    
    def _get_options_flow(self, symbol: str) -> Dict:
        return {'unusual_activity': [], 'big_trades': [], 'put_call_ratio': 1.0}
    
    def _get_greeks_summary(self, symbol: str) -> Dict:
        return {'total_delta': 0, 'total_gamma': 0, 'theta_decay': 0}
    
    def _detect_unusual_options_activity(self, symbol: str) -> Dict:
        return {'alerts': [], 'volume_spikes': [], 'unusual_spreads': []}
    
    def _get_recent_news(self, symbol: str, hours: int) -> List[Dict]:
        return []
    
    def _calculate_sentiment_score(self, symbol: str) -> float:
        return 0.0  # -1.0 to 1.0
    
    def _extract_news_themes(self, symbol: str) -> List[str]:
        return []
    
    def _get_correlation_analysis(self, symbol: str, other_symbols: List[str]) -> Dict:
        return {'correlations': {}, 'beta': 1.0}
    
    def _get_sector_performance(self) -> Dict:
        return {'sector_rotation': {}, 'relative_strength': {}}
    
    def _get_market_breadth(self) -> Dict:
        return {'advance_decline': 0, 'new_highs_lows': 0, 'vix': 0}
    
    def _get_vix_analysis(self) -> Dict:
        return {'current_vix': 0, 'vix_term_structure': {}, 'fear_greed': 'neutral'}
    
    def _get_economic_events(self) -> List[Dict]:
        return []