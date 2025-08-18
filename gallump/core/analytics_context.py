"""
Intelligent Context Management for MCP Analytics
Handles massive data feeds while staying within Claude Desktop token limits
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)

class ContextPriority(Enum):
    CRITICAL = 1      # Always include (current positions, active trades)
    HIGH = 2          # Include if space (recent significant moves)
    MEDIUM = 3        # Include if requested (sector data, correlations)
    LOW = 4           # Background data (historical comparisons)
    ARCHIVE = 5       # Summarize only (old news, expired options)

@dataclass
class ContextItem:
    """Individual piece of context with metadata"""
    key: str
    data: Any
    priority: ContextPriority
    timestamp: datetime
    token_estimate: int
    relevance_score: float = 0.0
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)

class IntelligentContextManager:
    """
    Manages context for Claude Desktop with intelligent prioritization
    - Keeps critical data always available
    - Summarizes less important data
    - Maintains conversation flow
    - Respects token limits
    """
    
    def __init__(self, max_tokens: int = 180000):  # Leave buffer for Claude Desktop
        self.max_tokens = max_tokens
        self.context_items: Dict[str, ContextItem] = {}
        self.conversation_focus = []  # Track current conversation topics
        self.user_preferences = {}   # Learn what user cares about
        
        # Token budgets by category
        self.token_budgets = {
            ContextPriority.CRITICAL: 50000,   # 28% - Portfolio, active positions
            ContextPriority.HIGH: 40000,       # 22% - Recent significant events
            ContextPriority.MEDIUM: 30000,     # 17% - Requested analysis
            ContextPriority.LOW: 20000,        # 11% - Background context
            ContextPriority.ARCHIVE: 10000     # 6%  - Summarized historical
        }
    
    def add_market_data(self, symbol: str, data: Dict, data_type: str) -> None:
        """Add market data with intelligent prioritization"""
        
        priority = self._determine_priority(symbol, data, data_type)
        token_estimate = self._estimate_tokens(data)
        relevance_score = self._calculate_relevance(symbol, data, data_type)
        
        key = f"{data_type}_{symbol}_{datetime.now().strftime('%H%M')}"
        
        item = ContextItem(
            key=key,
            data=data,
            priority=priority,
            timestamp=datetime.now(),
            token_estimate=token_estimate,
            relevance_score=relevance_score,
            tags=[symbol, data_type]
        )
        
        self.context_items[key] = item
        self._cleanup_if_needed()
    
    def add_news_data(self, articles: List[Dict], symbols: List[str]) -> None:
        """Add news with intelligent filtering and summarization"""
        
        # Filter and prioritize news
        high_impact_news = []
        medium_impact_news = []
        low_impact_news = []
        
        for article in articles:
            impact_score = self._score_news_impact(article, symbols)
            
            if impact_score > 0.7:
                high_impact_news.append(article)
            elif impact_score > 0.4:
                medium_impact_news.append(article)
            else:
                low_impact_news.append(article)
        
        # Add high impact news in full
        for article in high_impact_news:
            self._add_news_item(article, ContextPriority.HIGH, symbols)
        
        # Summarize medium impact news
        if medium_impact_news:
            summary = self._summarize_news(medium_impact_news)
            self._add_news_item(summary, ContextPriority.MEDIUM, symbols)
        
        # Archive low impact news (just headlines)
        if low_impact_news:
            headlines = [{"title": a.get("headline", ""), "sentiment": a.get("sentiment")} 
                        for a in low_impact_news]
            self._add_news_item({"type": "headline_summary", "headlines": headlines}, 
                              ContextPriority.ARCHIVE, symbols)
    
    def add_options_data(self, symbol: str, options_chain: Dict, greeks: Dict) -> None:
        """Add options data with focus on relevant strikes and expirations"""
        
        # Filter options to most relevant strikes
        current_price = options_chain.get('underlying_price', 0)
        relevant_options = self._filter_relevant_options(options_chain, current_price)
        
        # Summarize Greeks by expiration
        greeks_summary = self._summarize_greeks(greeks)
        
        # Detect unusual activity
        unusual_activity = self._detect_unusual_options_activity(options_chain)
        
        # Prioritize based on portfolio exposure
        priority = ContextPriority.HIGH if self._has_position(symbol) else ContextPriority.MEDIUM
        
        options_context = {
            'symbol': symbol,
            'current_price': current_price,
            'relevant_strikes': relevant_options,
            'greeks_summary': greeks_summary,
            'unusual_activity': unusual_activity,
            'iv_percentile': options_chain.get('iv_percentile'),
            'timestamp': datetime.now().isoformat()
        }
        
        key = f"options_{symbol}"
        item = ContextItem(
            key=key,
            data=options_context,
            priority=priority,
            timestamp=datetime.now(),
            token_estimate=self._estimate_tokens(options_context),
            relevance_score=self._calculate_options_relevance(symbol, options_context),
            tags=[symbol, 'options', 'greeks']
        )
        
        self.context_items[key] = item
    
    def get_context_for_claude(self, conversation_prompt: str, symbols: List[str]) -> Dict:
        """Build optimized context package for Claude Desktop"""
        
        # Update conversation focus
        self._update_conversation_focus(conversation_prompt, symbols)
        
        # Build context within token budget
        context_package = {
            'conversation_context': {
                'focus_symbols': symbols,
                'user_intent': self._analyze_user_intent(conversation_prompt),
                'conversation_topics': self.conversation_focus[-5:]  # Recent topics
            },
            'market_context': {},
            'portfolio_context': {},
            'analysis_suggestions': [],
            'context_summary': {}
        }
        
        # Allocate tokens by priority
        remaining_budget = self.max_tokens
        
        for priority in ContextPriority:
            if remaining_budget <= 0:
                break
                
            budget = min(self.token_budgets[priority], remaining_budget)
            priority_items = self._get_priority_items(priority, symbols, budget)
            
            if priority_items:
                category_name = f"{priority.name.lower()}_data"
                context_package['market_context'][category_name] = priority_items
                used_tokens = sum(item.token_estimate for item in priority_items.values())
                remaining_budget -= used_tokens
        
        # Add context management metadata
        context_package['context_summary'] = {
            'total_tokens_used': self.max_tokens - remaining_budget,
            'items_included': len([item for items in context_package['market_context'].values() 
                                 for item in items]),
            'items_summarized': self._count_summarized_items(),
            'focus_symbols': symbols,
            'data_freshness': self._get_data_freshness_summary(),
            'next_refresh_in': self._get_next_refresh_time()
        }
        
        return context_package
    
    def _determine_priority(self, symbol: str, data: Dict, data_type: str) -> ContextPriority:
        """Determine priority based on multiple factors"""
        
        # Critical: Current positions, active trades
        if self._has_position(symbol):
            return ContextPriority.CRITICAL
        
        # High: Watchlist symbols, recent significant moves
        if (symbol in self._get_watchlist() or 
            self._is_significant_move(data) or
            data_type in ['unusual_options', 'breaking_news']):
            return ContextPriority.HIGH
        
        # Medium: Requested analysis, sector leaders
        if (symbol in self.conversation_focus or
            data_type in ['sector_analysis', 'correlation']):
            return ContextPriority.MEDIUM
        
        # Low: Background market data
        if data_type in ['market_breadth', 'economic_calendar']:
            return ContextPriority.LOW
        
        return ContextPriority.ARCHIVE
    
    def _calculate_relevance(self, symbol: str, data: Dict, data_type: str) -> float:
        """Calculate relevance score 0.0 to 1.0"""
        score = 0.0
        
        # Portfolio relevance
        if self._has_position(symbol):
            score += 0.4
        elif symbol in self._get_watchlist():
            score += 0.2
        
        # Conversation relevance
        if symbol in self.conversation_focus:
            score += 0.3
        
        # Data significance
        if self._is_significant_move(data):
            score += 0.2
        
        # Recency bonus
        age_minutes = (datetime.now() - data.get('timestamp', datetime.now())).total_seconds() / 60
        recency_score = max(0, 1 - (age_minutes / 60))  # Decay over 1 hour
        score += recency_score * 0.1
        
        return min(1.0, score)
    
    def _filter_relevant_options(self, options_chain: Dict, current_price: float) -> Dict:
        """Filter options to most relevant strikes"""
        
        # Keep strikes within ±20% of current price
        price_range = current_price * 0.2
        min_strike = current_price - price_range
        max_strike = current_price + price_range
        
        filtered = {}
        for expiration, strikes in options_chain.get('expirations', {}).items():
            relevant_strikes = {}
            for strike, option_data in strikes.items():
                strike_price = float(strike)
                if min_strike <= strike_price <= max_strike:
                    # Keep only essential data
                    relevant_strikes[strike] = {
                        'bid': option_data.get('bid'),
                        'ask': option_data.get('ask'),
                        'volume': option_data.get('volume'),
                        'open_interest': option_data.get('open_interest'),
                        'iv': option_data.get('implied_volatility'),
                        'delta': option_data.get('delta'),
                        'gamma': option_data.get('gamma')
                    }
            
            if relevant_strikes:
                filtered[expiration] = relevant_strikes
        
        return filtered
    
    def _summarize_news(self, articles: List[Dict]) -> Dict:
        """Create concise news summary"""
        themes = {}
        sentiment_sum = 0
        
        for article in articles:
            # Extract themes
            for theme in article.get('themes', []):
                themes[theme] = themes.get(theme, 0) + 1
            
            # Aggregate sentiment
            sentiment_sum += article.get('sentiment_score', 0)
        
        return {
            'type': 'news_summary',
            'article_count': len(articles),
            'avg_sentiment': sentiment_sum / len(articles) if articles else 0,
            'top_themes': sorted(themes.items(), key=lambda x: x[1], reverse=True)[:5],
            'time_range': f"Last {len(articles)} articles",
            'summary': f"Market sentiment: {'Positive' if sentiment_sum > 0 else 'Negative'}"
        }
    
    def _cleanup_if_needed(self) -> None:
        """Remove stale or low-priority data if approaching token limit"""
        
        current_tokens = sum(item.token_estimate for item in self.context_items.values())
        
        if current_tokens > self.max_tokens * 0.8:  # 80% threshold
            # Remove items by priority and age
            items_to_remove = []
            
            for key, item in self.context_items.items():
                age_hours = (datetime.now() - item.timestamp).total_seconds() / 3600
                
                # Remove based on priority and age
                if (item.priority == ContextPriority.ARCHIVE and age_hours > 2) or \
                   (item.priority == ContextPriority.LOW and age_hours > 6) or \
                   (item.priority == ContextPriority.MEDIUM and age_hours > 24):
                    items_to_remove.append(key)
            
            for key in items_to_remove:
                del self.context_items[key]
            
            logger.info(f"Cleaned up {len(items_to_remove)} stale context items")
    
    def _estimate_tokens(self, data: Any) -> int:
        """Estimate token count for data"""
        json_str = json.dumps(data, default=str)
        # Rough estimate: ~4 characters per token
        return len(json_str) // 4
    
    def _get_priority_items(self, priority: ContextPriority, focus_symbols: List[str], budget: int) -> Dict:
        """Get items for this priority level within budget"""
        
        # Filter items by priority
        priority_items = {k: v for k, v in self.context_items.items() 
                         if v.priority == priority}
        
        # Sort by relevance and focus symbols
        sorted_items = sorted(priority_items.values(), 
                            key=lambda x: (
                                any(tag in focus_symbols for tag in x.tags),  # Focus symbols first
                                x.relevance_score,  # Then by relevance
                                -x.timestamp.timestamp()  # Then by recency
                            ), reverse=True)
        
        # Select items within budget
        selected = {}
        used_tokens = 0
        
        for item in sorted_items:
            if used_tokens + item.token_estimate <= budget:
                selected[item.key] = item.data
                used_tokens += item.token_estimate
                item.access_count += 1
                item.last_accessed = datetime.now()
        
        return selected
    
    # Placeholder methods for integration with existing systems
    def _has_position(self, symbol: str) -> bool:
        # Check if symbol is in current portfolio
        return False  # Implement with Gallump DB query
    
    def _get_watchlist(self) -> List[str]:
        # Get current watchlist
        return []  # Implement with Gallump DB query
    
    def _is_significant_move(self, data: Dict) -> bool:
        # Check if price move is significant
        return abs(data.get('day_change_percent', 0)) > 5
    
    def _update_conversation_focus(self, prompt: str, symbols: List[str]) -> None:
        # Track conversation topics
        self.conversation_focus.extend(symbols)
        self.conversation_focus = self.conversation_focus[-10:]  # Keep recent 10
    
    def _analyze_user_intent(self, prompt: str) -> str:
        # Analyze what user is trying to do
        if 'buy' in prompt.lower() or 'call' in prompt.lower():
            return 'bullish_analysis'
        elif 'sell' in prompt.lower() or 'put' in prompt.lower():
            return 'bearish_analysis'
        elif 'risk' in prompt.lower():
            return 'risk_analysis'
        return 'general_analysis'
    
    def _count_summarized_items(self) -> int:
        return len([item for item in self.context_items.values() 
                   if item.priority == ContextPriority.ARCHIVE])
    
    def _get_data_freshness_summary(self) -> Dict:
        now = datetime.now()
        fresh = len([item for item in self.context_items.values() 
                    if (now - item.timestamp).total_seconds() < 300])  # 5 minutes
        return {'fresh_items': fresh, 'total_items': len(self.context_items)}
    
    def _get_next_refresh_time(self) -> str:
        return "5 minutes"  # Based on cache TTLs
    
    def _score_news_impact(self, article: Dict, symbols: List[str]) -> float:
        # Score news impact 0.0 to 1.0
        score = 0.0
        
        # Check if mentions focus symbols
        title = article.get('headline', '').lower()
        if any(symbol.lower() in title for symbol in symbols):
            score += 0.5
        
        # Check sentiment strength
        sentiment = abs(article.get('sentiment_score', 0))
        score += sentiment * 0.3
        
        # Check recency
        age_hours = (datetime.now() - article.get('published_at', datetime.now())).total_seconds() / 3600
        if age_hours < 1:
            score += 0.2
        
        return min(1.0, score)
    
    def _add_news_item(self, article: Dict, priority: ContextPriority, symbols: List[str]) -> None:
        key = f"news_{hashlib.md5(str(article).encode()).hexdigest()[:8]}"
        item = ContextItem(
            key=key,
            data=article,
            priority=priority,
            timestamp=datetime.now(),
            token_estimate=self._estimate_tokens(article),
            relevance_score=self._score_news_impact(article, symbols),
            tags=symbols + ['news']
        )
        self.context_items[key] = item
    
    def _summarize_greeks(self, greeks: Dict) -> Dict:
        # Summarize Greeks data
        return {
            'total_delta': greeks.get('total_delta', 0),
            'total_gamma': greeks.get('total_gamma', 0),
            'theta_decay_daily': greeks.get('theta_decay', 0),
            'vega_exposure': greeks.get('vega_exposure', 0)
        }
    
    def _detect_unusual_options_activity(self, options_chain: Dict) -> List[Dict]:
        # Detect unusual options activity
        return []  # Implement unusual activity detection
    
    def _calculate_options_relevance(self, symbol: str, options_data: Dict) -> float:
        # Calculate options relevance score
        score = 0.5  # Base score
        
        if self._has_position(symbol):
            score += 0.3
        
        if options_data.get('unusual_activity'):
            score += 0.2
        
        return min(1.0, score)
    
    def prioritize_for_response(self, data: Dict) -> Dict:
        """Prioritize data for response formatting"""
        if not data:
            return {'status': 'no_data', 'context_summary': 'No data available'}
        
        return {
            'status': 'success',
            'data': data,
            'context_summary': f"Analyzed {len(data.get('positions', []))} positions"
        }