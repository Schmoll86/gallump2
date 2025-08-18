# Bidirectional Claude Desktop Bridge for Mobile Trading

## The Vision
Your mobile app → sends analysis requests → Claude Desktop (with MCP tools) → returns AI analysis → mobile app displays results

## Architecture

```
Mobile App (anywhere)
    ↓ WebSocket
Bridge Server (port 5002)
    ↓ Queues requests
Request Queue Database
    ↓ Polling
Claude Desktop Extension
    ↓ MCP Tools
IBKR Data + AI Analysis
    ↓ Results
Bridge Server
    ↓ WebSocket
Mobile App receives analysis
```

## Implementation Plan

### Phase 1: Request Queue System
Create a queue where mobile app can submit analysis requests that Claude Desktop will process:

```python
# enhanced_bridge_server.py
class BidirectionalMCPBridge:
    def __init__(self):
        self.pending_requests = []  # Queue of analysis requests
        self.completed_analyses = {}  # Results from Claude Desktop
        
    async def handle_mobile_request(self, ws, message):
        """Mobile app sends analysis request"""
        request_id = str(uuid.uuid4())
        request = {
            'id': request_id,
            'type': 'analysis_request',
            'prompt': message['prompt'],
            'symbols': message['symbols'],
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        self.pending_requests.append(request)
        
        # Store in database for persistence
        storage.save_analysis_request(request)
        
        # Send acknowledgment to mobile
        await ws.send_json({
            'type': 'request_queued',
            'request_id': request_id,
            'message': 'Analysis request queued for Claude Desktop'
        })
        
        # Wait for Claude Desktop to process (with timeout)
        result = await self.wait_for_analysis(request_id, timeout=30)
        
        if result:
            await ws.send_json({
                'type': 'analysis_complete',
                'request_id': request_id,
                'analysis': result['analysis']
            })
    
    async def handle_claude_desktop_poll(self):
        """Claude Desktop polls for pending requests"""
        if self.pending_requests:
            return self.pending_requests.pop(0)
        return None
    
    async def handle_claude_desktop_result(self, request_id, analysis):
        """Claude Desktop submits analysis result"""
        self.completed_analyses[request_id] = {
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }
```

### Phase 2: Claude Desktop Extension Script
Create a script that runs alongside Claude Desktop to process requests:

```python
# claude_desktop_processor.py
import asyncio
import aiohttp
from anthropic import Anthropic

class ClaudeDesktopProcessor:
    def __init__(self):
        self.bridge_url = "http://localhost:5002"
        self.running = True
        
    async def process_requests(self):
        """Poll bridge for requests and process them"""
        while self.running:
            try:
                # Check for pending requests
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.bridge_url}/pending_request") as resp:
                        if resp.status == 200:
                            request = await resp.json()
                            
                            if request:
                                # Process with Claude Desktop
                                # This is where you'd interact with Claude Desktop
                                # For now, we'll use the API directly
                                analysis = await self.analyze_with_claude(request)
                                
                                # Send result back to bridge
                                await session.post(
                                    f"{self.bridge_url}/submit_result",
                                    json={
                                        'request_id': request['id'],
                                        'analysis': analysis
                                    }
                                )
                
                await asyncio.sleep(2)  # Poll every 2 seconds
                
            except Exception as e:
                print(f"Error processing requests: {e}")
                await asyncio.sleep(5)
    
    async def analyze_with_claude(self, request):
        """Use Claude API with MCP context to analyze"""
        # This would ideally use Claude Desktop's session
        # For now, using API directly
        prompt = f"""
        Analyze this trading request with access to IBKR data:
        Request: {request['prompt']}
        Symbols: {request['symbols']}
        
        Use the MCP tools to get real-time data and provide analysis.
        """
        
        # In reality, this would use Claude Desktop's context
        # with all MCP tools available
        return "AI Analysis with MCP data would go here"
```

### Phase 3: Enhanced Mobile Interface
Update the MCP tab to work with the queue system:

```javascript
// ClaudeDesktopTab.jsx
const submitAnalysisRequest = async () => {
    setLoading(true);
    
    // Send request to queue
    ws.send(JSON.stringify({
        type: 'analysis_request',
        prompt: input,
        symbols: extractSymbols(input)
    }));
    
    // Show pending state
    setMessages(prev => [...prev, {
        type: 'system',
        content: '⏳ Request sent to Claude Desktop for analysis...'
    }]);
    
    // Will receive result via WebSocket when ready
};

// Handle incoming analysis
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'analysis_complete') {
        setMessages(prev => [...prev, {
            type: 'assistant',
            content: data.analysis
        }]);
        setLoading(false);
    }
};
```

## Alternative: Direct Claude Desktop Automation

Use AppleScript (macOS) or AutoHotkey (Windows) to control Claude Desktop:

```applescript
-- claude_desktop_automation.applescript
tell application "Claude"
    activate
    
    -- Read request from file
    set requestFile to "/tmp/claude_request.txt"
    set requestText to read requestFile
    
    -- Send to Claude
    tell window 1
        set value of text area 1 to requestText
        click button "Send"
    end tell
    
    -- Wait for response
    delay 5
    
    -- Copy response
    tell window 1
        select text area 2
        keystroke "c" using command down
    end tell
    
    -- Save to file
    set responseFile to "/tmp/claude_response.txt"
    do shell script "pbpaste > " & responseFile
end tell
```

## Recommended Approach: Hybrid System

1. **For Mobile Trading (Execution)**: Use Strategy Chat with Claude API
2. **For Deep Analysis**: Use Claude Desktop directly with MCP tools
3. **For Automated Analysis**: Build the request queue system above

## The Reality

Claude Desktop is designed as a standalone application, not as a backend service. While you CAN build a bidirectional bridge, consider:

1. **Complexity**: Requires constant polling and state management
2. **Latency**: Adds 5-30 seconds per request
3. **Reliability**: Claude Desktop could be closed/crashed
4. **Rate Limits**: Both API and Desktop have limits

## Better Solution: Dual Mode

### Mode 1: Execution (Mobile/Web)
- Strategy Chat for trade execution
- Uses Claude API directly
- RED BUTTON confirmation
- Real-time response

### Mode 2: Analysis (Desktop)
- Claude Desktop with MCP for deep analysis
- Full IBKR data access
- Complex multi-step research
- Save results to database for mobile viewing

Would you like me to implement the request queue system for true bidirectional communication?