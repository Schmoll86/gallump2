# core/scanner.py
"""IBKR Scanner Module - Provides access to all native IBKR scanner functionality"""

from ib_insync import IB, ScannerSubscription, Stock, util
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ScannerResult:
    """Represents a single scanner result"""
    symbol: str
    contract_id: int
    distance: str
    benchmark: str
    projection: str
    legs: str = ""
    
    def to_dict(self):
        return {
            'symbol': self.symbol,
            'contractId': self.contract_id,
            'distance': self.distance,
            'benchmark': self.benchmark,
            'projection': self.projection,
            'legs': self.legs
        }


class IBKRScanner:
    """IBKR Scanner interface for accessing native scanner functionality"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 4001, client_id: int = 77):
        """Initialize scanner with IBKR connection parameters"""
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib: Optional[IB] = None
        self.scanner_params: Optional[Dict] = None
        self._connected = False
        
    def connect(self) -> bool:
        """Establish connection to IBKR Gateway/TWS"""
        try:
            if self.ib is None:
                self.ib = IB()
            
            if not self.ib.isConnected():
                self.ib.connect(self.host, self.port, clientId=self.client_id)
                logger.info(f"Scanner connected to IBKR at {self.host}:{self.port}")
                self._connected = True
                return True
            return True
        except Exception as e:
            logger.error(f"Failed to connect scanner to IBKR: {e}")
            self._connected = False
            return False
    
    def get_scanner_parameters(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Fetch and parse all available scanner parameters from IBKR.
        Returns dict with instruments, locations, scanCodes, and filters.
        """
        if not self._ensure_connected():
            return {"error": "Not connected to IBKR"}
            
        # Use cache if available and not forcing refresh
        if self.scanner_params is not None and not force_refresh:
            return self.scanner_params
            
        try:
            # Request scanner parameters XML from IBKR
            raw_xml = self.ib.reqScannerParameters()
            
            # Parse XML to extract parameters
            root = ET.fromstring(raw_xml)
            params = {
                "instruments": [],
                "locations": [],
                "scanCodes": [],
                "filters": []
            }
            
            # Extract instrument types (STK, OPT, FUT, etc.)
            for elem in root.findall('.//InstrumentList/Instrument'):
                params["instruments"].append({
                    'name': elem.get('name', ''),
                    'type': elem.get('type', ''),
                    'filters': elem.get('filters', '').split(',') if elem.get('filters') else []
                })
            
            # Extract location codes (STK.US, STK.US.MAJOR, etc.)
            for elem in root.findall('.//LocationTree/Location'):
                params["locations"].append({
                    'code': elem.get('locationCode', ''),
                    'name': elem.get('displayName', '')
                })
            
            # Extract scan codes (TOP_PERC_GAIN, MOST_ACTIVE, etc.)
            for elem in root.findall('.//ScanTypeList/ScanType'):
                scan_code = elem.get('scanCode', '')
                display_name = elem.get('displayName', '')
                instruments = elem.get('instruments', '').split(',') if elem.get('instruments') else []
                
                params["scanCodes"].append({
                    'code': scan_code,
                    'name': display_name,
                    'instruments': instruments
                })
            
            # Extract available filters with their valid values
            for elem in root.findall('.//AbstractField'):
                filter_name = elem.get('code', '')
                filter_type = elem.get('type', '')
                
                # Get valid values if enumerated
                valid_values = []
                for val in elem.findall('.//ValidValue'):
                    valid_values.append(val.text)
                
                params["filters"].append({
                    'name': filter_name,
                    'type': filter_type,
                    'values': valid_values
                })
            
            # Cache the parameters
            self.scanner_params = params
            logger.info(f"Loaded {len(params['scanCodes'])} scanner types")
            
            return params
            
        except Exception as e:
            logger.error(f"Error fetching scanner parameters: {e}")
            return {"error": str(e)}
    
    def run_scan(self, 
                 scan_code: str, 
                 instrument: str = "STK",
                 location: str = "STK.US.MAJOR",
                 filters: Optional[Dict[str, Any]] = None,
                 limit: int = 50) -> List[ScannerResult]:
        """
        Execute a scanner with specified parameters.
        
        Args:
            scan_code: IBKR scan code (e.g., "TOP_PERC_GAIN", "MOST_ACTIVE")
            instrument: Instrument type (e.g., "STK", "OPT")
            location: Location code (e.g., "STK.US.MAJOR", "STK.US")
            filters: Optional filters dict (e.g., {"priceAbove": 5, "volumeAbove": 1000000})
            limit: Maximum number of results to return
            
        Returns:
            List of ScannerResult objects
        """
        if not self._ensure_connected():
            logger.error("Cannot run scan - not connected to IBKR")
            return []
        
        try:
            # Create scanner subscription
            sub = ScannerSubscription(
                instrument=instrument,
                locationCode=location,
                scanCode=scan_code
            )
            
            # Apply filters if provided
            if filters:
                # Convert filters to tag-value pairs
                scan_options = []
                for key, value in filters.items():
                    scan_options.append(f"{key}:{str(value)}")
                sub.scannerSubscriptionOptions = scan_options
            
            # Set result limit
            sub.numberOfRows = limit
            
            # Execute scan
            logger.info(f"Running scan: {scan_code} on {location}")
            scan_data = self.ib.reqScannerData(sub)
            
            # Convert to ScannerResult objects
            results = []
            for item in scan_data:
                result = ScannerResult(
                    symbol=item.contractDetails.contract.symbol,
                    contract_id=item.contractDetails.contract.conId,
                    distance=item.distance,
                    benchmark=item.benchmark,
                    projection=item.projection,
                    legs=item.legsStr
                )
                results.append(result)
            
            logger.info(f"Scan returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error running scan {scan_code}: {e}")
            return []
    
    def get_popular_scans(self) -> List[Dict[str, str]]:
        """Return a curated list of popular/useful scanner types"""
        return [
            {"code": "TOP_PERC_GAIN", "name": "Top Gainers", "description": "Stocks with highest % gain", "category": "momentum"},
            {"code": "TOP_PERC_LOSE", "name": "Top Losers", "description": "Stocks with highest % loss", "category": "momentum"},
            {"code": "MOST_ACTIVE", "name": "Most Active", "description": "Highest volume stocks", "category": "volume"},
            {"code": "HOT_BY_VOLUME", "name": "Hot by Volume", "description": "Unusual volume activity", "category": "volume"},
            {"code": "TOP_TRADE_COUNT", "name": "Top Trade Count", "description": "Most traded stocks", "category": "volume"},
            {"code": "HIGH_VS_13W_HL", "name": "Near 13W High", "description": "Trading near 13-week high", "category": "technical"},
            {"code": "LOW_VS_13W_HL", "name": "Near 13W Low", "description": "Trading near 13-week low", "category": "technical"},
            {"code": "HIGH_OPT_IMP_VOLAT", "name": "High IV Options", "description": "Options with high implied volatility", "category": "options"},
            {"code": "OPT_VOLUME_MOST_ACTIVE", "name": "Most Active Options", "description": "Options with highest volume", "category": "options"},
            {"code": "HOT_BY_OPT_VOLUME", "name": "Unusual Options Activity", "description": "Unusual options volume", "category": "options"}
        ]
    
    def get_popular_scan_codes(self) -> List[str]:
        """Get just the scan codes from popular scans for easy validation"""
        return [scan["code"] for scan in self.get_popular_scans()]
    
    def get_scans_by_category(self, category: str) -> List[Dict[str, str]]:
        """Get popular scans filtered by category: momentum, volume, technical, options"""
        return [scan for scan in self.get_popular_scans() if scan.get("category") == category]
    
    def get_scan_info(self, scan_code: str) -> Optional[Dict[str, str]]:
        """Get information about a specific scan code"""
        for scan in self.get_popular_scans():
            if scan["code"] == scan_code:
                return scan
        return None
    
    def run_popular_scan(self, scan_code: str, limit: int = 50) -> List[ScannerResult]:
        """
        Run a scan using one of the popular scan codes with optimized settings.
        This method provides enhanced integration with the current system.
        """
        if not self._ensure_connected():
            logger.error("Cannot run scan - not connected to IBKR")
            return []
        
        # Validate scan code is in popular list
        if scan_code not in self.get_popular_scan_codes():
            logger.warning(f"Scan code {scan_code} not in popular scans list")
            # Fall back to regular run_scan method
            return self.run_scan(scan_code, limit=limit)
        
        # Set optimal parameters based on scan type
        scan_info = self.get_scan_info(scan_code)
        instrument = "STK"  # Default to stocks
        location = "STK.US.MAJOR"  # Major US exchanges
        filters = {}
        
        # Optimize parameters based on category
        if scan_info and scan_info.get("category") == "options":
            instrument = "OPT"
            location = "STK.US"  # Options need broader location
        elif scan_info and scan_info.get("category") == "volume":
            # Add minimum volume filter for volume-based scans
            filters = {"volumeAbove": 100000}
        elif scan_info and scan_info.get("category") == "momentum":
            # Add minimum price filter for momentum scans
            filters = {"priceAbove": 1.0}
        
        logger.info(f"Running optimized scan: {scan_code} ({scan_info.get('name', 'Unknown')})")
        
        try:
            return self.run_scan(
                scan_code=scan_code,
                instrument=instrument,
                location=location,
                filters=filters,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Error running popular scan {scan_code}: {e}")
            return []
    
    def _ensure_connected(self) -> bool:
        """Ensure connection is established before operations"""
        if not self._connected or self.ib is None or not self.ib.isConnected():
            return self.connect()
        return True
    
    def disconnect(self):
        """Disconnect from IBKR"""
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()
            logger.info("Scanner disconnected from IBKR")
        self._connected = False
        
    def check_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Check market data entitlement and contract validity for a symbol.
        Used for diagnostics when prices show as zero.
        """
        if not self._ensure_connected():
            return {"error": "Not connected to IBKR"}
            
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            ticker = self.ib.reqMktData(contract, '', False, False)
            self.ib.sleep(2)  # Wait for tick data
            
            result = {
                "symbol": symbol,
                "has_data": False,
                "last_price": None,
                "bid": None,
                "ask": None,
                "errors": []
            }
            
            if ticker.last and ticker.last > 0:
                result["has_data"] = True
                result["last_price"] = ticker.last
                result["bid"] = ticker.bid
                result["ask"] = ticker.ask
            else:
                result["errors"].append(f"No price data - check entitlement and market hours")
                
            # Cancel market data subscription
            self.ib.cancelMktData(contract)
            
            return result
            
        except Exception as e:
            return {
                "symbol": symbol,
                "error": str(e),
                "errors": [f"Failed to check symbol: {e}"]
            }