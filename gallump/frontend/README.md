# Gallump Frontend

**📖 This Document**: Frontend setup and development guide. For API docs see [API_FLOW.md](../../API_FLOW.md). For quick start see [README.md](../../README.md).

## Overview
A mobile-first React frontend for the Gallump Trading Assistant, properly integrated with the Flask backend API. Built with Vite, React 18, Tailwind CSS, and Zustand for state management.

## Features Implemented

### ✅ Core Features
- **JWT Authentication** - Login with password, token management
- **Session Management** - Maintains conversation continuity across requests
- **Claude AI Chat** - Conversational interface with context awareness
- **RED BUTTON Execution** - Multi-stage confirmation for trade execution
- **Portfolio Monitoring** - Real-time positions with P&L tracking
- **System Health Bar** - Live connection status monitoring
- **Mobile Navigation** - Touch-optimized bottom navigation
- **Error Handling** - Global error boundary and toast notifications

### 🎯 Proper Backend Integration
- Uses `/api/strategies/generate` with session_id support
- Uses `/api/strategies/{id}/confirm` for execution (NOT /api/execute)
- Handles actual response structure (`recommendations` not `strategies`)
- Correct field names (`prompt` not `message`)
- Includes watchlist in all strategy generation requests
- Displays context statistics (token usage, message count)
- Shows stale data warnings when using cached prices

## Installation

```bash
# Navigate to frontend directory
cd gallump/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will run on http://localhost:3000 and proxy API requests to the backend on port 5001.

## Configuration

### Environment
The Vite config proxies all `/api` requests to `http://localhost:5001` where the Flask backend runs.

### Authentication
Default password is `Snoop23` as configured in the backend `.env` file.

## Project Structure

```
src/
├── services/          # API and business logic
│   ├── api.js        # All API endpoints
│   ├── auth.js       # JWT authentication
│   └── session.js    # Session management
├── stores/           # Global state (Zustand)
│   └── appStore.js   # Main application store
├── components/       # React components
│   ├── Auth/         # Login modal
│   ├── Chat/         # AI conversation interface
│   │   ├── ChatBox.jsx
│   │   ├── Message.jsx
│   │   └── ContextStats.jsx
│   ├── Strategy/     # Strategy display and execution
│   │   ├── StrategyCard.jsx
│   │   └── RedButton.jsx    # THE RED BUTTON
│   ├── Portfolio/    # Portfolio and positions
│   │   ├── PortfolioPanel.jsx
│   │   └── PositionCard.jsx
│   ├── Health/       # System monitoring
│   │   └── SystemHealth.jsx
│   └── Common/       # Shared components
│       ├── MobileNav.jsx
│       └── ErrorBoundary.jsx
├── App.jsx           # Main app component
├── main.jsx          # Entry point
└── index.css         # Tailwind styles
```

## Key Integration Points

### 1. Session Management
The frontend properly maintains session_id for conversation continuity:
```javascript
const response = await api.generateStrategy(
  userMessage,
  watchlist,
  sessionService.getSessionId()  // Maintains conversation
);
sessionService.setSessionId(response.session_id);
```

### 2. RED BUTTON Flow
Proper multi-stage confirmation before execution:
- Review → Countdown (3 seconds) → Final Confirmation → Execute
- Uses `/api/strategies/{id}/confirm` endpoint
- Shows risk summary and all orders before execution

### 3. Health Monitoring
Real-time system status displayed in top bar:
- IBKR connection status
- Market open/closed
- Cache, storage, scanner health
- Automatic refresh every 10 seconds

### 4. Mobile Optimization
- Touch-optimized buttons and inputs
- Bottom navigation bar
- Responsive layouts
- Safe area insets for modern phones
- Disabled pull-to-refresh to prevent conflicts

## Security Features

1. **JWT tokens stored in sessionStorage** (not localStorage)
2. **Automatic logout on 401 responses**
3. **Multi-stage trade confirmation**
4. **Risk warnings before execution**
5. **Clear error messages for failed trades**

## Testing

```bash
# Development mode with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Common Issues

### CORS Errors
The Vite proxy should handle CORS, but ensure the Flask backend has CORS enabled:
```python
from flask_cors import CORS
CORS(app)
```

### Authentication Failed
- Check the password matches the backend `.env` file
- Ensure the backend is running on port 5001
- Verify JWT token is being sent in Authorization header

### No Market Data
- Check IBKR connection in health bar
- Look for "stale data" or "no price data" warnings
- Use the `/api/diagnose/{symbol}` endpoint for debugging

## Mobile Testing

For testing on mobile devices:
1. Find your local IP address
2. Access `http://YOUR_IP:3000` from mobile device
3. Ensure both devices are on the same network

## Next Steps

### To Add Scanner Feature:
```jsx
// components/Scanner/ScannerPanel.jsx
export default function ScannerPanel() {
  // Implement scanner UI using api.runScan()
}
```

### To Add Watchlist Management:
```jsx
// components/Watchlist/WatchlistPanel.jsx
export default function WatchlistPanel() {
  // Use api.syncWatchlist() and api.getWatchlist()
}
```

## Architecture Compliance

This frontend strictly follows the Gallump architecture:
- **Single Responsibility**: Each service/component has one job
- **Proper Data Flow**: User → Session → Context → Brain → Confirmation → Execution
- **No Direct Execution**: All trades require explicit user confirmation
- **Session Continuity**: Maintains conversation context across requests
- **Error Transparency**: All errors are shown to the user

## Support

For issues or questions about the frontend:
1. Check the browser console for errors
2. Verify the backend is running (`python -m gallump.api.server`)
3. Check system health in the top status bar
4. Review network requests in browser DevTools
