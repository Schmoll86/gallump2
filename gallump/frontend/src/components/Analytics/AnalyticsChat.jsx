import React, { useState, useEffect, useRef } from 'react';
import { Send, Loader, AlertCircle, TrendingUp, DollarSign, Activity } from 'lucide-react';
import toast from 'react-hot-toast';

const AnalyticsChat = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [mcpStatus, setMcpStatus] = useState('checking');
  const [portfolio, setPortfolio] = useState(null);
  const messagesEndRef = useRef(null);

  // Analytics API endpoints (now integrated into main API server)
  const API_URL = 'http://localhost:5001/api/analytics';
  // No auth needed on local network
  const getAuthToken = () => 'local_access_token';

  useEffect(() => {
    checkMCPHealth();
    fetchPortfolioContext();
  }, []);

  // Extract ticker symbols from text
  const extractSymbols = (text) => {
    // Match uppercase words that look like stock symbols (2-5 letters)
    const matches = text.match(/\b[A-Z]{2,5}\b/g) || [];
    // Filter out common words that might be false positives
    const commonWords = ['I', 'A', 'THE', 'AND', 'OR', 'NOT', 'FOR', 'WITH', 'IV'];
    return matches.filter(match => !commonWords.includes(match));
  };

  const checkMCPHealth = async () => {
    try {
      const response = await fetch('http://localhost:5001/api/health');
      if (response.ok) {
        const data = await response.json();
        // Check if IBKR is connected and market is open
        const ibkr = data.components?.ibkr_connection;
        if (ibkr?.healthy && ibkr?.market_status?.is_open) {
          setMcpStatus('connected');  // Show as connected if market is open
        } else if (data.status === 'healthy') {
          setMcpStatus('connected');
        } else if (data.status === 'degraded') {
          setMcpStatus('degraded');
        } else {
          setMcpStatus('disconnected');
        }
      } else {
        setMcpStatus('disconnected');
      }
    } catch (error) {
      console.error('MCP health check failed:', error);
      setMcpStatus('disconnected');
    }
  };

  const fetchPortfolioContext = async () => {
    try {
      const response = await fetch(`${API_URL}/portfolio`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
      });
      
      if (response.ok) {
        const data = await response.json();
        setPortfolio(data);
      }
    } catch (error) {
      console.error('Failed to fetch portfolio context:', error);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    
    if (mcpStatus === 'disconnected') {
      toast.error('Analytics service is not available');
      return;
    }
    
    // Allow analytics to work even when degraded (some components may be unavailable)
    // Removed misleading "market closed" message

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      // Use simplified analytics chat endpoint
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          prompt: input,
          symbols: extractSymbols(input)
        })
      });

      if (response.ok) {
        const data = await response.json();
        
        // Format the analysis response into readable text
        let formattedContent = '';
        
        if (data.analysis && typeof data.analysis === 'string') {
          // New simplified format - analysis is already formatted
          formattedContent = data.analysis;
        } else if (data.analysis && typeof data.analysis === 'object') {
          const analysis = data.analysis;
          
          formattedContent = `**Analysis for ${analysis.symbol || 'Symbol'}**\n\n`;
          
          if (analysis.price_data) {
            formattedContent += `**Price Data:**\n`;
            formattedContent += `• Current Price: $${analysis.price_data.current_price || 'N/A'}\n`;
            formattedContent += `• Day Change: ${analysis.price_data.day_change || 0}%\n`;
            formattedContent += `• Volume: ${analysis.price_data.volume ? analysis.price_data.volume.toLocaleString() : 'N/A'}\n\n`;
          }
          
          if (analysis.technical_indicators) {
            formattedContent += `**Technical Indicators:**\n`;
            formattedContent += `• RSI: ${analysis.technical_indicators.rsi || 'N/A'}\n`;
            formattedContent += `• MACD: ${analysis.technical_indicators.macd || 'N/A'}\n`;
            formattedContent += `• Bollinger: ${analysis.technical_indicators.bollinger_position || 'N/A'}\n\n`;
          }
          
          if (analysis.volume_analysis) {
            formattedContent += `**Volume Analysis:**\n`;
            formattedContent += `• Relative Volume: ${analysis.volume_analysis.relative_volume || 'N/A'}x\n`;
            formattedContent += `• Volume Trend: ${analysis.volume_analysis.volume_trend || 'N/A'}\n\n`;
          }
        } else if (typeof data.analysis === 'string') {
          formattedContent = data.analysis;
        } else if (data.response) {
          formattedContent = data.response;
        } else {
          formattedContent = 'Analysis complete.';
        }
        
        const assistantMessage = {
          role: 'assistant',
          content: formattedContent,
          data: data.data || null,
          timestamp: new Date().toISOString()
        };
        
        setMessages(prev => [...prev, assistantMessage]);
        
        // If there's structured data, render it
        if (data.scanner_results) {
          renderScannerResults(data.scanner_results);
        }
        if (data.options_chain) {
          renderOptionsChain(data.options_chain);
        }
      } else {
        throw new Error('Analysis request failed');
      }
    } catch (error) {
      console.error('Analysis error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error analyzing your request. Please try again.',
        error: true,
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setLoading(false);
    }
  };

  const renderScannerResults = (results) => {
    // This would render structured scanner results
    console.log('Scanner results:', results);
  };

  const renderOptionsChain = (chain) => {
    // This would render structured options chain
    console.log('Options chain:', chain);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const formatMessage = (content) => {
    // Ensure content is a string
    if (!content || typeof content !== 'string') {
      return '<p class="mb-2">No content available</p>';
    }
    
    // Basic markdown-like formatting
    return content
      .split('\n')
      .map((line, i) => {
        // Bold text
        line = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Bullet points
        if (line.startsWith('•')) {
          return `<li class="ml-4">${line.substring(1).trim()}</li>`;
        }
        return `<p class="mb-2">${line}</p>`;
      })
      .join('');
  };

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* Header */}
      <div className="bg-slate-800 border-b border-slate-700 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity className="w-5 h-5 text-cyan-400" />
            <h1 className="text-lg font-semibold text-white">Analytics</h1>
            <span className="text-xs text-slate-300 bg-slate-700 px-2 py-1 rounded-md">READ-ONLY</span>
          </div>
          
          <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium
            ${mcpStatus === 'connected' ? 'bg-emerald-900/50 text-emerald-300 border border-emerald-500/30' : 
              mcpStatus === 'degraded' ? 'bg-amber-900/50 text-amber-300 border border-amber-500/30' : 
              'bg-red-900/50 text-red-300 border border-red-500/30'}`}>
            <div className={`w-2 h-2 rounded-full animate-pulse
              ${mcpStatus === 'connected' ? 'bg-emerald-400' : 
                mcpStatus === 'degraded' ? 'bg-amber-400' : 
                'bg-red-400'}`} />
            {mcpStatus}
          </div>
        </div>
        
        {portfolio && (
          <div className="mt-3 flex gap-6 text-xs text-slate-300">
            <span className="flex items-center gap-2 bg-slate-700/50 px-2 py-1 rounded">
              <DollarSign className="w-3 h-3 text-cyan-400" />
              {portfolio.positions?.length || 0} positions
            </span>
            <span className="flex items-center gap-2 bg-slate-700/50 px-2 py-1 rounded">
              <TrendingUp className="w-3 h-3 text-cyan-400" />
              ${portfolio.total_value?.toLocaleString() || '0'}
            </span>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-slate-400">
              <Activity className="w-12 h-12 mx-auto mb-3 text-slate-500" />
              <p className="text-lg font-medium mb-2">Analytics Ready</p>
              <p className="text-sm">Ask about market conditions, options, or technical analysis</p>
            </div>
          </div>
        )}
        
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-3xl rounded-lg px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-lg'
                  : message.error
                  ? 'bg-red-900/50 text-red-200 border border-red-500/30'
                  : 'bg-slate-800 border border-slate-600 text-slate-100 shadow-lg'
              }`}
            >
              {message.role === 'assistant' && !message.error && (
                <div className="flex items-center gap-2 mb-2 text-xs text-cyan-400">
                  <Activity className="w-3 h-3" />
                  Analytics
                </div>
              )}
              
              <div 
                className={`${message.role === 'user' ? 'text-white' : 'text-slate-100'} prose prose-invert max-w-none`}
                dangerouslySetInnerHTML={{ __html: formatMessage(message.content) }}
              />
              
              {message.data && (
                <div className="mt-3 p-3 bg-slate-900/70 rounded-md text-sm border border-slate-600">
                  <pre className="whitespace-pre-wrap text-slate-300 text-xs">
                    {JSON.stringify(message.data, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        ))}
        
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800 border border-slate-600 rounded-lg px-4 py-3 shadow-lg">
              <div className="flex items-center gap-2 text-cyan-400">
                <Loader className="w-4 h-4 animate-spin" />
                <span className="text-sm">Analyzing...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-700 bg-slate-800 p-4">
        <div className="flex gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={mcpStatus === 'disconnected' 
              ? "Analytics server not connected"
              : "Ask about market conditions, options, technical analysis, or specific stocks..."}
            disabled={loading || mcpStatus === 'disconnected'}
            className="flex-1 px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent disabled:bg-slate-800 disabled:text-slate-500 text-slate-100 placeholder-slate-400"
            rows="2"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim() || mcpStatus === 'disconnected'}
            className="px-6 py-3 bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-lg hover:from-cyan-500 hover:to-blue-500 disabled:from-slate-600 disabled:to-slate-600 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg transition-all duration-200"
          >
            {loading ? (
              <Loader className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
        
        <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            <span>Read-only market analysis • For trading, use Strategy Chat</span>
          </div>
          {(mcpStatus === 'connected' || mcpStatus === 'degraded') && (
            <div className="flex items-center gap-1 text-emerald-400">
              <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
              <span>Live data connected</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnalyticsChat;