# price_fetcher.py - Fetches current prices - ONE job only
import asyncio
import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
from ib_insync import Stock, Ticker
from gallump_next.core.types import MarketData
from gallump_next.core.connection_pool import ConnectionPool

class PriceFetcher:
    """Fetches current prices - ONE job only"""
    
    def __init__(self, connection_pool: ConnectionPool):
        self.pool = connection_pool
        self.logger = logging.getLogger(__name__)
        
    async def get_price(self, symbol: str) -> Optional[MarketData]:
        """Get single symbol price"""
        try:
            async def fetch_price(conn):
                # Create and qualify contract
                contract = Stock(symbol, 'SMART', 'USD')
                qualified = conn.ib.qualifyContracts(contract)
                
                if not qualified:
                    self.logger.warning(f"Could not qualify contract for {symbol}")
                    return None
                
                # Request market data
                ticker = conn.ib.reqMktData(qualified[0], snapshot=True)
                
                # Wait for data (max 5 seconds)
                for _ in range(50):  # 50 * 0.1 = 5 seconds
                    await asyncio.sleep(0.1)
                    if ticker.last or ticker.bid or ticker.ask:
                        break
                
                # Cancel market data subscription
                conn.ib.cancelMktData(qualified[0])
                
                return self._ticker_to_market_data(ticker, symbol)
            
            return await self.pool.with_connection(fetch_price)
            
        except Exception as e:
            self.logger.error(f"Error fetching price for {symbol}: {e}")
            return None
    
    async def get_prices(self, symbols: List[str]) -> Dict[str, MarketData]:
        """Get multiple prices in parallel"""
        tasks = [self.get_price(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        output = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                self.logger.error(f"Error fetching {symbol}: {result}")
            elif result:
                output[symbol] = result
        
        return output
    
    async def get_price_batch(self, symbols: List[str], batch_size: int = 10) -> Dict[str, MarketData]:
        """Get prices in batches to avoid overwhelming the connection"""
        all_results = {}
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            batch_results = await self.get_prices(batch)
            all_results.update(batch_results)
            
            # Small delay between batches
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.5)
        
        return all_results
    
    def _ticker_to_market_data(self, ticker: Ticker, symbol: str) -> MarketData:
        """Convert IB ticker to MarketData object"""
        return MarketData(
            symbol=symbol,
            bid=Decimal(str(ticker.bid)) if ticker.bid and ticker.bid > 0 else Decimal("0"),
            ask=Decimal(str(ticker.ask)) if ticker.ask and ticker.ask > 0 else Decimal("0"),
            last=Decimal(str(ticker.last)) if ticker.last and ticker.last > 0 else Decimal("0"),
            volume=ticker.volume if ticker.volume else 0,
            bid_size=ticker.bidSize if ticker.bidSize else 0,
            ask_size=ticker.askSize if ticker.askSize else 0,
            timestamp=datetime.now(),
            is_halted=ticker.halted if hasattr(ticker, 'halted') else False,
            is_snapshot=True
        )
    
    async def subscribe_to_price(self, symbol: str, callback):
        """Subscribe to real-time price updates for a symbol"""
        async def stream_price(conn):
            # Create and qualify contract
            contract = Stock(symbol, 'SMART', 'USD')
            qualified = conn.ib.qualifyContracts(contract)
            
            if not qualified:
                self.logger.warning(f"Could not qualify contract for {symbol}")
                return
            
            # Request streaming market data
            ticker = conn.ib.reqMktData(qualified[0], snapshot=False)
            
            # Set up ticker callback
            def on_ticker_update(ticker):
                market_data = self._ticker_to_market_data(ticker, symbol)
                callback(market_data)
            
            ticker.updateEvent += on_ticker_update
            
            # Keep streaming until cancelled
            try:
                while True:
                    await asyncio.sleep(1)
            finally:
                # Clean up
                ticker.updateEvent -= on_ticker_update
                conn.ib.cancelMktData(qualified[0])
        
        # Run streaming in background
        asyncio.create_task(self.pool.with_connection(stream_price))