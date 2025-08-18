# types.py - Single source of truth for all types
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Union, Literal
from datetime import datetime
from decimal import Decimal
from enum import Enum

# Enums
class OrderAction(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(Enum):
    MARKET = "MKT"
    LIMIT = "LMT"
    STOP = "STP"
    STOP_LIMIT = "STP LMT"
    TRAILING_STOP = "TRAIL"

class OrderStatus(Enum):
    PENDING_SUBMIT = "PendingSubmit"
    SUBMITTED = "Submitted"
    FILLED = "Filled"
    CANCELLED = "Cancelled"
    ERROR = "Error"

class TimeInForce(Enum):
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"

class AssetType(Enum):
    STOCK = "STK"
    OPTION = "OPT"
    FUTURE = "FUT"
    FOREX = "CASH"
    CRYPTO = "CRYPTO"

# Data Classes
@dataclass
class Position:
    symbol: str
    quantity: Decimal
    average_cost: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    asset_type: AssetType
    account: str
    contract_id: int

@dataclass
class Order:
    symbol: str
    action: OrderAction
    quantity: Decimal
    order_type: OrderType
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    trail_amount: Optional[Decimal] = None
    trail_percent: Optional[Decimal] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    asset_type: AssetType = AssetType.STOCK
    
@dataclass
class Execution:
    order_id: str
    symbol: str
    action: OrderAction
    quantity: Decimal
    price: Decimal
    commission: Decimal
    timestamp: datetime
    exchange: str

@dataclass
class MarketData:
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume: int
    bid_size: int
    ask_size: int
    timestamp: datetime
    is_halted: bool
    is_snapshot: bool

@dataclass
class Account:
    account_id: str
    net_liquidation: Decimal
    buying_power: Decimal
    cash: Decimal
    maintenance_margin: Decimal
    excess_liquidity: Decimal
    cushion: Decimal

@dataclass
class Strategy:
    name: str
    reasoning: str
    risk_level: Literal["conservative", "moderate", "aggressive"]
    confidence: float
    orders: List[Order]
    max_loss: Optional[Decimal] = None
    max_gain: Optional[Decimal] = None
    
@dataclass
class RiskCheck:
    approved: bool
    warnings: List[str]
    position_size_ok: bool
    buying_power_ok: bool
    daily_loss_ok: bool
    concentration_ok: bool

@dataclass
class ConnectionInfo:
    host: str
    port: int
    client_id: int
    is_connected: bool
    last_heartbeat: datetime
    connection_type: Literal["live", "paper"]