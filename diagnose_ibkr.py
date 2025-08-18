#!/usr/bin/env python3
"""
IBKR Diagnostic Tool
Checks connectivity, market data entitlements, and symbol validity
"""

import sys
import logging
from datetime import datetime
from ib_insync import IB, Stock, Option, Contract
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IBKRDiagnostic:
    """Diagnostic tool for IBKR connectivity and data issues"""
    
    def __init__(self, host='127.0.0.1', port=4001, client_id=99):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()
        
    def run_diagnostics(self):
        """Run complete diagnostic suite"""
        print("\n" + "="*60)
        print("IBKR DIAGNOSTIC TOOL")
        print("="*60 + "\n")
        
        # Test 1: Connection
        if not self.test_connection():
            print("\n❌ CRITICAL: Cannot connect to IBKR. Check:")
            print("  1. IB Gateway/TWS is running")
            print("  2. API is enabled in settings")
            print("  3. Port 4001 (live) or 4002 (paper) is correct")
            print("  4. Client ID is not already in use")
            return False
        
        # Test 2: Account info
        self.test_account_info()
        
        # Test 3: Market status
        self.test_market_status()
        
        # Test 4: Symbol checks for common positions
        test_symbols = ["AAPL", "SPY", "QQQ", "TSLA", "NVDA"]
        print("\n📊 Testing Market Data Entitlements:")
        print("-" * 40)
        for symbol in test_symbols:
            self.check_symbol(symbol)
        
        # Test 5: Options chain test
        self.test_options_chain("SPY")
        
        # Test 6: Scanner parameters
        self.test_scanner()
        
        # Cleanup
        self.disconnect()
        
        print("\n" + "="*60)
        print("DIAGNOSTIC COMPLETE")
        print("="*60 + "\n")
        
        return True
    
    def test_connection(self):
        """Test basic connection to IBKR"""
        print("🔌 Testing IBKR Connection...")
        print(f"   Host: {self.host}")
        print(f"   Port: {self.port}")
        print(f"   Client ID: {self.client_id}")
        
        try:
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            print("   ✅ Connected successfully!")
            return True
        except Exception as e:
            print(f"   ❌ Connection failed: {e}")
            return False
    
    def test_account_info(self):
        """Test account access and display key info"""
        print("\n👤 Account Information:")
        print("-" * 40)
        
        try:
            # Get account values
            account_values = self.ib.accountValues()
            
            # Extract key values
            key_values = {
                'NetLiquidation': None,
                'BuyingPower': None,
                'TotalCashValue': None,
                'GrossPositionValue': None
            }
            
            for av in account_values:
                if av.tag in key_values:
                    key_values[av.tag] = av.value
            
            for key, value in key_values.items():
                if value:
                    print(f"   {key}: ${value}")
            
            # Get positions count
            positions = self.ib.positions()
            print(f"   Open Positions: {len(positions)}")
            
        except Exception as e:
            print(f"   ❌ Error getting account info: {e}")
    
    def test_market_status(self):
        """Check if markets are open"""
        print("\n🕐 Market Status:")
        print("-" * 40)
        
        now = datetime.now()
        weekday = now.weekday()
        hour = now.hour
        
        # Simple market hours check (9:30 AM - 4:00 PM ET, Mon-Fri)
        # This is simplified - real implementation should handle holidays
        is_weekday = weekday < 5
        is_market_hours = 9 <= hour < 16 or (hour == 9 and now.minute >= 30)
        
        if is_weekday and is_market_hours:
            print("   ✅ Market is OPEN")
        else:
            print("   ⏸️  Market is CLOSED")
            print("   Note: Some data may be unavailable outside market hours")
    
    def check_symbol(self, symbol):
        """Check market data for a specific symbol"""
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            ticker = self.ib.reqMktData(contract, '', False, False)
            
            # Wait for data
            self.ib.sleep(2)
            
            if ticker.last and ticker.last > 0:
                print(f"   ✅ {symbol}: Last=${ticker.last:.2f}, Bid=${ticker.bid:.2f}, Ask=${ticker.ask:.2f}")
            else:
                print(f"   ⚠️  {symbol}: No price data (check entitlements)")
                
                # Try to get delayed data
                ticker_delayed = self.ib.reqMktData(contract, '', False, True)
                self.ib.sleep(1)
                
                if ticker_delayed.last and ticker_delayed.last > 0:
                    print(f"       → Delayed price available: ${ticker_delayed.last:.2f}")
                
            # Cancel subscription
            self.ib.cancelMktData(contract)
            
        except Exception as e:
            print(f"   ❌ {symbol}: Error - {e}")
    
    def test_options_chain(self, symbol):
        """Test options chain retrieval"""
        print(f"\n📈 Testing Options Chain for {symbol}:")
        print("-" * 40)
        
        try:
            stock = Stock(symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)
            
            # Get chain
            chains = self.ib.reqSecDefOptParams(
                stock.symbol,
                '',
                stock.secType,
                stock.conId
            )
            
            if chains:
                chain = chains[0]
                print(f"   ✅ Found {len(chain.expirations)} expirations")
                print(f"   ✅ Found {len(chain.strikes)} strikes")
                
                # Show first few expirations
                print(f"   Next expirations: {', '.join(chain.expirations[:3])}")
            else:
                print(f"   ⚠️  No options chain found for {symbol}")
                
        except Exception as e:
            print(f"   ❌ Error getting options chain: {e}")
    
    def test_scanner(self):
        """Test scanner parameter retrieval"""
        print("\n🔍 Testing Scanner Access:")
        print("-" * 40)
        
        try:
            xml_params = self.ib.reqScannerParameters()
            
            if xml_params and len(xml_params) > 100:
                print(f"   ✅ Scanner parameters retrieved ({len(xml_params)} bytes)")
                
                # Count scan types
                scan_count = xml_params.count('scanCode=')
                print(f"   ✅ Found approximately {scan_count} scanner types")
            else:
                print("   ⚠️  Scanner parameters seem incomplete")
                
        except Exception as e:
            print(f"   ❌ Error getting scanner parameters: {e}")
    
    def disconnect(self):
        """Disconnect from IBKR"""
        if self.ib.isConnected():
            self.ib.disconnect()
            print("\n🔌 Disconnected from IBKR")


def main():
    """Main entry point"""
    
    # Parse command line arguments
    host = '127.0.0.1'
    port = 4001  # Default to live trading port
    client_id = 99
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'paper':
            port = 4002
            print("Using PAPER trading port (4002)")
        elif sys.argv[1] == 'help':
            print("Usage: python diagnose_ibkr.py [paper]")
            print("  paper - Use paper trading port (4002)")
            print("  Default uses live trading port (4001)")
            return
    
    # Run diagnostics
    diagnostic = IBKRDiagnostic(host, port, client_id)
    diagnostic.run_diagnostics()


if __name__ == '__main__':
    main()