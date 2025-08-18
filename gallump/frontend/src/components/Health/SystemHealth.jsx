// components/Health/SystemHealth.jsx - System health monitoring bar
import React, { useEffect, useState } from 'react';
import api from '../../services/api';
import useAppStore from '../../stores/appStore';

export default function SystemHealth() {
  const [health, setHealth] = useState(null);
  const setSystemHealth = useAppStore(state => state.setSystemHealth);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await api.getHealth();
        setHealth(data);
        setSystemHealth(data);
      } catch (error) {
        setHealth({ status: 'error', error: error.message });
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 10000); // Check every 10 seconds
    
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (component) => {
    if (!component?.healthy) return 'bg-red-500';
    if (component?.status === 'degraded') return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getOverallStatus = () => {
    if (!health) return 'unknown';
    if (health.status === 'error') return 'error';
    if (health.status === 'degraded') return 'degraded';
    return 'healthy';
  };

  return (
    <div className="bg-gray-900 text-white px-4 py-2">
      <div className="flex items-center justify-between text-xs">
        {/* Status Indicators */}
        <div className="flex items-center space-x-4">
          {/* IBKR Connection */}
          <div className="flex items-center space-x-1">
            <div className={`w-2 h-2 rounded-full ${
              getStatusColor(health?.components?.ibkr_connection)
            }`} />
            <span>IBKR</span>
          </div>

          {/* Analytics */}
          <div className="flex items-center space-x-1">
            <div className={`w-2 h-2 rounded-full ${
              getStatusColor(health?.components?.scanner)
            }`} />
            <span>Analytics</span>
          </div>

          {/* Cache */}
          <div className="flex items-center space-x-1">
            <div className={`w-2 h-2 rounded-full ${
              getStatusColor(health?.components?.cache)
            }`} />
            <span>Cache</span>
          </div>

          {/* Storage */}
          <div className="flex items-center space-x-1">
            <div className={`w-2 h-2 rounded-full ${
              getStatusColor(health?.components?.storage)
            }`} />
            <span>Storage</span>
          </div>
        </div>

        {/* Market Status & Overall Health */}
        <div className="flex items-center space-x-4">
          {/* Market Status */}
          {health?.components?.ibkr_connection?.market_status && (
            <span className={
              health.components.ibkr_connection.market_status.is_open 
                ? 'text-green-400' 
                : 'text-yellow-400'
            }>
              Market {health.components.ibkr_connection.market_status.is_open ? 'Open' : 'Closed'}
            </span>
          )}
          
          {/* Overall Status */}
          <span className={`font-medium ${
            getOverallStatus() === 'healthy' ? 'text-green-400' :
            getOverallStatus() === 'degraded' ? 'text-yellow-400' :
            'text-red-400'
          }`}>
            {getOverallStatus() === 'healthy' ? '✓ All Systems' :
             getOverallStatus() === 'degraded' ? '⚠ Degraded' :
             '✗ System Error'}
          </span>
        </div>
      </div>

      {/* Error Banner */}
      {getOverallStatus() === 'error' && (
        <div className="mt-2 bg-red-600 px-2 py-1 rounded text-xs">
          System offline - Check connection settings
        </div>
      )}
    </div>
  );
}
