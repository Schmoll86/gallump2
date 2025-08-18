"""
Context Builder Module - Aggregates all data for trading decisions
Single responsibility: Build complete context from multiple data sources
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class Context:
    """Complete context for trading decisions"""
    symbol: Optional[str]
    portfolio: Dict[str, Any]
    market_status: Dict[str, Any]
    watchlist: List[str]
    price_history: Dict[str, Any]
    news: List[Dict[str, str]]
    news_sources: List[str]
    technical_indicators: Dict[str, Any]
    options_chain: Dict[str, Any]
    scanner_alerts: List[str]
    related_tickers: List[str]
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return asdict(self)


class ContextBuilder:
    """Builds complete trading context from all data sources"""
    
    def __init__(self, broker=None, cache=None, scanner=None):
        """
        Initialize with data source connections
        
        Args:
            broker: Broker instance for market data
            cache: Cache instance for cached data
            scanner: Scanner instance for market scans
        """
        self.broker = broker
        self.cache = cache
        self.scanner = scanner
    
    def build(self, 
              symbols: List[str], 
              user_prompt: str = "",
              portfolio: Optional[Dict] = None,
              watchlist: Optional[List[str]] = None) -> Context:
        """
        Build complete context for trading decision
        
        Args:
            symbols: List of symbols to analyze
            user_prompt: User's trading thesis/question
            portfolio: Current portfolio state
            watchlist: User's watchlist
            
        Returns:
            Complete Context object with all data
        """
        # Extract primary symbol from user prompt and watchlist
        symbol = self.extract_symbol_from_thesis(user_prompt, watchlist or [])
        if not symbol and symbols:
            symbol = symbols[0]
        
        # Get market status
        market_status = self._get_market_status()
        
        # Fetch all data components
        price_history = self.fetch_price_history(symbol) if symbol else {}
        news, news_sources = self.fetch_latest_news(symbol) if symbol else ([], [])
        ta_indicators = self.fetch_ta_indicators(symbol) if symbol else {}
        options_chain = self.fetch_options_chain(symbol) if symbol else {}
        scanner_alerts = self.fetch_scanner_hits(symbol) if symbol else []
        related_tickers = self.fetch_related_tickers(symbol) if symbol else []
        
        # Use provided portfolio or fetch current
        if portfolio is None:
            portfolio = self._get_portfolio_data()
        
        # Create context
        context = Context(
            symbol=symbol,
            portfolio=portfolio,
            market_status=market_status,
            watchlist=watchlist or [],
            price_history=price_history,
            news=news,
            news_sources=news_sources,
            technical_indicators=ta_indicators,
            options_chain=options_chain,
            scanner_alerts=scanner_alerts,
            related_tickers=related_tickers,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Built context for symbol: {symbol}")
        return context
    
    def extract_symbol_from_thesis(self, thesis: str, watchlist: List) -> Optional[str]:
        """
        Extract ticker symbol from user's thesis text
        Handles both simple array and enhanced watchlist formats
        
        Args:
            thesis: User's trading thesis/prompt
            watchlist: List of symbols (strings) or watchlist items (dicts)
            
        Returns:
            Extracted symbol or None
        """
        if not thesis:
            # If no thesis but we have a primary symbol, use it
            if watchlist:
                for item in watchlist:
                    if isinstance(item, dict) and item.get('is_primary'):
                        return item.get('symbol', '').upper()
            return None
            
        thesis_upper = thesis.upper()
        
        # Handle both formats
        symbols_to_check = []
        primary_symbol = None
        
        if watchlist:
            if isinstance(watchlist[0], dict):
                # Enhanced format - extract symbols and find primary
                for item in watchlist:
                    symbol = item.get('symbol')
                    if symbol:
                        symbols_to_check.append(symbol)
                        if item.get('is_primary'):
                            primary_symbol = symbol
            else:
                # Simple format
                symbols_to_check = watchlist
        
        # First check watchlist for exact matches in thesis
        for ticker in symbols_to_check:
            if ticker.upper() in thesis_upper:
                return ticker.upper()
        
        # If no match in thesis but we have a primary, use that
        if primary_symbol:
            logger.info(f"No symbol in thesis, using primary: {primary_symbol}")
            return primary_symbol.upper()
        
        # Common pattern matching for tickers (1-5 letter words in caps)
        import re
        pattern = r'\b[A-Z]{1,5}\b'
        matches = re.findall(pattern, thesis_upper)
        
        # Return first valid match
        for match in matches:
            # Could validate against known symbols here
            if len(match) <= 5 and match not in ['I', 'A', 'THE', 'FOR', 'AND', 'OR']:
                return match
        
        return None
    
    def fetch_latest_news(self, symbol: str) -> Tuple[List[Dict[str, str]], List[str]]:
        """
        Fetch latest news for symbol
        
        Returns:
            Tuple of (news_items, source_list)
        """
        if not symbol:
            return [], []
        
        try:
            # TODO: Integrate with actual news API
            # For now, return sample data
            news_items = [
                {
                    "headline": f"{symbol} shows strong momentum",
                    "source": "MarketWatch",
                    "timestamp": datetime.now().isoformat(),
                    "sentiment": "positive"
                }
            ]
            sources = ["MarketWatch"]
            
            # Cache the news
            if self.cache:
                self.cache.set_price(f"news_{symbol}", json.dumps(news_items))
            
            return news_items, sources
            
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            return [], []
    
    def fetch_ta_indicators(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch technical analysis indicators
        
        Returns:
            Dict of technical indicators
        """
        if not symbol:
            return {}
        
        try:
            # TODO: Integrate with TA library or API
            # For now, return sample indicators
            indicators = {
                "rsi": 55.2,
                "macd": 0.15,
                "macd_signal": 0.10,
                "sma_20": 150.5,
                "sma_50": 148.2,
                "volume_avg": 1500000,
                "trend": "neutral",
                "support": 145.0,
                "resistance": 155.0
            }
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error fetching TA for {symbol}: {e}")
            return {}
    
    def fetch_options_chain(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch options chain data
        
        Returns:
            Options chain structure
        """
        if not symbol or not self.broker:
            return {}
        
        try:
            # Check cache first
            if self.cache:
                cached = self.cache.get_options_chain(symbol)
                if cached:
                    return cached
            
            # Try to fetch real options data from IBKR
            if not self.broker or not self.broker.is_connected():
                logger.warning(f"Cannot fetch options chain for {symbol} - broker not connected")
                return None
            
            # Use the new broker method to fetch real options
            if hasattr(self.broker, 'get_options_chain'):
                chain = self.broker.get_options_chain(symbol)
                if chain:
                    # Add cached_at timestamp for freshness tracking
                    from datetime import datetime
                    chain['cached_at'] = datetime.now().isoformat()
                    
                    # Cache the chain
                    if self.cache:
                        self.cache.set_options_chain(symbol, chain)
                    
                    return chain
            
            # If no options data available
            logger.info(f"Options chain not available for {symbol}")
            return None
            
            # Cache the chain
            if self.cache:
                self.cache.set_options_chain(symbol, chain)
            
            return chain
            
        except Exception as e:
            logger.error(f"Error fetching options chain for {symbol}: {e}")
            return {}
    
    def fetch_scanner_hits(self, symbol: str) -> List[str]:
        """
        Fetch scanner alerts for symbol
        
        Returns:
            List of scanner alerts/hits
        """
        if not symbol:
            return []
        
        try:
            # TODO: Check if symbol appears in recent scanner results
            alerts = []
            
            # Check cached scanner results
            if self.cache:
                for scan_type in ["TOP_PERC_GAIN", "MOST_ACTIVE", "HIGH_OPT_IMP_VOLAT"]:
                    results = self.cache.get_scanner_results(scan_type)
                    if results:
                        for result in results:
                            if result.get('symbol') == symbol:
                                alerts.append(f"Appeared in {scan_type} scan")
            
            # Add any hardcoded alerts for testing
            if not alerts:
                alerts = ["Unusual volume detected", "Options activity spike"]
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error fetching scanner hits for {symbol}: {e}")
            return []
    
    def fetch_price_history(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch price history for symbol
        
        Returns:
            Price history data
        """
        if not symbol:
            return {}
        
        try:
            # Get latest price from broker if available
            latest_price = None
            if self.broker and self.broker.is_connected():
                prices = self.broker.get_last_prices([symbol])
                latest_price = prices.get(symbol, 0)
            
            # Check cache for historical data
            if self.cache and not latest_price:
                latest_price = self.cache.get_last_price(symbol)
            
            # Build history structure
            history = {
                "symbol": symbol,
                "latest": latest_price or 0,
                "ohlc": [
                    # Sample 5-day history
                    {"date": "2025-01-10", "open": 148.0, "high": 152.0, "low": 147.5, "close": 151.0, "volume": 1500000},
                    {"date": "2025-01-11", "open": 151.0, "high": 153.0, "low": 150.0, "close": 152.5, "volume": 1600000},
                    {"date": "2025-01-12", "open": 152.5, "high": 154.0, "low": 151.5, "close": 153.0, "volume": 1400000},
                    {"date": "2025-01-13", "open": 153.0, "high": 155.0, "low": 152.0, "close": 154.5, "volume": 1700000},
                    {"date": "2025-01-14", "open": 154.5, "high": 156.0, "low": 154.0, "close": latest_price or 155.0, "volume": 1800000}
                ],
                "change_pct": 2.5,
                "change_dollar": 3.75
            }
            
            return history
            
        except Exception as e:
            logger.error(f"Error fetching price history for {symbol}: {e}")
            return {}
    
    def fetch_related_tickers(self, symbol: str) -> List[str]:
        """
        Fetch related/correlated tickers
        
        Returns:
            List of related ticker symbols
        """
        if not symbol:
            return []
        
        try:
            # TODO: Implement sector/correlation logic
            # For now, return sector peers based on common sectors
            sector_peers = {
                "AAPL": ["MSFT", "GOOGL", "META", "NVDA"],
                "XOM": ["CVX", "COP", "OXY", "SLB"],
                "JPM": ["BAC", "WFC", "GS", "MS"],
                "TSLA": ["RIVN", "LCID", "NIO", "F"]
            }
            
            return sector_peers.get(symbol, ["SPY", "QQQ", "IWM"])
            
        except Exception as e:
            logger.error(f"Error fetching related tickers for {symbol}: {e}")
            return []
    
    def _get_market_status(self) -> Dict[str, Any]:
        """Get current market status"""
        if self.broker and self.broker.is_connected():
            return self.broker.get_market_status()
        
        # Default status
        return {
            "is_open": False,
            "next_open": "9:30 AM ET",
            "next_close": "4:00 PM ET",
            "current_time": datetime.now().isoformat()
        }
    
    def _get_portfolio_data(self) -> Dict[str, Any]:
        """Get current portfolio data"""
        if self.broker and self.broker.is_connected():
            return self.broker.get_portfolio()
        
        # Check cache for snapshot
        if self.cache:
            snapshot = self.cache.get_portfolio_snapshot()
            if snapshot:
                return snapshot
        
        # Default empty portfolio
        return {
            "total_value": 0,
            "buying_power": 0,
            "positions": [],
            "timestamp": datetime.now().isoformat()
        }


# Standalone function for backwards compatibility
def build(symbols: List[str], user_prompt: str = "") -> Context:
    """
    Legacy function for building context
    Creates a default ContextBuilder and builds context
    """
    builder = ContextBuilder()
    return builder.build(symbols, user_prompt)