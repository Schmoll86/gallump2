// components/Chat/ChatBox.jsx - Main conversational interface
import React, { useState, useRef, useEffect } from 'react';
import api from '../../services/api';
import sessionService from '../../services/session';
import useAppStore from '../../stores/appStore';
import Message from './Message';
import StrategyCard from '../Strategy/StrategyCard';
import ContextStats from './ContextStats';
import EnhancedWatchlist from './EnhancedWatchlist';
import toast from 'react-hot-toast';
import { PaperAirplaneIcon, PlusIcon, XMarkIcon } from '@heroicons/react/24/solid';

export default function ChatBox() {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const messagesEndRef = useRef(null);
  const watchlist = useAppStore(state => state.watchlist);
  const watchlistFormat = useAppStore(state => state.watchlistFormat);
  const setWatchlist = useAppStore(state => state.setWatchlist);

  useEffect(() => {
    // Initialize with welcome message
    setMessages([{
      role: 'assistant',
      content: 'Hello! I\'m your AI trading assistant. Discuss any trading thesis with me. I\'ll provide market analysis and strategy recommendations that you can review before execution.'
    }]);
    
    // Load initial watchlist (enhanced or simple format)
    api.getWatchlist().then(data => {
      if (data) {
        setWatchlist(data); // Store handles both formats
      }
    }).catch(err => {
      console.error('Failed to load watchlist:', err);
    });
  }, []);

  useEffect(() => {
    // Auto-scroll to bottom
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    
    // Add user message to display
    const newUserMessage = { role: 'user', content: userMessage };
    setMessages(prev => [...prev, newUserMessage]);
    sessionService.addMessage('user', userMessage);
    
    setLoading(true);

    try {
      console.log('Sending chat request with watchlist:', watchlist);
      // Call generate strategy endpoint with session management
      const response = await api.generateStrategy(
        userMessage,
        watchlist,
        sessionService.getSessionId()
      );
      console.log('Got response:', response);

      // Update session
      if (response.session_id) {
        sessionService.setSessionId(response.session_id);
      }
      if (response.context_stats) {
        sessionService.updateContextStats(response.context_stats);
      }

      // Add AI response
      const aiMessage = { 
        role: 'assistant', 
        content: response.response 
      };
      setMessages(prev => [...prev, aiMessage]);
      sessionService.addMessage('assistant', response.response);

      // Store recommendations if present
      if (response.recommendations && response.recommendations.length > 0) {
        setRecommendations(response.recommendations);
      }

      // Check token limit warning
      if (sessionService.isNearTokenLimit()) {
        toast.warning('Approaching context limit. Consider starting a new conversation soon.');
      }

    } catch (error) {
      console.error('Chat error:', error);
      toast.error(error.response?.data?.error || 'Failed to get response');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* Context Stats Bar */}
      <ContextStats />
      
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-2 space-y-4">
        {messages.map((msg, idx) => (
          <Message key={idx} message={msg} />
        ))}
        
        {loading && (
          <div className="flex items-center space-x-2 text-slate-400">
            <div className="animate-pulse">Claude is thinking...</div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Recommendations Panel */}
      {recommendations.length > 0 && (
        <div className="border-t border-slate-700 bg-slate-800 p-4">
          <h3 className="font-semibold text-sm text-cyan-400 mb-3">
            Strategy Recommendations
          </h3>
          <div className="space-y-2">
            {recommendations.map((rec, idx) => (
              <StrategyCard key={idx} strategy={rec} index={idx} />
            ))}
          </div>
        </div>
      )}

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="border-t border-slate-700 p-4 bg-slate-800">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Discuss your trading thesis..."
            className="flex-1 px-3 py-2 bg-slate-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-400 placeholder-slate-400"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="btn-primary px-3"
            aria-label="Send message"
          >
            <PaperAirplaneIcon className="h-5 w-5" />
          </button>
        </div>
        {/* Enhanced Watchlist */}
        <EnhancedWatchlist />
      </form>
    </div>
  );
}
