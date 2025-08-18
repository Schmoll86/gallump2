// components/Portfolio/PositionCard.jsx - Individual position display
import React from 'react';
import { ExclamationCircleIcon } from '@heroicons/react/24/outline';

export default function PositionCard({ position }) {
  // Calculate P&L percentage
  const pnlPercent = position.averageCost > 0 
    ? ((position.marketPrice / position.averageCost) - 1) * 100 
    : 0;
  
  const isStale = position.price_source === 'cached' || position.stale_data;
  const hasError = position.price_source === 'unavailable';
  
  return (
    <div className={`bg-slate-800 border rounded-lg p-4 ${
      hasError ? 'border-red-500' : isStale ? 'border-yellow-500' : 'border-slate-700'
    }`}>
      {/* Stale/Error Warning */}
      {(isStale || hasError) && (
        <div className={`mb-2 px-2 py-1 rounded text-xs flex items-center ${
          hasError 
            ? 'bg-red-900/20 text-red-400 border border-red-700' 
            : 'bg-yellow-900/20 text-yellow-400 border border-yellow-700'
        }`}>
          <ExclamationCircleIcon className="h-4 w-4 mr-1" />
          {hasError 
            ? position.error || 'No price data available' 
            : 'Using cached price'
          }
        </div>
      )}
      
      {/* Position Details */}
      <div className="flex justify-between items-start">
        <div>
          <div className="font-semibold text-lg text-white">{position.symbol}</div>
          <div className="text-sm text-slate-400">
            {position.position || position.quantity} shares
            @ ${position.averageCost?.toFixed(2) || '0.00'}
          </div>
        </div>
        
        <div className="text-right">
          <div className="font-mono text-lg text-white">
            ${position.marketPrice?.toFixed(2) || 'N/A'}
          </div>
          <div className={`text-sm font-medium ${
            position.unrealizedPnL >= 0 ? 'text-green-400' : 'text-red-400'
          }`}>
            {position.unrealizedPnL >= 0 ? '+' : ''}
            ${position.unrealizedPnL?.toFixed(2) || '0.00'}
            {' '}
            ({pnlPercent >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%)
          </div>
        </div>
      </div>
      
      {/* Market Value */}
      <div className="mt-3 pt-3 border-t border-slate-700 flex justify-between text-sm">
        <span className="text-slate-400">Market Value</span>
        <span className="font-medium text-white">
          ${position.marketValue?.toFixed(2) || '0.00'}
        </span>
      </div>
    </div>
  );
}
