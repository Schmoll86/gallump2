# Session Memory Architecture

## Three-Tier Memory System

### 1. HOT Memory (Redis/Cache) - Current Session
- **Scope**: Last 5-10 messages in active session
- **TTL**: 30 minutes (extends on activity)
- **Size**: ~2-3KB
- **Access**: Sub-millisecond

```python
class SessionManager:
    def get_session(self, session_id: str) -> List[Dict]:
        # Redis key: session:{session_id}:messages
        return redis.get(f"session:{session_id}:messages")
```

### 2. WARM Memory (Database) - Relevant Context
- **Scope**: Recent trades/conversations for SAME symbol/strategy
- **Time window**: Last 7 days
- **Query**: Indexed by (symbol, strategy_type, timestamp)
- **Size**: ~10-20 messages max

```sql
SELECT * FROM conversations 
WHERE symbol = ? 
  AND created_at > datetime('now', '-7 days')
  AND strategies_generated > 0
ORDER BY created_at DESC 
LIMIT 10
```

### 3. COLD Memory (Compressed) - Learned Insights
- **Scope**: Mistakes, successful patterns, key lessons
- **Storage**: Annotations table (already exists!)
- **Format**: Compressed summaries, not full conversations
- **Size**: ~20-30 bullet points

```python
def get_trading_insights(self, symbol: Optional[str] = None) -> str:
    mistakes = storage.get_mistakes(symbol, limit=5)
    insights = storage.get_annotations(note_type='insight', limit=5)
    return self._format_as_bullets(mistakes + insights)
```

## Context Allocation Strategy

### For Each Request:
```python
def build_conversation_context(session_id: str, symbol: str) -> Dict:
    # 1. HOT: Current session (80% weight)
    current_session = cache.get_session(session_id)  # Last 5-10 messages
    
    # 2. WARM: Recent relevant (15% weight)  
    recent_relevant = storage.get_conversations(
        symbol=symbol,
        days=7,
        limit=5  # Only most relevant
    )
    
    # 3. COLD: Compressed insights (5% weight)
    insights = storage.get_trading_insights(symbol)
    
    return {
        'immediate': current_session,      # ~2000 tokens
        'relevant': recent_relevant,       # ~500 tokens  
        'insights': insights               # ~200 tokens
    }
```

## Why This Works

1. **Efficient**: Redis session = microsecond access
2. **Relevant**: Only loads context that matters NOW
3. **Scalable**: O(1) for hot path, bounded queries for warm
4. **Smart**: Preserves lessons without conversation bloat

## Implementation Priority

1. Add session_id to Brain initialization
2. Implement SessionManager with Redis
3. Update storage queries for bounded lookups
4. Compress old conversations into insights via cron job