import React, { useState, useEffect, useRef } from 'react';
import { Brain, Wifi, WifiOff, Loader2, Monitor } from 'lucide-react';

const ClaudeDesktopTab = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const ws = useRef(null);
  const messagesEndRef = useRef(null);
  const reconnectTimeout = useRef(null);

  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (ws.current) {
        ws.current.close();
      }
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      // Connect to MCP Bridge Service via Vite proxy
      const wsUrl = window.location.hostname === 'localhost' 
        ? `ws://${window.location.host}/ws`  // Use Vite proxy in dev
        : 'ws://localhost:5002/ws';  // Direct connection in production
      console.log('Attempting to connect to MCP Bridge at:', wsUrl);
      ws.current = new WebSocket(wsUrl);
      
      ws.current.onopen = () => {
        console.log('Connected to MCP Bridge');
        setIsConnected(true);
        setMessages(prev => [...prev, {
          type: 'system',
          content: '🟢 Connected to Claude Desktop MCP'
        }]);
      };
      
      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleBridgeMessage(data);
      };
      
      ws.current.onclose = () => {
        console.log('Disconnected from MCP Bridge');
        setIsConnected(false);
        setMessages(prev => [...prev, {
          type: 'system',
          content: '🔴 Disconnected from Claude Desktop MCP'
        }]);
        
        // Attempt to reconnect after 3 seconds
        reconnectTimeout.current = setTimeout(() => {
          connectWebSocket();
        }, 3000);
      };
      
      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        console.error('Error type:', error.type);
        console.error('Error target:', error.target?.url);
        setMessages(prev => [...prev, {
          type: 'system',
          content: '⚠️ Connection error - check if MCP Bridge is running on port 5002'
        }]);
      };
      
    } catch (error) {
      console.error('Failed to connect:', error);
      setIsConnected(false);
    }
  };

  const handleBridgeMessage = (data) => {
    setIsLoading(false);
    
    switch (data.type) {
      case 'analysis_result':
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: formatAnalysisResult(data.data)
        }]);
        break;
        
      case 'portfolio_data':
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: formatPortfolioData(data.data)
        }]);
        break;
        
      case 'market_data':
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: formatMarketData(data.symbol, data.data)
        }]);
        break;
        
      case 'scanner_results':
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: formatScannerResults(data.data)
        }]);
        break;
        
      case 'options_chain':
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: formatOptionsChain(data.data)
        }]);
        break;
        
      case 'market_depth':
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: formatMarketDepth(data.data)
        }]);
        break;
        
      case 'news_feed':
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: formatNewsItems(data.data)
        }]);
        break;
        
      case 'error':
        setMessages(prev => [...prev, {
          type: 'error',
          content: `Error: ${data.message}`
        }]);
        break;
        
      default:
        console.log('Unknown message type:', data.type);
    }
  };

  const formatAnalysisResult = (data) => {
    if (data.content && data.content[0]) {
      return data.content[0].text;
    }
    return JSON.stringify(data, null, 2);
  };

  const formatPortfolioData = (data) => {
    if (data.content && data.content[0]) {
      return data.content[0].text;
    }
    return 'Portfolio data received';
  };

  const formatMarketData = (symbol, data) => {
    if (data.content && data.content[0]) {
      return data.content[0].text;
    }
    return `Market data for ${symbol}`;
  };

  const formatScannerResults = (data) => {
    if (!data || !data.content) return "No scanner results";
    
    // If it's already formatted text, return as is
    if (data.content[0] && data.content[0].text) {
      return data.content[0].text;
    }
    
    // Otherwise format the raw data
    let output = "📊 Scanner Results:\n\n";
    if (data.results && Array.isArray(data.results)) {
      data.results.forEach((item, idx) => {
        output += `${idx + 1}. ${item.symbol}: `;
        output += `${item.change_percent > 0 ? '📈' : '📉'} ${item.change_percent}% `;
        output += `Vol: ${item.volume?.toLocaleString() || 'N/A'}\n`;
      });
    }
    return output;
  };

  const formatOptionsChain = (data) => {
    if (!data || !data.content) return "No options data";
    
    if (data.content[0] && data.content[0].text) {
      return data.content[0].text;
    }
    
    let output = "📊 Options Chain:\n\n";
    // Format options data if raw
    return output;
  };

  const formatMarketDepth = (data) => {
    if (!data || !data.content) return "No market depth";
    
    if (data.content[0] && data.content[0].text) {
      return data.content[0].text;
    }
    
    let output = "📊 Market Depth:\n\n";
    // Format depth data if raw
    return output;
  };

  const formatNewsItems = (data) => {
    if (!data || !data.content) return "No news available";
    
    if (data.content[0] && data.content[0].text) {
      return data.content[0].text;
    }
    
    let output = "📰 Recent News:\n\n";
    // Format news if raw
    return output;
  };

  const sendMessage = () => {
    if (!input.trim() || !isConnected || isLoading) return;
    
    const userMessage = input.trim();
    
    // Add user message to display
    setMessages(prev => [...prev, {
      type: 'user',
      content: userMessage
    }]);
    
    // Determine message type based on content
    let messageToSend = {
      type: 'analyze',
      prompt: userMessage,
      symbols: extractSymbols(userMessage),
      id: Date.now()
    };
    
    // Check for specific commands
    if (userMessage.toLowerCase().includes('portfolio')) {
      messageToSend = { type: 'get_portfolio' };
    } else if (userMessage.match(/^[A-Z]+$/)) {
      // Single symbol
      messageToSend = {
        type: 'get_market_data',
        symbol: userMessage
      };
    }
    
    // Send via WebSocket
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(messageToSend));
      setIsLoading(true);
    }
    
    setInput('');
  };

  const extractSymbols = (text) => {
    // Extract stock symbols (uppercase words 1-5 chars)
    const matches = text.match(/\b[A-Z]{1,5}\b/g);
    return matches || [];
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-purple-950 to-indigo-950">
      {/* Header with connection status */}
      <div className="bg-purple-900/50 backdrop-blur-sm p-4 border-b border-purple-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Monitor className="w-6 h-6 text-purple-400" />
            <h2 className="text-xl font-bold text-purple-100">Claude Desktop Analysis</h2>
          </div>
          <div className="flex items-center gap-2">
            {isConnected ? (
              <>
                <Wifi className="w-5 h-5 text-green-400" />
                <span className="text-sm text-green-400">Connected to MCP</span>
              </>
            ) : (
              <>
                <WifiOff className="w-5 h-5 text-red-400" />
                <span className="text-sm text-red-400">Disconnected</span>
              </>
            )}
          </div>
        </div>
        <p className="text-xs text-purple-300 mt-2">
          Deep IBKR analysis via Claude Desktop • No execution • Unlimited context
        </p>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-purple-400 mt-8">
            <Brain className="w-16 h-16 mx-auto mb-4 opacity-50" />
            <p className="text-lg mb-2">Claude Desktop MCP Ready</p>
            <p className="text-sm opacity-75">
              Ask about portfolio, market analysis, or specific symbols
            </p>
            <div className="mt-6 text-xs text-purple-500 space-y-1">
              <p>Try: "What's my portfolio P&L?"</p>
              <p>Try: "Analyze AAPL with options data"</p>
              <p>Try: "Market overview with sector rotation"</p>
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`
                ${msg.type === 'user' ? 'ml-auto bg-purple-800/50' : ''}
                ${msg.type === 'assistant' ? 'mr-auto bg-indigo-800/50' : ''}
                ${msg.type === 'system' ? 'mx-auto bg-gray-800/50 text-center' : ''}
                ${msg.type === 'error' ? 'mx-auto bg-red-900/50' : ''}
                max-w-[80%] rounded-lg p-4 backdrop-blur-sm
              `}
            >
              <pre className="whitespace-pre-wrap text-sm text-white font-mono">
                {msg.content}
              </pre>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="p-4 bg-purple-900/50 backdrop-blur-sm border-t border-purple-800">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            placeholder={isConnected ? "Ask Claude Desktop for analysis..." : "Waiting for connection..."}
            disabled={!isConnected}
            className="flex-1 px-4 py-3 bg-purple-950/50 text-white rounded-lg 
                     border border-purple-700 focus:border-purple-500 focus:outline-none
                     placeholder-purple-400 disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={!isConnected || !input.trim() || isLoading}
            className="px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 
                     text-white rounded-lg transition-colors flex items-center gap-2
                     disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <Brain className="w-5 h-5" />
                <span>Analyze</span>
              </>
            )}
          </button>
        </div>
        
        {/* Quick action buttons */}
        <div className="flex gap-2 mt-2">
          <button
            onClick={() => {
              const msg = 'Show my portfolio';
              setMessages(prev => [...prev, { type: 'user', content: msg }]);
              if (ws.current && ws.current.readyState === WebSocket.OPEN) {
                ws.current.send(JSON.stringify({ type: 'get_portfolio' }));
                setIsLoading(true);
              }
            }}
            className="px-3 py-1 bg-purple-700 hover:bg-purple-600 text-white text-sm rounded"
          >
            📊 Portfolio
          </button>
        </div>
      </div>
    </div>
  );
};

export default ClaudeDesktopTab;
