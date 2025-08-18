// components/Strategy/RedButton.jsx - Critical execution confirmation
import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import useAppStore from '../../stores/appStore';
import toast from 'react-hot-toast';
import { ExclamationTriangleIcon, XMarkIcon } from '@heroicons/react/24/outline';

export default function RedButton({ strategy, onClose }) {
  const [stage, setStage] = useState('review'); // review -> countdown -> ready
  const [countdown, setCountdown] = useState(null);
  const [executing, setExecuting] = useState(false);
  const refreshPortfolio = useAppStore(state => state.setPortfolio);

  useEffect(() => {
    if (countdown === null) return;
    
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    } else {
      setStage('ready');
    }
  }, [countdown]);

  const handleInitiate = () => {
    setStage('countdown');
    setCountdown(3);
  };

  const handleExecute = async () => {
    setExecuting(true);
    
    try {
      const response = await api.confirmStrategy(strategy.id);
      
      if (response.status === 'executed') {
        toast.success('Strategy executed successfully!');
        
        // Show executed orders
        response.executed_orders?.forEach(order => {
          toast.success(`Order ${order.order_id}: ${order.action} ${order.quantity} ${order.symbol}`, {
            duration: 5000
          });
        });
        
        // Refresh portfolio
        const portfolio = await api.getPortfolio();
        refreshPortfolio(portfolio);
        
        onClose();
      } else if (response.status === 'partial') {
        toast.warning('Partial execution - check failed orders');
        
        response.failed_orders?.forEach(order => {
          toast.error(`Failed: ${order.symbol} - ${order.error}`, {
            duration: 5000
          });
        });
      }
    } catch (error) {
      const errorData = error.response?.data;
      
      if (errorData?.warnings) {
        // Risk check failures
        errorData.warnings.forEach(warning => toast.error(warning));
      } else {
        toast.error(errorData?.error || 'Execution failed');
      }
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
      {stage === 'review' && (
        <div className="bg-white rounded-2xl p-6 max-w-md w-full">
          <div className="flex justify-between items-start mb-4">
            <h2 className="text-xl font-bold">Confirm Strategy Execution</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>
          
          {/* Risk Summary */}
          <div className="bg-red-50 border-2 border-red-200 rounded-lg p-4 mb-4">
            <div className="flex items-center mb-2">
              <ExclamationTriangleIcon className="h-5 w-5 text-red-600 mr-2" />
              <span className="font-semibold text-red-800">Risk Summary</span>
            </div>
            
            {strategy.max_loss && (
              <div className="flex justify-between mb-1">
                <span className="text-sm">Max Loss:</span>
                <span className="font-mono text-red-600 font-medium">
                  ${strategy.max_loss.toFixed(2)}
                </span>
              </div>
            )}
            
            <div className="flex justify-between mb-1">
              <span className="text-sm">Risk Level:</span>
              <span className="font-medium capitalize">
                {strategy.risk_level || 'Medium'}
              </span>
            </div>
            
            {strategy.stop_loss && (
              <div className="flex justify-between">
                <span className="text-sm">Stop Loss:</span>
                <span className="font-mono">${strategy.stop_loss}</span>
              </div>
            )}
          </div>

          {/* Orders Summary */}
          <div className="mb-4">
            <h3 className="font-semibold text-sm mb-2">Orders to Execute:</h3>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {strategy.orders?.map((order, idx) => (
                <div key={idx} className="text-sm bg-gray-50 rounded px-2 py-1">
                  {order.action} {order.quantity} {order.symbol}
                  {order.order_type === 'LMT' && ` @ $${order.limit_price}`}
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={handleInitiate}
            className="w-full bg-red-600 hover:bg-red-700 text-white py-4 rounded-lg font-bold text-lg transition-colors"
          >
            INITIATE EXECUTION
          </button>
        </div>
      )}

      {stage === 'countdown' && (
        <div className="text-center">
          <div className="text-8xl font-bold text-red-500 mb-4 animate-pulse">
            {countdown}
          </div>
          <p className="text-white text-xl">Preparing to execute...</p>
          <button
            onClick={onClose}
            className="mt-4 text-gray-300 hover:text-white"
          >
            Cancel
          </button>
        </div>
      )}

      {stage === 'ready' && (
        <div className="bg-white rounded-2xl p-8 max-w-md w-full text-center">
          <div className="mb-6">
            <div className="text-6xl mb-4">⚠️</div>
            <h2 className="text-2xl font-bold mb-2">Final Confirmation</h2>
            <p className="text-gray-600">
              This will execute {strategy.orders?.length || 0} real orders
            </p>
          </div>
          
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 py-3 rounded-lg font-medium"
            >
              Cancel
            </button>
            <button
              onClick={handleExecute}
              disabled={executing}
              className="flex-1 bg-red-600 hover:bg-red-700 text-white py-3 rounded-lg font-bold animate-pulse-red"
            >
              {executing ? 'EXECUTING...' : 'EXECUTE TRADE'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
