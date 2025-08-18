# Session Integration Guide

## Key Changes Required

### 1. Update server.py

```python
# Add session manager initialization
from gallump.core.session_manager import SessionManager

# Initialize once at module level
session_manager = SessionManager(cache=cache, storage=storage)

@app.route('/api/strategies/generate', methods=['POST'])
@auth_required
def generate_strategy():
    data = request.json
    user_prompt = data.get('prompt', '')
    watchlist = data.get('watchlist', [])
    session_id = data.get('session_id')  # Client provides session ID
    
    # Get or create session
    session_id = session_manager.get_or_create_session(session_id)
    
    # Add user message to session
    symbol = watchlist[0] if watchlist else None
    session_manager.add_message(session_id, 'user', user_prompt, symbol)
    
    # Get full context including conversation history
    session_context = session_manager.get_context(session_id, symbol)
    
    # Build market context as before
    context_builder = ContextBuilder(broker=broker, cache=cache, scanner=scanner)
    market_context = context_builder.build(
        symbols=watchlist,
        user_prompt=user_prompt,
        watchlist=watchlist
    )
    
    # Initialize Brain with session awareness
    brain = Brain(session_id=session_id, session_manager=session_manager)
    
    # Pass both market and session context
    result = brain.converse(
        user_message=user_prompt,
        market_context=market_context,
        session_context=session_context
    )
    
    # Add assistant response to session
    session_manager.add_message(session_id, 'assistant', result['response'], symbol)
    
    # Return with session_id for client continuity
    return jsonify({
        'session_id': session_id,  # Client must store this
        'response': result['response'],
        'recommendations': result['recommendations'],
        'requires_confirmation': True,
        'context_stats': {
            'messages_in_session': len(session_context.current_messages),
            'relevant_history_loaded': len(session_context.relevant_history),
            'insights_included': len(session_context.insights)
        }
    })
```

### 2. Update Brain.py

```python
class Brain:
    def __init__(self, session_id: str = None, session_manager=None):
        """Initialize with session awareness"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        self.client = Anthropic(api_key=api_key) if api_key else None
        self.session_id = session_id
        self.session_manager = session_manager
        # Remove self.memories - now handled by SessionManager
        
    def converse(self, user_message: str, market_context: Context, 
                 session_context: SessionContext) -> Dict:
        """Process with both market and session context"""
        
        # Build prompt with session awareness
        from gallump.core.prompt_builder import PromptBuilder
        prompt_builder = PromptBuilder()
        
        prompt = prompt_builder.build_trading_prompt(
            user_message=user_message,
            market_context=market_context,
            session_context=session_context  # NEW: Pass session context
        )
        
        # Get Claude's response
        response = self._call_claude(prompt)
        
        # Parse recommendations
        recommendations = self._parse_recommendations(response)
        
        return {
            'response': response,
            'recommendations': recommendations
        }
```

### 3. Update PromptBuilder.py

```python
def build_trading_prompt(self, 
                        user_message: str,
                        market_context: Context,
                        session_context: SessionContext) -> str:
    """Build prompt with intelligent context selection"""
    
    # Format session context intelligently
    prompt_sections = [
        self._build_header(),
        
        # Current conversation (HOT memory)
        self._build_session_section(session_context.current_messages),
        
        # Current user input
        f"Current User Input:\n> {user_message}",
        
        # Market data
        self._build_market_context_section(market_context),
        self._build_portfolio_section(market_context),
        
        # Relevant history (WARM memory) - only if relevant
        self._build_relevant_history(session_context.relevant_history) 
            if session_context.relevant_history else None,
        
        # Insights (COLD memory) - compressed lessons
        self._build_insights_section(session_context.insights)
            if session_context.insights else None,
        
        self._build_instructions(),
        self._build_schema_reference()
    ]
    
    full_prompt = "\n\n".join(filter(None, prompt_sections))
    return self._ensure_token_limit(full_prompt)

def _build_session_section(self, messages: List[Dict]) -> str:
    """Format current session messages"""
    if not messages:
        return "=== NEW CONVERSATION ==="
    
    lines = ["=== CURRENT CONVERSATION ==="]
    for msg in messages[-5:]:  # Only last 5 for space
        role = msg['role'].capitalize()
        text = msg['message'][:200]  # Truncate long messages
        lines.append(f"{role}: {text}")
    
    return "\n".join(lines)

def _build_insights_section(self, insights: List[str]) -> str:
    """Format compressed insights and lessons"""
    if not insights:
        return None
    
    return f"""=== LEARNED PATTERNS ===
{chr(10).join(insights[:10])}"""  # Max 10 insights
```

### 4. Update Cache.py for Redis session support

```python
def set(self, key: str, value: Any, expire_minutes: int = None):
    """Set value with optional expiration"""
    if self.use_redis and self.redis_client:
        try:
            serialized = json.dumps(value) if not isinstance(value, str) else value
            if expire_minutes:
                self.redis_client.setex(key, expire_minutes * 60, serialized)
            else:
                self.redis_client.set(key, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis set failed: {e}")
    
    # Fallback to memory cache
    self.memory_cache[key] = value
    return True

def get(self, key: str) -> Any:
    """Get value from cache"""
    if self.use_redis and self.redis_client:
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value) if value.startswith('{') else value
        except Exception as e:
            logger.error(f"Redis get failed: {e}")
    
    # Fallback to memory cache
    return self.memory_cache.get(key)
```

## Client-Side Changes

The frontend must:
1. Store `session_id` from first response
2. Include `session_id` in all subsequent requests
3. Handle session expiry (30 min timeout)

```javascript
// Example client code
let currentSessionId = null;

async function askClaude(prompt, watchlist) {
    const response = await fetch('/api/strategies/generate', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            prompt: prompt,
            watchlist: watchlist,
            session_id: currentSessionId  // Include if exists
        })
    });
    
    const data = await response.json();
    currentSessionId = data.session_id;  // Store for next request
    return data;
}
```

## Benefits

1. **Efficient**: O(1) session lookup, bounded DB queries
2. **Intelligent**: Only loads relevant context
3. **Scalable**: Works with 10 or 10,000 conversations
4. **Maintainable**: Clear separation of concerns

## Token Budget

- Current session: ~2,000 tokens (80%)
- Relevant history: ~500 tokens (15%)
- Insights: ~200 tokens (5%)
- **Total context**: ~2,700 tokens (leaves ~97k for market data & response)