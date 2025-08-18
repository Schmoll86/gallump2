// components/Chat/ContextStats.jsx - Display session context statistics
import React from 'react';
import sessionService from '../../services/session';

export default function ContextStats() {
  const stats = sessionService.getContextStats();
  const sessionId = sessionService.getSessionId();
  
  if (!stats && !sessionId) return null;
  
  return (
    <div className="bg-slate-800 border-b border-slate-700 px-4 py-2">
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center space-x-4 text-cyan-400">
          {sessionId && (
            <span>
              Session: {sessionId.slice(0, 8)}...
            </span>
          )}
          {stats && (
            <>
              <span>Messages: {stats.messages_in_session}</span>
              <span>History: {stats.relevant_history_loaded}</span>
              <span>Insights: {stats.insights_included}</span>
              <span className={`font-medium ${
                stats.token_estimate > 80000 ? 'text-red-400' : ''
              }`}>
                Tokens: ~{stats.token_estimate?.toLocaleString()}
              </span>
            </>
          )}
        </div>
        {stats?.token_estimate > 80000 && (
          <span className="text-red-400 font-medium">
            Approaching limit
          </span>
        )}
      </div>
    </div>
  );
}
