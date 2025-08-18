// services/session.js - Session management for chat continuity
class SessionService {
  constructor() {
    this.sessionId = null;
    this.messages = [];
    this.contextStats = null;
    this.tokenLimit = 8000; // Claude's approximate limit
    this.tokenWarningThreshold = 6000;
  }

  getSessionId() {
    return this.sessionId;
  }

  setSessionId(id) {
    this.sessionId = id;
  }

  addMessage(role, content) {
    this.messages.push({
      role,
      content,
      timestamp: new Date().toISOString()
    });
    
    // Keep only last 20 messages in memory
    if (this.messages.length > 20) {
      this.messages = this.messages.slice(-20);
    }
  }

  getMessages() {
    return this.messages;
  }

  clearMessages() {
    this.messages = [];
    this.sessionId = null;
    this.contextStats = null;
  }

  updateContextStats(stats) {
    this.contextStats = stats;
  }

  getContextStats() {
    return this.contextStats;
  }

  isNearTokenLimit() {
    if (!this.contextStats || !this.contextStats.token_estimate) {
      return false;
    }
    return this.contextStats.token_estimate > this.tokenWarningThreshold;
  }

  // Estimate tokens (rough approximation)
  estimateTokens() {
    const totalChars = this.messages.reduce((sum, msg) => 
      sum + (msg.content?.length || 0), 0
    );
    // Rough estimate: 1 token ≈ 4 characters
    return Math.floor(totalChars / 4);
  }
}

export default new SessionService();
