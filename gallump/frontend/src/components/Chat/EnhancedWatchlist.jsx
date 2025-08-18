// components/Chat/EnhancedWatchlist.jsx - Enhanced watchlist with primary symbol and thesis
import React, { useState } from 'react';
import { StarIcon, PlusIcon, XMarkIcon, PencilIcon, CheckIcon } from '@heroicons/react/24/solid';
import { StarIcon as StarOutlineIcon } from '@heroicons/react/24/outline';
import useAppStore from '../../stores/appStore';
import api from '../../services/api';
import toast from 'react-hot-toast';

export default function EnhancedWatchlist() {
  const watchlist = useAppStore(state => state.watchlist);
  const watchlistFormat = useAppStore(state => state.watchlistFormat);
  const primarySymbol = useAppStore(state => state.primarySymbol);
  const removeFromWatchlist = useAppStore(state => state.removeFromWatchlist);
  const setPrimarySymbol = useAppStore(state => state.setPrimarySymbol);
  const updateWatchlistItem = useAppStore(state => state.updateWatchlistItem);
  const addToWatchlist = useAppStore(state => state.addToWatchlist);
  
  const [showAddInput, setShowAddInput] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [newThesis, setNewThesis] = useState('');
  const [editingThesis, setEditingThesis] = useState(null);
  const [thesisInput, setThesisInput] = useState('');
  
  const handleAddSymbol = async () => {
    if (!newSymbol.trim()) return;
    
    const symbol = newSymbol.trim().toUpperCase();
    const newItem = {
      symbol,
      thesis: newThesis.trim(),
      is_primary: watchlist.length === 0, // First item is primary by default
      category: 'Long'
    };
    
    try {
      // Add to local state
      addToWatchlist(newItem);
      
      // Sync with backend
      await api.syncWatchlist(watchlistFormat === 'enhanced' 
        ? [...watchlist, newItem]
        : [...watchlist, symbol]
      );
      
      toast.success(`Added ${symbol} to watchlist`);
      setNewSymbol('');
      setNewThesis('');
      setShowAddInput(false);
    } catch (error) {
      toast.error('Failed to add symbol');
      console.error(error);
    }
  };
  
  const handleSetPrimary = async (symbol) => {
    try {
      setPrimarySymbol(symbol);
      await api.updateWatchlistItem(symbol, { is_primary: true });
      toast.success(`${symbol} set as primary focus`);
    } catch (error) {
      toast.error('Failed to set primary symbol');
      console.error(error);
    }
  };
  
  const handleUpdateThesis = async (symbol, thesis) => {
    try {
      updateWatchlistItem(symbol, { thesis });
      await api.updateWatchlistItem(symbol, { thesis });
      toast.success('Thesis updated');
      setEditingThesis(null);
      setThesisInput('');
    } catch (error) {
      toast.error('Failed to update thesis');
      console.error(error);
    }
  };
  
  const handleRemove = async (symbol) => {
    try {
      removeFromWatchlist(symbol);
      // Sync updated list with backend
      const updatedList = watchlistFormat === 'enhanced'
        ? watchlist.filter(item => item.symbol !== symbol)
        : watchlist.filter(s => s !== symbol);
      await api.syncWatchlist(updatedList);
      toast.success(`Removed ${symbol}`);
    } catch (error) {
      toast.error('Failed to remove symbol');
      console.error(error);
    }
  };
  
  // Normalize watchlist to always work with objects internally
  const normalizedWatchlist = watchlistFormat === 'enhanced' 
    ? watchlist 
    : watchlist.map(symbol => ({
        symbol,
        thesis: '',
        is_primary: symbol === primarySymbol,
        category: 'Long'
      }));
  
  return (
    <div className="mt-2 space-y-2">
      <div className="text-xs text-slate-400 font-medium mb-1">Watchlist</div>
      
      {/* Watchlist items */}
      <div className="space-y-1">
        {normalizedWatchlist.map((item) => {
          const symbol = typeof item === 'string' ? item : item.symbol;
          const thesis = typeof item === 'object' ? item.thesis : '';
          const isPrimary = typeof item === 'object' ? item.is_primary : false;
          
          return (
            <div key={symbol} className="flex items-start gap-2 p-2 bg-slate-800 rounded-lg">
              {/* Primary star */}
              <button
                onClick={() => handleSetPrimary(symbol)}
                className="mt-0.5"
                title={isPrimary ? "Primary focus" : "Set as primary"}
              >
                {isPrimary ? (
                  <StarIcon className="h-4 w-4 text-yellow-400" />
                ) : (
                  <StarOutlineIcon className="h-4 w-4 text-slate-500 hover:text-yellow-400 transition-colors" />
                )}
              </button>
              
              {/* Symbol and thesis */}
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-cyan-400">{symbol}</span>
                  <button
                    onClick={() => handleRemove(symbol)}
                    className="text-slate-500 hover:text-red-400 transition-colors"
                    title="Remove"
                  >
                    <XMarkIcon className="h-3 w-3" />
                  </button>
                </div>
                
                {/* Thesis */}
                {editingThesis === symbol ? (
                  <div className="flex items-center gap-1 mt-1">
                    <input
                      type="text"
                      value={thesisInput}
                      onChange={(e) => setThesisInput(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleUpdateThesis(symbol, thesisInput)}
                      placeholder="Trading thesis..."
                      className="flex-1 px-2 py-0.5 text-xs bg-slate-700 text-white border border-slate-600 rounded focus:outline-none focus:ring-1 focus:ring-cyan-400"
                      autoFocus
                    />
                    <button
                      onClick={() => handleUpdateThesis(symbol, thesisInput)}
                      className="text-green-500 hover:text-green-400"
                    >
                      <CheckIcon className="h-3 w-3" />
                    </button>
                    <button
                      onClick={() => {
                        setEditingThesis(null);
                        setThesisInput('');
                      }}
                      className="text-slate-500 hover:text-slate-400"
                    >
                      <XMarkIcon className="h-3 w-3" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1 mt-1">
                    {thesis ? (
                      <span className="text-xs text-slate-400">{thesis}</span>
                    ) : (
                      <span className="text-xs text-slate-500 italic">No thesis</span>
                    )}
                    <button
                      onClick={() => {
                        setEditingThesis(symbol);
                        setThesisInput(thesis || '');
                      }}
                      className="text-slate-500 hover:text-cyan-400 transition-colors"
                      title="Edit thesis"
                    >
                      <PencilIcon className="h-3 w-3" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
      
      {/* Add new symbol */}
      {showAddInput ? (
        <div className="p-2 bg-slate-800 rounded-lg space-y-2">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value)}
              placeholder="Symbol"
              className="w-24 px-2 py-1 text-xs bg-slate-700 text-white border border-slate-600 rounded focus:outline-none focus:ring-1 focus:ring-cyan-400"
              autoFocus
            />
            <input
              type="text"
              value={newThesis}
              onChange={(e) => setNewThesis(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleAddSymbol()}
              placeholder="Thesis (optional)"
              className="flex-1 px-2 py-1 text-xs bg-slate-700 text-white border border-slate-600 rounded focus:outline-none focus:ring-1 focus:ring-cyan-400"
            />
            <button
              onClick={handleAddSymbol}
              className="text-green-500 hover:text-green-400"
              title="Add"
            >
              <CheckIcon className="h-4 w-4" />
            </button>
            <button
              onClick={() => {
                setShowAddInput(false);
                setNewSymbol('');
                setNewThesis('');
              }}
              className="text-slate-500 hover:text-slate-400"
              title="Cancel"
            >
              <XMarkIcon className="h-4 w-4" />
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowAddInput(true)}
          className="flex items-center gap-1 px-2 py-1 text-xs bg-slate-700 text-slate-300 rounded hover:bg-slate-600 transition-colors"
        >
          <PlusIcon className="h-3 w-3" />
          Add Symbol
        </button>
      )}
    </div>
  );
}