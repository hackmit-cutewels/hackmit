"use client"
import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import SignupScreen from './SignupScreen';
import MapView from './MapView';

const GraphVisualization = () => {
  const svgRef = useRef(null);
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [user_id, setUser_id] = useState('');
  const [currentUser, setCurrentUser] = useState(null);
  const [loginError, setLoginError] = useState(null);
  const [showSignup, setShowSignup] = useState(false);
  const [viewMode, setViewMode] = useState('graph'); // 'graph' or 'map'

  // Debug view mode changes
  useEffect(() => {
    console.log('View mode changed to:', viewMode, 'Graph data exists:', !!graphData);
  }, [viewMode, graphData]);

  const handleLogin = async () => {
    if (!user_id.trim()) {
      setLoginError('Please enter a user ID');
      return;
    }
    
    setCurrentUser(user_id.trim());
    setLoginError(null);
    await fetchGraphData(user_id.trim());
  };

  const handleLogout = () => {
    setCurrentUser(null);
    setUser_id('');
    setGraphData(null);
    setError(null);
    setLoginError(null);
    setShowSignup(false);
    setViewMode('graph');
  };

  const handleSignupSuccess = (newUser_id) => {
    setCurrentUser(newUser_id);
    setUser_id(newUser_id);
    setShowSignup(false);
    setLoginError(null);
    fetchGraphData(newUser_id);
  };

  const handleBackToLogin = () => {
    setShowSignup(false);
    setLoginError(null);
  };

  const fetchGraphData = async (userId) => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:1234/api/graph_data?user_id=${encodeURIComponent(userId)}`);
      if (!response.ok) {
        throw new Error('Failed to fetch graph data');
      }
      const data = await response.json();
      setGraphData(data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching graph data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!graphData || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous content

    // Clean up any existing tooltips
    d3.selectAll('.phone-tooltip').remove();

    const width = 600;
    const height = 400;
    const padding = 50; // Extra padding for glow effect
    
    svg.attr('width', width + padding * 2).attr('height', height + padding * 2);

    console.log('Nodes:', graphData.nodes);
    console.log('Edges:', graphData.edges);

    // Create zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        container.attr('transform', event.transform);
      });

    // Apply zoom to svg
    svg.call(zoom);

    // Create a container group for all graph elements with padding offset
    const container = svg.append('g')
      .attr('transform', `translate(${padding}, ${padding})`);

    // Create simulation
    const simulation = d3.forceSimulation(graphData.nodes)
      .force('link', d3.forceLink(graphData.edges)
          .id(d => d.id)
          .distance(80))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2));

    // Create simple definitions for clean minimal look
    const defs = svg.append('defs');

    // Create links with minimal styling
    const link = container.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(graphData.edges)
      .enter().append('line')
      .attr('stroke', '#d1d5db')
      .attr('stroke-width', 1)
      .attr('opacity', 0.6);

    // Create nodes with different shapes
    const node = container.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(graphData.nodes)
      .enter().append('g')
      .style('cursor', 'pointer')
      .call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended));

    // Add shapes based on node type
    node.each(function(d) {
      const g = d3.select(this);
      
      if (d.type === 'interest') {
        // Square for interests with glow effect
        const size = 12;
        g.append('rect')
          .attr('x', -size/2)
          .attr('y', -size/2)
          .attr('width', size)
          .attr('height', size)
          .attr('fill', '#f59e0b')
          .attr('stroke', '#d97706')
          .attr('stroke-width', 1.5)
          .attr('rx', 2)
          .style('filter', 'drop-shadow(0 0 4px rgba(245, 158, 11, 0.4))');
      } else if (d.type === 'place') {
        // Diamond for places with blue color
        const size = 12;
        g.append('path')
          .attr('d', `M 0,-${size/2} L ${size/2},0 L 0,${size/2} L -${size/2},0 Z`)
          .attr('fill', '#3b82f6')
          .attr('stroke', '#1d4ed8')
          .attr('stroke-width', 1.5)
          .style('filter', 'drop-shadow(0 0 4px rgba(59, 130, 246, 0.4))');
      } else {
        // Circle for people - neutral colors
        const radius = d.id === currentUser ? 20 : 16;
        g.append('circle')
          .attr('r', radius)
          .attr('fill', d.id === currentUser ? '#6b7280' : '#9ca3af')
          .attr('stroke', d.id === currentUser ? '#4b5563' : '#6b7280')
          .attr('stroke-width', 1.5);
      }
    });

    // Add clean labels with better contrast
    const label = container.append('g')
      .attr('class', 'labels')
      .selectAll('text')
      .data(graphData.nodes)
      .enter().append('text')
      .text(d => {
        if (d.id === currentUser) return 'you';
        if (d.type === 'person') return ''; // Hide phone numbers on blue nodes
        if (d.type === 'place') return ''; // Hide place coordinates by default
        return d.label;
      })
      .attr('text-anchor', 'middle')
      .attr('dy', '.35em')
      .attr('fill', d => d.id === currentUser ? '#ffffff' : '#1f2937')
      .attr('font-size', d => d.id === currentUser ? '11px' : '9px')
      .attr('font-weight', d => d.id === currentUser ? '500' : '400')
      .attr('font-family', 'serif')
      .style('pointer-events', 'none')
      .style('opacity', d => (d.type === 'interest' || d.type === 'place') ? 0 : 1)
      .style('text-shadow', d => d.id === currentUser ? '0 1px 2px rgba(0, 0, 0, 0.5)' : '0 1px 1px rgba(255, 255, 255, 0.8)');

    // Create tooltip for phone numbers
    const tooltip = d3.select('body')
      .append('div')
      .attr('class', 'phone-tooltip')
      .style('position', 'absolute')
      .style('background', 'white')
      .style('color', '#374151')
      .style('padding', '8px 12px')
      .style('border-radius', '6px')
      .style('font-size', '12px')
      .style('font-weight', '500')
      .style('font-family', 'serif')
      .style('pointer-events', 'none')
      .style('opacity', 0)
      .style('z-index', 1000)
      .style('box-shadow', '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)')
      .style('border', '1px solid #e5e7eb');

    // Add subtle hover effects
    node
      .on('mouseover', function(event, d) {
        const g = d3.select(this);
        g.selectAll('circle, rect, path')
          .transition()
          .duration(150)
          .attr('r', d => {
            if (d.id === currentUser) return 22;
            return d.type === 'interest' ? 14 : d.type === 'place' ? 14 : 18;
          })
          .attr('width', d => d.type === 'interest' ? 14 : null)
          .attr('height', d => d.type === 'interest' ? 14 : null)
          .attr('x', d => d.type === 'interest' ? -7 : null)
          .attr('y', d => d.type === 'interest' ? -7 : null)
          .attr('d', d => {
            if (d.type === 'place') {
              const size = 14;
              return `M 0,-${size/2} L ${size/2},0 L 0,${size/2} L -${size/2},0 Z`;
            }
            return null;
          })
          .attr('stroke-width', 2)
          .style('filter', d => {
            if (d.type === 'interest') return 'drop-shadow(0 0 6px rgba(245, 158, 11, 0.6))';
            if (d.type === 'place') return 'drop-shadow(0 0 6px rgba(59, 130, 246, 0.6))';
            return null;
          });
        
        // Labels are now only shown via tooltips, not as black text on hover

        // Show phone number tooltip for person nodes (other than current user)
        if (d.type === 'person' && d.id !== currentUser && d.phone_number) {
          tooltip
            .style('opacity', 1)
            .html(`💬 ${d.phone_number}`)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 10) + 'px');
        }
        
        // Show place coordinates tooltip for place nodes
        if (d.type === 'place') {
          tooltip
            .style('opacity', 1)
            .html(`📍 ${d.label}`)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 10) + 'px');
        }
        
        // Show interest name tooltip for interest nodes
        if (d.type === 'interest') {
          tooltip
            .style('opacity', 1)
            .html(`${d.label}`)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 10) + 'px');
        }
      })
      .on('mousemove', function(event, d) {
        // Update tooltip position on mouse move
        if ((d.type === 'person' && d.id !== currentUser && d.phone_number) || d.type === 'place' || d.type === 'interest') {
          tooltip
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 10) + 'px');
        }
      })
      .on('mouseout', function(event, d) {
        const g = d3.select(this);
        g.selectAll('circle, rect, path')
          .transition()
          .duration(150)
          .attr('r', d => {
            if (d.id === currentUser) return 20;
            return d.type === 'interest' ? 12 : d.type === 'place' ? 12 : 16;
          })
          .attr('width', d => d.type === 'interest' ? 12 : null)
          .attr('height', d => d.type === 'interest' ? 12 : null)
          .attr('x', d => d.type === 'interest' ? -6 : null)
          .attr('y', d => d.type === 'interest' ? -6 : null)
          .attr('d', d => {
            if (d.type === 'place') {
              const size = 12;
              return `M 0,-${size/2} L ${size/2},0 L 0,${size/2} L -${size/2},0 Z`;
            }
            return null;
          })
          .attr('stroke-width', 1.5)
          .style('filter', d => {
            if (d.type === 'interest') return 'drop-shadow(0 0 4px rgba(245, 158, 11, 0.4))';
            if (d.type === 'place') return 'drop-shadow(0 0 4px rgba(59, 130, 246, 0.4))';
            return null;
          });
        
        // Labels are now only shown via tooltips, no need to hide them on mouseout

        // Hide tooltip
        tooltip.style('opacity', 0);
      })
      .on('click', function(event, d) {
        /*// Open SMS for blue nodes (people with phone numbers)
        if (d.type === 'person' && d.id !== currentUser && d.phone_number) {
          openSMS(d.phone_number);
        }
        // Open Google Maps for place nodes
        if (d.type === 'place' && d.latitude && d.longitude) {
          openGoogleMaps(d.latitude, d.longitude);
        } 
        */
      });

    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      node
        .attr('transform', d => `translate(${d.x}, ${d.y})`);

      label
        .attr('x', d => d.x)
        .attr('y', d => d.y);
    });

    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    // Add reset zoom button functionality
    const resetZoom = () => {
      svg.transition().duration(750).call(
        zoom.transform,
        d3.zoomIdentity
      );
    };

    // Store reset function for button access
    svg.node().resetZoom = resetZoom;

    // Cleanup function
    return () => {
      d3.selectAll('.phone-tooltip').remove();
    };

  }, [graphData, currentUser]);

  // Re-render graph when switching back to graph view
  useEffect(() => {
    if (viewMode === 'graph' && graphData && svgRef.current) {
      console.log('Switching back to graph view, graphData:', graphData);
      // Force re-render by clearing and re-drawing
      const svg = d3.select(svgRef.current);
      svg.selectAll('*').remove();
      
      // Force the main useEffect to run again
      setTimeout(() => {
        if (svgRef.current && graphData) {
          // Trigger a re-render by updating the graphData state
          setGraphData({...graphData});
        }
      }, 50);
    }
  }, [viewMode]);

  const handleResetZoom = () => {
    const svg = d3.select(svgRef.current);
    if (svg.node().resetZoom) {
      svg.node().resetZoom();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleLogin();
    }
  };

  const openSMS = (phoneNumber) => {
    // Create SMS URL with the phone number
    const smsUrl = `sms:${phoneNumber}`;
    window.open(smsUrl, '_blank');
  };

  const openGoogleMaps = (latitude, longitude) => {
    // Create Google Maps URL with the coordinates
    const mapsUrl = `https://www.google.com/maps?q=${latitude},${longitude}`;
    window.open(mapsUrl, '_blank');
  };

  // Signup Screen
  if (showSignup) {
    return <SignupScreen onSignupSuccess={handleSignupSuccess} onBackToLogin={handleBackToLogin} />;
  }

  // If in map view, show the MapView component
  if (viewMode === 'map') {
    return <MapView currentUser={currentUser} onLogout={handleLogout} onViewModeChange={setViewMode} />;
  }

  // Login Screen
  if (!currentUser) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-8">
        <div className="max-w-md w-full">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-serif text-gray-900 mb-4">
              Graph Explorer
            </h1>
            <p className="text-lg text-gray-600 font-serif">
              Enter your user ID to explore your network
            </p>
          </div>
          
          <div className="space-y-6">
            <div>
              <label htmlFor="user_id" className="block text-sm font-medium text-gray-700 mb-2 font-serif">
                User ID
              </label>
              <input
                id="user_id"
                type="text"
                value={user_id}
                onChange={(e) => setUser_id(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Enter your user ID..."
                className="w-full px-4 py-3 border border-gray-300 rounded-md text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent font-serif"
                autoFocus
              />
            </div>
            
            {loginError && (
              <div className="text-red-600 text-sm text-center font-serif">
                {loginError}
              </div>
            )}
            
            <div className="space-y-3">
              <button
                onClick={handleLogin}
                disabled={loading}
                className="w-full px-4 py-3 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-400 text-white font-medium rounded-md transition-colors duration-200 font-serif"
              >
                {loading ? 'Loading...' : 'Explore Network'}
              </button>
              
              <button
                onClick={() => setShowSignup(true)}
                className="w-full px-4 py-3 text-gray-600 hover:text-gray-900 font-serif transition-colors duration-200 cursor-pointer"
              >
                Set API Key
              </button>
            </div>
          </div>
          
          <div className="mt-12 text-center text-gray-500 text-sm">
            <img src="/NETZ-LOGO.svg" alt="NETZ Logo" className="h-20 mx-auto" />
          </div>
        </div>
      </div>
    );
  }


  // Main Graph View
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
          <div className="flex items-center space-x-4">
             {/*   <div className="flex bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('graph')}
                  className={`px-4 py-2 rounded-md font-serif transition-colors duration-200 ${
                    viewMode === 'graph'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Graph View
                </button>
                <button
                  onClick={() => setViewMode('map')}
                  className={`px-4 py-2 rounded-md font-serif transition-colors duration-200 ${
                    viewMode === 'map'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Map View
                </button>
              </div>*/}
              <button
                onClick={handleLogout}
                className="px-4 py-2 text-gray-600 hover:text-gray-900 font-serif transition-colors duration-200"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Graph Container */}
          <div className="lg:col-span-3">
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-serif text-gray-900">Graph Visualization</h2>
                <div className="flex gap-3">
                  <button
                    onClick={handleResetZoom}
                    className="px-4 py-2 text-gray-600 hover:text-gray-900 border border-gray-300 rounded-md font-serif transition-colors duration-200"
                    disabled={loading}
                  >
                    Reset View
                  </button>
                  <button
                    onClick={() => fetchGraphData(currentUser)}
                    className="px-4 py-2 bg-gray-900 hover:bg-gray-800 text-white rounded-md font-serif transition-colors duration-200"
                    disabled={loading}
                  >
                    {loading ? 'Loading...' : 'Refresh'}
                  </button>
                </div>
              </div>
              
              <div className="bg-gray-50/50 rounded-lg p-4 border border-gray-100">
                {loading && (
                  <div className="flex items-center justify-center h-96">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                  </div>
                )}
                
                {error && (
                  <div className="flex items-center justify-center h-96 text-center">
                    <div className="text-red-600">
                      <p className="text-lg font-medium mb-2 font-serif">Error loading graph</p>
                      <p className="text-sm text-gray-600 font-serif">{error}</p>
                      <p className="text-xs mt-4 text-gray-500 font-serif">
                        Make sure your FastAPI server is running on localhost:1234
                      </p>
                    </div>
                  </div>
                )}
                
                {!loading && !error && graphData && (
                  <div className="flex justify-center">
                    <svg ref={svgRef} key={`graph-${viewMode}-${currentUser}`} className="border border-gray-100 rounded-lg bg-white shadow-sm"></svg>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Stats Card */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h3 className="text-lg font-serif text-gray-900 mb-4">Network Statistics</h3>
              {graphData ? (
                <div className="space-y-3">
                  <div className="flex justify-between text-gray-700">
                    <span className="font-serif">Nodes:</span>
                    <span className="font-semibold font-serif">{graphData.nodes.length}</span>
                  </div>
                  <div className="flex justify-between text-gray-700">
                    <span className="font-serif">Interests:</span>
                    <span className="font-semibold font-serif">
                      {graphData.nodes.filter(n => n.type === 'interest').length}
                    </span>
                  </div>
                  <div className="flex justify-between text-gray-700">
                    <span className="font-serif">Places:</span>
                    <span className="font-semibold font-serif">
                      {graphData.nodes.filter(n => n.type === 'place').length}
                    </span>
                  </div>
                  <div className="flex justify-between text-gray-700">
                    <span className="font-serif">People:</span>
                    <span className="font-semibold font-serif">
                      {graphData.nodes.filter(n => n.type === 'person').length}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-gray-600 font-serif">No data loaded</p>
              )}
            </div>

            {/* Instructions Card */}
            {/*<div className="bg-white border border-gray-200 rounded-lg p-6">
              <h3 className="text-lg font-serif text-gray-900 mb-4">Controls</h3>
              <ul className="space-y-3 text-gray-700 text-sm">
                <li className="flex items-start">
                  <span className="text-gray-400 mr-2 font-serif">•</span>
                  <span className="font-serif"><strong>Mouse wheel:</strong> Zoom in/out</span>
                </li>
                <li className="flex items-start">
                  <span className="text-gray-400 mr-2 font-serif">•</span>
                  <span className="font-serif"><strong>Click & drag background:</strong> Pan view</span>
                </li>
                <li className="flex items-start">
                  <span className="text-gray-400 mr-2 font-serif">•</span>
                  <span className="font-serif"><strong>Drag nodes:</strong> Reposition them</span>
                </li>
                <li className="flex items-start">
                  <span className="text-gray-400 mr-2 font-serif">•</span>
                  <span className="font-serif"><strong>Hover interest/place nodes:</strong> Show labels</span>
                </li>
                <li className="flex items-start">
                  <span className="text-gray-400 mr-2 font-serif">•</span>
                  <span className="font-serif"><strong>Hover person nodes:</strong> Show phone numbers</span>
                </li>
                <li className="flex items-start">
                  <span className="text-green-600 mr-2 font-serif">•</span>
                  <span className="font-serif"><strong>Green nodes:</strong> Your node (highlighted)</span>
                </li>
                <li className="flex items-start">
                  <span className="text-orange-500 mr-2 font-serif">•</span>
                  <span className="font-serif"><strong>Orange squares:</strong> Interest types</span>
                </li>
                <li className="flex items-start">
                  <span className="text-blue-500 mr-2 font-serif">•</span>
                  <span className="font-serif"><strong>Blue diamonds:</strong> Places (click to open in Google Maps)</span>
                </li>
                <li className="flex items-start">
                  <span className="text-gray-500 mr-2 font-serif">•</span>
                  <span className="font-serif"><strong>Gray circles:</strong> Other people (shows phone numbers)</span>
                </li>
              </ul>
            </div>  */}
          </div>  
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-8 py-6">
          <div className="text-center text-gray-500">
            <img src="/NETZ-LOGO.svg" alt="NETZ Logo" className="h-20 mx-auto" />
          </div>
        </div>
      </div>
    </div>
  );
};

export default GraphVisualization;
