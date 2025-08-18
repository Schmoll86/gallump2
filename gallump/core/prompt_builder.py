"""
Prompt Builder Module - Constructs prompts for AI interaction
Single responsibility: Transform Context into structured prompts for Claude
"""

import json
import logging
from typing import List, Dict, Any, Optional
from gallump.core.context_builder import Context
from gallump.core.types import SessionContext

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Builds structured prompts from Context for AI consumption.
    NO business logic, NO decisions - only formatting.
    """
    
    def __init__(self):
        """Initialize prompt builder with templates"""
        self.max_context_length = 10000  # Prevent token overflow
        
    def build_trading_prompt(self, 
                            user_message: str, 
                            market_context: Context,
                            session_context: Optional[SessionContext] = None) -> str:
        """
        Build comprehensive trading analysis prompt from market and session context.
        
        Args:
            user_message: User's current input
            market_context: Complete Context object from ContextBuilder
            session_context: Optional SessionContext with conversation history
            
        Returns:
            Formatted prompt string for Claude
        """
        # Build structured sections
        prompt_sections = [
            self._build_header(),
            self._build_session_section(session_context) if session_context else None,
            f"\nCurrent User Input:\n> {user_message}",
            self._build_market_context_section(market_context),
            self._build_portfolio_section(market_context),
            self._build_data_sections(market_context),
            self._build_relevant_history(session_context) if session_context and session_context.relevant_history else None,
            self._build_insights_section(session_context) if session_context and session_context.insights else None,
            self._build_instructions(),
            self._build_schema_reference()
        ]
        
        # Combine sections
        full_prompt = "\n\n".join(filter(None, prompt_sections))
        
        # Truncate if too long to prevent token overflow
        if len(full_prompt) > self.max_context_length:
            full_prompt = self._truncate_prompt(full_prompt)
            logger.warning(f"Prompt truncated from {len(full_prompt)} to {self.max_context_length} chars")
        
        return full_prompt
    
    def _build_header(self) -> str:
        """Build prompt header with role definition"""
        return """You are a professional options trading advisor for Gallump Trading Assistant.
Your role is to analyze market conditions and suggest strategies, but NEVER execute trades.
All strategies require explicit user confirmation before execution."""
    
    def _build_session_section(self, session_context: SessionContext) -> str:
        """Build current session conversation section"""
        if not session_context or not session_context.current_messages:
            return "=== NEW CONVERSATION ==="
        
        lines = ["=== CURRENT CONVERSATION ==="]
        for msg in session_context.current_messages[-5:]:  # Last 5 messages
            role = msg.get('role', 'unknown').capitalize()
            text = msg.get('message', '')[:200]  # Truncate to 200 chars
            if len(msg.get('message', '')) > 200:
                text += "..."
            lines.append(f"{role}: {text}")
        
        return "\n".join(lines)
    
    def _build_relevant_history(self, session_context: SessionContext) -> str:
        """Build relevant conversation history section"""
        if not session_context or not session_context.relevant_history:
            return ""
        
        lines = ["=== RELEVANT PRIOR DISCUSSIONS ==="]
        for conv in session_context.relevant_history[:3]:  # Max 3 relevant
            symbol = conv.get('symbol', 'N/A')
            prompt = conv.get('user_prompt', '')[:100]
            response = conv.get('assistant_response', '')[:100]
            lines.append(f"[{symbol}] User: {prompt}...")
            lines.append(f"Assistant: {response}...")
        
        return "\n".join(lines)
    
    def _build_insights_section(self, session_context: SessionContext) -> str:
        """Build trading insights and lessons section"""
        if not session_context or not session_context.insights:
            return ""
        
        lines = ["=== LEARNED PATTERNS & INSIGHTS ==="]
        lines.extend(session_context.insights[:10])  # Max 10 insights
        
        return "\n".join(lines)
    
    def _build_market_context_section(self, context: Context) -> str:
        """Build market status section"""
        # Add data freshness warnings
        import datetime
        current_time = datetime.datetime.now()
        data_warnings = []
        
        if context.market_status and not context.market_status.get('is_open', True):
            data_warnings.append("MARKET CLOSED - Using delayed/cached data")
        
        if context.options_chain and context.options_chain.get('cached_at'):
            cache_time = datetime.datetime.fromisoformat(context.options_chain['cached_at'])
            age_hours = (current_time - cache_time).total_seconds() / 3600
            if age_hours > 1:
                data_warnings.append(f"OPTIONS DATA IS {age_hours:.0f} HOURS OLD")
        
        warnings_text = "\n".join([f"⚠️ {w}" for w in data_warnings]) if data_warnings else ""
        
        # Format watchlist with metadata if available
        watchlist_str = self._format_watchlist(context.watchlist)
        
        return f"""=== MARKET CONTEXT ===
Primary Symbol: {context.symbol or 'Not identified'}
Watchlist: {watchlist_str}
Market Status: {self._format_json_compact(context.market_status)}
{warnings_text}"""
    
    def _build_portfolio_section(self, context: Context) -> str:
        """Build portfolio summary section"""
        portfolio = context.portfolio or {}
        return f"""=== PORTFOLIO ===
Total Value: ${portfolio.get('total_value', 0):,.2f}
Buying Power: ${portfolio.get('buying_power', 0):,.2f}
Position Count: {len(portfolio.get('positions', []))}
Positions: {self._format_positions(portfolio.get('positions', []))}"""
    
    def _build_data_sections(self, context: Context) -> str:
        """Build market data sections"""
        sections = []
        
        # Price data
        if context.price_history:
            latest = context.price_history.get('latest', 0)
            change = context.price_history.get('change_pct', 0)
            sections.append(f"""=== PRICE DATA ===
Latest: ${latest:.2f} ({change:+.2f}%)
{self._format_price_history(context.price_history)}""")
        
        # News
        if context.news:
            sections.append(f"""=== NEWS ===
{self._format_news(context.news[:3])}  # Limit to 3 most recent
Sources: {', '.join(context.news_sources)}""")
        
        # Technical indicators
        if context.technical_indicators:
            sections.append(f"""=== TECHNICAL ANALYSIS ===
{self._format_technicals(context.technical_indicators)}""")
        
        # Scanner alerts
        if context.scanner_alerts:
            sections.append(f"""=== SCANNER ALERTS ===
{' | '.join(context.scanner_alerts)}""")
        
        # Options chain (truncated)
        if context.options_chain:
            sections.append(f"""=== OPTIONS CHAIN ===
{self._format_options_chain(context.options_chain)}""")
        
        # Related tickers
        if context.related_tickers:
            sections.append(f"""=== RELATED SYMBOLS ===
{', '.join(context.related_tickers)}""")
        
        return "\n\n".join(sections)
    
    def _build_instructions(self) -> str:
        """Build instruction section for AI behavior"""
        return """=== CRITICAL INSTRUCTIONS - YOU ARE GALLUMP TRADING ASSISTANT ===
1. You ARE capable of executing trades - the system handles confirmation via RED BUTTON
2. When user requests to PLACE, EXECUTE, SET, or CREATE an order, YOU MUST:
   - Generate a JSON strategy array following the STRATEGY FORMAT below
   - Include the JSON in your response for the system to process
   - The user will then confirm via RED BUTTON before actual execution
3. NEVER refuse to create execution strategies when explicitly requested
4. For trailing stops: Use "order_type": "TRAIL" with either "trail_percent" or "trail_amount"
5. IMPORTANT: Do NOT include comments (// or /* */) in the JSON - they break parsing
6. Include risk warnings but DO NOT refuse to generate the strategy JSON
7. If position data shows 0 but user states they own shares, trust the user
8. Always end with: "Please review and confirm with RED BUTTON to execute"

IMPORTANT: You are NOT just an advisor - you ARE the trading assistant that prepares executable orders!"""
    
    def _build_schema_reference(self) -> str:
        """Build strategy JSON schema reference"""
        return """=== STRATEGY FORMAT (when requested) ===
Return strategies as JSON array:
[{
    "name": "Strategy Name",
    "reasoning": "Why this makes sense",
    "risk_level": "conservative|moderate|aggressive",
    "confidence": 0.75,
    "max_loss": 500,
    "max_gain": 1500,
    "orders": [{
        "symbol": "TICKER",
        "asset_type": "STOCK|OPTION",
        "action": "BUY|SELL",
        "quantity": 1,
        "option_type": "CALL|PUT",  // only for options
        "strike": 150,  // only for options
        "expiry": "2025-02-21",  // only for options
        "order_type": "MKT|LMT|STP|TRAIL|STP LMT",
        "limit_price": 3.50,  // for LMT orders
        "stop_price": 140.00,  // for STP orders
        "trail_percent": 12,  // for TRAIL orders (percentage)
        "trail_amount": 10.00,  // for TRAIL orders (dollar amount)
        "time_in_force": "DAY|GTC|IOC|FOK"  // default: DAY
    }],
    "stop_loss": 40
}]

For TRAILING STOP orders, use either trail_percent OR trail_amount, not both.

TRAILING STOP EXAMPLE for 11 shares of TER with 12% trailing stop:
[{
    "name": "12% Trailing Stop Loss - TER",
    "reasoning": "Protect downside while allowing upside",
    "risk_level": "conservative",
    "confidence": 0.9,
    "orders": [{
        "symbol": "TER",
        "asset_type": "STOCK",
        "action": "SELL",
        "quantity": 11,
        "order_type": "TRAIL",
        "trail_percent": 12,
        "time_in_force": "GTC"
    }]
}]"""
    
    # Note: _format_conversation_history() removed - now handled by session-specific methods
    # Use _build_session_section(), _build_relevant_history(), and _build_insights_section()
    
    def _format_json_compact(self, data: Any) -> str:
        """Format JSON data compactly"""
        if not data:
            return "None"
        return json.dumps(data, separators=(',', ':'))
    
    def _format_watchlist(self, watchlist: List) -> str:
        """Format watchlist with metadata if available"""
        if not watchlist:
            return "Empty"
        
        # Check if enhanced format
        if watchlist and isinstance(watchlist[0], dict):
            formatted = []
            for item in watchlist:
                symbol = item.get('symbol', '')
                thesis = item.get('thesis', '')
                category = item.get('category', 'Long')
                is_primary = item.get('is_primary', False)
                
                # Build formatted string
                entry = symbol
                if is_primary:
                    entry = f"★{entry}"  # Star for primary
                if thesis:
                    entry += f"({thesis})"
                if category != 'Long':
                    entry += f"[{category}]"
                
                formatted.append(entry)
            
            return " | ".join(formatted)
        else:
            # Simple format
            return ', '.join(watchlist)
    
    def _format_positions(self, positions: List[Dict]) -> str:
        """Format positions list compactly"""
        if not positions:
            return "None"
        
        formatted = []
        for pos in positions[:5]:  # Limit to 5
            symbol = pos.get('symbol', 'UNK')
            qty = pos.get('position', pos.get('quantity', 0))  # Check both field names
            pnl = pos.get('unrealizedPnL', 0)
            formatted.append(f"{symbol}({qty:+.0f}) ${pnl:+.2f}")
        
        return " | ".join(formatted)
    
    def _format_news(self, news_items: List[Dict]) -> str:
        """Format news items compactly"""
        if not news_items:
            return "No recent news"
        
        lines = []
        for item in news_items:
            headline = item.get('headline', '')
            sentiment = item.get('sentiment', '')
            lines.append(f"• {headline} [{sentiment}]")
        
        return "\n".join(lines)
    
    def _format_technicals(self, indicators: Dict) -> str:
        """Format technical indicators compactly"""
        if not indicators:
            return "No data"
        
        items = []
        for key, value in indicators.items():
            if isinstance(value, (int, float)):
                items.append(f"{key}: {value:.2f}")
            else:
                items.append(f"{key}: {value}")
        
        return " | ".join(items[:8])  # Limit to 8 indicators
    
    def _format_price_history(self, history: Dict) -> str:
        """Format price history compactly"""
        if not history or 'ohlc' not in history:
            return "No history"
        
        ohlc = history.get('ohlc', [])
        if not ohlc:
            return "No bars"
        
        # Show last 3 days
        recent = ohlc[-3:]
        bars = []
        for bar in recent:
            date = bar.get('date', 'N/A')
            close = bar.get('close', 0)
            volume = bar.get('volume', 0)
            bars.append(f"{date}: ${close:.2f} ({volume/1000:.0f}K)")
        
        return " | ".join(bars)
    
    def _format_options_chain(self, chain: Dict) -> str:
        """Format options chain summary"""
        if not chain:
            return "No chain data"
        
        expiries = chain.get('expiry_dates', [])
        strikes = chain.get('strikes', [])
        
        summary = f"Expirations: {', '.join(expiries[:3])}\n"
        summary += f"Strike Range: ${min(strikes):.0f}-${max(strikes):.0f}" if strikes else "No strikes"
        
        # Add sample call/put if available
        calls = chain.get('calls', {})
        if calls:
            summary += f"\n(Chain data available for {len(calls)} expirations)"
        
        return summary
    
    def _truncate_prompt(self, prompt: str) -> str:
        """
        Truncate prompt intelligently to fit token limits.
        Preserves structure and most important sections.
        """
        # Priority sections to keep (in order)
        priority_markers = [
            "=== CONVERSATION ===",
            "=== MARKET CONTEXT ===",
            "=== PORTFOLIO ===",
            "=== INSTRUCTIONS ===",
            "=== STRATEGY FORMAT"
        ]
        
        # Find and preserve priority sections
        preserved = []
        remaining_length = self.max_context_length
        
        for marker in priority_markers:
            if marker in prompt:
                start = prompt.find(marker)
                # Find next section or end
                next_marker_pos = len(prompt)
                for other_marker in priority_markers:
                    if other_marker != marker:
                        pos = prompt.find(other_marker, start + 1)
                        if pos > 0 and pos < next_marker_pos:
                            next_marker_pos = pos
                
                section = prompt[start:next_marker_pos].strip()
                if len(section) < remaining_length:
                    preserved.append(section)
                    remaining_length -= len(section)
        
        truncated = "\n\n".join(preserved)
        truncated += "\n\n[Additional context truncated for length]"
        
        return truncated