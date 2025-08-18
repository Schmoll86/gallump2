// App.jsx - Main application component
import React, { useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import useAppStore from './stores/appStore';
import authService from './services/auth';

// Components
import LoginModal from './components/Auth/LoginModal';
import ChatBox from './components/Chat/ChatBox';
import PortfolioPanel from './components/Portfolio/PortfolioPanel';
import SystemHealth from './components/Health/SystemHealth';
import MobileNav from './components/Common/MobileNav';
import { ErrorBoundary } from './components/Common/ErrorBoundary';
import AnalyticsChat from './components/Analytics/AnalyticsChat';
// import ClaudeDesktopTab from './components/ClaudeDesktopTab'; // Removed - broken MCP bridge

const SettingsPanel = () => {
  const reset = useAppStore(state => state.reset);
  
  const handleLogout = () => {
    authService.logout();
    reset();
    window.location.reload();
  };
  
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-4">Settings</h2>
      <button 
        onClick={handleLogout}
        className="btn-danger w-full"
      >
        Logout
      </button>
    </div>
  );
};

function App() {
  const isAuthenticated = useAppStore(state => state.isAuthenticated);
  const activeTab = useAppStore(state => state.activeTab);
  const setAuth = useAppStore(state => state.setAuth);

  useEffect(() => {
    // Check for existing token on mount
    const token = authService.getToken();
    if (token) {
      setAuth(token);
    }
  }, []);

  if (!isAuthenticated) {
    return <LoginModal />;
  }

  const renderActiveTab = () => {
    switch(activeTab) {
      case 'portfolio':
        return <PortfolioPanel />;
      case 'scanner':
        return <AnalyticsChat />;
      // case 'claude-desktop':
      //   return <ClaudeDesktopTab />; // Removed - broken MCP bridge
      case 'settings':
        return <SettingsPanel />;
      case 'chat':
      default:
        return <ChatBox />;
    }
  };

  return (
    <ErrorBoundary>
      <div className="h-screen flex flex-col bg-gray-50">
        {/* System Health Bar */}
        <SystemHealth />
        
        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          {renderActiveTab()}
        </div>
        
        {/* Mobile Navigation */}
        <MobileNav />
        
        {/* Toast Notifications */}
        <Toaster 
          position="top-center"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
            },
            success: {
              style: {
                background: '#10b981',
              },
            },
            error: {
              style: {
                background: '#ef4444',
              },
            },
          }}
        />
      </div>
    </ErrorBoundary>
  );
}

export default App;
