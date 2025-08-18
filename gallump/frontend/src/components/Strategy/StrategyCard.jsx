// components/Strategy/StrategyCard.jsx - Display strategy recommendations
import React, { useState } from 'react';
import RedButton from './RedButton';
import { ChartBarIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

export default function StrategyCard({ strategy, index }) {
  const [showRedButton, setShowRedButton] = useState(false);
  
  // Parse strategy details
  // Convert confidence to percentage (if it's between 0 and 1, multiply by 100)
  const rawConfidence = strategy.confidence || 0;
  const confidence = rawConfidence <= 1 ? rawConfidence * 100 : rawConfidence;
  const riskLevel = strategy.risk_level || 'medium';
  const orders = strategy.orders || [];
  
  const getRiskColor = () => {
    switch(riskLevel.toLowerCase()) {
      case 'low': return 'text-green-400';
      case 'medium': return 'text-yellow-400';
      case 'high': return 'text-red-400';
      default: return 'text-slate-400';
    }
  };

  return (
    <>
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 hover:border-cyan-400/50 transition-all">
        <div className="flex justify-between items-start mb-3">
          <div>
            <h4 className="font-semibold text-white">
              {strategy.name || `Strategy ${index + 1}`}
            </h4>
            {strategy.description && (
              <p className="text-sm text-slate-400 mt-1">{strategy.description}</p>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <ChartBarIcon className="h-5 w-5 text-slate-400" />
            <span className="text-sm font-medium text-cyan-400">{confidence}%</span>
          </div>
        </div>

        {/* Orders */}
        {orders.length > 0 && (
          <div className="space-y-1 mb-3">
            {orders.map((order, idx) => (
              <div key={idx} className="text-sm bg-gray-50 rounded px-2 py-1">
                <span className={`font-medium ${
                  order.action === 'BUY' ? 'text-green-600' : 'text-red-600'
                }`}>
                  {order.action}
                </span>
                {' '}
                {order.quantity} {order.symbol}
                {order.option_type && ` ${order.option_type}`}
                {order.strike && ` $${order.strike}`}
                {order.expiry && ` ${order.expiry}`}
                {' @ '}
                {order.order_type === 'LMT' ? `$${order.limit_price}` : 
                 order.order_type === 'TRAIL' ? `TRAIL ${order.trail_percent ? order.trail_percent + '%' : '$' + order.trail_amount}` :
                 order.order_type || 'MKT'}
              </div>
            ))}
          </div>
        )}

        {/* Risk and Max Loss */}
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center space-x-3">
            <span className={`flex items-center ${getRiskColor()}`}>
              <ExclamationTriangleIcon className="h-4 w-4 mr-1" />
              Risk: {riskLevel}
            </span>
            {strategy.max_loss && (
              <span className="text-gray-600">
                Max Loss: ${strategy.max_loss.toFixed(2)}
              </span>
            )}
          </div>
        </div>

        {/* Reasoning */}
        {strategy.reasoning && (
          <div className="mt-3 pt-3 border-t text-sm text-gray-600">
            {strategy.reasoning}
          </div>
        )}

        {/* Execute Button */}
        <div className="mt-4">
          <button
            onClick={() => setShowRedButton(true)}
            className="w-full bg-orange-500 hover:bg-orange-600 text-white font-medium py-2 rounded-lg transition-colors"
          >
            Review for Execution
          </button>
        </div>
      </div>

      {/* Red Button Modal */}
      {showRedButton && (
        <RedButton
          strategy={{ ...strategy, id: index }}
          onClose={() => setShowRedButton(false)}
        />
      )}
    </>
  );
}
