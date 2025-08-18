# order_validator.py - Validates orders - ONE job only
from typing import List, Tuple
from decimal import Decimal
from gallump_next.core.types import Order, OrderType, OrderAction

class OrderValidator:
    """Validates orders - ONE job only"""
    
    def validate(self, order: Order) -> Tuple[bool, List[str]]:
        """Validate a single order"""
        errors = []
        
        # Check quantity
        if order.quantity <= 0:
            errors.append("Quantity must be positive")
        
        if order.quantity > 100000:
            errors.append("Quantity exceeds maximum allowed (100,000)")
        
        # Check symbol
        if not order.symbol or len(order.symbol) == 0:
            errors.append("Symbol is required")
        
        if len(order.symbol) > 10:
            errors.append("Symbol is too long (max 10 characters)")
        
        # Check action
        if order.action not in [OrderAction.BUY, OrderAction.SELL]:
            errors.append(f"Invalid action: {order.action}")
        
        # Check limit price for limit orders
        if order.order_type == OrderType.LIMIT:
            if not order.limit_price or order.limit_price <= 0:
                errors.append("Limit orders require valid limit price")
            
            if order.limit_price > Decimal("100000"):
                errors.append("Limit price exceeds maximum (100,000)")
        
        # Check stop price for stop orders
        if order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
            if not order.stop_price or order.stop_price <= 0:
                errors.append("Stop orders require valid stop price")
            
            if order.stop_price > Decimal("100000"):
                errors.append("Stop price exceeds maximum (100,000)")
        
        # Check stop limit orders have both prices
        if order.order_type == OrderType.STOP_LIMIT:
            if not order.limit_price or order.limit_price <= 0:
                errors.append("Stop limit orders require valid limit price")
        
        # Check trailing stop
        if order.order_type == OrderType.TRAILING_STOP:
            if not order.trail_amount and not order.trail_percent:
                errors.append("Trailing stop requires amount or percent")
            
            if order.trail_amount and order.trail_percent:
                errors.append("Trailing stop cannot have both amount and percent")
            
            if order.trail_amount:
                if order.trail_amount <= 0:
                    errors.append("Trail amount must be positive")
                if order.trail_amount > Decimal("1000"):
                    errors.append("Trail amount exceeds maximum (1000)")
            
            if order.trail_percent:
                if order.trail_percent <= 0:
                    errors.append("Trail percent must be positive")
                if order.trail_percent > Decimal("50"):
                    errors.append("Trail percent exceeds maximum (50%)")
        
        # Market orders should not have prices
        if order.order_type == OrderType.MARKET:
            if order.limit_price:
                errors.append("Market orders should not have limit price")
            if order.stop_price:
                errors.append("Market orders should not have stop price")
        
        return len(errors) == 0, errors
    
    def validate_batch(self, orders: List[Order]) -> Tuple[bool, Dict[int, List[str]]]:
        """Validate multiple orders"""
        all_valid = True
        errors_by_index = {}
        
        for i, order in enumerate(orders):
            valid, errors = self.validate(order)
            if not valid:
                all_valid = False
                errors_by_index[i] = errors
        
        return all_valid, errors_by_index
    
    def validate_bracket_order(self, entry: Order, target: Order, stop: Order) -> Tuple[bool, List[str]]:
        """Validate a bracket order (entry + target + stop loss)"""
        errors = []
        
        # Validate each order individually
        entry_valid, entry_errors = self.validate(entry)
        if not entry_valid:
            errors.extend([f"Entry order: {e}" for e in entry_errors])
        
        target_valid, target_errors = self.validate(target)
        if not target_valid:
            errors.extend([f"Target order: {e}" for e in target_errors])
        
        stop_valid, stop_errors = self.validate(stop)
        if not stop_valid:
            errors.extend([f"Stop order: {e}" for e in stop_errors])
        
        # Bracket-specific validations
        if entry.symbol != target.symbol or entry.symbol != stop.symbol:
            errors.append("All bracket orders must be for the same symbol")
        
        if entry.quantity != target.quantity or entry.quantity != stop.quantity:
            errors.append("All bracket orders must have the same quantity")
        
        # Target and stop should have opposite action from entry
        if entry.action == OrderAction.BUY:
            if target.action != OrderAction.SELL:
                errors.append("Target order must be SELL for BUY entry")
            if stop.action != OrderAction.SELL:
                errors.append("Stop order must be SELL for BUY entry")
        else:
            if target.action != OrderAction.BUY:
                errors.append("Target order must be BUY for SELL entry")
            if stop.action != OrderAction.BUY:
                errors.append("Stop order must be BUY for SELL entry")
        
        # Check price relationships for BUY entry
        if entry.action == OrderAction.BUY and entry.order_type == OrderType.LIMIT:
            if target.order_type == OrderType.LIMIT and target.limit_price:
                if target.limit_price <= entry.limit_price:
                    errors.append("Target price must be higher than entry for BUY")
            
            if stop.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and stop.stop_price:
                if stop.stop_price >= entry.limit_price:
                    errors.append("Stop price must be lower than entry for BUY")
        
        # Check price relationships for SELL entry
        if entry.action == OrderAction.SELL and entry.order_type == OrderType.LIMIT:
            if target.order_type == OrderType.LIMIT and target.limit_price:
                if target.limit_price >= entry.limit_price:
                    errors.append("Target price must be lower than entry for SELL")
            
            if stop.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and stop.stop_price:
                if stop.stop_price <= entry.limit_price:
                    errors.append("Stop price must be higher than entry for SELL")
        
        return len(errors) == 0, errors