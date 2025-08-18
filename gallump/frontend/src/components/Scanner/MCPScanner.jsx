import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Activity, BarChart3, RefreshCw, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

const MCPScanner = () => {
  const [scannerTypes, setScannerTypes] = useState([]);
  const [selectedScanner, setSelectedScanner] = useState('TOP_PERC_GAIN');
  const [scanResults, setScanResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mcpStatus, setMcpStatus] = useState('checking');
  const [error, setError] = useState(null);

  // Analytics API URL (integrated into main API server)
  const API_URL = 'http://localhost:5001/api';

  // Check MCP server health on mount
  useEffect(() => {
    checkMCPHealth();
    fetchScannerTypes();
  }, []);

  const checkMCPHealth = async () => {
    try {
      const response = await fetch(`${API_URL}/health`);
      if (response.ok) {
        const data = await response.json();
        setMcpStatus(data.analytics?.status === 'available' ? 'connected' : 'degraded');
      } else {
        setMcpStatus('disconnected');
      }
    } catch (error) {
      console.error('Analytics health check failed:', error);
      setMcpStatus('disconnected');
    }
  };

  const fetchScannerTypes = async () => {
    try {
      const response = await fetch(`${API_URL}/analytics/scanner-types`);
      
      if (response.ok) {
        const data = await response.json();
        setScannerTypes(data.scanner_types || []);
      }
    } catch (error) {
      console.error('Failed to fetch scanner types:', error);
      // Use default scanner types as fallback
      setScannerTypes([
        { code: 'TOP_PERC_GAIN', name: 'Top Gainers', description: 'Stocks with highest % gain' },
        { code: 'TOP_PERC_LOSE', name: 'Top Losers', description: 'Stocks with highest % loss' },
        { code: 'MOST_ACTIVE', name: 'Most Active', description: 'Highest volume stocks' },
      ]);
    }
  };

  const runScanner = async () => {
    if (mcpStatus === 'disconnected') {
      toast.error('MCP Analytics Server is not available');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/analytics/scan`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          scan_code: selectedScanner
        })
      });

      if (response.ok) {
        const data = await response.json();
        setScanResults(data.results || []);
        
        if (data.note) {
          toast.success(data.note);
        } else {
          toast.success(`Found ${data.count} results`);
        }
      } else {
        throw new Error('Scanner request failed');
      }
    } catch (error) {
      console.error('Scanner error:', error);
      setError('Failed to run scanner. Please try again.');
      toast.error('Scanner failed');
    } finally {
      setLoading(false);
    }
  };

  const getScannerIcon = (code) => {
    switch (code) {
      case 'TOP_PERC_GAIN':
        return <TrendingUp className="w-4 h-4 text-green-600" />;
      case 'TOP_PERC_LOSE':
        return <TrendingDown className="w-4 h-4 text-red-600" />;
      case 'MOST_ACTIVE':
      case 'HOT_BY_VOLUME':
        return <Activity className="w-4 h-4 text-blue-600" />;
      default:
        return <BarChart3 className="w-4 h-4 text-gray-600" />;
    }
  };

  const formatPercent = (value) => {
    if (!value) return '0.0%';
    const color = value >= 0 ? 'text-green-600' : 'text-red-600';
    return <span className={color}>{value > 0 ? '+' : ''}{value.toFixed(1)}%</span>;
  };

  const formatVolume = (value) => {
    if (!value) return '0';
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`;
    }
    if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`;
    }
    return value.toString();
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-4">
      {/* MCP Status Badge */}
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-bold">Market Scanner (Analytics)</h2>
        <div className="flex items-center gap-2">
          <div className={`px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1
            ${mcpStatus === 'connected' ? 'bg-green-100 text-green-800' : 
              mcpStatus === 'degraded' ? 'bg-yellow-100 text-yellow-800' : 
              'bg-red-100 text-red-800'}`}>
            <div className={`w-2 h-2 rounded-full animate-pulse
              ${mcpStatus === 'connected' ? 'bg-green-500' : 
                mcpStatus === 'degraded' ? 'bg-yellow-500' : 
                'bg-red-500'}`} />
            Analytics {mcpStatus}
          </div>
          <span className="text-xs text-gray-500">READ-ONLY</span>
        </div>
      </div>

      {/* Scanner Selection */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <select
            value={selectedScanner}
            onChange={(e) => setSelectedScanner(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading || mcpStatus === 'disconnected'}
          >
            {scannerTypes.map(type => (
              <option key={type.code} value={type.code}>
                {type.name} - {type.description}
              </option>
            ))}
          </select>
          
          <button
            onClick={runScanner}
            disabled={loading || mcpStatus === 'disconnected'}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2 justify-center"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Scanning...
              </>
            ) : (
              <>
                <BarChart3 className="w-4 h-4" />
                Run Scanner
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-600" />
          <span className="text-sm text-red-800">{error}</span>
        </div>
      )}

      {/* Results */}
      {scanResults.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-3 bg-gray-50 border-b border-gray-200">
            <h3 className="font-medium text-sm text-gray-700">
              Scanner Results ({scanResults.length})
            </h3>
          </div>
          
          <div className="divide-y divide-gray-200">
            {scanResults.map((result, index) => (
              <div key={index} className="p-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {getScannerIcon(selectedScanner)}
                    <div>
                      <div className="font-semibold text-gray-900">
                        {result.symbol}
                      </div>
                      <div className="text-sm text-gray-500">
                        Vol: {formatVolume(result.volume)}
                      </div>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <div className="font-medium text-gray-900">
                      ${result.price?.toFixed(2) || '0.00'}
                    </div>
                    <div className="text-sm">
                      {formatPercent(result.change_percent)}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && scanResults.length === 0 && !error && (
        <div className="text-center py-12 text-gray-500">
          <BarChart3 className="w-12 h-12 mx-auto mb-3 text-gray-400" />
          <p className="text-sm">Select a scanner and click "Run Scanner" to see results</p>
          <p className="text-xs mt-2 text-gray-400">
            MCP Analytics provides read-only market analysis
          </p>
        </div>
      )}

      {/* Info Footer */}
      <div className="mt-4 p-3 bg-blue-50 rounded-lg">
        <p className="text-xs text-blue-800">
          <strong>Note:</strong> Analytics provides read-only market scanning. 
          For trade execution, use the Strategy Chat feature. Scanner results may be delayed 
          or use mock data during after-hours trading.
        </p>
      </div>
    </div>
  );
};

export default MCPScanner;