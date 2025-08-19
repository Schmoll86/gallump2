# connection_pool.py - Connection pooling for IBKR connections
import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from gallump_next.core.connection_manager import ConnectionManager

class ConnectionPool:
    """Manages a pool of IBKR connections for efficiency"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 4001, max_connections: int = 3):
        self.host = host
        self.port = port
        self.max_connections = max_connections
        self.connections: List[ConnectionManager] = []
        self.available: asyncio.Queue = asyncio.Queue()
        self.in_use: List[ConnectionManager] = []
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the connection pool"""
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            self.logger.info(f"Initializing connection pool with {self.max_connections} connections")
            
            for i in range(self.max_connections):
                conn = ConnectionManager(self.host, self.port)
                if await conn.connect():
                    self.connections.append(conn)
                    await self.available.put(conn)
                    self.logger.info(f"Connection {i+1}/{self.max_connections} established")
                else:
                    self.logger.error(f"Failed to establish connection {i+1}")
            
            if not self.connections:
                raise ConnectionError("Failed to establish any connections")
            
            self._initialized = True
            self.logger.info(f"Connection pool initialized with {len(self.connections)} connections")
    
    async def get_connection(self, timeout: float = 10.0) -> ConnectionManager:
        """Get an available connection from the pool"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Wait for available connection with timeout
            conn = await asyncio.wait_for(self.available.get(), timeout=timeout)
            
            # Verify connection is still valid
            if not conn.is_connected():
                self.logger.warning("Connection is not active, attempting to reconnect")
                if not await conn.connect():
                    # Connection failed, try to get another
                    return await self.get_connection(timeout)
            
            self.in_use.append(conn)
            return conn
            
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout waiting for available connection (timeout={timeout}s)")
            raise TimeoutError(f"No connections available within {timeout} seconds")
    
    async def release_connection(self, conn: ConnectionManager):
        """Release a connection back to the pool"""
        if conn in self.in_use:
            self.in_use.remove(conn)
        
        # Check if connection is still valid
        if conn.is_connected():
            await self.available.put(conn)
        else:
            self.logger.warning("Released connection is not active, attempting to reconnect")
            if await conn.connect():
                await self.available.put(conn)
            else:
                # Connection is dead, create a new one
                self.connections.remove(conn)
                new_conn = ConnectionManager(self.host, self.port)
                if await new_conn.connect():
                    self.connections.append(new_conn)
                    await self.available.put(new_conn)
                    self.logger.info("Replaced dead connection with new one")
    
    async def with_connection(self, func, *args, **kwargs):
        """Execute a function with a connection from the pool"""
        conn = await self.get_connection()
        try:
            return await func(conn, *args, **kwargs)
        finally:
            await self.release_connection(conn)
    
    async def close_all(self):
        """Close all connections in the pool"""
        self.logger.info("Closing all connections in pool")
        
        # Close in-use connections
        for conn in self.in_use:
            await conn.disconnect()
        
        # Close available connections
        while not self.available.empty():
            conn = await self.available.get()
            await conn.disconnect()
        
        self.connections.clear()
        self.in_use.clear()
        self._initialized = False
        
        self.logger.info("All connections closed")
    
    def get_pool_status(self) -> dict:
        """Get current pool status"""
        return {
            "total_connections": len(self.connections),
            "available": self.available.qsize(),
            "in_use": len(self.in_use),
            "max_connections": self.max_connections,
            "initialized": self._initialized,
            "connections": [
                {
                    "client_id": conn.client_id,
                    "connected": conn.is_connected(),
                    "last_heartbeat": conn.last_heartbeat.isoformat()
                }
                for conn in self.connections
            ]
        }
    
    async def health_check(self) -> bool:
        """Check health of all connections"""
        if not self._initialized:
            return False
        
        healthy_count = 0
        for conn in self.connections:
            if conn.is_connected():
                # Check if heartbeat is recent
                time_since_heartbeat = datetime.now() - conn.last_heartbeat
                if time_since_heartbeat < timedelta(minutes=2):
                    healthy_count += 1
        
        health_ratio = healthy_count / len(self.connections) if self.connections else 0
        return health_ratio >= 0.5  # At least 50% of connections are healthy