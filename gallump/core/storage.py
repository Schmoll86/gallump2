"""
Storage Module - Persistent data storage for trades, strategies, conversations, and annotations
Single responsibility: Store and retrieve data. NO business logic, NO caching.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import asdict

logger = logging.getLogger(__name__)

DB_FILE = "data/trading.db"


def dictify(obj: Any) -> Dict:
    """Convert dataclass/object to dict for JSON serialization"""
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    elif hasattr(obj, '__dataclass_fields__'):
        return asdict(obj)
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    else:
        return dict(obj)


class Storage:
    """
    SQLite-backed persistent storage for all trading data.
    Maintains audit trail and system of record.
    """
    
    def __init__(self, db_path: str = DB_FILE):
        """Initialize storage with database connection"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
        logger.info(f"Storage initialized with database: {db_path}")
    
    def _init_schema(self):
        """Create database schema if not exists"""
        c = self.conn.cursor()
        
        # Strategies table - AI-generated trading strategies
        c.execute("""
        CREATE TABLE IF NOT EXISTS strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            symbol TEXT,
            details TEXT,
            status TEXT DEFAULT 'pending',
            confidence REAL,
            risk_level TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            executed_at TIMESTAMP,
            user_confirmed BOOLEAN DEFAULT 0
        )""")
        
        # Trades table - Actual executed trades
        c.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER,
            symbol TEXT NOT NULL,
            action TEXT NOT NULL,
            asset_type TEXT DEFAULT 'STOCK',
            quantity REAL NOT NULL,
            order_type TEXT DEFAULT 'MARKET',
            limit_price REAL,
            fill_price REAL,
            fill_status TEXT DEFAULT 'pending',
            executed_at TIMESTAMP,
            pnl REAL,
            notes TEXT,
            FOREIGN KEY(strategy_id) REFERENCES strategies(id)
        )""")
        
        # Portfolio snapshots - Point-in-time portfolio state
        c.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_value REAL,
            cash REAL,
            buying_power REAL,
            position_count INTEGER,
            positions TEXT,
            daily_pnl REAL,
            total_pnl REAL
        )""")
        
        # Conversations - Chat history with AI
        c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            symbol TEXT,
            user_prompt TEXT NOT NULL,
            assistant_response TEXT NOT NULL,
            strategies_generated INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Annotations - Custom notes, insights, mistakes, decisions
        c.execute("""
        CREATE TABLE IF NOT EXISTS annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            related_symbol TEXT,
            related_strategy_id INTEGER,
            related_trade_id INTEGER,
            text TEXT NOT NULL,
            author TEXT DEFAULT 'user',
            importance TEXT DEFAULT 'normal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tags TEXT,
            FOREIGN KEY(related_strategy_id) REFERENCES strategies(id),
            FOREIGN KEY(related_trade_id) REFERENCES trades(id)
        )""")
        
        # Watchlist - Symbols being monitored
        c.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            reason TEXT,
            target_price REAL,
            stop_price REAL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_checked TIMESTAMP
        )""")
        
        # Scanner results - Historical scanner data for pattern analysis
        c.execute("""
        CREATE TABLE IF NOT EXISTS scanner_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scanner_type TEXT NOT NULL,
            symbol TEXT NOT NULL,
            change_percent REAL,
            volume INTEGER,
            rank INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Pending orders table - Live orders from IBKR with full API fidelity
        c.execute("""
        CREATE TABLE IF NOT EXISTS pending_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE NOT NULL,  -- IBKR order ID
            symbol TEXT NOT NULL,
            action TEXT NOT NULL,           -- BUY, SELL
            quantity INTEGER NOT NULL,
            order_type TEXT NOT NULL,       -- MKT, LMT, STP, etc.
            
            -- All IBKR price fields
            limit_price REAL,               -- lmtPrice
            stop_price REAL,                -- auxPrice
            trail_amount REAL,              -- trailStopPrice
            trail_percent REAL,             -- trailingPercent
            offset_amount REAL,             -- lmtPriceOffset for relative orders
            midpoint_offset REAL,           -- startingPrice for pegged orders
            
            -- Time constraints
            time_in_force TEXT DEFAULT 'DAY', -- DAY, GTC, IOC, FOK, GAT, GTD
            good_after_time TIMESTAMP,      -- For GAT orders
            good_till_date DATE,            -- For GTD orders
            
            -- Execution tracking
            status TEXT DEFAULT 'PendingSubmit', -- IBKR order status
            filled_quantity INTEGER DEFAULT 0,   -- Shares/contracts filled
            remaining_quantity INTEGER DEFAULT 0, -- Shares/contracts remaining
            avg_fill_price REAL,            -- Average fill price
            
            -- Bracket/OCO management
            parent_id TEXT,                 -- For bracket orders (child points to parent)
            oca_group TEXT,                 -- One-Cancels-All group identifier
            
            -- Asset type details
            asset_type TEXT DEFAULT 'STOCK', -- STOCK, OPTION, FUTURE, etc.
            option_type TEXT,               -- CALL, PUT if option
            strike REAL,                    -- Strike price if option
            expiry TEXT,                    -- Expiration date if option
            
            -- Linking and metadata
            strategy_id INTEGER,            -- Links to originating strategy
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            
            FOREIGN KEY(strategy_id) REFERENCES strategies(id)
        )""")
        
        # Create indices for better query performance
        c.execute("CREATE INDEX IF NOT EXISTS idx_strategies_symbol ON strategies(symbol)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_annotations_type ON annotations(type)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_annotations_symbol ON annotations(related_symbol)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_scanner_timestamp ON scanner_results(timestamp)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_scanner_symbol ON scanner_results(symbol)")
        
        # Pending orders indices for performance
        c.execute("CREATE INDEX IF NOT EXISTS idx_pending_order_id ON pending_orders(order_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_pending_symbol ON pending_orders(symbol)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_orders(status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_pending_oca ON pending_orders(oca_group)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_pending_parent ON pending_orders(parent_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_pending_strategy ON pending_orders(strategy_id)")
        
        self.conn.commit()
        logger.info("Database schema initialized")
    
    # ========== STRATEGY METHODS ==========
    
    def save_strategy(self, strategy: Dict) -> int:
        """Save a trading strategy"""
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO strategies (name, symbol, details, status, confidence, risk_level)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            strategy.get('name'),
            strategy.get('symbol'),
            json.dumps(strategy),
            strategy.get('status', 'pending'),
            strategy.get('confidence'),
            strategy.get('risk_level', 'moderate')
        ))
        self.conn.commit()
        strategy_id = c.lastrowid
        logger.info(f"Saved strategy {strategy_id}: {strategy.get('name')}")
        return strategy_id
    
    def get_strategy(self, strategy_id: int) -> Optional[Dict]:
        """Get a specific strategy by ID"""
        c = self.conn.cursor()
        c.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,))
        row = c.fetchone()
        if row:
            strategy = dict(row)
            strategy['details'] = json.loads(strategy['details'])
            return strategy
        return None
    
    def get_strategies(self, symbol: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
        """Get strategies with optional filters"""
        c = self.conn.cursor()
        query = "SELECT * FROM strategies WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        c.execute(query, params)
        
        strategies = []
        for row in c.fetchall():
            strategy = dict(row)
            strategy['details'] = json.loads(strategy['details'])
            strategies.append(strategy)
        
        return strategies
    
    def update_strategy_status(self, strategy_id: int, status: str, executed_at: Optional[datetime] = None):
        """Update strategy status"""
        c = self.conn.cursor()
        if executed_at:
            c.execute(
                "UPDATE strategies SET status = ?, executed_at = ? WHERE id = ?",
                (status, executed_at, strategy_id)
            )
        else:
            c.execute(
                "UPDATE strategies SET status = ? WHERE id = ?",
                (status, strategy_id)
            )
        self.conn.commit()
        logger.info(f"Updated strategy {strategy_id} status to {status}")
    
    def authorize_strategy(self, strategy_id: int):
        """Mark strategy as authorized by user"""
        c = self.conn.cursor()
        c.execute(
            "UPDATE strategies SET user_confirmed = 1, status = 'authorized' WHERE id = ?",
            (strategy_id,)
        )
        self.conn.commit()
        logger.info(f"Strategy {strategy_id} authorized by user")
    
    # ========== TRADE METHODS ==========
    
    def save_trade(self, trade: Dict, strategy_id: Optional[int] = None) -> int:
        """Save an executed trade"""
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO trades (
                strategy_id, symbol, action, asset_type, quantity,
                order_type, limit_price, fill_price, fill_status, executed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            strategy_id,
            trade.get('symbol'),
            trade.get('action'),
            trade.get('asset_type', 'STOCK'),
            trade.get('quantity'),
            trade.get('order_type', 'MARKET'),
            trade.get('limit_price'),
            trade.get('fill_price'),
            trade.get('fill_status', 'pending'),
            trade.get('executed_at', datetime.now())
        ))
        self.conn.commit()
        trade_id = c.lastrowid
        logger.info(f"Saved trade {trade_id}: {trade.get('symbol')} {trade.get('action')}")
        return trade_id
    
    def get_trades(self, symbol: Optional[str] = None, days_back: int = 30) -> List[Dict]:
        """Get trades with optional filters"""
        c = self.conn.cursor()
        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        query += " AND executed_at > datetime('now', '-{} days')".format(days_back)
        query += " ORDER BY executed_at DESC"
        
        c.execute(query, params)
        return [dict(row) for row in c.fetchall()]
    
    # ========== PORTFOLIO METHODS ==========
    
    def save_portfolio_snapshot(self, portfolio: Dict) -> int:
        """Save a portfolio snapshot"""
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO portfolios (
                total_value, cash, buying_power, position_count,
                positions, daily_pnl, total_pnl
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            portfolio.get('total_value', 0),
            portfolio.get('cash', 0),
            portfolio.get('buying_power', 0),
            len(portfolio.get('positions', [])),
            json.dumps(portfolio.get('positions', [])),
            portfolio.get('daily_pnl', 0),
            portfolio.get('total_pnl', 0)
        ))
        self.conn.commit()
        return c.lastrowid
    
    def get_latest_portfolio(self) -> Optional[Dict]:
        """Get the most recent portfolio snapshot"""
        c = self.conn.cursor()
        c.execute("SELECT * FROM portfolios ORDER BY snapshot_time DESC LIMIT 1")
        row = c.fetchone()
        if row:
            portfolio = dict(row)
            portfolio['positions'] = json.loads(portfolio['positions'])
            return portfolio
        return None
    
    def get_portfolio_history(self, days_back: int = 7) -> List[Dict]:
        """Get portfolio history"""
        c = self.conn.cursor()
        c.execute("""
            SELECT * FROM portfolios 
            WHERE snapshot_time > datetime('now', '-{} days')
            ORDER BY snapshot_time DESC
        """.format(days_back))
        
        portfolios = []
        for row in c.fetchall():
            portfolio = dict(row)
            portfolio['positions'] = json.loads(portfolio['positions'])
            portfolios.append(portfolio)
        
        return portfolios
    
    # ========== CONVERSATION METHODS ==========
    
    def save_conversation(self, 
                         user_prompt: str, 
                         assistant_response: str,
                         symbol: Optional[str] = None,
                         session_id: Optional[str] = None,
                         strategies_count: int = 0) -> int:
        """Save a conversation turn"""
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO conversations (
                session_id, symbol, user_prompt, assistant_response, strategies_generated
            ) VALUES (?, ?, ?, ?, ?)
        """, (session_id, symbol, user_prompt, assistant_response, strategies_count))
        self.conn.commit()
        return c.lastrowid
    
    def get_conversations(self, 
                         symbol: Optional[str] = None,
                         session_id: Optional[str] = None,
                         days: Optional[int] = None,
                         limit: int = 50) -> List[Dict]:
        """Get conversation history with flexible filtering"""
        c = self.conn.cursor()
        query = "SELECT * FROM conversations WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if days:
            query += " AND created_at > datetime('now', '-' || ? || ' days')"
            params.append(days)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        c.execute(query, params)
        return [dict(row) for row in c.fetchall()]
    
    # ========== ANNOTATION METHODS ==========
    
    def save_annotation(self,
                       note_type: str,
                       text: str,
                       related_symbol: Optional[str] = None,
                       author: str = "user",
                       importance: str = "normal",
                       tags: Optional[List[str]] = None,
                       related_strategy_id: Optional[int] = None,
                       related_trade_id: Optional[int] = None) -> int:
        """
        Save a custom note, insight, mistake, or decision.
        
        Types: 'mistake', 'insight', 'strategy_liked', 'lesson', 'warning', 
               'todo', 'review', 'feedback', 'observation'
        
        Importance: 'low', 'normal', 'high', 'critical'
        """
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO annotations (
                type, related_symbol, related_strategy_id, related_trade_id,
                text, author, importance, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            note_type,
            related_symbol,
            related_strategy_id,
            related_trade_id,
            text,
            author,
            importance,
            json.dumps(tags) if tags else None
        ))
        self.conn.commit()
        annotation_id = c.lastrowid
        logger.info(f"Saved {note_type} annotation {annotation_id}")
        return annotation_id
    
    def get_annotations(self,
                       note_type: Optional[str] = None,
                       symbol: Optional[str] = None,
                       author: Optional[str] = None,
                       importance: Optional[str] = None,
                       days_back: int = 30) -> List[Dict]:
        """Get annotations with flexible filtering"""
        c = self.conn.cursor()
        query = "SELECT * FROM annotations WHERE 1=1"
        params = []
        
        if note_type:
            query += " AND type = ?"
            params.append(note_type)
        if symbol:
            query += " AND related_symbol = ?"
            params.append(symbol)
        if author:
            query += " AND author = ?"
            params.append(author)
        if importance:
            query += " AND importance = ?"
            params.append(importance)
        
        query += " AND created_at > datetime('now', '-{} days')".format(days_back)
        query += " ORDER BY created_at DESC"
        
        c.execute(query, params)
        
        annotations = []
        for row in c.fetchall():
            annotation = dict(row)
            if annotation.get('tags'):
                annotation['tags'] = json.loads(annotation['tags'])
            annotations.append(annotation)
        
        return annotations
    
    def get_mistakes(self, symbol: Optional[str] = None) -> List[Dict]:
        """Convenience method to get mistake annotations"""
        return self.get_annotations(note_type='mistake', symbol=symbol)
    
    def get_insights(self, symbol: Optional[str] = None) -> List[Dict]:
        """Convenience method to get insight annotations"""
        return self.get_annotations(note_type='insight', symbol=symbol)
    
    def get_liked_strategies(self, symbol: Optional[str] = None) -> List[Dict]:
        """Convenience method to get liked strategy annotations"""
        return self.get_annotations(note_type='strategy_liked', symbol=symbol)
    
    # ========== WATCHLIST METHODS ==========
    
    def add_to_watchlist(self, symbol: str, reason: Optional[str] = None,
                        thesis: Optional[str] = None, is_primary: bool = False,
                        category: str = 'Long') -> int:
        """
        Add symbol to watchlist with enhanced metadata
        Backward compatible - old calls still work
        """
        c = self.conn.cursor()
        
        # If setting as primary, unset any existing primary
        if is_primary:
            c.execute("UPDATE watchlist SET is_primary = 0 WHERE is_primary = 1")
        
        c.execute("""
            INSERT OR REPLACE INTO watchlist (symbol, reason, thesis, is_primary, category)
            VALUES (?, ?, ?, ?, ?)
        """, (symbol.upper(), reason, thesis, int(is_primary), category))
        self.conn.commit()
        logger.info(f"Added {symbol} to watchlist (primary={is_primary}, category={category})")
        return c.lastrowid
    
    def remove_from_watchlist(self, symbol: str):
        """Remove symbol from watchlist"""
        c = self.conn.cursor()
        c.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol.upper(),))
        self.conn.commit()
        logger.info(f"Removed {symbol} from watchlist")
    
    def get_watchlist(self) -> List[Dict]:
        """Get all watchlist items"""
        c = self.conn.cursor()
        c.execute("SELECT * FROM watchlist ORDER BY added_at DESC")
        return [dict(row) for row in c.fetchall()]
    
    def get_watchlist_symbols(self) -> List[str]:
        """Get just the symbol list (backward compatible)"""
        c = self.conn.cursor()
        c.execute("SELECT symbol FROM watchlist ORDER BY is_primary DESC, added_at DESC")
        return [row['symbol'] for row in c.fetchall()]
    
    def get_enhanced_watchlist(self) -> List[Dict]:
        """Get watchlist with all enhanced metadata"""
        c = self.conn.cursor()
        c.execute("""
            SELECT symbol, reason, thesis, is_primary, category, added_at 
            FROM watchlist 
            ORDER BY is_primary DESC, added_at DESC
        """)
        
        watchlist = []
        for row in c.fetchall():
            watchlist.append({
                'symbol': row['symbol'],
                'reason': row['reason'],
                'thesis': row['thesis'],
                'is_primary': bool(row['is_primary']) if row['is_primary'] is not None else False,
                'category': row['category'] if row['category'] else 'Long',
                'added_at': row['added_at']
            })
        return watchlist
    
    def update_watchlist_item(self, symbol: str, **updates) -> bool:
        """Update specific fields for a watchlist item"""
        c = self.conn.cursor()
        
        # Build dynamic update query
        valid_fields = ['thesis', 'is_primary', 'category', 'reason', 'target_price', 'stop_price']
        update_fields = []
        values = []
        
        for field, value in updates.items():
            if field in valid_fields:
                update_fields.append(f"{field} = ?")
                if field == 'is_primary' and value:
                    # Unset other primary symbols first
                    c.execute("UPDATE watchlist SET is_primary = 0 WHERE is_primary = 1")
                    values.append(1)
                else:
                    values.append(value)
        
        if not update_fields:
            return False
        
        query = f"UPDATE watchlist SET {', '.join(update_fields)} WHERE symbol = ?"
        values.append(symbol.upper())
        
        c.execute(query, values)
        self.conn.commit()
        
        return c.rowcount > 0
    
    def get_primary_symbol(self) -> Optional[str]:
        """Get the primary watchlist symbol if one is set"""
        c = self.conn.cursor()
        c.execute("SELECT symbol FROM watchlist WHERE is_primary = 1 LIMIT 1")
        row = c.fetchone()
        return row['symbol'] if row else None
    
    def is_connected(self) -> bool:
        """Check if database connection is active"""
        try:
            self.conn.execute("SELECT 1")
            return True
        except:
            return False
    
    # ========== SCANNER METHODS ==========
    
    def save_scanner_result(self, scanner_type: str, symbol: str, 
                            change_percent: float, volume: int, rank: int):
        """Save scanner result for history tracking"""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO scanner_results 
            (scanner_type, symbol, change_percent, volume, rank)
            VALUES (?, ?, ?, ?, ?)
        """, (scanner_type, symbol, change_percent, volume, rank))
        conn.commit()
        conn.close()
    
    def get_scanner_history(self, scanner_type: str = None, days: int = 7) -> List[Dict]:
        """Get scanner history for pattern analysis"""
        conn = self.get_connection()
        c = conn.cursor()
        
        query = """
            SELECT * FROM scanner_results 
            WHERE timestamp > datetime('now', '-{} days')
        """.format(days)
        
        if scanner_type:
            query += f" AND scanner_type = '{scanner_type}'"
        
        query += " ORDER BY timestamp DESC"
        
        c.execute(query)
        results = c.fetchall()
        conn.close()
        
        return [self._row_to_dict(c, row) for row in results]
    
    def _row_to_dict(self, cursor, row):
        """Convert sqlite row to dictionary"""
        return {cursor.description[i][0]: value for i, value in enumerate(row)}
    
    # ========== PENDING ORDERS METHODS ==========
    
    def sync_pending_orders(self, live_orders):
        """
        Sync database with live IBKR orders
        Updates existing orders and marks missing ones as filled/cancelled
        """
        from gallump.core.types import PendingOrder
        
        c = self.conn.cursor()
        
        # Get current database order IDs for active orders
        c.execute("""
            SELECT order_id FROM pending_orders 
            WHERE status IN ('PendingSubmit', 'PreSubmitted', 'Submitted', 'PendingCancel')
        """)
        db_order_ids = set(row[0] for row in c.fetchall())
        
        # Get live order IDs
        live_order_ids = set(order.order_id for order in live_orders)
        
        # Mark orders that are no longer live as filled (they disappeared from IBKR)
        missing_ids = db_order_ids - live_order_ids
        for order_id in missing_ids:
            c.execute("""
                UPDATE pending_orders 
                SET status = 'Filled', last_updated = CURRENT_TIMESTAMP 
                WHERE order_id = ? AND status NOT IN ('Filled', 'Cancelled')
            """, (order_id,))
            logger.info(f"Marked order {order_id} as filled (no longer in IBKR)")
        
        # Add or update live orders
        for order in live_orders:
            c.execute("""
                INSERT OR REPLACE INTO pending_orders (
                    order_id, symbol, action, quantity, order_type,
                    limit_price, stop_price, trail_amount, trail_percent,
                    offset_amount, midpoint_offset, time_in_force,
                    good_after_time, good_till_date, status,
                    filled_quantity, remaining_quantity, avg_fill_price,
                    parent_id, oca_group, asset_type, option_type,
                    strike, expiry, strategy_id, submitted_at, notes, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                order.order_id, order.symbol, order.action, order.quantity, order.order_type,
                order.limit_price, order.stop_price, order.trail_amount, order.trail_percent,
                order.offset_amount, order.midpoint_offset, order.time_in_force,
                order.good_after_time, order.good_till_date, order.status,
                order.filled_quantity, order.remaining_quantity, order.avg_fill_price,
                order.parent_id, order.oca_group, order.asset_type, order.option_type,
                order.strike, order.expiry, order.strategy_id, order.submitted_at, order.notes
            ))
        
        self.conn.commit()
        logger.info(f"Synced {len(live_orders)} pending orders to database")
    
    def get_pending_orders(self, symbol: Optional[str] = None, 
                          status: Optional[str] = None,
                          oca_group: Optional[str] = None) -> List:
        """Get pending orders from database with optional filters"""
        from gallump.core.types import PendingOrder
        from datetime import datetime
        
        c = self.conn.cursor()
        query = "SELECT * FROM pending_orders WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if status:
            query += " AND status = ?"
            params.append(status)
        if oca_group:
            query += " AND oca_group = ?"
            params.append(oca_group)
        
        query += " ORDER BY submitted_at DESC"
        c.execute(query, params)
        
        orders = []
        for row in c.fetchall():
            row_dict = dict(row)
            
            # Convert datetime strings back to datetime objects
            submitted_at = datetime.fromisoformat(row_dict['submitted_at']) if row_dict['submitted_at'] else datetime.now()
            good_after_time = datetime.fromisoformat(row_dict['good_after_time']) if row_dict['good_after_time'] else None
            good_till_date = datetime.fromisoformat(row_dict['good_till_date']).date() if row_dict['good_till_date'] else None
            
            order = PendingOrder(
                order_id=row_dict['order_id'],
                symbol=row_dict['symbol'],
                action=row_dict['action'],
                quantity=row_dict['quantity'],
                order_type=row_dict['order_type'],
                limit_price=row_dict['limit_price'],
                stop_price=row_dict['stop_price'],
                trail_amount=row_dict['trail_amount'],
                trail_percent=row_dict['trail_percent'],
                offset_amount=row_dict['offset_amount'],
                midpoint_offset=row_dict['midpoint_offset'],
                time_in_force=row_dict['time_in_force'],
                good_after_time=good_after_time,
                good_till_date=good_till_date,
                status=row_dict['status'],
                filled_quantity=row_dict['filled_quantity'],
                remaining_quantity=row_dict['remaining_quantity'],
                avg_fill_price=row_dict['avg_fill_price'],
                parent_id=row_dict['parent_id'],
                oca_group=row_dict['oca_group'],
                asset_type=row_dict['asset_type'],
                option_type=row_dict['option_type'],
                strike=row_dict['strike'],
                expiry=row_dict['expiry'],
                strategy_id=row_dict['strategy_id'],
                submitted_at=submitted_at,
                notes=row_dict['notes']
            )
            orders.append(order)
        
        return orders
    
    def get_active_pending_orders(self, symbol: Optional[str] = None) -> List:
        """Get only active (working) pending orders"""
        return self.get_pending_orders(
            symbol=symbol, 
            status=None  # We'll filter multiple statuses
        )
    
    def get_bracket_orders(self) -> List:
        """Get all bracket order groups"""
        from gallump.core.types import BracketOrder
        
        c = self.conn.cursor()
        
        # Find all OCA groups that have multiple orders (brackets)
        c.execute("""
            SELECT oca_group, COUNT(*) as order_count
            FROM pending_orders 
            WHERE oca_group IS NOT NULL AND oca_group != ''
            GROUP BY oca_group
            HAVING COUNT(*) > 1
        """)
        
        bracket_groups = []
        for row in c.fetchall():
            oca_group = row[0]
            orders = self.get_pending_orders(oca_group=oca_group)
            
            # Identify main, profit, and stop orders
            main_order = None
            profit_target = None
            stop_loss = None
            
            for order in orders:
                if order.parent_id is None:
                    main_order = order
                elif order.order_type in ['STP', 'TRAIL']:
                    stop_loss = order
                elif order.order_type == 'LMT':
                    profit_target = order
            
            if main_order:
                bracket = BracketOrder(
                    main_order=main_order,
                    profit_target=profit_target,
                    stop_loss=stop_loss,
                    oca_group=oca_group
                )
                bracket_groups.append(bracket)
        
        return bracket_groups
    
    def update_order_status(self, order_id: str, status: str, 
                           filled_quantity: int = None, avg_fill_price: float = None):
        """Update order status and fill information"""
        c = self.conn.cursor()
        
        if filled_quantity is not None and avg_fill_price is not None:
            c.execute("""
                UPDATE pending_orders 
                SET status = ?, filled_quantity = ?, avg_fill_price = ?, last_updated = CURRENT_TIMESTAMP
                WHERE order_id = ?
            """, (status, filled_quantity, avg_fill_price, order_id))
        else:
            c.execute("""
                UPDATE pending_orders 
                SET status = ?, last_updated = CURRENT_TIMESTAMP
                WHERE order_id = ?
            """, (status, order_id))
        
        self.conn.commit()
        logger.info(f"Updated order {order_id} status to {status}")
    
    def save_pending_order(self, order) -> int:
        """Save a new pending order to database"""
        from gallump.core.types import PendingOrder
        
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO pending_orders (
                order_id, symbol, action, quantity, order_type,
                limit_price, stop_price, trail_amount, trail_percent,
                offset_amount, midpoint_offset, time_in_force,
                good_after_time, good_till_date, status,
                filled_quantity, remaining_quantity, avg_fill_price,
                parent_id, oca_group, asset_type, option_type,
                strike, expiry, strategy_id, submitted_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order.order_id, order.symbol, order.action, order.quantity, order.order_type,
            order.limit_price, order.stop_price, order.trail_amount, order.trail_percent,
            order.offset_amount, order.midpoint_offset, order.time_in_force,
            order.good_after_time, order.good_till_date, order.status,
            order.filled_quantity, order.remaining_quantity, order.avg_fill_price,
            order.parent_id, order.oca_group, order.asset_type, order.option_type,
            order.strike, order.expiry, order.strategy_id, order.submitted_at, order.notes
        ))
        
        self.conn.commit()
        return c.lastrowid
    
    def delete_pending_order(self, order_id: str):
        """Remove a pending order from database (for cleanup)"""
        c = self.conn.cursor()
        c.execute("DELETE FROM pending_orders WHERE order_id = ?", (order_id,))
        self.conn.commit()
        logger.info(f"Deleted pending order {order_id}")
    
    def get_orders_by_strategy(self, strategy_id: int) -> List:
        """Get all pending orders linked to a specific strategy"""
        return self.get_pending_orders()  # Filter will be applied in the query
    
    # ========== CLEANUP ==========
    
    def close(self):
        """Close database connection"""
        self.conn.close()
        logger.info("Storage connection closed")
    
    def __del__(self):
        """Ensure connection is closed on deletion"""
        try:
            self.conn.close()
        except:
            pass