"""
Cache Module - In-memory and Redis caching for market data and scanner results
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import redis

logger = logging.getLogger(__name__)


@dataclass
class CachedPrice:
    """Cached price data with timestamp"""
    symbol: str
    price: float
    timestamp: datetime
    source: str = 'live'  # 'live', 'delayed', 'cached'
    
    def is_stale(self, max_age_minutes: int = 15) -> bool:
        """Check if cached price is stale"""
        age = datetime.now() - self.timestamp
        return age > timedelta(minutes=max_age_minutes)


class Cache:
    """Cache manager for market data and application state"""
    
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379, use_redis: bool = False):
        """
        Initialize cache with optional Redis backend
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            use_redis: Whether to use Redis (falls back to in-memory if False or Redis unavailable)
        """
        self.use_redis = use_redis
        self.redis_client = None
        
        # In-memory cache fallback
        self.memory_cache = {
            'prices': {},
            'scanner_results': {},
            'watchlist': [],
            'portfolio_snapshot': None,
            'options_chains': {},
            'pending_orders': None,
            'bracket_orders': {}
        }
        
        # Try to connect to Redis if requested
        if use_redis:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    decode_responses=True,
                    socket_connect_timeout=2
                )
                self.redis_client.ping()
                logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
            except Exception as e:
                logger.warning(f"Redis not available, using in-memory cache: {e}")
                self.use_redis = False
                self.redis_client = None
    
    def is_healthy(self) -> bool:
        """Check if cache is operational"""
        if self.use_redis and self.redis_client:
            try:
                return self.redis_client.ping()
            except:
                return False
        return True  # In-memory cache is always "healthy"
    
    def set_price(self, symbol: str, price: float, source: str = 'live'):
        """Cache a price for a symbol with extended TTL for after-hours"""
        cached_price = CachedPrice(
            symbol=symbol,
            price=price,
            timestamp=datetime.now(),
            source=source
        )
        
        # Use longer TTL for after-hours/closing prices
        ttl_minutes = 60 if source in ['close', 'after_hours'] else 15
        
        if self.use_redis and self.redis_client:
            try:
                key = f"price:{symbol}"
                self.redis_client.setex(
                    key,
                    timedelta(minutes=ttl_minutes),
                    json.dumps({
                        'price': price,
                        'timestamp': cached_price.timestamp.isoformat(),
                        'source': source
                    })
                )
            except Exception as e:
                logger.error(f"Redis set error: {e}")
        
        # Always update in-memory cache
        self.memory_cache['prices'][symbol] = cached_price
    
    def get_last_price(self, symbol: str) -> Optional[float]:
        """Get last cached price for a symbol"""
        
        # Try Redis first
        if self.use_redis and self.redis_client:
            try:
                key = f"price:{symbol}"
                data = self.redis_client.get(key)
                if data:
                    price_data = json.loads(data)
                    return price_data['price']
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        # Fall back to in-memory cache
        if symbol in self.memory_cache['prices']:
            cached = self.memory_cache['prices'][symbol]
            if not cached.is_stale(max_age_minutes=60):  # 1 hour for cached prices
                return cached.price
        
        return None
    
    def set_scanner_results(self, scan_code: str, results: List[Dict]):
        """Cache scanner results"""
        cache_key = f"scanner:{scan_code}"
        cache_data = {
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
        
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(
                    cache_key,
                    timedelta(minutes=5),  # Scanner results expire after 5 minutes
                    json.dumps(cache_data)
                )
            except Exception as e:
                logger.error(f"Redis set error for scanner: {e}")
        
        # Always update in-memory cache
        self.memory_cache['scanner_results'][scan_code] = cache_data
    
    def get_scanner_results(self, scan_code: str) -> Optional[List[Dict]]:
        """Get cached scanner results"""
        
        # Try Redis first
        if self.use_redis and self.redis_client:
            try:
                cache_key = f"scanner:{scan_code}"
                data = self.redis_client.get(cache_key)
                if data:
                    cache_data = json.loads(data)
                    return cache_data['results']
            except Exception as e:
                logger.error(f"Redis get error for scanner: {e}")
        
        # Fall back to in-memory cache
        if scan_code in self.memory_cache['scanner_results']:
            cache_data = self.memory_cache['scanner_results'][scan_code]
            # Check if not too old (5 minutes)
            timestamp = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - timestamp < timedelta(minutes=5):
                return cache_data['results']
        
        return None
    
    def set_watchlist(self, symbols: List[str]):
        """Cache watchlist symbols"""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(
                    'watchlist',
                    timedelta(hours=24),
                    json.dumps(symbols)
                )
            except Exception as e:
                logger.error(f"Redis set error for watchlist: {e}")
        
        self.memory_cache['watchlist'] = symbols
    
    def get_watchlist(self) -> List[str]:
        """Get cached watchlist"""
        if self.use_redis and self.redis_client:
            try:
                data = self.redis_client.get('watchlist')
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.error(f"Redis get error for watchlist: {e}")
        
        return self.memory_cache['watchlist']
    
    def set_session_data(self, session_id: str, data: Any, expire_minutes: int = 30):
        """Set session data with expiration"""
        key = f"session:{session_id}"
        
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(
                    key,
                    timedelta(minutes=expire_minutes),
                    json.dumps(data) if not isinstance(data, str) else data
                )
                return True
            except Exception as e:
                logger.error(f"Redis set error for session: {e}")
        
        # Fallback to memory cache with timestamp for expiry
        self.memory_cache[key] = {
            'data': data,
            'expires': datetime.now() + timedelta(minutes=expire_minutes)
        }
        return True
    
    def get_session_data(self, session_id: str) -> Optional[Any]:
        """Get session data"""
        key = f"session:{session_id}"
        
        if self.use_redis and self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    try:
                        return json.loads(data)
                    except json.JSONDecodeError:
                        return data
            except Exception as e:
                logger.error(f"Redis get error for session: {e}")
        
        # Fallback to memory cache
        if key in self.memory_cache:
            cached = self.memory_cache[key]
            # Check expiry
            if datetime.now() < cached['expires']:
                return cached['data']
            else:
                # Clean up expired session
                del self.memory_cache[key]
        
        return None
    
    def set_portfolio_snapshot(self, portfolio: Dict):
        """Cache portfolio snapshot for after-hours access"""
        snapshot = {
            'data': portfolio,
            'timestamp': datetime.now().isoformat()
        }
        
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(
                    'portfolio_snapshot',
                    timedelta(hours=12),  # Keep for 12 hours
                    json.dumps(snapshot)
                )
            except Exception as e:
                logger.error(f"Redis set error for portfolio: {e}")
        
        self.memory_cache['portfolio_snapshot'] = snapshot
    
    def get_portfolio_snapshot(self) -> Optional[Dict]:
        """Get cached portfolio snapshot"""
        
        # Try Redis first
        if self.use_redis and self.redis_client:
            try:
                data = self.redis_client.get('portfolio_snapshot')
                if data:
                    snapshot = json.loads(data)
                    # Check if not too old (12 hours)
                    timestamp = datetime.fromisoformat(snapshot['timestamp'])
                    if datetime.now() - timestamp < timedelta(hours=12):
                        return snapshot['data']
            except Exception as e:
                logger.error(f"Redis get error for portfolio: {e}")
        
        # Fall back to in-memory cache
        if self.memory_cache['portfolio_snapshot']:
            snapshot = self.memory_cache['portfolio_snapshot']
            timestamp = datetime.fromisoformat(snapshot['timestamp'])
            if datetime.now() - timestamp < timedelta(hours=12):
                return snapshot['data']
        
        return None
    
    def set_options_chain(self, symbol: str, chain_data: Dict):
        """Cache options chain data"""
        cache_key = f"options:{symbol}"
        cache_data = {
            'chain': chain_data,
            'timestamp': datetime.now().isoformat()
        }
        
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(
                    cache_key,
                    timedelta(minutes=15),  # Options chains expire after 15 minutes
                    json.dumps(cache_data)
                )
            except Exception as e:
                logger.error(f"Redis set error for options chain: {e}")
        
        self.memory_cache['options_chains'][symbol] = cache_data
    
    def get_options_chain(self, symbol: str) -> Optional[Dict]:
        """Get cached options chain"""
        
        # Try Redis first
        if self.use_redis and self.redis_client:
            try:
                cache_key = f"options:{symbol}"
                data = self.redis_client.get(cache_key)
                if data:
                    cache_data = json.loads(data)
                    # Check if not too old (15 minutes)
                    timestamp = datetime.fromisoformat(cache_data['timestamp'])
                    if datetime.now() - timestamp < timedelta(minutes=15):
                        return cache_data['chain']
            except Exception as e:
                logger.error(f"Redis get error for options chain: {e}")
        
        # Fall back to in-memory cache
        if symbol in self.memory_cache['options_chains']:
            cache_data = self.memory_cache['options_chains'][symbol]
            timestamp = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - timestamp < timedelta(minutes=15):
                return cache_data['chain']
        
        return None
    
    def clear_all(self):
        """Clear all cached data"""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.flushdb()
            except Exception as e:
                logger.error(f"Redis flush error: {e}")
        
        # Clear in-memory cache
        self.memory_cache = {
            'prices': {},
            'scanner_results': {},
            'watchlist': [],
            'portfolio_snapshot': None,
            'options_chains': {}
        }
        
        logger.info("Cache cleared")
    
    def cache_scanner_results(self, scanner_type: str, results: List, ttl: int = 300):
        """Cache scanner results for 5 minutes"""
        key = f"scanner:{scanner_type}"
        self.set(key, results, expire_seconds=ttl)
        logger.info(f"Cached {len(results)} results for scanner {scanner_type}")
    
    def get_cached_scanner(self, scanner_type: str) -> Optional[List]:
        """Get cached scanner results if available"""
        key = f"scanner:{scanner_type}"
        return self.get(key)
    
    def cache_options_chain(self, symbol: str, chain: Dict, ttl: int = 300):
        """Cache options chain for 5 minutes"""
        key = f"options:{symbol}"
        self.set(key, chain, expire_seconds=ttl)
    
    def get_cached_options(self, symbol: str) -> Optional[Dict]:
        """Get cached options chain if available"""
        key = f"options:{symbol}"
        return self.get(key)
    
    def cache_market_depth(self, symbol: str, depth: Dict, ttl: int = 30):
        """Cache market depth for 30 seconds"""
        key = f"depth:{symbol}"
        self.set(key, depth, expire_seconds=ttl)
    
    def get_cached_depth(self, symbol: str) -> Optional[Dict]:
        """Get cached market depth if available"""
        key = f"depth:{symbol}"
        return self.get(key)
    
    def cache_news(self, key: str, news: List, ttl: int = 600):
        """Cache news for 10 minutes"""
        cache_key = f"news:{key}"
        self.set(cache_key, news, expire_seconds=ttl)
    
    def get_cached_news(self, key: str) -> Optional[List]:
        """Get cached news if available"""
        cache_key = f"news:{key}"
        return self.get(cache_key)
    
    # ========== PENDING ORDERS CACHING ==========
    
    def cache_pending_orders(self, orders, ttl: int = 30):
        """
        Cache pending orders for 30 seconds
        Args:
            orders: List of PendingOrder objects or dicts
            ttl: Time to live in seconds
        """
        from gallump.core.types import PendingOrder
        
        # Convert PendingOrder objects to dicts for JSON serialization
        serializable_orders = []
        for order in orders:
            if isinstance(order, PendingOrder):
                serializable_orders.append(order.to_dict())
            else:
                serializable_orders.append(order)
        
        cache_data = {
            'orders': serializable_orders,
            'timestamp': datetime.now().isoformat(),
            'count': len(serializable_orders)
        }
        
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(
                    'pending_orders',
                    timedelta(seconds=ttl),
                    json.dumps(cache_data)
                )
            except Exception as e:
                logger.error(f"Redis set error for pending orders: {e}")
        
        # Always update in-memory cache
        self.memory_cache['pending_orders'] = cache_data
        logger.info(f"Cached {len(serializable_orders)} pending orders")
    
    def get_cached_pending_orders(self):
        """
        Get cached pending orders
        Returns list of PendingOrder objects if available
        """
        from gallump.core.types import PendingOrder
        from datetime import datetime
        
        # Try Redis first
        if self.use_redis and self.redis_client:
            try:
                data = self.redis_client.get('pending_orders')
                if data:
                    cache_data = json.loads(data)
                    # Check if not too old (30 seconds)
                    timestamp = datetime.fromisoformat(cache_data['timestamp'])
                    if datetime.now() - timestamp < timedelta(seconds=30):
                        # Convert dicts back to PendingOrder objects
                        orders = []
                        for order_dict in cache_data['orders']:
                            # Handle datetime field conversions
                            if 'submitted_at' in order_dict and order_dict['submitted_at']:
                                order_dict['submitted_at'] = datetime.fromisoformat(order_dict['submitted_at'])
                            if 'good_after_time' in order_dict and order_dict['good_after_time']:
                                order_dict['good_after_time'] = datetime.fromisoformat(order_dict['good_after_time'])
                            if 'good_till_date' in order_dict and order_dict['good_till_date']:
                                from datetime import date
                                order_dict['good_till_date'] = date.fromisoformat(order_dict['good_till_date'])
                            
                            order = PendingOrder(**order_dict)
                            orders.append(order)
                        
                        logger.info(f"Retrieved {len(orders)} pending orders from Redis cache")
                        return orders
            except Exception as e:
                logger.error(f"Redis get error for pending orders: {e}")
        
        # Fall back to in-memory cache
        if self.memory_cache['pending_orders']:
            cache_data = self.memory_cache['pending_orders']
            # Check if not too old (30 seconds)
            timestamp = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - timestamp < timedelta(seconds=30):
                # Convert dicts back to PendingOrder objects
                orders = []
                for order_dict in cache_data['orders']:
                    # Handle datetime field conversions
                    if 'submitted_at' in order_dict and order_dict['submitted_at']:
                        if isinstance(order_dict['submitted_at'], str):
                            order_dict['submitted_at'] = datetime.fromisoformat(order_dict['submitted_at'])
                    if 'good_after_time' in order_dict and order_dict['good_after_time']:
                        if isinstance(order_dict['good_after_time'], str):
                            order_dict['good_after_time'] = datetime.fromisoformat(order_dict['good_after_time'])
                    if 'good_till_date' in order_dict and order_dict['good_till_date']:
                        if isinstance(order_dict['good_till_date'], str):
                            from datetime import date
                            order_dict['good_till_date'] = date.fromisoformat(order_dict['good_till_date'])
                    
                    order = PendingOrder(**order_dict)
                    orders.append(order)
                
                logger.info(f"Retrieved {len(orders)} pending orders from memory cache")
                return orders
        
        return []
    
    def cache_bracket_orders(self, brackets, ttl: int = 60):
        """
        Cache bracket order groups for 1 minute
        Args:
            brackets: List of BracketOrder objects
            ttl: Time to live in seconds
        """
        from gallump.core.types import BracketOrder
        
        cache_data = {
            'brackets': [],
            'timestamp': datetime.now().isoformat(),
            'count': len(brackets)
        }
        
        # Serialize bracket orders
        for bracket in brackets:
            if isinstance(bracket, BracketOrder):
                bracket_dict = {
                    'main_order': bracket.main_order.to_dict(),
                    'profit_target': bracket.profit_target.to_dict() if bracket.profit_target else None,
                    'stop_loss': bracket.stop_loss.to_dict() if bracket.stop_loss else None,
                    'oca_group': bracket.oca_group
                }
                cache_data['brackets'].append(bracket_dict)
        
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(
                    'bracket_orders',
                    timedelta(seconds=ttl),
                    json.dumps(cache_data)
                )
            except Exception as e:
                logger.error(f"Redis set error for bracket orders: {e}")
        
        # Always update in-memory cache
        self.memory_cache['bracket_orders'] = cache_data
        logger.info(f"Cached {len(brackets)} bracket orders")
    
    def get_cached_bracket_orders(self):
        """Get cached bracket order groups"""
        from gallump.core.types import BracketOrder, PendingOrder
        from datetime import datetime
        
        # Try Redis first
        if self.use_redis and self.redis_client:
            try:
                data = self.redis_client.get('bracket_orders')
                if data:
                    cache_data = json.loads(data)
                    # Check if not too old (1 minute)
                    timestamp = datetime.fromisoformat(cache_data['timestamp'])
                    if datetime.now() - timestamp < timedelta(seconds=60):
                        brackets = []
                        for bracket_dict in cache_data['brackets']:
                            # Reconstruct PendingOrder objects
                            main_order = PendingOrder(**bracket_dict['main_order'])
                            profit_target = PendingOrder(**bracket_dict['profit_target']) if bracket_dict['profit_target'] else None
                            stop_loss = PendingOrder(**bracket_dict['stop_loss']) if bracket_dict['stop_loss'] else None
                            
                            bracket = BracketOrder(
                                main_order=main_order,
                                profit_target=profit_target,
                                stop_loss=stop_loss,
                                oca_group=bracket_dict['oca_group']
                            )
                            brackets.append(bracket)
                        
                        return brackets
            except Exception as e:
                logger.error(f"Redis get error for bracket orders: {e}")
        
        # Fall back to in-memory cache
        if self.memory_cache['bracket_orders']:
            cache_data = self.memory_cache['bracket_orders']
            # Check if not too old (1 minute)
            timestamp = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - timestamp < timedelta(seconds=60):
                brackets = []
                for bracket_dict in cache_data['brackets']:
                    # Reconstruct PendingOrder objects
                    main_order = PendingOrder(**bracket_dict['main_order'])
                    profit_target = PendingOrder(**bracket_dict['profit_target']) if bracket_dict['profit_target'] else None
                    stop_loss = PendingOrder(**bracket_dict['stop_loss']) if bracket_dict['stop_loss'] else None
                    
                    bracket = BracketOrder(
                        main_order=main_order,
                        profit_target=profit_target,
                        stop_loss=stop_loss,
                        oca_group=bracket_dict['oca_group']
                    )
                    brackets.append(bracket)
                
                return brackets
        
        return []
    
    def invalidate_pending_orders(self):
        """Invalidate cached pending orders to force refresh"""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.delete('pending_orders')
                self.redis_client.delete('bracket_orders')
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
        
        # Clear in-memory cache
        self.memory_cache['pending_orders'] = None
        self.memory_cache['bracket_orders'] = {}
        
        logger.info("Pending orders cache invalidated")
    
    def get_pending_orders_stats(self) -> Dict:
        """Get statistics about cached pending orders"""
        orders = self.get_cached_pending_orders()
        
        if not orders:
            return {'total': 0, 'by_status': {}, 'by_type': {}}
        
        stats = {
            'total': len(orders),
            'by_status': {},
            'by_type': {},
            'by_symbol': {},
            'working_orders': 0,
            'bracket_orders': 0
        }
        
        for order in orders:
            # Count by status
            stats['by_status'][order.status] = stats['by_status'].get(order.status, 0) + 1
            
            # Count by type
            stats['by_type'][order.order_type] = stats['by_type'].get(order.order_type, 0) + 1
            
            # Count by symbol
            stats['by_symbol'][order.symbol] = stats['by_symbol'].get(order.symbol, 0) + 1
            
            # Count working orders
            if order.is_working_order():
                stats['working_orders'] += 1
            
            # Count bracket components
            if order.is_bracket_component():
                stats['bracket_orders'] += 1
        
        return stats