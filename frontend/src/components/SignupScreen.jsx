"use client"
import React, { useState } from 'react';

const SignupScreen = ({ onSignupSuccess, onBackToLogin }) => {
  const [formData, setFormData] = useState({
    user_id: '',
    apiKey: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error when user starts typing
    if (error) setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault(); 
    
    if (!formData.user_id.trim() || !formData.apiKey.trim()) {
      setError('Please fill in all fields');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      // Call the Next.js API route instead of the external endpoint
      const response = await fetch('/api/set-api-key', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          'user_id': formData.user_id.trim(),
          'api_key': formData.apiKey.trim()
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Failed to set API key');
      }

      setSuccess(true);
      // Wait a moment to show success message, then proceed
      setTimeout(() => {
        onSignupSuccess(formData.user_id.trim());
      }, 1500);

    } catch (err) {
      setError(err.message);
      console.error('Signup error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSubmit(e);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-8">
        <div className="max-w-md w-full text-center">
          <div className="mb-8">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h1 className="text-3xl font-serif text-gray-900 mb-2">
              Welcome!
            </h1>
            <p className="text-lg text-gray-600 font-serif">
              API key set successfully
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-8">
      <div className="max-w-md w-full">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-serif text-gray-900 mb-4">
            Set API Key
          </h1>
          <p className="text-lg text-gray-600 font-serif">
            Enter your Poke API key and choose a user ID
          </p>
        </div>

        {/* Important Information Box */}
        <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4 mb-8">
          <div className="flex items-start">
            <svg className="w-6 h-6 text-blue-600 mt-1 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="text-sm">
              <h3 className="font-bold text-blue-900 mb-2">Important Information:</h3>
              <ul className="space-y-2 text-blue-800">
                <li>
                  <strong>User ID:</strong> The User_Id must be unique and must be used as the "API-Key" of our integration.
                </li>
                <li>
                  <strong>API Key:</strong> The API_Key is the Poke-API-Key, which you can find here:{' '}
                  <a 
                    href="https://poke.com/settings/advanced" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-blue-600 underline hover:text-blue-800"
                  >
                    https://poke.com/settings/advanced
                  </a>
                </li>
              </ul>
            </div>
          </div>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="user_id" className="block text-sm font-medium text-gray-700 mb-2 font-serif">
              User ID
            </label>
            <input
              id="user_id"
              name="user_id"
              type="text"
              value={formData.user_id}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              placeholder="Choose a unique user ID..."
              className="w-full px-4 py-3 border border-gray-300 rounded-md text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent font-serif"
              autoFocus
            />
            <p className="mt-2 text-sm text-gray-500 font-serif">
              This must be unique and will be used as the API-Key for our integration
            </p>
          </div>

          <div>
            <label htmlFor="apiKey" className="block text-sm font-medium text-gray-700 mb-2 font-serif">
              Poke API Key
            </label>
            <input
              id="apiKey"
              name="apiKey"
              type="password"
              value={formData.apiKey}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              placeholder="Enter your Poke-API key..."
              className="w-full px-4 py-3 border border-gray-300 rounded-md text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent font-serif"
            />
            <p className="mt-2 text-sm text-gray-500 font-serif">
              Get your Poke-API-Key from{' '}
              <a 
                href="https://poke.com/settings/advanced" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 underline"
              >
                poke.com/settings/advanced
              </a>
            </p>
          </div>
          
          {error && (
            <div className="text-red-600 text-sm text-center font-serif bg-red-50 p-3 rounded-md">
              {error}
            </div>
          )}
          
          <div className="space-y-3">
            <button
              type="submit"
              disabled={loading}
              className="w-full px-4 py-3 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-400 text-white font-medium rounded-md transition-colors duration-200 font-serif cursor-pointer disabled:cursor-not-allowed"
            >
              {loading ? 'Setting API Key...' : 'Set API Key'}
            </button>
            
            <button
              type="button"
              onClick={onBackToLogin}
              className="w-full px-4 py-3 text-gray-600 hover:text-gray-900 font-serif transition-colors duration-200 cursor-pointer"
            >
              Back to Login
            </button>
          </div>
        </form>
        
        <div className="mt-12 text-center text-gray-500 text-sm">
          <p className="font-serif">cutewels@eth-zurich</p>
        </div>
      </div>
    </div>
  );
};

export default SignupScreen;
