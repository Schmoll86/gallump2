#!/usr/bin/env python3
"""
MCP Bridge Service - Connects Web UI to Claude Desktop via WebSocket
This allows remote access to Claude Desktop's MCP capabilities from your phone
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any
import aiohttp
from aiohttp import web
import aiohttp_cors
import weakref

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPBridgeService:
    """
    Bridges between:
    - WebSocket connections from frontend
    - Claude Desktop MCP server (stdio communication)
    - IBKR data feeds
    """
    
    def __init__(self):
        self.app = web.Application()
        self.websockets = set()  # Changed from WeakSet
        self.mcp_process: Optional[subprocess.Popen] = None
        self.cache = {}  # Simple cache
        self.running = False
        self.setup_routes()
        self.setup_cors()
    
    def get_cached(self, key: str):
        """Get cached value if not expired"""
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                return value
        return None
    
    def set_cached(self, key: str, value: Any, ttl: int = 60):
        """Cache value with TTL in seconds"""
        self.cache[key] = (value, time.time() + ttl)
        
    def setup_routes(self):
        """Setup WebSocket and HTTP routes"""
        self.app.router.add_get('/ws', self.websocket_handler)
        self.app.router.add_get('/health', self.health_check)
        
    def setup_cors(self):
        """Setup CORS for frontend access"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*"
            )
        })
        
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def start_mcp_server(self):
        """Start the MCP server process that Claude Desktop connects to"""
        try:
            mcp_path = Path(__file__).parent / 'mcp_enhanced_claude.py'
            self.mcp_process = await asyncio.create_subprocess_exec(
                'python3',  # Use explicit python3 instead of sys.executable
                str(mcp_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            logger.info("MCP server process started")
            
            # Read initial stderr to check for startup errors
            try:
                initial_stderr = await asyncio.wait_for(
                    self.mcp_process.stderr.readline(), 
                    timeout=2.0
                )
                if initial_stderr:
                    logger.warning(f"MCP stderr: {initial_stderr.decode().strip()}")
            except asyncio.TimeoutError:
                # No stderr output is actually good - means no errors
                pass
            
            # Initialize MCP connection
            init_response = await self.send_to_mcp({
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "mcp-bridge",
                        "version": "1.0.0"
                    }
                }
            })
            
            if init_response:
                logger.info(f"MCP initialized successfully: {init_response}")
            else:
                logger.error("Failed to initialize MCP server")
                raise Exception("MCP initialization failed")
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
    
    async def monitor_mcp_process(self):
        """Monitor MCP process and restart if it dies"""
        while self.running:
            if self.mcp_process and self.mcp_process.returncode is not None:
                logger.error(f"MCP process died with code {self.mcp_process.returncode}, restarting...")
                await self.start_mcp_server()
            await asyncio.sleep(5)
    
    async def send_to_mcp(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send request to MCP server and get response"""
        if not self.mcp_process or not self.mcp_process.stdin:
            logger.error("MCP process not running")
            await self.start_mcp_server()  # Try to restart
            if not self.mcp_process:
                return None
            
        try:
            # Send request
            request_json = json.dumps(request) + '\n'
            self.mcp_process.stdin.write(request_json.encode())
            await self.mcp_process.stdin.drain()
            
            # Read response - keep reading until we get valid JSON
            max_attempts = 10
            for attempt in range(max_attempts):
                response_line = await asyncio.wait_for(
                    self.mcp_process.stdout.readline(),
                    timeout=5.0
                )
                if response_line:
                    line = response_line.decode().strip()
                    if line.startswith('{'):  # Looks like JSON
                        try:
                            return json.loads(line)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse JSON: {line[:100]}")
                            continue
                    else:
                        logger.debug(f"Skipping non-JSON line: {line[:100]}")
            
            logger.error(f"No valid JSON response after {max_attempts} attempts")
            return None
                
        except asyncio.TimeoutError:
            logger.error("MCP response timeout")
            return None
        except Exception as e:
            logger.error(f"MCP communication error: {e}")
            return None
    
    async def websocket_handler(self, request):
        """Handle WebSocket connections from frontend with auto-reconnection support"""
        ws = web.WebSocketResponse(heartbeat=30)  # Add heartbeat for connection monitoring
        await ws.prepare(request)
        self.websockets.add(ws)
        
        # Send initial connection success message
        await ws.send_json({
            'type': 'connection',
            'status': 'connected',
            'message': 'Connected to MCP Bridge'
        })
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.handle_frontend_message(ws, data)
                    except json.JSONDecodeError as e:
                        await ws.send_json({
                            'type': 'error',
                            'message': f'Invalid JSON: {e}'
                        })
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
                elif msg.type == aiohttp.WSMsgType.CLOSE:
                    logger.info('WebSocket connection closed')
                    break
                    
        except ConnectionResetError:
            logger.info("WebSocket connection reset by client")
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
            await ws.send_json({
                'type': 'error',
                'message': f'Server error: {str(e)}'
            })
        finally:
            self.websockets.discard(ws)
            if not ws.closed:
                await ws.close()
            
        return ws
    
    async def handle_frontend_message(self, ws, message):
        """Handle messages from frontend and route to appropriate handler"""
        msg_type = message.get('type')
        
        # Handle ping for connection monitoring
        if msg_type == 'ping':
            await ws.send_json({'type': 'pong', 'timestamp': time.time()})
            return
        
        if msg_type == 'analyze':
            # Route to MCP for analysis
            await self.handle_analysis_request(ws, message)
        elif msg_type == 'get_portfolio':
            # Get portfolio via MCP
            await self.handle_portfolio_request(ws)
        elif msg_type == 'get_market_data':
            # Get market data via MCP
            await self.handle_market_data_request(ws, message)
        else:
            await ws.send_json({
                'type': 'error',
                'message': f'Unknown message type: {msg_type}'
            })
    
    async def handle_analysis_request(self, ws, message):
        """Handle analysis request using MCP tools"""
        prompt = message.get('prompt', '')
        symbols = message.get('symbols', [])
        
        # Send to MCP for analysis
        mcp_request = {
            "jsonrpc": "2.0",
            "id": message.get('id', 1),
            "method": "tools/call",
            "params": {
                "name": "enhanced_market_analysis",
                "arguments": {
                    "prompt": prompt,
                    "symbols": symbols
                }
            }
        }
        
        response = await self.send_to_mcp(mcp_request)
        
        if response:
            await ws.send_json({
                'type': 'analysis_result',
                'data': response.get('result', {})
            })
        else:
            await ws.send_json({
                'type': 'error',
                'message': 'Failed to get analysis from MCP'
            })
    
    async def handle_portfolio_request(self, ws):
        """Get portfolio data via MCP"""
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "enhanced_portfolio_analysis",
                "arguments": {}
            }
        }
        
        response = await self.send_to_mcp(mcp_request)
        
        if response:
            await ws.send_json({
                'type': 'portfolio_data',
                'data': response.get('result', {})
            })
    
    async def handle_market_data_request(self, ws, message):
        """Get market data for specific symbols"""
        symbol = message.get('symbol')
        
        if not symbol:
            await ws.send_json({
                'type': 'error',
                'message': 'Symbol required'
            })
            return
        
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "enhanced_symbol_analysis",
                "arguments": {
                    "symbol": symbol,
                    "analysis_type": "basic"
                }
            }
        }
        
        response = await self.send_to_mcp(mcp_request)
        
        if response:
            await ws.send_json({
                'type': 'market_data',
                'symbol': symbol,
                'data': response.get('result', {})
            })
    
    async def health_check(self, request):
        """Health check endpoint"""
        mcp_running = self.mcp_process and self.mcp_process.returncode is None
        
        return web.json_response({
            'status': 'healthy',
            'mcp_running': mcp_running,
            'websocket_clients': len(self.websockets)
        })
    
    async def broadcast_to_clients(self, message):
        """Broadcast message to all connected WebSocket clients"""
        if self.websockets:
            await asyncio.gather(
                *[ws.send_json(message) for ws in self.websockets],
                return_exceptions=True
            )
    
    async def start(self):
        """Start the bridge service"""
        self.running = True
        await self.start_mcp_server()
        
        # Start monitoring task
        asyncio.create_task(self.monitor_mcp_process())
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5002)
        await site.start()
        
        logger.info("MCP Bridge Service running on port 5002")
        logger.info("WebSocket endpoint: ws://localhost:5002/ws")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down MCP Bridge Service")
        finally:
            if self.mcp_process:
                self.mcp_process.terminate()
                await self.mcp_process.wait()

async def main():
    bridge = MCPBridgeService()
    await bridge.start()

if __name__ == '__main__':
    asyncio.run(main())
