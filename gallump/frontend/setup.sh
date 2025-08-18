#!/bin/bash

# Setup script for Gallump Frontend

echo "🚀 Setting up Gallump Frontend..."

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install Node.js first."
    exit 1
fi

echo "✓ npm found"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Check if backend is running
echo "🔍 Checking backend connection..."
if curl -s http://localhost:5001/api/health > /dev/null 2>&1; then
    echo "✓ Backend is running on port 5001"
else
    echo "⚠️  Backend not detected on port 5001"
    echo "   Please start the backend with: python -m gallump.api.server"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the frontend development server:"
echo "  npm run dev"
echo ""
echo "The app will be available at http://localhost:3000"
echo "Default password: Snoop23"
