// components/Chat/Message.jsx - Individual message display
import React from 'react';
import { UserIcon, CpuChipIcon } from '@heroicons/react/24/outline';

export default function Message({ message }) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex max-w-[85%] ${isUser ? 'flex-row-reverse' : 'flex-row'} gap-2`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
          ${isUser ? 'bg-cyan-900' : isSystem ? 'bg-amber-900' : 'bg-slate-700'}`}>
          {isUser ? (
            <UserIcon className="w-5 h-5 text-cyan-400" />
          ) : (
            <CpuChipIcon className="w-5 h-5 text-slate-300" />
          )}
        </div>
        
        {/* Message Content */}
        <div className={`rounded-lg px-4 py-2 ${
          isUser 
            ? 'bg-cyan-600 text-white' 
            : isSystem 
            ? 'bg-amber-900/20 border border-amber-700 text-amber-200'
            : 'bg-slate-800 border border-slate-700 text-slate-200'
        }`}>
          <div className="whitespace-pre-wrap break-words">
            {message.content}
          </div>
          {message.timestamp && (
            <div className={`text-xs mt-1 ${
              isUser ? 'text-cyan-200' : 'text-slate-500'
            }`}>
              {new Date(message.timestamp).toLocaleTimeString()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
