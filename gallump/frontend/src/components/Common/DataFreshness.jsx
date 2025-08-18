// components/Common/DataFreshness.jsx - Shows data staleness indicators
import React from 'react';
import { ClockIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

export default function DataFreshness({ timestamp, source }) {
  if (!timestamp) return null;
  
  const getAge = () => {
    const now = new Date();
    const dataTime = new Date(timestamp);
    const diffMs = now - dataTime;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    
    if (diffMins < 1) return 'Live';
    if (diffMins < 60) return `${diffMins}m old`;
    if (diffHours < 24) return `${diffHours}h old`;
    return `${Math.floor(diffHours / 24)}d old`;
  };
  
  const getColor = () => {
    const now = new Date();
    const dataTime = new Date(timestamp);
    const diffMs = now - dataTime;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 5) return 'text-green-600';
    if (diffMins < 60) return 'text-yellow-600';
    return 'text-red-600';
  };
  
  const age = getAge();
  const color = getColor();
  const isStale = age !== 'Live';
  
  return (
    <div className={`inline-flex items-center space-x-1 text-xs ${color}`}>
      {isStale ? (
        <ExclamationTriangleIcon className="h-4 w-4" />
      ) : (
        <ClockIcon className="h-4 w-4" />
      )}
      <span>
        {age}
        {source && source !== 'live' && ` (${source})`}
      </span>
    </div>
  );
}