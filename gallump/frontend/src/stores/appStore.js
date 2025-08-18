// stores/appStore.js - Global state management with Zustand
import { create } from 'zustand';

const useAppStore = create((set, get) => ({
  // Authentication
  isAuthenticated: false,
  token: null,
  
  // Portfolio
  portfolio: null,
  positions: [],
  
  // Watchlist (can be simple array or enhanced format)
  watchlist: [],
  watchlistFormat: 'simple', // 'simple' or 'enhanced'
  primarySymbol: null,
  
  // Health status
  systemHealth: null,
  
  // UI State
  activeTab: 'chat',
  loading: false,
  error: null,
  
  // Actions
  setAuth: (token) => set({ isAuthenticated: !!token, token }),
  
  setPortfolio: (portfolio) => set({ portfolio }),
  
  setPositions: (positions) => set({ positions }),
  
  setWatchlist: (data) => set((state) => {
    // Handle both formats from API
    if (data.format === 'enhanced') {
      return {
        watchlist: data.watchlist || [],
        watchlistFormat: 'enhanced',
        primarySymbol: data.primary || null
      };
    } else if (Array.isArray(data)) {
      // Simple array format (backward compatible)
      return {
        watchlist: data,
        watchlistFormat: 'simple',
        primarySymbol: null
      };
    } else {
      // Already enhanced object
      return {
        watchlist: data.watchlist || data,
        watchlistFormat: data.format || 'simple',
        primarySymbol: data.primary || null
      };
    }
  }),
  
  addToWatchlist: (symbolOrItem) => set((state) => {
    if (state.watchlistFormat === 'enhanced') {
      const newItem = typeof symbolOrItem === 'string' 
        ? { symbol: symbolOrItem, thesis: '', is_primary: false, category: 'Long' }
        : symbolOrItem;
      return { watchlist: [...state.watchlist, newItem] };
    } else {
      const symbol = typeof symbolOrItem === 'string' ? symbolOrItem : symbolOrItem.symbol;
      return { watchlist: [...state.watchlist, symbol] };
    }
  }),
  
  removeFromWatchlist: (symbol) => set((state) => {
    if (state.watchlistFormat === 'enhanced') {
      return { 
        watchlist: state.watchlist.filter(item => item.symbol !== symbol),
        primarySymbol: state.primarySymbol === symbol ? null : state.primarySymbol
      };
    } else {
      return { watchlist: state.watchlist.filter(s => s !== symbol) };
    }
  }),
  
  setPrimarySymbol: (symbol) => set((state) => {
    if (state.watchlistFormat === 'enhanced') {
      const updatedWatchlist = state.watchlist.map(item => ({
        ...item,
        is_primary: item.symbol === symbol
      }));
      return { 
        watchlist: updatedWatchlist,
        primarySymbol: symbol
      };
    }
    return state;
  }),
  
  updateWatchlistItem: (symbol, updates) => set((state) => {
    if (state.watchlistFormat === 'enhanced') {
      const updatedWatchlist = state.watchlist.map(item => 
        item.symbol === symbol ? { ...item, ...updates } : item
      );
      return { 
        watchlist: updatedWatchlist,
        primarySymbol: updates.is_primary ? symbol : state.primarySymbol
      };
    }
    return state;
  }),
  
  setSystemHealth: (health) => set({ systemHealth: health }),
  
  setActiveTab: (tab) => set({ activeTab: tab }),
  
  setLoading: (loading) => set({ loading }),
  
  setError: (error) => set({ error }),
  
  clearError: () => set({ error: null }),
  
  reset: () => set({
    isAuthenticated: false,
    token: null,
    portfolio: null,
    positions: [],
    watchlist: [],
    systemHealth: null,
    activeTab: 'chat',
    loading: false,
    error: null
  })
}));

export default useAppStore;
