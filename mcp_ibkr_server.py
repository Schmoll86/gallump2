#!/usr/bin/env python3
"""
MCP Server for IBKR Trading Tools
This provides tools TO Claude Desktop for market analysis
Run this as: python mcp_ibkr_server.py
"""

import json
import sys
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/mcp_ibkr_server.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Import IBKR modules
try:
    from ib_insync import IB, Stock, Option, util, MarketOrder, LimitOrder
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    logger.error("ib_insync not installed. Please run: pip install ib_insync")
    sys.exit(1)

class IBKRMCPServer:
    """MCP Server that provides IBKR tools to Claude Desktop"""
    
    def __init__(self):
        self.ib = IB()
        self.connected = False
        self.host = os.environ.get('IBKR_HOST', '127.0.0.1')
        self.port = int(os.environ.get('IBKR_PORT', '4001'))
        self.client_id = int(os.environ.get('IBKR_CLIENT_ID', '999'))
        
    async def connect(self):
        """Connect to IBKR"""
        if self.connected:
            return True
            
        try:
            await self.ib.connectAsync(self.host, self.port, clientId=self.client_id)
            self.connected = True
            logger.info(f"Connected to IBKR at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {e}")
            self.connected = False
            return False
    
    async def ensure_connected(self):
        """Ensure we're connected before operations"""
        if not self.connected or not self.ib.isConnected():
            await self.connect()
    
    # Tool implementations
    async def get_quote(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get real-time quote for a symbol"""
        await self.ensure_connected()
        
        symbol = params.get('symbol')
        if not symbol:
            return {"error": "Symbol required"}
        
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            qualified = self.ib.qualifyContracts(contract)
            
            if not qualified:
                return {"error": f"Could not qualify {symbol}"}
            
            ticker = self.ib.reqMktData(qualified[0], snapshot=True)
            await asyncio.sleep(2)  # Wait for data
            
            self.ib.cancelMktData(qualified[0])
            
            return {
                "symbol": symbol,
                "bid": float(ticker.bid) if ticker.bid else 0,
                "ask": float(ticker.ask) if ticker.ask else 0,
                "last": float(ticker.last) if ticker.last else 0,
                "volume": ticker.volume if ticker.volume else 0,
                "high": float(ticker.high) if ticker.high else 0,
                "low": float(ticker.low) if ticker.low else 0,
                "close": float(ticker.close) if ticker.close else 0
            }
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            return {"error": str(e)}
    
    async def get_positions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get current positions"""
        await self.ensure_connected()
        
        try:
            positions = []
            for pos in self.ib.positions():
                positions.append({
                    "symbol": pos.contract.symbol,
                    "quantity": float(pos.position),
                    "avgCost": float(pos.avgCost) if hasattr(pos, 'avgCost') else 0,
                    "account": pos.account
                })
            
            return {"positions": positions}
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return {"error": str(e)}
    
    async def get_orders(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get open orders"""
        await self.ensure_connected()
        
        try:
            orders = []
            for trade in self.ib.openTrades():
                order = trade.order
                contract = trade.contract
                
                orders.append({
                    "orderId": trade.order.orderId,
                    "symbol": contract.symbol,
                    "action": order.action,
                    "quantity": float(order.totalQuantity),
                    "orderType": order.orderType,
                    "limitPrice": float(order.lmtPrice) if order.lmtPrice else None,
                    "status": trade.orderStatus.status
                })
            
            return {"orders": orders}
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return {"error": str(e)}
    
    async def scan_market(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run market scanner"""
        await self.ensure_connected()
        
        scan_type = params.get('scan_type', 'TOP_PERC_GAIN')
        
        try:
            from ib_insync import ScannerSubscription
            
            sub = ScannerSubscription(
                instrument='STK',
                locationCode='STK.US.MAJOR',
                scanCode=scan_type
            )
            
            scanData = self.ib.reqScannerData(sub)
            
            results = []
            for item in scanData[:20]:  # Limit to top 20
                results.append({
                    "symbol": item.contractDetails.contract.symbol,
                    "rank": item.rank,
                    "distance": item.distance
                })
            
            return {"scan_type": scan_type, "results": results}
        except Exception as e:
            logger.error(f"Error scanning market: {e}")
            return {"error": str(e)}
    
    async def get_account_summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get account summary"""
        await self.ensure_connected()
        
        try:
            account_values = {}
            for av in self.ib.accountValues():
                if av.tag in ['NetLiquidation', 'BuyingPower', 'TotalCashValue', 
                             'GrossPositionValue', 'MaintMarginReq']:
                    account_values[av.tag] = float(av.value)
            
            return {"account": account_values}
        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            return {"error": str(e)}
    
    async def get_historical_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get historical price data"""
        await self.ensure_connected()
        
        symbol = params.get('symbol')
        duration = params.get('duration', '1 D')
        bar_size = params.get('bar_size', '5 mins')
        
        if not symbol:
            return {"error": "Symbol required"}
        
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            qualified = self.ib.qualifyContracts(contract)
            
            if not qualified:
                return {"error": f"Could not qualify {symbol}"}
            
            bars = self.ib.reqHistoricalData(
                qualified[0],
                endDateTime='',
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow='TRADES',
                useRTH=True
            )
            
            data = []
            for bar in bars:
                data.append({
                    "time": bar.date.isoformat(),
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": int(bar.volume)
                })
            
            return {"symbol": symbol, "bars": data}
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return {"error": str(e)}
    
    async def get_options_chain(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get options chain for a symbol"""
        await self.ensure_connected()
        
        symbol = params.get('symbol')
        expiry = params.get('expiry')  # Format: YYYYMMDD
        
        if not symbol:
            return {"error": "Symbol required"}
        
        try:
            # Get the underlying
            underlying = Stock(symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(underlying)
            
            # Get option chain
            chains = self.ib.reqSecDefOptParams(
                underlying.symbol,
                '',
                underlying.secType,
                underlying.conId
            )
            
            if not chains:
                return {"error": f"No options chain found for {symbol}"}
            
            chain = chains[0]
            
            # If expiry specified, filter
            expiries = chain.expirations
            if expiry and expiry in expiries:
                expiries = [expiry]
            
            options_data = {
                "symbol": symbol,
                "expiries": expiries,
                "strikes": chain.strikes
            }
            
            return options_data
        except Exception as e:
            logger.error(f"Error getting options chain: {e}")
            return {"error": str(e)}
    
    # MCP Protocol Implementation
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request"""
        method = request.get('method')
        params = request.get('params', {})
        request_id = request.get('id')
        
        # Map methods to handlers
        handlers = {
            'tools/list': self.list_tools,
            'tools/call': self.call_tool,
        }
        
        handler = handlers.get(method)
        if not handler:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                "id": request_id
            }
        
        try:
            result = await handler(params)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": request_id
            }
    
    async def list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available tools"""
        tools = [
            {
                "name": "get_quote",
                "description": "Get real-time quote for a stock symbol",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Stock symbol"}
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "get_positions",
                "description": "Get current portfolio positions",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_orders",
                "description": "Get open orders",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "scan_market",
                "description": "Scan market for opportunities",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "scan_type": {
                            "type": "string",
                            "description": "Type of scan (TOP_PERC_GAIN, TOP_PERC_LOSE, MOST_ACTIVE)",
                            "default": "TOP_PERC_GAIN"
                        }
                    }
                }
            },
            {
                "name": "get_account_summary",
                "description": "Get account summary including buying power",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_historical_data",
                "description": "Get historical price data",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Stock symbol"},
                        "duration": {"type": "string", "description": "Duration (e.g., '1 D', '1 W')", "default": "1 D"},
                        "bar_size": {"type": "string", "description": "Bar size (e.g., '5 mins', '1 hour')", "default": "5 mins"}
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "get_options_chain",
                "description": "Get options chain for a symbol",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Stock symbol"},
                        "expiry": {"type": "string", "description": "Expiry date (YYYYMMDD)"}
                    },
                    "required": ["symbol"]
                }
            }
        ]
        
        return {"tools": tools}
    
    async def call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool"""
        tool_name = params.get('name')
        tool_params = params.get('arguments', {})
        
        # Map tool names to methods
        tool_methods = {
            'get_quote': self.get_quote,
            'get_positions': self.get_positions,
            'get_orders': self.get_orders,
            'scan_market': self.scan_market,
            'get_account_summary': self.get_account_summary,
            'get_historical_data': self.get_historical_data,
            'get_options_chain': self.get_options_chain,
        }
        
        method = tool_methods.get(tool_name)
        if not method:
            return {"error": f"Unknown tool: {tool_name}"}
        
        return await method(tool_params)
    
    async def run(self):
        """Main run loop for MCP server"""
        logger.info("Starting IBKR MCP Server")
        
        # Connect to IBKR
        await self.connect()
        
        # Main loop - read from stdin, write to stdout
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                # Parse JSON-RPC request
                request = json.loads(line)
                logger.info(f"Received request: {request}")
                
                # Handle request
                response = await self.handle_request(request)
                
                # Send response
                print(json.dumps(response))
                sys.stdout.flush()
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    },
                    "id": None
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
        
        # Cleanup
        if self.connected:
            self.ib.disconnect()
        logger.info("IBKR MCP Server stopped")

async def main():
    server = IBKRMCPServer()
    await server.run()

if __name__ == "__main__":
    # Run the server
    asyncio.run(main())