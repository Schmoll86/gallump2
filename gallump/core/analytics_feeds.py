"""
IBKR Data Feeds Integration for MCP Analytics
Handles Level 2, options chains, Greeks, news subscriptions
with intelligent context management
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from ib_insync import *
import threading
import queue
from .analytics_context import IntelligentContextManager, ContextPriority

logger = logging.getLogger(__name__)

class MCPDataFeeds:
    """
    Manages IBKR data subscriptions for MCP Analytics
    - Level 2 market data
    - Options chains with Greeks
    - News feeds
    - Real-time updates with context management
    """
    
    def __init__(self, ib_connection=None, context_manager=None):
        self.ib = ib_connection
        self.context_manager = context_manager or IntelligentContextManager()
        
        # Active subscriptions
        self.active_tickers = {}
        self.active_news_subscriptions = {}
        self.options_subscriptions = {}
        
        # Data queues for processing
        self.market_data_queue = queue.Queue()
        self.news_queue = queue.Queue()
        self.options_queue = queue.Queue()
        
        # Processing threads
        self.processing_threads = []
        self.running = False
        
        # Subscription limits (manage IBKR quotas)
        self.max_tickers = 100
        self.max_news_symbols = 50
        self.max_options_chains = 25
    
    def start_feeds(self, symbols: List[str], include_options: bool = True, include_news: bool = True):
        """Start data feeds for symbols with intelligent subscription management"""
        
        if not self.ib or not self.ib.isConnected():
            logger.error("IBKR not connected - cannot start feeds")
            return False
        
        self.running = True
        
        # Prioritize symbols based on portfolio and focus
        prioritized_symbols = self._prioritize_symbols(symbols)
        
        # Start market data subscriptions
        self._start_market_data_feeds(prioritized_symbols[:self.max_tickers])
        
        # Start options feeds for high-priority symbols
        if include_options:
            options_symbols = prioritized_symbols[:self.max_options_chains]
            self._start_options_feeds(options_symbols)
        
        # Start news feeds
        if include_news:
            news_symbols = prioritized_symbols[:self.max_news_symbols]
            self._start_news_feeds(news_symbols)
        
        # Start processing threads
        self._start_processing_threads()
        
        logger.info(f"Started MCP data feeds for {len(prioritized_symbols)} symbols")
        return True
    
    def stop_feeds(self):
        """Stop all data feeds and processing"""
        self.running = False
        
        # Cancel IBKR subscriptions
        for ticker in self.active_tickers.values():
            self.ib.cancelMktData(ticker.contract)
        
        for contract in self.options_subscriptions.keys():
            self.ib.cancelMktData(contract)
        
        # Wait for processing threads to finish
        for thread in self.processing_threads:
            thread.join(timeout=5)
        
        self.active_tickers.clear()
        self.options_subscriptions.clear()
        self.active_news_subscriptions.clear()
        
        logger.info("Stopped all MCP data feeds")
    
    def _prioritize_symbols(self, symbols: List[str]) -> List[str]:
        """Prioritize symbols based on portfolio, watchlist, and focus"""
        
        # Get portfolio positions (highest priority)
        portfolio_symbols = self._get_portfolio_symbols()
        
        # Get watchlist symbols (medium priority)
        watchlist_symbols = self._get_watchlist_symbols()
        
        # Combine and deduplicate while maintaining priority
        prioritized = []
        
        # 1. Portfolio symbols first
        for symbol in portfolio_symbols:
            if symbol not in prioritized:
                prioritized.append(symbol)
        
        # 2. Requested symbols that are in watchlist
        for symbol in symbols:
            if symbol in watchlist_symbols and symbol not in prioritized:
                prioritized.append(symbol)
        
        # 3. Other requested symbols
        for symbol in symbols:
            if symbol not in prioritized:
                prioritized.append(symbol)
        
        # 4. Remaining watchlist symbols
        for symbol in watchlist_symbols:
            if symbol not in prioritized:
                prioritized.append(symbol)
        
        return prioritized
    
    def _start_market_data_feeds(self, symbols: List[str]):
        """Start Level 2 market data feeds"""
        
        for symbol in symbols:
            try:
                contract = Stock(symbol, 'SMART', 'USD')
                
                # Request Level 2 market data
                ticker = self.ib.reqMktData(
                    contract,
                    genericTickList='100,101,104,106,165,221,225,233,236,258',
                    snapshot=False,
                    regulatorySnapshot=False
                )
                
                # Set up callback for real-time updates
                ticker.updateEvent += self._on_market_data_update
                
                self.active_tickers[symbol] = ticker
                
                logger.debug(f"Started market data feed for {symbol}")
                
            except Exception as e:
                logger.error(f"Failed to start market data for {symbol}: {e}")
    
    def _start_options_feeds(self, symbols: List[str]):
        """Start options chain and Greeks feeds"""
        
        for symbol in symbols:
            try:
                # Get options parameters
                stock_contract = Stock(symbol, 'SMART', 'USD')
                
                # Request options parameters first
                def on_options_params(ticker):
                    self._setup_options_chain_subscription(symbol, ticker)
                
                # This is a simplified version - you'd implement full options chain subscription
                self._request_options_chain(symbol)
                
            except Exception as e:
                logger.error(f"Failed to start options feed for {symbol}: {e}")
    
    def _start_news_feeds(self, symbols: List[str]):
        """Start news feeds for symbols"""
        
        try:
            # Subscribe to news for all symbols
            for symbol in symbols:
                # IBKR news subscription
                news_providers = [
                    'BRFUPDN',  # Briefing.com
                    'DJNL',     # Dow Jones
                    'FLY',      # Fly on the Wall
                ]
                
                for provider in news_providers:
                    try:
                        news_articles = self.ib.reqNewsArticle(
                            providerCode=provider,
                            articleId='',
                            newsArticleOptions=[]
                        )
                        
                        # Set up news callback
                        self.ib.newsBulletinEvent += self._on_news_update
                        
                    except Exception as e:
                        logger.debug(f"News provider {provider} not available: {e}")
                
                self.active_news_subscriptions[symbol] = True
                
        except Exception as e:
            logger.error(f"Failed to start news feeds: {e}")
    
    def _on_market_data_update(self, ticker):
        """Handle real-time market data updates"""
        
        if not self.running:
            return
        
        try:
            symbol = ticker.contract.symbol
            
            # Extract relevant market data
            market_data = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'price': ticker.marketPrice(),
                'bid': ticker.bid,
                'ask': ticker.ask,
                'volume': ticker.volume,
                'day_high': ticker.high,
                'day_low': ticker.low,
                'day_change': ticker.change,
                'day_change_percent': ticker.changePercent,
                'bid_size': ticker.bidSize,
                'ask_size': ticker.askSize,
                'last_size': ticker.lastSize,
                'halted': ticker.halted
            }
            
            # Add Level 2 data if available
            if hasattr(ticker, 'domBids') and ticker.domBids:
                market_data['level2_bids'] = [(bid.price, bid.size) for bid in ticker.domBids[:5]]
            
            if hasattr(ticker, 'domAsks') and ticker.domAsks:
                market_data['level2_asks'] = [(ask.price, ask.size) for ask in ticker.domAsks[:5]]
            
            # Queue for processing
            self.market_data_queue.put(('market_data', symbol, market_data))
            
        except Exception as e:
            logger.error(f"Error processing market data update: {e}")
    
    def _on_news_update(self, news):
        """Handle real-time news updates"""
        
        if not self.running:
            return
        
        try:
            # Extract news data
            news_data = {
                'headline': news.message,
                'timestamp': datetime.now(),
                'provider': getattr(news, 'providerCode', 'Unknown'),
                'article_id': getattr(news, 'articleId', ''),
                'sentiment_score': self._analyze_news_sentiment(news.message)
            }
            
            # Determine relevant symbols
            relevant_symbols = self._extract_symbols_from_news(news.message)
            
            # Queue for processing
            self.news_queue.put(('news', relevant_symbols, news_data))
            
        except Exception as e:
            logger.error(f"Error processing news update: {e}")
    
    def _request_options_chain(self, symbol: str):
        """Request options chain and Greeks for symbol"""
        
        try:
            stock_contract = Stock(symbol, 'SMART', 'USD')
            
            # Get option parameters
            option_params = self.ib.reqSecDefOptParams(
                underlyingSymbol=symbol,
                futFopExchange='',
                underlyingSecType='STK',
                underlyingConId=8314
            )
            
            if option_params:
                # Process options chain
                self._process_options_chain(symbol, option_params)
            
        except Exception as e:
            logger.error(f"Error requesting options chain for {symbol}: {e}")
    
    def _process_options_chain(self, symbol: str, option_params):
        """Process options chain data and Greeks"""
        
        try:
            current_price = self._get_current_price(symbol)
            if not current_price:
                return
            
            options_data = {
                'symbol': symbol,
                'underlying_price': current_price,
                'timestamp': datetime.now(),
                'expirations': {},
                'greeks_summary': {},
                'unusual_activity': []
            }
            
            # Process each expiration
            for param in option_params:
                expiration = param.expiration
                strikes = param.strikes
                
                # Filter strikes around current price (±20%)
                price_range = current_price * 0.2
                relevant_strikes = [s for s in strikes 
                                  if current_price - price_range <= s <= current_price + price_range]
                
                expiration_data = {}
                
                for strike in relevant_strikes:
                    # Create option contracts
                    call_contract = Option(symbol, expiration, strike, 'C', 'SMART')
                    put_contract = Option(symbol, expiration, strike, 'P', 'SMART')
                    
                    try:
                        # Request market data for options
                        call_ticker = self.ib.reqMktData(call_contract, snapshot=True)
                        put_ticker = self.ib.reqMktData(put_contract, snapshot=True)
                        
                        # Wait for data
                        self.ib.sleep(0.1)
                        
                        expiration_data[strike] = {
                            'call': self._extract_option_data(call_ticker),
                            'put': self._extract_option_data(put_ticker)
                        }
                        
                    except Exception as e:
                        logger.debug(f"Could not get data for {symbol} {expiration} {strike}: {e}")
                
                if expiration_data:
                    options_data['expirations'][expiration] = expiration_data
            
            # Calculate Greeks summary
            options_data['greeks_summary'] = self._calculate_greeks_summary(options_data)
            
            # Detect unusual activity
            options_data['unusual_activity'] = self._detect_unusual_activity(options_data)
            
            # Queue for processing
            self.options_queue.put(('options', symbol, options_data))
            
        except Exception as e:
            logger.error(f"Error processing options chain for {symbol}: {e}")
    
    def _extract_option_data(self, ticker) -> Dict:
        """Extract essential option data"""
        
        return {
            'bid': ticker.bid if ticker.bid > 0 else None,
            'ask': ticker.ask if ticker.ask > 0 else None,
            'last': ticker.last if ticker.last > 0 else None,
            'volume': ticker.volume,
            'open_interest': getattr(ticker, 'openInterest', 0),
            'implied_volatility': getattr(ticker, 'impliedVolatility', None),
            'delta': getattr(ticker, 'delta', None),
            'gamma': getattr(ticker, 'gamma', None),
            'theta': getattr(ticker, 'theta', None),
            'vega': getattr(ticker, 'vega', None)
        }
    
    def _start_processing_threads(self):
        """Start background threads to process data queues"""
        
        # Market data processor
        market_thread = threading.Thread(target=self._process_market_data_queue)
        market_thread.daemon = True
        market_thread.start()
        self.processing_threads.append(market_thread)
        
        # News processor
        news_thread = threading.Thread(target=self._process_news_queue)
        news_thread.daemon = True
        news_thread.start()
        self.processing_threads.append(news_thread)
        
        # Options processor
        options_thread = threading.Thread(target=self._process_options_queue)
        options_thread.daemon = True
        options_thread.start()
        self.processing_threads.append(options_thread)
    
    def _process_market_data_queue(self):
        """Process market data updates"""
        
        while self.running:
            try:
                if not self.market_data_queue.empty():
                    data_type, symbol, data = self.market_data_queue.get(timeout=1)
                    
                    # Add to context manager
                    self.context_manager.add_market_data(symbol, data, data_type)
                    
                else:
                    time.sleep(0.1)
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing market data: {e}")
    
    def _process_news_queue(self):
        """Process news updates"""
        
        while self.running:
            try:
                if not self.news_queue.empty():
                    data_type, symbols, data = self.news_queue.get(timeout=1)
                    
                    # Add to context manager
                    self.context_manager.add_news_data([data], symbols)
                    
                else:
                    time.sleep(0.1)
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing news: {e}")
    
    def _process_options_queue(self):
        """Process options data updates"""
        
        while self.running:
            try:
                if not self.options_queue.empty():
                    data_type, symbol, data = self.options_queue.get(timeout=1)
                    
                    # Add to context manager
                    greeks = data.get('greeks_summary', {})
                    self.context_manager.add_options_data(symbol, data, greeks)
                    
                else:
                    time.sleep(0.1)
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing options data: {e}")
    
    # Helper methods
    def _get_portfolio_symbols(self) -> List[str]:
        """Get symbols from current portfolio"""
        # Implement with Gallump DB query
        return []
    
    def _get_watchlist_symbols(self) -> List[str]:
        """Get symbols from watchlist"""
        # Implement with Gallump DB query
        return []
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        ticker = self.active_tickers.get(symbol)
        return ticker.marketPrice() if ticker else None
    
    def _analyze_news_sentiment(self, headline: str) -> float:
        """Analyze news sentiment (-1.0 to 1.0)"""
        # Implement sentiment analysis
        positive_words = ['up', 'gain', 'bullish', 'positive', 'growth', 'strong']
        negative_words = ['down', 'loss', 'bearish', 'negative', 'decline', 'weak']
        
        headline_lower = headline.lower()
        pos_count = sum(1 for word in positive_words if word in headline_lower)
        neg_count = sum(1 for word in negative_words if word in headline_lower)
        
        if pos_count + neg_count == 0:
            return 0.0
        
        return (pos_count - neg_count) / (pos_count + neg_count)
    
    def _extract_symbols_from_news(self, headline: str) -> List[str]:
        """Extract stock symbols from news headline"""
        # Simple implementation - could be enhanced with NLP
        import re
        symbols = re.findall(r'\b[A-Z]{1,5}\b', headline)
        return [s for s in symbols if len(s) <= 5 and s.isalpha()]
    
    def _calculate_greeks_summary(self, options_data: Dict) -> Dict:
        """Calculate summary of Greeks across all options"""
        total_delta = 0
        total_gamma = 0
        total_theta = 0
        total_vega = 0
        count = 0
        
        for expiration, strikes in options_data.get('expirations', {}).items():
            for strike, option_data in strikes.items():
                for option_type in ['call', 'put']:
                    opt = option_data.get(option_type, {})
                    if opt.get('delta') is not None:
                        total_delta += opt['delta']
                        count += 1
                    if opt.get('gamma') is not None:
                        total_gamma += opt['gamma']
                    if opt.get('theta') is not None:
                        total_theta += opt['theta']
                    if opt.get('vega') is not None:
                        total_vega += opt['vega']
        
        return {
            'total_delta': total_delta,
            'total_gamma': total_gamma,
            'total_theta': total_theta,
            'total_vega': total_vega,
            'option_count': count
        }
    
    def _detect_unusual_activity(self, options_data: Dict) -> List[Dict]:
        """Detect unusual options activity"""
        unusual = []
        
        for expiration, strikes in options_data.get('expirations', {}).items():
            for strike, option_data in strikes.items():
                for option_type in ['call', 'put']:
                    opt = option_data.get(option_type, {})
                    volume = opt.get('volume', 0)
                    open_interest = opt.get('open_interest', 0)
                    
                    # Simple unusual activity detection
                    if volume > 1000 and volume > open_interest * 2:
                        unusual.append({
                            'type': 'high_volume',
                            'expiration': expiration,
                            'strike': strike,
                            'option_type': option_type,
                            'volume': volume,
                            'open_interest': open_interest,
                            'ratio': volume / max(open_interest, 1)
                        })
        
        return unusual