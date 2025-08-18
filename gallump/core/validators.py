"""
Validators Module - Validates and normalizes all trading data
Single responsibility: Ensure data integrity and type safety before processing
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def validate_strategy(strategy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize a trading strategy dictionary.
    Ensures all required fields exist and are properly typed.
    
    Args:
        strategy: Raw strategy dictionary
        
    Returns:
        Normalized and validated strategy dictionary
        
    Raises:
        ValueError: If validation fails
    """
    # Required top-level fields
    required_fields = ['name', 'orders']
    for field in required_fields:
        if field not in strategy:
            raise ValueError(f"Strategy missing required field: {field}")
    
    # Validate name
    if not strategy['name'] or not isinstance(strategy['name'], str):
        raise ValueError("Strategy name must be a non-empty string")
    
    # Validate orders array
    if not isinstance(strategy['orders'], list):
        raise ValueError("Strategy orders must be a list")
    
    if len(strategy['orders']) == 0:
        raise ValueError("Strategy must contain at least one order")
    
    # Validate each order
    validated_orders = []
    for i, order in enumerate(strategy['orders']):
        try:
            validated_order = validate_order(order)
            validated_orders.append(validated_order)
        except ValueError as e:
            raise ValueError(f"Order {i} validation failed: {e}")
    
    # Build normalized strategy
    normalized = {
        'name': strategy['name'],
        'orders': validated_orders,
        'id': strategy.get('id', f"strat-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
        'description': strategy.get('description', ''),
        'reasoning': strategy.get('reasoning', ''),
        'risk_level': strategy.get('risk_level', 'moderate'),
        'confidence': float(strategy.get('confidence', 0.5)),
        'stop_loss': float(strategy.get('stop_loss', 40)),  # Default 40% stop loss
        'max_loss': float(strategy.get('max_loss', 0)),
        'max_gain': float(strategy.get('max_gain', 0)),
        'created_at': strategy.get('created_at', datetime.now().isoformat())
    }
    
    # Validate confidence is between 0 and 100 (or 0 and 1)
    if normalized['confidence'] > 1:
        normalized['confidence'] = normalized['confidence'] / 100
    
    if not 0 <= normalized['confidence'] <= 1:
        raise ValueError(f"Confidence must be between 0 and 1, got {normalized['confidence']}")
    
    # Validate risk level
    valid_risk_levels = ['conservative', 'moderate', 'aggressive']
    if normalized['risk_level'] not in valid_risk_levels:
        logger.warning(f"Unknown risk level: {normalized['risk_level']}, defaulting to moderate")
        normalized['risk_level'] = 'moderate'
    
    logger.info(f"Validated strategy: {normalized['name']} with {len(normalized['orders'])} orders")
    return normalized


def validate_order(order: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize a single order dictionary.
    Ensures all required fields exist and are properly typed.
    
    Args:
        order: Raw order dictionary
        
    Returns:
        Normalized and validated order dictionary
        
    Raises:
        ValueError: If validation fails
    """
    # Required fields for all orders
    required_fields = ['symbol', 'action', 'quantity']
    for field in required_fields:
        if field not in order or order[field] is None:
            raise ValueError(f"Order missing required field: {field}")
    
    # Normalize and validate action
    action = str(order['action']).upper()
    if action not in ['BUY', 'SELL']:
        raise ValueError(f"Invalid action: {action}. Must be BUY or SELL")
    
    # Validate quantity
    try:
        quantity = int(order['quantity'])
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
    except (ValueError, TypeError):
        raise ValueError(f"Invalid quantity: {order['quantity']}")
    
    # Determine asset type
    asset_type = order.get('asset_type', 'STOCK').upper()
    if asset_type not in ['STOCK', 'OPTION']:
        raise ValueError(f"Invalid asset_type: {asset_type}")
    
    # Build normalized order
    normalized = {
        'symbol': str(order['symbol']).upper(),
        'action': action,
        'quantity': quantity,
        'asset_type': asset_type,
        'order_type': order.get('order_type', 'MARKET').upper(),
        'time_in_force': order.get('time_in_force', 'DAY').upper()
    }
    
    # Validate order type
    valid_order_types = ['MARKET', 'MKT', 'LIMIT', 'LMT', 'STOP', 'STP', 'STOP_LIMIT', 'STP LMT', 'TRAIL', 'TRAILING_STOP']
    # Normalize order type aliases
    order_type_map = {
        'MARKET': 'MKT',
        'LIMIT': 'LMT', 
        'STOP': 'STP',
        'STOP_LIMIT': 'STP LMT',
        'TRAILING_STOP': 'TRAIL'
    }
    if normalized['order_type'] in order_type_map:
        normalized['order_type'] = order_type_map[normalized['order_type']]
    
    if normalized['order_type'] not in ['MKT', 'LMT', 'STP', 'STP LMT', 'TRAIL']:
        raise ValueError(f"Invalid order_type: {normalized['order_type']}")
    
    # Add limit price if LIMIT or STOP_LIMIT order
    if normalized['order_type'] in ['LMT', 'STP LMT']:
        if 'limit_price' not in order or order['limit_price'] is None:
            raise ValueError(f"{normalized['order_type']} order requires limit_price")
        try:
            normalized['limit_price'] = float(order['limit_price'])
            if normalized['limit_price'] <= 0:
                raise ValueError("Limit price must be positive")
        except (ValueError, TypeError):
            raise ValueError(f"Invalid limit_price: {order['limit_price']}")
    
    # Add stop price if STOP or STOP_LIMIT order
    if normalized['order_type'] in ['STP', 'STP LMT']:
        if 'stop_price' not in order or order['stop_price'] is None:
            raise ValueError(f"{normalized['order_type']} order requires stop_price")
        try:
            normalized['stop_price'] = float(order['stop_price'])
            if normalized['stop_price'] <= 0:
                raise ValueError("Stop price must be positive")
        except (ValueError, TypeError):
            raise ValueError(f"Invalid stop_price: {order['stop_price']}")
    
    # Add trailing stop parameters if TRAIL order
    if normalized['order_type'] == 'TRAIL':
        # Must have either trail_percent or trail_amount (but not both)
        has_percent = 'trail_percent' in order and order['trail_percent'] is not None
        has_amount = 'trail_amount' in order and order['trail_amount'] is not None
        
        if not has_percent and not has_amount:
            raise ValueError("TRAIL order requires either trail_percent or trail_amount")
        
        if has_percent:
            try:
                normalized['trail_percent'] = float(order['trail_percent'])
                if normalized['trail_percent'] <= 0 or normalized['trail_percent'] > 100:
                    raise ValueError("Trail percent must be between 0 and 100")
            except (ValueError, TypeError):
                raise ValueError(f"Invalid trail_percent: {order['trail_percent']}")
        
        if has_amount:
            try:
                normalized['trail_amount'] = float(order['trail_amount'])
                if normalized['trail_amount'] <= 0:
                    raise ValueError("Trail amount must be positive")
            except (ValueError, TypeError):
                raise ValueError(f"Invalid trail_amount: {order['trail_amount']}")
    
    # Validate options-specific fields
    if asset_type == 'OPTION':
        # Required options fields
        option_fields = ['expiry', 'strike', 'option_type']
        for field in option_fields:
            if field not in order or order[field] is None:
                # Check for alternative field names
                if field == 'option_type' and 'right' in order:
                    continue  # Will handle below
                raise ValueError(f"Option order missing required field: {field}")
        
        # Validate expiry date format (YYYY-MM-DD)
        expiry = str(order['expiry'])
        try:
            datetime.strptime(expiry, '%Y-%m-%d')
            normalized['expiry'] = expiry
        except ValueError:
            raise ValueError(f"Invalid expiry date format: {expiry}. Use YYYY-MM-DD")
        
        # Validate strike price
        try:
            normalized['strike'] = float(order['strike'])
            if normalized['strike'] <= 0:
                raise ValueError("Strike price must be positive")
        except (ValueError, TypeError):
            raise ValueError(f"Invalid strike price: {order['strike']}")
        
        # Normalize option type / right
        # Accept either 'option_type' (CALL/PUT) or 'right' (C/P)
        option_type = None
        if 'option_type' in order:
            opt = str(order['option_type']).upper()
            if opt == 'CALL':
                option_type = 'C'
            elif opt == 'PUT':
                option_type = 'P'
            elif opt in ['C', 'P']:
                option_type = opt
            else:
                raise ValueError(f"Invalid option_type: {opt}")
        elif 'right' in order:
            right = str(order['right']).upper()
            if right in ['C', 'P']:
                option_type = right
            elif right == 'CALL':
                option_type = 'C'
            elif right == 'PUT':
                option_type = 'P'
            else:
                raise ValueError(f"Invalid right: {right}")
        
        if not option_type:
            raise ValueError("Option order must specify option_type (CALL/PUT) or right (C/P)")
        
        normalized['option_type'] = option_type
        normalized['right'] = option_type  # Store both for compatibility
    
    # Add optional fields if present
    optional_fields = ['strategy_name', 'leg_group_id', 'notes']
    for field in optional_fields:
        if field in order and order[field] is not None:
            normalized[field] = order[field]
    
    logger.debug(f"Validated order: {normalized['symbol']} {normalized['action']} {normalized['quantity']}")
    return normalized


def normalize_order_dict(order: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize field names and values for compatibility.
    Handles common variations in field naming.
    
    Args:
        order: Raw order dictionary with potentially inconsistent field names
        
    Returns:
        Normalized order dictionary
    """
    # Field name mappings for normalization
    field_mappings = {
        'qty': 'quantity',
        'side': 'action',
        'ticker': 'symbol',
        'type': 'order_type',
        'tif': 'time_in_force',
        'limit': 'limit_price',
        'stop': 'stop_price'
    }
    
    # Create normalized dict with mapped field names
    normalized = {}
    for key, value in order.items():
        # Map field name if needed
        mapped_key = field_mappings.get(key.lower(), key.lower())
        normalized[mapped_key] = value
    
    # Ensure action is BUY/SELL (not buy/sell or Buy/Sell)
    if 'action' in normalized:
        normalized['action'] = str(normalized['action']).upper()
    elif 'side' in normalized:
        normalized['action'] = str(normalized['side']).upper()
    
    # Ensure symbol is uppercase
    if 'symbol' in normalized:
        normalized['symbol'] = str(normalized['symbol']).upper()
    
    # Convert option_type to right for IBKR compatibility
    if 'option_type' in normalized and 'right' not in normalized:
        opt = str(normalized['option_type']).upper()
        if opt == 'CALL':
            normalized['right'] = 'C'
        elif opt == 'PUT':
            normalized['right'] = 'P'
        elif opt in ['C', 'P']:
            normalized['right'] = opt
    
    return normalized


def validate_portfolio_constraints(orders: List[Dict], portfolio: Dict) -> List[str]:
    """
    Validate orders against portfolio constraints.
    
    Args:
        orders: List of validated orders
        portfolio: Current portfolio state
        
    Returns:
        List of warning messages (empty if all constraints pass)
    """
    warnings = []
    
    # Calculate total order value
    total_order_value = 0
    for order in orders:
        # Estimate order value (simplified - doesn't account for options multiplier)
        if 'limit_price' in order:
            price = order['limit_price']
        else:
            # For market orders, would need current price
            price = 0  # Cannot calculate without market data
        
        total_order_value += price * order['quantity']
    
    # Check buying power
    buying_power = portfolio.get('buying_power', 0)
    if total_order_value > buying_power:
        warnings.append(f"Order value ${total_order_value:.2f} exceeds buying power ${buying_power:.2f}")
    
    # Check position concentration
    positions = portfolio.get('positions', [])
    position_count = len(positions)
    
    if position_count >= 10:
        warnings.append(f"Portfolio already has {position_count} positions (recommended max: 10)")
    
    # Check for duplicate symbols
    existing_symbols = {pos.get('symbol') for pos in positions}
    order_symbols = {order['symbol'] for order in orders}
    duplicates = existing_symbols & order_symbols
    
    if duplicates:
        warnings.append(f"Already have positions in: {', '.join(duplicates)}")
    
    return warnings