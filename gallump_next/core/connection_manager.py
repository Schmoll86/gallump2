# connection_manager.py - Manages a single IBKR connection with automatic reconnection
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from ib_insync import IB, util, Stock, Option, Future, Forex
import nest_asyncio
from gallump_next.core.types import ConnectionInfo

nest_asyncio.apply()

class ConnectionManager:
    """Manages a single IBKR connection with automatic reconnection"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 4001):
        self.host = host
        self.port = port
        self.ib: Optional[IB] = None
        self.client_id: int = self._get_next_client_id()
        self.reconnect_attempts = 0
        self.max_reconnects = 5
        self.last_heartbeat = datetime.now()
        self.connection_type = "live" if port == 4001 else "paper"
        self.logger = logging.getLogger(__name__)
        self._heartbeat_task: Optional[asyncio.Task] = None
        
    def _get_next_client_id(self) -> int:
        """Generate unique client ID"""
        import random
        return random.randint(100, 999)
    
    async def connect(self) -> bool:
        """Establish connection with retry logic"""
        try:
            if self.ib and self.ib.isConnected():
                return True
                
            self.ib = IB()
            await self.ib.connectAsync(
                self.host, 
                self.port, 
                clientId=self.client_id,
                timeout=10
            )
            
            # Register event handlers
            self.ib.errorEvent += self._on_error
            self.ib.disconnectedEvent += self._on_disconnect
            
            # Start heartbeat
            self._start_heartbeat()
            
            self.logger.info(f"Connected to IBKR: {self.host}:{self.port} (Client ID: {self.client_id})")
            self.reconnect_attempts = 0
            return True
            
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return await self._reconnect()
    
    async def _reconnect(self) -> bool:
        """Reconnect with exponential backoff"""
        if self.reconnect_attempts >= self.max_reconnects:
            self.logger.error(f"Max reconnection attempts ({self.max_reconnects}) reached")
            return False
        
        wait_time = min(2 ** self.reconnect_attempts, 30)  # Max 30 seconds
        self.logger.info(f"Reconnecting in {wait_time} seconds... (Attempt {self.reconnect_attempts + 1}/{self.max_reconnects})")
        
        await asyncio.sleep(wait_time)
        self.reconnect_attempts += 1
        self.client_id = self._get_next_client_id()
        
        return await self.connect()
    
    def _start_heartbeat(self):
        """Start heartbeat task to keep connection alive"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        
        async def heartbeat():
            while self.ib and self.ib.isConnected():
                try:
                    # Request current time as heartbeat
                    self.ib.reqCurrentTime()
                    self.last_heartbeat = datetime.now()
                    await asyncio.sleep(30)  # Heartbeat every 30 seconds
                except Exception as e:
                    self.logger.warning(f"Heartbeat failed: {e}")
                    break
        
        self._heartbeat_task = asyncio.create_task(heartbeat())
    
    def _on_error(self, reqId: int, errorCode: int, errorString: str, contract):
        """Handle IB errors"""
        # Ignore common non-critical errors
        if errorCode in [2104, 2106, 2158]:  # Market data farm messages
            return
        
        self.logger.warning(f"IB Error {errorCode}: {errorString}")
        
        # Critical errors that require reconnection
        if errorCode in [504, 502, 1100, 1102]:
            self.logger.error(f"Critical error, initiating reconnection")
            asyncio.create_task(self._reconnect())
    
    def _on_disconnect(self):
        """Handle disconnection"""
        self.logger.warning("Disconnected from IBKR")
        asyncio.create_task(self._reconnect())
    
    async def disconnect(self):
        """Gracefully disconnect"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()
            self.logger.info("Disconnected from IBKR")
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self.ib is not None and self.ib.isConnected()
    
    def get_connection_info(self) -> ConnectionInfo:
        """Get current connection information"""
        return ConnectionInfo(
            host=self.host,
            port=self.port,
            client_id=self.client_id,
            is_connected=self.is_connected(),
            last_heartbeat=self.last_heartbeat,
            connection_type=self.connection_type
        )
    
    def qualify_contract(self, symbol: str, asset_type: str = "STK", exchange: str = "SMART", currency: str = "USD"):
        """Qualify a contract to get full details"""
        if not self.is_connected():
            raise ConnectionError("Not connected to IBKR")
        
        if asset_type == "STK":
            contract = Stock(symbol, exchange, currency)
        elif asset_type == "OPT":
            contract = Option(symbol, exchange=exchange, currency=currency)
        elif asset_type == "FUT":
            contract = Future(symbol, exchange=exchange)
        elif asset_type == "CASH":
            contract = Forex(symbol)
        else:
            raise ValueError(f"Unknown asset type: {asset_type}")
        
        # Qualify the contract
        qualified = self.ib.qualifyContracts(contract)
        
        if not qualified:
            raise ValueError(f"Could not qualify contract: {symbol}")
        
        return qualified[0]