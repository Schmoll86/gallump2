// components/Auth/LoginModal.jsx - Authentication modal
import React, { useState } from 'react';
import authService from '../../services/auth';
import useAppStore from '../../stores/appStore';
import toast from 'react-hot-toast';

export default function LoginModal() {
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const setAuth = useAppStore(state => state.setAuth);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!password.trim()) {
      toast.error('Please enter a password');
      return;
    }

    setLoading(true);
    
    try {
      const result = await authService.login(password);
      
      if (result.success) {
        setAuth(result.token);
        toast.success('Login successful!');
      } else {
        toast.error(result.error || 'Login failed');
      }
    } catch (error) {
      toast.error('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full">
        <div className="card">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900">Gallump Trading</h1>
            <p className="mt-2 text-sm text-gray-600">
              AI-Powered Options Trading Assistant
            </p>
          </div>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-field mt-1"
                placeholder="Enter password"
                disabled={loading}
                autoFocus
              />
            </div>
            
            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary"
            >
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
