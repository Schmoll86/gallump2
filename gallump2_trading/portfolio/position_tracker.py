# position_tracker.py - Track positions - ONE job only
import asyncio
import logging
from typing import List, Optional, Dict
from decimal import Decimal
from datetime import datetime
from gallump_next.core.types import Position, AssetType
from gallump_next.core.connection_pool import ConnectionPool

class PositionTracker:
    """Track positions - ONE job only"""
    
    def __init__(self, connection_pool: ConnectionPool):
        self.pool = connection_pool
        self.logger = logging.getLogger(__name__)
        self._position_cache: Dict[str, Position] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl_seconds = 5  # Cache for 5 seconds
    
    async def get_all_positions(self, force_refresh: bool = False) -> List[Position]:
        """Get all current positions"""
        # Check cache
        if not force_refresh and self._is_cache_valid():
            return list(self._position_cache.values())
        
        try:
            async def fetch_positions(conn):
                # Get positions from IBKR
                ib_positions = conn.ib.positions()
                
                positions = []
                for ib_pos in ib_positions:
                    position = self._convert_ib_position(ib_pos)
                    if position:
                        positions.append(position)
                
                return positions
            
            positions = await self.pool.with_connection(fetch_positions)
            
            # Update cache
            self._update_cache(positions)
            
            return positions
            
        except Exception as e:
            self.logger.error(f"Error fetching positions: {e}")
            # Return cached data if available
            if self._position_cache:
                self.logger.info("Returning cached positions due to error")
                return list(self._position_cache.values())
            return []
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol"""
        positions = await self.get_all_positions()
        
        for position in positions:
            if position.symbol == symbol:
                return position
        
        return None
    
    async def get_positions_by_symbols(self, symbols: List[str]) -> Dict[str, Position]:
        """Get positions for multiple symbols"""
        positions = await self.get_all_positions()
        
        result = {}
        for position in positions:
            if position.symbol in symbols:
                result[position.symbol] = position
        
        return result
    
    async def has_position(self, symbol: str) -> bool:
        """Check if we have a position in a symbol"""
        position = await self.get_position(symbol)
        return position is not None and position.quantity != 0
    
    async def get_total_value(self) -> Decimal:
        """Get total portfolio value"""
        positions = await self.get_all_positions()
        
        total = Decimal("0")
        for position in positions:
            total += position.market_value
        
        return total
    
    async def get_total_pnl(self) -> Dict[str, Decimal]:
        """Get total P&L (unrealized and realized)"""
        positions = await self.get_all_positions()
        
        unrealized = Decimal("0")
        realized = Decimal("0")
        
        for position in positions:
            unrealized += position.unrealized_pnl
            realized += position.realized_pnl
        
        return {
            "unrealized": unrealized,
            "realized": realized,
            "total": unrealized + realized
        }
    
    async def monitor_positions(self, callback, interval: float = 5.0):
        """Monitor positions and call callback on changes"""
        previous_positions = {}
        
        while True:
            try:
                current_positions = await self.get_all_positions(force_refresh=True)
                
                # Check for changes
                current_dict = {p.symbol: p for p in current_positions}
                
                # Find new positions
                for symbol, position in current_dict.items():
                    if symbol not in previous_positions:
                        await callback("new_position", position)
                    elif self._position_changed(previous_positions[symbol], position):
                        await callback("position_changed", position, previous_positions[symbol])
                
                # Find closed positions
                for symbol, position in previous_positions.items():
                    if symbol not in current_dict:
                        await callback("position_closed", position)
                
                previous_positions = current_dict
                
            except Exception as e:
                self.logger.error(f"Error monitoring positions: {e}")
            
            await asyncio.sleep(interval)
    
    def _convert_ib_position(self, ib_position) -> Optional[Position]:
        """Convert IB position to our Position type"""
        try:
            contract = ib_position.contract
            position_data = ib_position.position
            
            # Determine asset type
            asset_type = AssetType.STOCK  # Default
            if contract.secType == "OPT":
                asset_type = AssetType.OPTION
            elif contract.secType == "FUT":
                asset_type = AssetType.FUTURE
            elif contract.secType == "CASH":
                asset_type = AssetType.FOREX
            
            # Calculate values (current price will be fetched separately if needed)
            avg_cost = Decimal(str(ib_position.avgCost)) if hasattr(ib_position, 'avgCost') else Decimal("0")
            quantity = Decimal(str(position_data))
            
            # For now, we'll set current price to 0 and let caller fetch if needed
            # This keeps the position tracker focused on its ONE job
            current_price = Decimal("0")
            market_value = Decimal("0")
            unrealized_pnl = Decimal("0")
            realized_pnl = Decimal("0")
            
            return Position(
                symbol=contract.symbol,
                quantity=quantity,
                average_cost=avg_cost,
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                realized_pnl=realized_pnl,
                asset_type=asset_type,
                account=ib_position.account,
                contract_id=contract.conId if hasattr(contract, 'conId') else 0
            )
            
        except Exception as e:
            self.logger.error(f"Error converting IB position: {e}")
            return None
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self._cache_time:
            return False
        
        age = (datetime.now() - self._cache_time).total_seconds()
        return age < self._cache_ttl_seconds
    
    def _update_cache(self, positions: List[Position]):
        """Update position cache"""
        self._position_cache = {p.symbol: p for p in positions}
        self._cache_time = datetime.now()
    
    def _position_changed(self, old_pos: Position, new_pos: Position) -> bool:
        """Check if position has materially changed"""
        if old_pos.quantity != new_pos.quantity:
            return True
        if abs(old_pos.unrealized_pnl - new_pos.unrealized_pnl) > Decimal("0.01"):
            return True
        return False