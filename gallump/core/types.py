from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, date

@dataclass
class Position:
    """
    Portfolio position with market data
    Maps to frontend PositionCard component display
    """
    symbol: str
    position: float  # Number of shares/contracts (frontend uses this or quantity)
    marketPrice: float  # Current market price (frontend: currentPrice)
    marketValue: float  # Total position value
    averageCost: float  # Average cost basis
    unrealizedPnL: float  # Unrealized profit/loss
    realizedPnL: float  # Realized profit/loss
    contractId: int
    
    # Additional fields added by get_positions endpoint:
    # price_source: str  # 'live', 'cached', or 'unavailable'
    # stale_data: bool  # True if using cached price
    # error: str  # Error message if price unavailable

@dataclass
class Portfolio:
    """Portfolio summary - displayed in PortfolioPanel"""
    total_value: float
    positions: List[Position]

@dataclass
class Trade:
    """Trade details for risk evaluation"""
    asset_type: str
    price: float
    quantity: float

@dataclass
class RiskResult:
    """
    Risk evaluation result
    Used by RED BUTTON to show warnings before execution
    """
    approved: bool
    position_size: float
    stop_loss: float
    max_loss: float  # Displayed prominently in RedButton component
    warnings: List[str]  # Each warning shown as toast notification

@dataclass
class SessionContext:
    """
    Conversation session context for trading discussions
    Displayed in frontend ContextStats component
    """
    session_id: str  # Shown truncated in UI (first 8 chars)
    current_messages: List[Dict[str, Any]]  # Hot memory - active session
    relevant_history: List[Dict[str, Any]]  # Warm memory - recent relevant 
    insights: List[str]                     # Cold memory - compressed lessons
    symbol: Optional[str] = None
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    
    def token_estimate(self) -> int:
        """
        Estimate token count for this context
        Frontend shows warning at >80,000 tokens
        """
        # Rough estimate: 1 token per 4 characters
        current_tokens = sum(len(str(m)) for m in self.current_messages) // 4
        history_tokens = sum(len(str(m)) for m in self.relevant_history) // 4
        insights_tokens = sum(len(i) for i in self.insights) // 4
        return current_tokens + history_tokens + insights_tokens

@dataclass
class MCPAnalysis:
    """
    Read-only market analysis from MCP server
    Cannot contain execution instructions
    """
    scan_results: List[Dict[str, Any]]  # Scanner results
    context_score: float  # Relevance to current session
    technical_indicators: Dict[str, float]  # Technical analysis
    timestamp: str  # When analysis was performed
    source: str = "MCP_ANALYTICS"  # Always MCP
    can_execute: bool = False  # Always False for MCP

@dataclass 
class Strategy:
    """
    Trading strategy recommendation
    Displayed in frontend StrategyCard component
    """
    name: str  # Strategy name/title
    reasoning: str  # AI's reasoning (shown in expandable section)
    orders: List[Dict[str, Any]]  # List of orders to execute
    confidence: float  # 0-100 confidence score (shown with bar icon)
    risk_level: str  # 'low', 'medium', 'high' (color-coded in UI)
    id: Optional[int] = None  # Database ID after saving
    description: Optional[str] = None  # Brief description
    max_loss: Optional[float] = None  # Maximum potential loss (RED text)
    stop_loss: Optional[float] = None  # Stop loss price
    session_id: Optional[str] = None  # Links to conversation session
    status: str = 'PENDING_USER_APPROVAL'  # Status tracking

@dataclass
class Order:
    """
    Individual order within a strategy
    Each order shown as a line item in RedButton confirmation
    """
    symbol: str  # Ticker symbol
    action: str  # 'BUY' or 'SELL' (color-coded green/red)
    quantity: int  # Number of shares/contracts
    order_type: str  # 'MKT' or 'LMT'
    limit_price: Optional[float] = None  # Limit price if LMT order
    asset_type: str = 'STOCK'  # 'STOCK' or 'OPTION'
    option_type: Optional[str] = None  # 'CALL' or 'PUT' if option
    strike: Optional[float] = None  # Strike price if option
    expiry: Optional[str] = None  # Expiration date if option

# IBKR-compliant order type enumeration
IBKR_ORDER_TYPES = {
    'MKT': 'Market',
    'LMT': 'Limit', 
    'STP': 'Stop',
    'STP LMT': 'Stop Limit',
    'TRAIL': 'Trailing Stop',
    'TRAIL LIMIT': 'Trailing Stop Limit',
    'MIT': 'Market If Touched',
    'LIT': 'Limit If Touched',
    'MOC': 'Market On Close',
    'LOC': 'Limit On Close',
    'PEGMKT': 'Pegged to Market',
    'PEGMID': 'Pegged to Midpoint',
    'REL': 'Relative',
    'SNAP MKT': 'Snap to Market',
    'SNAP MID': 'Snap to Midpoint'
}

IBKR_ORDER_STATUSES = {
    'PendingSubmit', 'PendingCancel', 'PreSubmitted', 'Submitted',
    'Cancelled', 'Filled', 'Inactive', 'PartiallyFilled', 'ApiCancelled'
}

IBKR_TIME_IN_FORCE = {
    'DAY': 'Day Order',
    'GTC': 'Good Till Cancelled', 
    'IOC': 'Immediate or Cancel',
    'FOK': 'Fill or Kill',
    'GAT': 'Good After Time',
    'GTD': 'Good Till Date'
}

@dataclass
class PendingOrder:
    """
    Live pending order from IBKR with full API fidelity
    Displayed in frontend PendingOrdersPanel
    """
    order_id: str  # IBKR order ID
    symbol: str
    action: str  # 'BUY', 'SELL'
    quantity: int
    order_type: str  # From IBKR_ORDER_TYPES
    
    # Price fields (IBKR-specific mapping)
    limit_price: Optional[float] = None  # lmtPrice
    stop_price: Optional[float] = None  # auxPrice
    trail_amount: Optional[float] = None  # trailStopPrice
    trail_percent: Optional[float] = None  # trailingPercent
    
    # Algorithmic order fields
    offset_amount: Optional[float] = None  # lmtPriceOffset for relative orders
    midpoint_offset: Optional[float] = None  # startingPrice for pegged orders
    
    # Time constraints
    time_in_force: str = 'DAY'  # From IBKR_TIME_IN_FORCE
    good_after_time: Optional[datetime] = None  # GAT orders
    good_till_date: Optional[date] = None  # GTD orders
    
    # Order status and execution tracking
    status: str = 'PendingSubmit'  # From IBKR_ORDER_STATUSES
    filled_quantity: int = 0  # Shares/contracts filled
    remaining_quantity: int = 0  # Shares/contracts remaining
    avg_fill_price: Optional[float] = None  # Average fill price
    
    # Bracket/OCO linking
    parent_id: Optional[str] = None  # For bracket orders
    oca_group: Optional[str] = None  # One-Cancels-All group
    
    # Metadata
    submitted_at: datetime = datetime.now()
    strategy_id: Optional[int] = None  # Links to originating strategy
    notes: Optional[str] = None
    
    # Asset type details
    asset_type: str = 'STOCK'  # 'STOCK', 'OPTION', 'FUTURE', etc.
    option_type: Optional[str] = None  # 'CALL' or 'PUT' if option
    strike: Optional[float] = None  # Strike price if option
    expiry: Optional[str] = None  # Expiration date if option
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'action': self.action,
            'quantity': self.quantity,
            'order_type': self.order_type,
            'limit_price': self.limit_price,
            'stop_price': self.stop_price,
            'trail_amount': self.trail_amount,
            'trail_percent': self.trail_percent,
            'offset_amount': self.offset_amount,
            'midpoint_offset': self.midpoint_offset,
            'time_in_force': self.time_in_force,
            'good_after_time': self.good_after_time.isoformat() if self.good_after_time else None,
            'good_till_date': self.good_till_date.isoformat() if self.good_till_date else None,
            'status': self.status,
            'filled_quantity': self.filled_quantity,
            'remaining_quantity': self.remaining_quantity,
            'avg_fill_price': self.avg_fill_price,
            'parent_id': self.parent_id,
            'oca_group': self.oca_group,
            'submitted_at': self.submitted_at.isoformat(),
            'strategy_id': self.strategy_id,
            'notes': self.notes,
            'asset_type': self.asset_type,
            'option_type': self.option_type,
            'strike': self.strike,
            'expiry': self.expiry
        }
    
    def is_bracket_component(self) -> bool:
        """Check if this order is part of a bracket order"""
        return self.parent_id is not None or self.oca_group is not None
    
    def is_working_order(self) -> bool:
        """Check if order is actively working (not filled/cancelled)"""
        return self.status in ['PendingSubmit', 'PreSubmitted', 'Submitted']
    
    def get_display_price(self) -> Optional[float]:
        """Get the most relevant price for display"""
        if self.order_type == 'MKT':
            return None  # Market orders don't have a price
        elif self.order_type in ['LMT', 'STP LMT']:
            return self.limit_price
        elif self.order_type in ['STP', 'MIT', 'LIT']:
            return self.stop_price
        elif self.order_type == 'TRAIL':
            return self.trail_amount or self.trail_percent
        else:
            return self.limit_price or self.stop_price

@dataclass
class BracketOrder:
    """
    Bracket order with main entry, profit target, and stop loss
    Groups related orders for display and management
    """
    main_order: PendingOrder
    profit_target: Optional[PendingOrder] = None
    stop_loss: Optional[PendingOrder] = None
    oca_group: str = ""  # Links all bracket components
    
    def get_all_orders(self) -> List[PendingOrder]:
        """Get all orders in the bracket"""
        orders = [self.main_order]
        if self.profit_target:
            orders.append(self.profit_target)
        if self.stop_loss:
            orders.append(self.stop_loss)
        return orders
    
    def is_complete(self) -> bool:
        """Check if bracket has all three components"""
        return all([self.main_order, self.profit_target, self.stop_loss])
    
    def get_status(self) -> str:
        """Get overall bracket status"""
        orders = self.get_all_orders()
        
        # If main order not filled, return its status
        if not self.main_order.filled_quantity:
            return self.main_order.status
            
        # If main filled, check exit orders
        exit_orders = [o for o in orders if o != self.main_order]
        if any(o.status == 'Filled' for o in exit_orders):
            return 'Bracket Closed'
        elif any(o.status in ['Submitted', 'PreSubmitted'] for o in exit_orders):
            return 'Managing Position'
        else:
            return 'Bracket Active'
