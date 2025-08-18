// services/api.js - Main API service with all endpoints
import axios from 'axios';
import authService from './auth';

class APIService {
  constructor() {
    // Configure axios defaults
    axios.defaults.baseURL = '';
    // No authentication needed on local network
    // Removed all Bearer token logic
  }

  // === Core Trading Flow ===
  async generateStrategy(prompt, watchlist = [], sessionId = null) {
    const payload = {
      prompt,
      watchlist,
    };
    
    if (sessionId) {
      payload.session_id = sessionId;
    }

    const response = await axios.post('/api/strategies/generate', payload);
    return response.data;
  }

  async confirmStrategy(strategyId) {
    const response = await axios.post(`/api/strategies/${strategyId}/confirm`, {
      confirmed: true
    });
    return response.data;
  }

  // === Portfolio & Positions ===
  async getPortfolio() {
    const response = await axios.get('/api/portfolio');
    return response.data;
  }

  async getPositions() {
    const response = await axios.get('/api/get_positions');
    return response.data;
  }

  // === Market Scanner ===
  async getAvailableScanners() {
    const response = await axios.get('/api/available_scanners');
    return response.data;
  }

  async runScan(scanCode, options = {}) {
    const payload = {
      scan_code: scanCode,
      instrument: options.instrument || 'STK',
      location: options.location || 'STK.US.MAJOR',
      filters: options.filters || {},
      limit: options.limit || 50
    };
    const response = await axios.post('/api/run_scan', payload);
    return response.data;
  }

  // === Health & Diagnostics ===
  async getHealth() {
    const response = await axios.get('/api/health');
    return response.data;
  }

  async diagnoseSymbol(symbol) {
    const response = await axios.get(`/api/diagnose/${symbol}`);
    return response.data;
  }

  // === Watchlist ===
  async getWatchlist() {
    const response = await axios.get('/api/watchlist');
    return response.data;
  }

  async syncWatchlist(symbols) {
    // Handle both simple array and enhanced format
    const payload = Array.isArray(symbols) ? { symbols } : { watchlist: symbols };
    const response = await axios.post('/api/watchlist/sync', payload);
    return response.data;
  }
  
  async updateWatchlistItem(symbol, updates) {
    const response = await axios.patch(`/api/watchlist/${symbol}`, updates);
    return response.data;
  }

  // === Options Chain ===
  async getOptionsChain(symbol) {
    const response = await axios.get(`/api/options/chain/${symbol}`);
    return response.data;
  }

  // === Analytics Endpoints ===
  async analyzePortfolio() {
    const response = await axios.post('/api/analytics/portfolio');
    return response.data;
  }

  async analyzeSymbol(symbol) {
    const response = await axios.get(`/api/analytics/symbol/${symbol}`);
    return response.data;
  }

  async analyzeMarket(prompt, symbols = []) {
    const response = await axios.post('/api/analytics/market', {
      prompt,
      symbols
    });
    return response.data;
  }

  async analyzeOptions(symbol) {
    const response = await axios.get(`/api/analytics/options/${symbol}`);
    return response.data;
  }

  // === Pending Orders ===
  async getPendingOrders(symbol = null, status = null) {
    const params = {};
    if (symbol) params.symbol = symbol;
    if (status) params.status = status;
    const response = await axios.get('/api/orders/pending', { params });
    return response.data;
  }

  async getBracketOrders() {
    const response = await axios.get('/api/orders/brackets');
    return response.data;
  }

  async cancelOrder(orderId) {
    const response = await axios.post(`/api/orders/cancel/${orderId}`);
    return response.data;
  }

  async getOrderStats() {
    const response = await axios.get('/api/orders/stats');
    return response.data;
  }
}

export default new APIService();
