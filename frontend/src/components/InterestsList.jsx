"use client"
import React, { useEffect, useState } from 'react';

const InterestsList = ({ currentUser, onLogout }) => {
  const [interestsData, setInterestsData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchInterestsData = async (userId) => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:1234/api/interests_list?user_id=${encodeURIComponent(userId)}`);
      if (!response.ok) {
        throw new Error('Failed to fetch interests data');
      }
      const data = await response.json();
      setInterestsData(data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching interests data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (currentUser) {
      fetchInterestsData(currentUser);
    }
  }, [currentUser]);

  const handleRefresh = () => {
    if (currentUser) {
      fetchInterestsData(currentUser);
    }
  };

  if (!currentUser) {
    return null;
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-serif text-gray-900">
                poke
              </h1>
              <p className="text-lg text-gray-600 font-serif mt-1">
                Logged in as <span className="font-mono">{currentUser}</span>
              </p>
            </div>
            <button
              onClick={onLogout}
              className="px-4 py-2 text-gray-600 hover:text-gray-900 font-serif transition-colors duration-200"
            >
              Logout
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-8 py-8">
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-serif text-gray-900">Your Interests & Connections</h2>
            <button
              onClick={handleRefresh}
              className="px-4 py-2 bg-gray-900 hover:bg-gray-800 text-white rounded-md font-serif transition-colors duration-200"
              disabled={loading}
            >
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
          
          {loading && (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
            </div>
          )}
          
          {error && (
            <div className="flex items-center justify-center h-64 text-center">
              <div className="text-red-600">
                <p className="text-lg font-medium mb-2 font-serif">Error loading interests</p>
                <p className="text-sm text-gray-600 font-serif">{error}</p>
                <p className="text-xs mt-4 text-gray-500 font-serif">
                  Make sure your FastAPI server is running on localhost:1234
                </p>
              </div>
            </div>
          )}
          
          {!loading && !error && interestsData && (
            <div className="space-y-6">
              {interestsData.interests.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-600 font-serif text-lg">No interests found</p>
                </div>
              ) : (
                interestsData.interests.map((interestItem, index) => (
                  <div key={index} className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-xl font-serif text-gray-900">
                        {interestItem.interest}
                      </h3>
                      <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm font-serif">
                        {interestItem.count} {interestItem.count === 1 ? 'person' : 'people'} sharing
                      </span>
                    </div>
                    
                    {interestItem.people_sharing.length > 0 ? (
                      <div className="space-y-3">
                        <h4 className="text-sm font-medium text-gray-700 font-serif">
                          People who share this interest:
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                          {interestItem.people_sharing.map((person, personIndex) => (
                            <div
                              key={personIndex}
                              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100"
                            >
                              <div className="flex items-center space-x-3">
                                <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                                  <span className="text-white text-sm font-medium font-serif">
                                    💬
                                  </span>
                                </div>
                                <div>
                                  <p className="text-sm font-medium text-gray-900 font-serif">
                                    {person.phone_number}
                                  </p>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-4">
                        <p className="text-gray-500 font-serif text-sm">
                          No other people share this interest yet
                        </p>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-8 py-6">
          <div className="text-center text-gray-500">
            <p className="font-serif">cutewels@eth-zurich</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InterestsList;
