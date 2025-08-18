/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'trading-green': '#10b981',
        'trading-red': '#ef4444',
        'trading-blue': '#3b82f6',
        'trading-dark': '#1f2937',
      },
      animation: {
        'pulse-red': 'pulse-red 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        'pulse-red': {
          '0%, 100%': { 
            opacity: '1',
            boxShadow: '0 0 0 0 rgba(239, 68, 68, 0.5)'
          },
          '50%': {
            opacity: '0.9',
            boxShadow: '0 0 0 10px rgba(239, 68, 68, 0)'
          },
        }
      }
    },
  },
  plugins: [],
}
