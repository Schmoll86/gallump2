#!/usr/bin/env python3
"""
Emergency fix script to get Gallump fully operational
Fixes:
1. Market data showing $0
2. Portfolio not displaying 
3. System showing as offline
"""

import subprocess
import time
import requests
import json

def kill_process(name):
    """Kill process by name"""
    try:
        subprocess.run(f"pkill -f {name}", shell=True)
        print(f"✓ Killed {name}")
    except:
        pass

def start_backend():
    """Start the backend server"""
    print("Starting backend server...")
    subprocess.Popen(
        ["python", "-m", "gallump.api.server"],
        env={**subprocess.os.environ, "PYTHONPATH": "."},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(5)
    
def start_mcp_bridge():
    """Start MCP bridge"""
    print("Starting MCP bridge...")
    subprocess.Popen(
        ["python", "mcp_bridge_service.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(3)

def test_system():
    """Test if system is working"""
    try:
        # Test health
        r = requests.get("http://localhost:5001/api/health")
        health = r.json()
        print(f"Health Status: {health['status']}")
        
        # Test portfolio
        r = requests.get("http://localhost:5001/api/portfolio")
        portfolio = r.json()
        print(f"Portfolio Value: ${portfolio.get('total_value', 0):,.2f}")
        print(f"Positions: {len(portfolio.get('positions', []))}")
        
        # Test market data
        r = requests.get("http://localhost:5001/api/get_positions")
        positions = r.json()
        if positions['positions']:
            first = positions['positions'][0]
            print(f"Market Data Test: {first['symbol']} = ${first.get('currentPrice', 0)}")
        
        return True
    except Exception as e:
        print(f"Test failed: {e}")
        return False

def main():
    print("=== Gallump Emergency Fix ===\n")
    
    # Kill existing processes
    print("Stopping existing processes...")
    kill_process("gallump.api.server")
    kill_process("mcp_bridge_service")
    time.sleep(2)
    
    # Start services
    print("\nStarting services...")
    start_backend()
    start_mcp_bridge()
    
    # Test system
    print("\nTesting system...")
    if test_system():
        print("\n✅ SYSTEM OPERATIONAL")
        print("Open http://localhost:3000 in your browser")
    else:
        print("\n❌ SYSTEM FAILED - Check logs")

if __name__ == "__main__":
    main()