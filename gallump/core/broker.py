"""
Broker Module - IBKR connection and order execution with enhanced reliability
Single responsibility: Connect to IBKR and execute trades
"""

from ib_insync import IB, Stock, Option, Order, Contract, MarketOrder, LimitOrder, StopOrder, util
import nest_asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, time
import random
import pytz
import holidays
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents a portfolio position"""
    symbol: str
    position: float  # Use 'position' to match IBKR naming
    marketPrice: float
    marketValue: float
    averageCost: float
    unrealizedPnL: float
    realizedPnL: float
    contractId: int
    
    def to_dict(self):
        return {
            'symbol': self.symbol,
            'position': self.position,
            'marketPrice': self.marketPrice,
            'marketValue': self.marketValue,
            'averageCost': self.averageCost,
            'unrealizedPnL': self.unrealizedPnL,
            'realizedPnL': self.realizedPnL,
            'contractId': self.contractId
        }


class Broker:
    """IBKR Broker interface with dynamic client ID and market awareness"""
    
    def __init__(self, host='127.0.0.1', port=4001, client_id=None):
        nest_asyncio.apply()  # Allow nested event loops
        self.host = host
        self.port = port
        self.client_id = client_id  # Will be set dynamically if None
        self.ib = IB()
        self.connected = False
        self.connection_ready = False
        
        # Connection health tracking
        self.last_successful_request = None
        self.failed_request_count = 0
        self.total_request_count = 0
        
    def connect(self) -> bool:
        """Connect to IBKR Gateway with dynamic client ID and verification"""
        if self.connected:
            return True
            
        # Try connection with dynamic client IDs to avoid conflicts
        for attempt in range(10):
            try:
                if not self.client_id:
                    self.client_id = random.randint(10, 999)
                
                logger.info(f"Attempting connection with client ID: {self.client_id}")
                
                # Set connection timeout
                self.ib.RequestTimeout = 10  # 10 second timeout for all requests
                self.ib.connect(self.host, self.port, clientId=self.client_id, timeout=5)
                
                # Wait for connection to stabilize
                self.ib.sleep(2)
                
                # Verify connection is working
                try:
                    self.ib.reqCurrentTime()
                    self.connection_ready = True
                except Exception as e:
                    logger.error(f"Connection test failed: {e}")
                    self.ib.disconnect()
                    self.client_id = None  # Try new ID next time
                    continue
                
                # Set delayed data mode for after-hours
                self.ib.reqMarketDataType(3)  # Use delayed data when market closed
                self.connected = True
                logger.info(f"Connected to IBKR at {self.host}:{self.port} with client ID: {self.client_id}")
                
                # Initialize account data subscription
                self._initialize_account_subscription()
                return True
                
            except Exception as e:
                if "already in use" in str(e):
                    self.client_id = None  # Reset to try another ID
                    continue
                elif "Socket disconnect" in str(e):
                    self.ib = IB()  # Create new instance
                    self.client_id = None
                    continue
                else:
                    logger.error(f"Connection failed: {e}")
                    
        logger.error("Failed to connect - all client IDs may be in use")
        return False
    
    def _initialize_account_subscription(self):
        """Initialize account data subscription to avoid blocking later"""
        try:
            accounts = self.ib.managedAccounts()
            if accounts:
                logger.info(f"Managed accounts: {accounts}")
                self.ib.reqAccountSummary()
                self.ib.sleep(1)  # Let initial data populate
        except Exception as e:
            logger.warning(f"Could not initialize account subscription: {e}")
    
    def is_connected(self) -> bool:
        """Check if connected to IBKR"""
        return self.connected and self.ib.isConnected()
    
    def disconnect(self):
        """Disconnect from IBKR"""
        if self.connected:
            try:
                self.ib.disconnect()
            except:
                pass  # Ignore disconnect errors
            self.connected = False
            self.connection_ready = False
            logger.info("Disconnected from IBKR")
    
    def get_positions(self) -> List[Dict]:
        """Get all current positions"""
        if not self.is_connected():
            logger.error("Not connected to IBKR")
            return []
        
        if not self.connection_ready:
            logger.error("Connection not ready - still initializing")
            return []
            
        try:
            positions = []
            ib_positions = self.ib.positions()
            
            if not ib_positions:
                return []
            
            for p in ib_positions:
                pos = Position(
                    symbol=p.contract.symbol,
                    position=p.position,
                    marketPrice=0,  # Will be filled separately if needed
                    marketValue=p.marketValue if hasattr(p, 'marketValue') else 0,
                    averageCost=p.avgCost,
                    unrealizedPnL=p.unrealizedPnL if hasattr(p, 'unrealizedPnL') else 0,
                    realizedPnL=p.realizedPnL if hasattr(p, 'realizedPnL') else 0,
                    contractId=p.contract.conId
                )
                positions.append(pos.to_dict())
            
            self._track_request_success()
            return positions
            
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            self._track_request_failure(str(e))
            return []
    
    def get_last_prices(self, symbols: List[str], timeout: int = 5) -> Dict[str, float]:
        """Get last prices for multiple symbols - uses fresh connection"""
        from ib_insync import IB, Stock
        import random
        
        results = {}
        temp_ib = IB()
        
        try:
            # Create a fresh connection for market data
            client_id = random.randint(1000, 9999)
            temp_ib.connect('127.0.0.1', 4001, clientId=client_id)
            logger.info(f"Created fresh connection for market data with client ID {client_id}")
            
            # Request market data for each symbol
            for symbol in symbols:
                try:
                    contract = Stock(symbol, 'SMART', 'USD')
                    ticker = temp_ib.reqMktData(contract, '', False, False)
                    
                    # Wait for data
                    temp_ib.sleep(2)
                    
                    # Get the price
                    price = 0
                    if ticker.last and ticker.last > 0:
                        price = ticker.last
                    elif ticker.bid and ticker.bid > 0:
                        price = ticker.bid
                    elif ticker.close and ticker.close > 0:
                        price = ticker.close
                        
                    results[symbol] = float(price) if price else 0
                    logger.debug(f"{symbol}: ${price}")
                    
                    # Cancel the market data
                    try:
                        temp_ib.cancelMktData(ticker)
                    except:
                        pass  # Ignore cancel errors
                    
                except Exception as e:
                    logger.warning(f"Error getting {symbol}: {e}")
                    results[symbol] = 0
                    
        except Exception as e:
            logger.error(f"Failed to connect for market data: {e}")
            return {symbol: 0 for symbol in symbols}
        finally:
            try:
                temp_ib.disconnect()
            except:
                pass
                
        self._track_request_success()
        return results
    
    def is_market_open(self) -> bool:
        """Check if US stock market is currently open"""
        tz = pytz.timezone('US/Eastern')
        now = datetime.now(tz)
        
        # Check if weekend
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
            
        # Check if holiday
        us_holidays = holidays.US()
        if now.date() in us_holidays:
            return False
            
        # Regular market hours: 9:30 AM - 4:00 PM ET
        market_open = time(9, 30)
        market_close = time(16, 0)
        current_time = now.time()
        
        return market_open <= current_time <= market_close
    
    def get_market_status(self) -> Dict[str, Any]:
        """Get detailed market status"""
        tz = pytz.timezone('US/Eastern')
        now = datetime.now(tz)
        is_open = self.is_market_open()
        
        # Calculate next open
        next_open = None
        if not is_open:
            # If after 4 PM, next open is tomorrow 9:30 AM
            if now.time() > time(16, 0):
                next_day = now.date() + timedelta(days=1)
            else:
                next_day = now.date()
                
            # Skip weekends and holidays
            us_holidays = holidays.US()
            while next_day.weekday() >= 5 or next_day in us_holidays:
                next_day += timedelta(days=1)
                
            next_open = datetime.combine(next_day, time(9, 30))
            next_open = tz.localize(next_open)
        
        return {
            'is_open': is_open,
            'current_time': now.isoformat(),
            'next_open': next_open.isoformat() if next_open else None,
            'mode': 'TRADING' if is_open else 'AFTER_HOURS',
            'data_availability': 'REAL_TIME' if is_open else 'DELAYED'
        }
    
    def check_market_data_entitlement(self, symbol: str) -> bool:
        """Check if we have market data entitlement for a symbol"""
        if not self.is_connected():
            return False
        
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            ticker = self.ib.reqMktData(contract, '', False, False)
            self.ib.sleep(2)
            
            has_data = ticker.last is not None and ticker.last > 0
            self.ib.cancelMktData(contract)
            
            return has_data
            
        except Exception as e:
            logger.error(f"Error checking entitlement for {symbol}: {e}")
            return False
    
    def get_options_chain(self, symbol: str, expiry_days: int = 60) -> Optional[Dict]:
        """
        Fetch real options chain from IBKR
        Args:
            symbol: Stock symbol
            expiry_days: Number of days out to fetch expirations
        Returns:
            Options chain data or None
        """
        if not self.is_connected():
            logger.error("Not connected to IBKR for options chain")
            return None
        
        try:
            from ib_insync import Stock, Option
            from datetime import datetime, timedelta
            
            # Create stock contract
            stock = Stock(symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)
            
            # Get current stock price for strike selection
            ticker = self.ib.reqMktData(stock, '', False, False)
            self.ib.sleep(2)
            
            current_price = ticker.last if ticker.last else ticker.close
            if not current_price or current_price <= 0:
                logger.warning(f"Cannot get current price for {symbol}")
                self.ib.cancelMktData(ticker)
                return None
            
            self.ib.cancelMktData(ticker)
            
            # Get available expirations
            chains = self.ib.reqSecDefOptParams(
                stock.symbol, '', stock.secType, stock.conId
            )
            
            if not chains:
                logger.warning(f"No options chains found for {symbol}")
                return None
            
            chain = chains[0]
            
            # Filter expirations within requested days
            today = datetime.now()
            max_date = today + timedelta(days=expiry_days)
            
            expirations = []
            for exp in chain.expirations:
                exp_date = datetime.strptime(exp, '%Y%m%d')
                if exp_date <= max_date:
                    expirations.append(exp)
            
            if not expirations:
                logger.warning(f"No expirations within {expiry_days} days for {symbol}")
                return None
            
            # Select strikes around current price (±20%)
            min_strike = current_price * 0.8
            max_strike = current_price * 1.2
            strikes = [s for s in chain.strikes if min_strike <= s <= max_strike]
            
            # Build options chain structure
            options_data = {
                'symbol': symbol,
                'current_price': float(current_price),
                'timestamp': datetime.now().isoformat(),
                'expiry_dates': expirations[:3],  # Limit to 3 nearest expirations
                'strikes': strikes,
                'calls': {},
                'puts': {}
            }
            
            # Fetch option data for nearest expiration only (to limit API calls)
            if expirations and strikes:
                nearest_expiry = expirations[0]
                exp_str = datetime.strptime(nearest_expiry, '%Y%m%d').strftime('%Y-%m-%d')
                
                options_data['calls'][exp_str] = {}
                options_data['puts'][exp_str] = {}
                
                # Sample a few strikes to avoid overwhelming API
                sample_strikes = strikes[::max(1, len(strikes)//5)][:5]  # Max 5 strikes
                
                for strike in sample_strikes:
                    # Fetch call option
                    try:
                        call = Option(symbol, nearest_expiry, strike, 'C', 'SMART')
                        self.ib.qualifyContracts(call)
                        
                        call_ticker = self.ib.reqMktData(call, '', False, False)
                        self.ib.sleep(1)
                        
                        options_data['calls'][exp_str][str(strike)] = {
                            'bid': float(call_ticker.bid) if call_ticker.bid else 0,
                            'ask': float(call_ticker.ask) if call_ticker.ask else 0,
                            'last': float(call_ticker.last) if call_ticker.last else 0,
                            'volume': int(call_ticker.volume) if call_ticker.volume else 0
                        }
                        
                        self.ib.cancelMktData(call_ticker)
                    except Exception as e:
                        logger.debug(f"Could not fetch call {symbol} {strike}: {e}")
                    
                    # Fetch put option
                    try:
                        put = Option(symbol, nearest_expiry, strike, 'P', 'SMART')
                        self.ib.qualifyContracts(put)
                        
                        put_ticker = self.ib.reqMktData(put, '', False, False)
                        self.ib.sleep(1)
                        
                        options_data['puts'][exp_str][str(strike)] = {
                            'bid': float(put_ticker.bid) if put_ticker.bid else 0,
                            'ask': float(put_ticker.ask) if put_ticker.ask else 0,
                            'last': float(put_ticker.last) if put_ticker.last else 0,
                            'volume': int(put_ticker.volume) if put_ticker.volume else 0
                        }
                        
                        self.ib.cancelMktData(put_ticker)
                    except Exception as e:
                        logger.debug(f"Could not fetch put {symbol} {strike}: {e}")
            
            self._track_request_success()
            return options_data
            
        except Exception as e:
            logger.error(f"Error fetching options chain for {symbol}: {e}")
            self._track_request_failure(str(e))
            return None
    
    def place_order(self, symbol: str, action: str, quantity: int, 
                   order_type: str = 'MKT', limit_price: Optional[float] = None) -> Optional[str]:
        """
        Place an order with IBKR
        
        Args:
            symbol: Stock symbol
            action: 'BUY' or 'SELL'
            quantity: Number of shares
            order_type: 'MKT' or 'LMT'
            limit_price: Limit price for limit orders
            
        Returns:
            Order ID if successful, None otherwise
        """
        if not self.is_connected():
            logger.error("Not connected to IBKR")
            return None
        
        try:
            # Create contract
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Create order
            if order_type == 'LMT' and limit_price:
                order = LimitOrder(action, quantity, limit_price)
            else:
                order = MarketOrder(action, quantity)
            
            # Place order
            trade = self.ib.placeOrder(contract, order)
            
            # Wait for order to be submitted
            self.ib.sleep(1)
            
            if trade.order.orderId:
                logger.info(f"Order placed: {action} {quantity} {symbol} @ {order_type}")
                return str(trade.order.orderId)
            else:
                logger.error("Order failed - no order ID returned")
                return None
                
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order"""
        if not self.is_connected():
            return False
        
        try:
            # Find the order
            for trade in self.ib.trades():
                if str(trade.order.orderId) == order_id:
                    self.ib.cancelOrder(trade.order)
                    logger.info(f"Cancelled order {order_id}")
                    return True
            
            logger.warning(f"Order {order_id} not found")
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_portfolio(self) -> Dict[str, Any]:
        """Get current portfolio state"""
        if not self.is_connected():
            raise Exception("Not connected to IBKR")
        
        if not self.connection_ready:
            raise Exception("Connection not ready - still initializing")
            
        try:
            # Get account values
            account_values = self.ib.accountValues()
            
            # If no account values, try accountSummary as fallback
            if not account_values:
                logger.info("No accountValues, trying accountSummary...")
                account_summary = self.ib.accountSummary()
                account_values = account_summary
            
            # Parse the values
            net_liquidation = 0
            total_cash = 0
            buying_power = 0
            
            for value in account_values:
                if hasattr(value, 'tag'):
                    if value.tag == 'NetLiquidation':
                        net_liquidation = float(value.value)
                    elif value.tag == 'TotalCashValue':
                        total_cash = float(value.value)
                    elif value.tag == 'BuyingPower':
                        buying_power = float(value.value)
            
            # Get positions
            positions = self.get_positions()
            
            # Add current prices to positions
            if positions:
                symbols = [p['symbol'] for p in positions if 'symbol' in p]
                try:
                    prices = self.get_last_prices(symbols)
                    for pos in positions:
                        symbol = pos.get('symbol')
                        if symbol and symbol in prices:
                            pos['currentPrice'] = prices[symbol]
                            pos['marketPrice'] = prices[symbol]
                            pos['marketValue'] = prices[symbol] * pos.get('position', 0)
                            # Calculate unrealized P&L
                            avg_cost = pos.get('averageCost', 0)
                            position_size = pos.get('position', 0)
                            if avg_cost and position_size:
                                pos['unrealizedPnL'] = (prices[symbol] - avg_cost) * position_size
                except Exception as e:
                    logger.warning(f"Could not fetch current prices: {e}")
            
            self._track_request_success()
            
            return {
                'total_value': net_liquidation,
                'cash': total_cash,
                'buying_power': buying_power,
                'positions': positions,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self._track_request_failure(str(e))
            raise Exception(f"Failed to get portfolio: {str(e)}")
    
    def get_open_orders(self) -> List[Dict]:
        """Get list of open orders (basic format for compatibility)"""
        try:
            if not self.is_connected():
                return []
            
            trades = self.ib.openTrades()
            orders = []
            for trade in trades:
                orders.append({
                    'order_id': trade.order.orderId,
                    'symbol': trade.contract.symbol,
                    'action': trade.order.action,
                    'quantity': trade.order.totalQuantity,
                    'order_type': trade.order.orderType,
                    'limit_price': getattr(trade.order, 'lmtPrice', None),
                    'status': trade.orderStatus.status
                })
            
            self._track_request_success()
            return orders
            
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            self._track_request_failure(str(e))
            return []
    
    def get_enhanced_open_orders(self):
        """
        Get comprehensive IBKR orders with full API fidelity
        Returns list of PendingOrder objects with all IBKR fields
        """
        from gallump.core.types import PendingOrder
        from datetime import datetime
        
        try:
            if not self.is_connected():
                logger.warning("Cannot get enhanced orders - not connected to IBKR")
                return []
            
            trades = self.ib.openTrades()
            orders = []
            
            for trade in trades:
                order_obj = trade.order
                status_obj = trade.orderStatus
                contract = trade.contract
                
                # Handle asset type detection
                asset_type = 'STOCK'
                option_type = None
                strike = None
                expiry = None
                
                if hasattr(contract, 'secType'):
                    if contract.secType == 'OPT':
                        asset_type = 'OPTION'
                        option_type = getattr(contract, 'right', None)  # CALL/PUT
                        strike = getattr(contract, 'strike', None)
                        expiry = getattr(contract, 'lastTradeDateOrContractMonth', None)
                    elif contract.secType == 'FUT':
                        asset_type = 'FUTURE'
                    elif contract.secType == 'CASH':
                        asset_type = 'FOREX'
                
                # Calculate remaining quantity
                remaining_qty = order_obj.totalQuantity - status_obj.filled
                
                order = PendingOrder(
                    order_id=str(order_obj.orderId),
                    symbol=contract.symbol,
                    action=order_obj.action,
                    quantity=order_obj.totalQuantity,
                    order_type=order_obj.orderType,
                    
                    # Price levels (IBKR-specific field mapping)
                    limit_price=getattr(order_obj, 'lmtPrice', None),
                    stop_price=getattr(order_obj, 'auxPrice', None),
                    trail_amount=getattr(order_obj, 'trailStopPrice', None),
                    trail_percent=getattr(order_obj, 'trailingPercent', None),
                    
                    # Advanced order parameters
                    offset_amount=getattr(order_obj, 'lmtPriceOffset', None),
                    midpoint_offset=getattr(order_obj, 'startingPrice', None),
                    
                    # Time constraints
                    time_in_force=order_obj.tif if order_obj.tif else 'DAY',
                    good_after_time=getattr(order_obj, 'goodAfterTime', None),
                    good_till_date=getattr(order_obj, 'goodTillDate', None),
                    
                    # Status and fills
                    status=status_obj.status,
                    filled_quantity=int(status_obj.filled) if status_obj.filled else 0,
                    remaining_quantity=int(remaining_qty) if remaining_qty else 0,
                    avg_fill_price=status_obj.avgFillPrice if status_obj.avgFillPrice and status_obj.avgFillPrice > 0 else None,
                    
                    # Bracket/OCO linking
                    parent_id=str(order_obj.parentId) if order_obj.parentId else None,
                    oca_group=order_obj.ocaGroup if order_obj.ocaGroup else None,
                    
                    # Asset type details
                    asset_type=asset_type,
                    option_type=option_type,
                    strike=strike,
                    expiry=expiry,
                    
                    submitted_at=datetime.now()  # IBKR doesn't always provide submission time
                )
                orders.append(order)
            
            self._track_request_success()
            logger.info(f"Retrieved {len(orders)} enhanced orders from IBKR")
            return orders
            
        except Exception as e:
            logger.error(f"Error getting enhanced IBKR orders: {e}")
            self._track_request_failure(str(e))
            return []
    
    def validate_ibkr_order_type(self, order_type: str, order_params: Dict) -> bool:
        """Validate order type against IBKR requirements"""
        
        # TRAIL orders require trailAmount OR trailingPercent
        if order_type == 'TRAIL':
            return 'trail_amount' in order_params or 'trail_percent' in order_params
        
        # Stop Limit requires both limit and stop prices
        if order_type == 'STP LMT':
            return all(k in order_params for k in ['limit_price', 'stop_price'])
        
        # Pegged orders require offset
        if order_type in ['PEGMKT', 'PEGMID']:
            return 'offset_amount' in order_params
        
        # MIT/LIT require auxPrice (stop_price)
        if order_type in ['MIT', 'LIT']:
            return 'stop_price' in order_params
        
        return True
    
    def sync_order_statuses(self):
        """
        Sync order statuses with IBKR's real-time state
        Should be called periodically to update database
        """
        try:
            from gallump.core.storage import Storage
            
            # Get all active orders from database
            storage = Storage()
            db_orders = storage.get_active_pending_orders()
            
            # Get current IBKR status
            live_orders = self.get_enhanced_open_orders()
            live_status_map = {o.order_id: (o.status, o.filled_quantity, o.avg_fill_price) for o in live_orders}
            
            # Update any status changes
            for db_order in db_orders:
                if db_order.order_id in live_status_map:
                    live_status, filled_qty, avg_price = live_status_map[db_order.order_id]
                    if (live_status != db_order.status or 
                        filled_qty != db_order.filled_quantity):
                        storage.update_order_status(
                            db_order.order_id, 
                            live_status, 
                            filled_qty, 
                            avg_price
                        )
                        logger.info(f"Updated order {db_order.order_id}: {db_order.status} -> {live_status}")
                else:
                    # Order no longer in IBKR = filled or cancelled
                    if db_order.status in ['PendingSubmit', 'PreSubmitted', 'Submitted']:
                        storage.update_order_status(db_order.order_id, 'Filled')
                        logger.info(f"Marked order {db_order.order_id} as filled (no longer in IBKR)")
                        
        except Exception as e:
            logger.error(f"Order status sync failed: {e}")
    
    def place_bracket_order(self, symbol: str, action: str, quantity: int,
                           entry_price: float, profit_target: float, 
                           stop_loss: float) -> Dict[str, str]:
        """
        Place IBKR bracket order using proper API structure
        Returns dict with all three order IDs
        """
        import time
        
        try:
            from ib_insync import Stock, LimitOrder, StopOrder
            
            if not self.is_connected():
                raise Exception("Not connected to IBKR")
            
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Generate unique OCA group identifier
            oca_group = f"BRACKET_{int(time.time() * 1000)}"
            
            # Parent order (main entry)
            parent_order = LimitOrder(action, quantity, entry_price)
            parent_order.transmit = False  # Don't transmit until children set
            parent_order.orderId = self.ib.client.getReqId()
            
            # Profit target (opposite action)
            profit_action = 'SELL' if action == 'BUY' else 'BUY'
            profit_order = LimitOrder(profit_action, quantity, profit_target)
            profit_order.parentId = parent_order.orderId
            profit_order.transmit = False
            profit_order.orderId = self.ib.client.getReqId()
            
            # Stop loss
            stop_order = StopOrder(profit_action, quantity, stop_loss)
            stop_order.parentId = parent_order.orderId
            stop_order.transmit = True  # Transmit the entire group
            stop_order.orderId = self.ib.client.getReqId()
            
            # Set OCO group for profit and stop (they cancel each other)
            profit_order.ocaGroup = oca_group
            stop_order.ocaGroup = oca_group
            
            # Place orders in sequence
            logger.info(f"Placing bracket order for {symbol}: Entry={entry_price}, Target={profit_target}, Stop={stop_loss}")
            
            parent_trade = self.ib.placeOrder(contract, parent_order)
            profit_trade = self.ib.placeOrder(contract, profit_order)
            stop_trade = self.ib.placeOrder(contract, stop_order)
            
            # Wait for order IDs to be assigned
            time.sleep(0.5)
            
            result = {
                'parent_id': str(parent_order.orderId),
                'profit_id': str(profit_order.orderId),
                'stop_id': str(stop_order.orderId),
                'oca_group': oca_group,
                'status': 'submitted'
            }
            
            logger.info(f"Bracket order placed successfully: {result}")
            self._track_request_success()
            return result
            
        except Exception as e:
            logger.error(f"Failed to place bracket order: {e}")
            self._track_request_failure(str(e))
            raise Exception(f"Bracket order failed: {str(e)}")
    
    def place_trailing_stop_order(self, symbol: str, action: str, quantity: int,
                                 trail_amount: float = None, trail_percent: float = None,
                                 parent_id: str = None) -> str:
        """
        Place a trailing stop order
        Either trail_amount (dollar amount) or trail_percent must be specified
        """
        try:
            from ib_insync import Stock, Order
            
            if not self.is_connected():
                raise Exception("Not connected to IBKR")
            
            if not trail_amount and not trail_percent:
                raise ValueError("Either trail_amount or trail_percent must be specified")
            
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Create trailing stop order
            order = Order()
            order.action = action
            order.totalQuantity = quantity
            order.orderType = 'TRAIL'
            
            if trail_amount:
                order.trailStopPrice = trail_amount
            if trail_percent:
                order.trailingPercent = trail_percent
            
            if parent_id:
                order.parentId = int(parent_id)
            
            # Place the order
            trade = self.ib.placeOrder(contract, order)
            
            order_id = str(order.orderId)
            logger.info(f"Trailing stop order placed: {order_id} for {symbol}")
            
            self._track_request_success()
            return order_id
            
        except Exception as e:
            logger.error(f"Failed to place trailing stop: {e}")
            self._track_request_failure(str(e))
            raise Exception(f"Trailing stop order failed: {str(e)}")
    
    def modify_order(self, order_id: str, **modifications) -> bool:
        """
        Modify an existing order
        Supports price, quantity, and order type changes
        """
        try:
            if not self.is_connected():
                raise Exception("Not connected to IBKR")
            
            # Find the existing order
            trades = self.ib.openTrades()
            target_trade = None
            
            for trade in trades:
                if str(trade.order.orderId) == order_id:
                    target_trade = trade
                    break
            
            if not target_trade:
                raise Exception(f"Order {order_id} not found")
            
            # Apply modifications
            order = target_trade.order
            
            if 'quantity' in modifications:
                order.totalQuantity = modifications['quantity']
            if 'limit_price' in modifications:
                order.lmtPrice = modifications['limit_price']
            if 'stop_price' in modifications:
                order.auxPrice = modifications['stop_price']
            if 'trail_amount' in modifications:
                order.trailStopPrice = modifications['trail_amount']
            if 'trail_percent' in modifications:
                order.trailingPercent = modifications['trail_percent']
            
            # Submit modification
            modified_trade = self.ib.placeOrder(target_trade.contract, order)
            
            logger.info(f"Modified order {order_id}: {modifications}")
            self._track_request_success()
            return True
            
        except Exception as e:
            logger.error(f"Failed to modify order {order_id}: {e}")
            self._track_request_failure(str(e))
            return False
    
    def _track_request_success(self):
        """Track successful API request for health monitoring"""
        self.last_successful_request = datetime.now()
        self.total_request_count += 1
    
    def _track_request_failure(self, error: str):
        """Track failed API request for health monitoring"""
        self.failed_request_count += 1
        self.total_request_count += 1
    
    def get_connection_health(self) -> Dict:
        """Get detailed connection health metrics"""
        success_rate = 0
        if self.total_request_count > 0:
            success_rate = (self.total_request_count - self.failed_request_count) / self.total_request_count
        
        return {
            'connected': self.connected,
            'connection_ready': self.connection_ready,
            'client_id': self.client_id,
            'last_successful_request': self.last_successful_request.isoformat() if self.last_successful_request else None,
            'total_requests': self.total_request_count,
            'failed_requests': self.failed_request_count,
            'success_rate': success_rate,
            'market_status': self.get_market_status()
        }