// components/Common/MobileNav.jsx - Mobile navigation tabs
import React from 'react';
import useAppStore from '../../stores/appStore';
import {
  ChatBubbleLeftRightIcon,
  ChartBarIcon,
  MagnifyingGlassIcon,
  ComputerDesktopIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline';
import {
  ChatBubbleLeftRightIcon as ChatSolid,
  ChartBarIcon as ChartSolid,
  MagnifyingGlassIcon as SearchSolid,
  ComputerDesktopIcon as ComputerSolid,
  Cog6ToothIcon as CogSolid
} from '@heroicons/react/24/solid';

export default function MobileNav() {
  const activeTab = useAppStore(state => state.activeTab);
  const setActiveTab = useAppStore(state => state.setActiveTab);

  const tabs = [
    { 
      id: 'chat', 
      label: 'Chat',
      icon: ChatBubbleLeftRightIcon,
      activeIcon: ChatSolid
    },
    { 
      id: 'portfolio', 
      label: 'Portfolio',
      icon: ChartBarIcon,
      activeIcon: ChartSolid
    },
    { 
      id: 'scanner', 
      label: 'Analytics',
      icon: MagnifyingGlassIcon,
      activeIcon: SearchSolid
    },
    // Removed MCP tab - broken bridge concept
    { 
      id: 'settings', 
      label: 'Settings',
      icon: Cog6ToothIcon,
      activeIcon: CogSolid
    }
  ];

  return (
    <div className="bg-slate-800 border-t border-slate-700 safe-bottom">
      <div className="flex justify-around">
        {tabs.map(tab => {
          const Icon = activeTab === tab.id ? tab.activeIcon : tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 py-3 px-2 flex flex-col items-center space-y-1 transition-colors duration-200 ${
                activeTab === tab.id 
                  ? 'text-cyan-400' 
                  : 'text-slate-400 hover:text-slate-300'
              }`}
            >
              <Icon className="h-6 w-6" />
              <span className="text-xs font-medium">{tab.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
