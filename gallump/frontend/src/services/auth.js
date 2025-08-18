// services/auth.js - Authentication service with JWT management
import axios from 'axios';

class AuthService {
  constructor() {
    this.token = sessionStorage.getItem('jwt_token');
    this.refreshTimer = null;
  }

  async login(password) {
    try {
      const response = await axios.post('/api/auth/login', { password });
      
      if (response.data.token) {
        this.token = response.data.token;
        sessionStorage.setItem('jwt_token', this.token);
        this.setupTokenRefresh();
        return { success: true, token: this.token };
      }
      
      return { success: false, error: 'No token received' };
    } catch (error) {
      console.error('Login error:', error);
      return { 
        success: false, 
        error: error.response?.data?.error || 'Login failed' 
      };
    }
  }

  logout() {
    this.token = null;
    sessionStorage.removeItem('jwt_token');
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  setupTokenRefresh() {
    // JWT expires after 24 hours per server.py
    // Refresh 30 minutes before expiry
    const refreshIn = 23.5 * 60 * 60 * 1000; // 23.5 hours in ms
    
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
    }
    
    this.refreshTimer = setTimeout(() => {
      // In production, implement token refresh endpoint
      console.log('Token approaching expiry - user should re-authenticate');
    }, refreshIn);
  }

  getToken() {
    return this.token;
  }

  getAuthHeader() {
    return this.token ? { 'Authorization': `Bearer ${this.token}` } : {};
  }

  isAuthenticated() {
    return !!this.token;
  }
}

export default new AuthService();
