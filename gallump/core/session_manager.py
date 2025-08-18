"""
Session Manager - Handles conversation sessions and intelligent context loading
Single responsibility: Manage conversation state efficiently across requests
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import hashlib
from gallump.core.types import SessionContext

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages conversation sessions with intelligent context loading.
    Uses three-tier memory: Hot (Redis), Warm (Recent DB), Cold (Insights).
    """
    
    def __init__(self, cache=None, storage=None):
        """
        Initialize with cache and storage backends
        
        Args:
            cache: Cache instance for hot memory (Redis/in-memory)
            storage: Storage instance for warm/cold memory (SQLite)
        """
        self.cache = cache
        self.storage = storage
        self.max_session_messages = 10  # Limit hot memory
        self.max_relevant_history = 5   # Limit warm memory
        self.max_insights = 20          # Limit cold memory
        self.session_ttl_minutes = 30   # Session timeout
        
    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        """
        Get existing session or create new one
        
        Args:
            session_id: Optional existing session ID
            
        Returns:
            Session ID (existing or newly created)
        """
        if session_id and self._is_session_active(session_id):
            return session_id
        
        # Generate new session ID
        new_id = hashlib.md5(f"{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        # Initialize empty session in cache
        if self.cache:
            self.cache.set_session_data(
                f"{new_id}:messages",
                [],
                expire_minutes=self.session_ttl_minutes
            )
            self.cache.set_session_data(
                f"{new_id}:meta",
                {
                    'created_at': datetime.now().isoformat(),
                    'last_activity': datetime.now().isoformat(),
                    'message_count': 0
                },
                expire_minutes=self.session_ttl_minutes
            )
        
        logger.info(f"Created new session: {new_id}")
        return new_id
    
    def add_message(self, session_id: str, role: str, message: str, symbol: Optional[str] = None):
        """
        Add message to session (hot memory)
        
        Args:
            session_id: Session identifier
            role: 'user' or 'assistant'
            message: Message content
            symbol: Optional symbol context
        """
        # Get current messages
        messages = self._get_session_messages(session_id)
        
        # Add new message
        messages.append({
            'timestamp': datetime.now().isoformat(),
            'role': role,
            'message': message,
            'symbol': symbol
        })
        
        # Trim to max size (keep most recent)
        if len(messages) > self.max_session_messages:
            messages = messages[-self.max_session_messages:]
        
        # Update cache
        if self.cache:
            self.cache.set_session_data(
                f"{session_id}:messages",
                messages,
                expire_minutes=self.session_ttl_minutes
            )
            
            # Update metadata
            meta = self._get_session_meta(session_id)
            meta['last_activity'] = datetime.now().isoformat()
            meta['message_count'] = len(messages)
            if symbol:
                meta['last_symbol'] = symbol
            
            self.cache.set_session_data(
                f"{session_id}:meta",
                meta,
                expire_minutes=self.session_ttl_minutes
            )
        
        # Also persist to storage for warm memory
        if self.storage and role == 'assistant':  # Save complete exchanges
            try:
                # Find the preceding user message
                user_msg = next((m for m in reversed(messages[:-1]) if m['role'] == 'user'), None)
                if user_msg:
                    self.storage.save_conversation(
                        user_prompt=user_msg['message'],
                        assistant_response=message,
                        symbol=symbol,
                        session_id=session_id
                    )
            except Exception as e:
                logger.error(f"Failed to persist conversation: {e}")
    
    def get_context(self, session_id: str, symbol: Optional[str] = None) -> SessionContext:
        """
        Get complete context for session (all three memory tiers)
        
        Args:
            session_id: Session identifier
            symbol: Optional symbol for relevant context loading
            
        Returns:
            SessionContext with hot, warm, and cold memory
        """
        # 1. HOT: Current session messages
        current_messages = self._get_session_messages(session_id)
        
        # 2. WARM: Recent relevant conversations
        relevant_history = []
        if self.storage and symbol:
            try:
                # Get recent conversations for same symbol
                recent = self.storage.get_conversations(
                    symbol=symbol,
                    days=7  # Last week
                )
                # Filter out current session and limit
                relevant_history = [
                    conv for conv in recent 
                    if conv.get('session_id') != session_id
                ][:self.max_relevant_history]
            except Exception as e:
                logger.error(f"Failed to load relevant history: {e}")
        
        # 3. COLD: Compressed insights and lessons
        insights = []
        if self.storage:
            try:
                # Get mistakes and successful patterns
                mistakes = self.storage.get_mistakes(symbol=symbol)[:10]
                good_trades = self.storage.get_annotations(
                    note_type='strategy_liked',
                    symbol=symbol
                )[:5]
                
                # Format as concise bullets
                for mistake in mistakes:
                    insights.append(f"⚠️ Past mistake: {mistake['text'][:100]}")
                for trade in good_trades:
                    insights.append(f"✓ Successful: {trade['text'][:100]}")
                    
                insights = insights[:self.max_insights]
            except Exception as e:
                logger.error(f"Failed to load insights: {e}")
        
        # Build context object
        context = SessionContext(
            session_id=session_id,
            current_messages=current_messages,
            relevant_history=relevant_history,
            insights=insights,
            symbol=symbol,
            created_at=self._get_session_meta(session_id).get('created_at'),
            last_activity=datetime.now()
        )
        
        # Log token usage
        token_estimate = context.token_estimate()
        if token_estimate > 5000:
            logger.warning(f"Large context for session {session_id}: ~{token_estimate} tokens")
        
        return context
    
    def clear_old_sessions(self, days: int = 30):
        """
        Clean up old sessions from storage (not cache - Redis handles TTL)
        
        Args:
            days: Delete sessions older than this many days
        """
        if self.storage:
            cutoff = datetime.now() - timedelta(days=days)
            # This would need a new storage method to clean old conversations
            logger.info(f"Would clean sessions older than {cutoff}")
    
    def _is_session_active(self, session_id: str) -> bool:
        """Check if session exists and is active"""
        if not self.cache:
            return False
        
        meta = self._get_session_meta(session_id)
        if not meta:
            return False
        
        # Check if session has timed out
        last_activity = datetime.fromisoformat(meta.get('last_activity', ''))
        timeout = datetime.now() - timedelta(minutes=self.session_ttl_minutes)
        
        return last_activity > timeout
    
    def _get_session_messages(self, session_id: str) -> List[Dict]:
        """Get messages from hot memory (cache)"""
        if not self.cache:
            return []
        
        try:
            data = self.cache.get_session_data(f"{session_id}:messages")
            if data:
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to get session messages: {e}")
        
        return []
    
    def _get_session_meta(self, session_id: str) -> Dict:
        """Get session metadata from cache"""
        if not self.cache:
            return {}
        
        try:
            data = self.cache.get_session_data(f"{session_id}:meta")
            if data:
                return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.error(f"Failed to get session meta: {e}")
        
        return {}