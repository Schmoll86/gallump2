// components/Portfolio/PortfolioPanel.jsx - Portfolio overview and positions
import React, { useEffect, useState } from 'react';
import api from '../../services/api';
import useAppStore from '../../stores/appStore';
import PositionCard from './PositionCard';
import DataFreshness from '../Common/DataFreshness';
import toast from 'react-hot-toast';
import { ArrowPathIcon } from '@heroicons/react/24/outline';

export default function PortfolioPanel() {
  const [loading, setLoading] = useState(false);
  const [positions, setPositions] = useState([]);
  const portfolio = useAppStore(state => state.portfolio);
  const setPortfolio = useAppStore(state => state.setPortfolio);

  const fetchData = async () => {
    setLoading(true);
    try {
      const portfolioData = await api.getPortfolio();
      
      setPortfolio(portfolioData);
      // Use positions from portfolio data which has the correct price fields
      setPositions(portfolioData.positions || []);
    } catch (error) {
      toast.error('Failed to fetch portfolio data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const totalPnL = positions.reduce((sum, pos) => 
    sum + (pos.unrealizedPnL || 0), 0
  );

  return (
    <div className="h-full flex flex-col bg-slate-900">
      {/* Header */}
      <div className="bg-slate-800 border-b border-slate-700 px-4 py-3">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-white">Portfolio</h2>
          <button
            onClick={fetchData}
            disabled={loading}
            className="text-slate-400 hover:text-cyan-400 transition-colors"
            aria-label="Refresh"
          >
            <ArrowPathIcon className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="p-4 grid grid-cols-2 gap-4">
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <div className="text-sm text-slate-400">Total Value</div>
          <div className="text-2xl font-bold text-white">
            ${portfolio?.total_value?.toLocaleString() || '0'}
          </div>
        </div>
        
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <div className="text-sm text-slate-400">Unrealized P&L</div>
          <div className={`text-2xl font-bold ${
            totalPnL >= 0 ? 'text-green-400' : 'text-red-400'
          }`}>
            {totalPnL >= 0 ? '+' : ''}${totalPnL.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Positions List */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {loading && positions.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            Loading positions...
          </div>
        ) : positions.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            No open positions
          </div>
        ) : (
          <div className="space-y-3">
            {positions.map((position, idx) => (
              <PositionCard key={idx} position={position} />
            ))}
          </div>
        )}
      </div>

      {/* Last Update */}
      {positions.length > 0 && (
        <div className="border-t px-4 py-2 text-xs text-gray-500 text-center">
          Last updated: {new Date().toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}
