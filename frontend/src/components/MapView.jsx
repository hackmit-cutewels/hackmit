"use client"
import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

const MapView = ({ currentUser, onLogout, onViewModeChange }) => {
  const svgRef = useRef(null);
  const [mapData, setMapData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedPlace, setSelectedPlace] = useState(null);
  const [worldData, setWorldData] = useState(null);
  const [currentLocationIndex, setCurrentLocationIndex] = useState(0);
  const [zoomTransform, setZoomTransform] = useState(null);

  const fetchMapData = async (userId) => {
    try {
      console.log('Fetching map data for user:', userId);
      setLoading(true);
      const response = await fetch(`http://localhost:1234/api/map_data?user_id=${encodeURIComponent(userId)}`);
      if (!response.ok) {
        throw new Error('Failed to fetch map data');
      }
      const data = await response.json();
      console.log('Map data received:', data);
      setMapData(data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching map data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Load world map data
  useEffect(() => {
    console.log('Loading world map data...');
    d3.json('https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson')
      .then(data => {
        console.log('World data loaded:', data);
        setWorldData(data);
      })
      .catch(err => {
        console.error('Error loading world data:', err);
      });
  }, []);

  useEffect(() => {
    if (currentUser) {
      fetchMapData(currentUser);
    }
  }, [currentUser]);

  const handleRefresh = () => {
    if (currentUser) {
      fetchMapData(currentUser);
    }
  };

  const openSMS = (phoneNumber) => {
    const smsUrl = `sms:${phoneNumber}`;
    window.open(smsUrl, '_blank');
  };

  const jumpToLocation = (index) => {
    if (!mapData || !mapData.places || index < 0 || index >= mapData.places.length) return;
    
    const place = mapData.places[index];
    setCurrentLocationIndex(index);
    
    // Calculate the zoom transform to center on the location
    const svg = d3.select(svgRef.current);
    const width = 800;
    const height = 500;
    
    const projection = d3.geoMercator()
      .scale(100)
      .center([-71.0942, 42.3601])
      .translate([width / 2, height / 2]);
    
    const [x, y] = projection([place.longitude, place.latitude]);
    
    // Calculate zoom transform to center on the location
    const scale = 3; // Zoom level
    let translateX = width / 2 - x * scale;
    let translateY = height / 2 - y * scale;
    
    // Constrain the translation to keep the map within bounds
    // Calculate the bounds of the projected world map at the current scale
    const worldBounds = d3.geoBounds(worldData);
    const [worldMinX, worldMinY] = projection([worldBounds[0][0], worldBounds[0][1]]);
    const [worldMaxX, worldMaxY] = projection([worldBounds[1][0], worldBounds[1][1]]);
    
    const scaledWorldWidth = (worldMaxX - worldMinX) * scale;
    const scaledWorldHeight = (worldMaxY - worldMinY) * scale;
    
    // Constrain translation to prevent the map from going out of bounds
    const minTranslateX = width - scaledWorldWidth;
    const maxTranslateX = 0;
    const minTranslateY = height - scaledWorldHeight;
    const maxTranslateY = 0;
    
    translateX = Math.max(minTranslateX, Math.min(maxTranslateX, translateX));
    translateY = Math.max(minTranslateY, Math.min(maxTranslateY, translateY));
    
    const transform = d3.zoomIdentity.translate(translateX, translateY).scale(scale);
    
    // Apply the transform with animation
    svg.transition()
      .duration(750)
      .call(
        d3.zoom().transform,
        transform
      );
  };

  const nextLocation = () => {
    if (mapData && mapData.places.length > 0) {
      const nextIndex = (currentLocationIndex + 1) % mapData.places.length;
      jumpToLocation(nextIndex);
    }
  };

  const prevLocation = () => {
    if (mapData && mapData.places.length > 0) {
      const prevIndex = currentLocationIndex === 0 ? mapData.places.length - 1 : currentLocationIndex - 1;
      jumpToLocation(prevIndex);
    }
  };

  // D3.js map rendering
  useEffect(() => {
    console.log('Map rendering effect triggered:', { worldData: !!worldData, mapData: !!mapData, svgRef: !!svgRef.current });
    if (!worldData || !mapData || !svgRef.current) {
      console.log('Missing data for map rendering:', { worldData: !!worldData, mapData: !!mapData, svgRef: !!svgRef.current });
      return;
    }

    console.log('Rendering map with data:', { worldData, mapData });
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = 800;
    const height = 500;
    const padding = 20;

    svg.attr('width', width).attr('height', height);

    // Create projection
    const projection = d3.geoMercator()
      .scale(100)
      .center([-71.0942, 42.3601]) // Boston area
      .translate([width / 2, height / 2]);

    const path = d3.geoPath().projection(projection);

    // Create zoom behavior with bounds checking
    const zoom = d3.zoom()
      .scaleExtent([0.5, 8])
      .on('zoom', (event) => {
        // Constrain the transform to prevent out-of-bounds panning
        const { transform } = event;
        const { k, x, y } = transform;
        
        // Calculate the bounds of the projected world map at the current scale
        const worldBounds = d3.geoBounds(worldData);
        const [worldMinX, worldMinY] = projection([worldBounds[0][0], worldBounds[0][1]]);
        const [worldMaxX, worldMaxY] = projection([worldBounds[1][0], worldBounds[1][1]]);
        
        const scaledWorldWidth = (worldMaxX - worldMinX) * k;
        const scaledWorldHeight = (worldMaxY - worldMinY) * k;
        
        // Constrain translation to prevent the map from going out of bounds
        const minTranslateX = width - scaledWorldWidth;
        const maxTranslateX = 0;
        const minTranslateY = height - scaledWorldHeight;
        const maxTranslateY = 0;
        
        const constrainedX = Math.max(minTranslateX, Math.min(maxTranslateX, x));
        const constrainedY = Math.max(minTranslateY, Math.min(maxTranslateY, y));
        
        const constrainedTransform = d3.zoomIdentity.translate(constrainedX, constrainedY).scale(k);
        
        container.attr('transform', constrainedTransform);
        setZoomTransform(constrainedTransform);
      });

    svg.call(zoom);

    // Create container for map elements
    const container = svg.append('g');

    // Draw world map
    container.append('g')
      .attr('class', 'countries')
      .selectAll('path')
      .data(worldData.features)
      .enter().append('path')
      .attr('d', path)
      .attr('fill', '#f8f9fa')
      .attr('stroke', '#e9ecef')
      .attr('stroke-width', 0.5);

    // Create tooltip
    const tooltip = d3.select('body')
      .append('div')
      .attr('class', 'map-tooltip')
      .style('position', 'absolute')
      .style('background', 'white')
      .style('color', '#374151')
      .style('padding', '12px 16px')
      .style('border-radius', '8px')
      .style('font-size', '14px')
      .style('font-weight', '500')
      .style('font-family', 'serif')
      .style('pointer-events', 'none')
      .style('opacity', 0)
      .style('z-index', 1000)
      .style('box-shadow', '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)')
      .style('border', '1px solid #e5e7eb')
      .style('max-width', '300px');

    // Draw place markers
    const markers = container.append('g')
      .attr('class', 'markers')
      .selectAll('g')
      .data(mapData.places)
      .enter().append('g')
      .attr('class', 'marker')
      .style('cursor', 'pointer')
      .on('click', function(event, d) {
        setSelectedPlace(d);
      })
      .on('mouseover', function(event, d) {
        const [x, y] = projection([d.longitude, d.latitude]);
        tooltip
          .style('opacity', 1)
          .html(`
            <div>
              <div class="font-bold text-gray-900 mb-1">Location</div>
              <div class="text-sm text-gray-600 mb-2">${d.latitude.toFixed(4)}, ${d.longitude.toFixed(4)}</div>
              <div class="text-sm font-medium text-gray-700">
                ${d.people_count} ${d.people_count === 1 ? 'person' : 'people'} with shared interests
              </div>
            </div>
          `)
          .style('left', (event.pageX + 10) + 'px')
          .style('top', (event.pageY - 10) + 'px');

        d3.select(this).select('circle')
          .transition()
          .duration(150)
          .attr('r', 12)
          .attr('stroke-width', 3);
      })
      .on('mousemove', function(event) {
        tooltip
          .style('left', (event.pageX + 10) + 'px')
          .style('top', (event.pageY - 10) + 'px');
      })
      .on('mouseout', function() {
        tooltip.style('opacity', 0);
        d3.select(this).select('circle')
          .transition()
          .duration(150)
          .attr('r', 8)
          .attr('stroke-width', 2);
      });

    // Add circles for each place
    markers.append('circle')
      .attr('cx', d => projection([d.longitude, d.latitude])[0])
      .attr('cy', d => projection([d.longitude, d.latitude])[1])
      .attr('r', 8)
      .attr('fill', '#3b82f6')
      .attr('stroke', '#1d4ed8')
      .attr('stroke-width', 2);

    // Add text labels for people count
    markers.append('text')
      .attr('x', d => projection([d.longitude, d.latitude])[0])
      .attr('y', d => projection([d.longitude, d.latitude])[1])
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('fill', 'white')
      .attr('font-size', '10px')
      .attr('font-weight', 'bold')
      .text(d => d.people_count);

    // Cleanup function
    return () => {
      d3.selectAll('.map-tooltip').remove();
    };
  }, [worldData, mapData]);

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
            <div className="flex items-center space-x-4">
              <div className="flex bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => onViewModeChange('graph')}
                  className="px-4 py-2 rounded-md font-serif transition-colors duration-200 text-gray-600 hover:text-gray-900"
                >
                  Graph View
                </button>
                <button
                  onClick={() => onViewModeChange('map')}
                  className="px-4 py-2 rounded-md font-serif transition-colors duration-200 bg-white text-gray-900 shadow-sm"
                >
                  Map View
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Map Container */}
          <div className="lg:col-span-3">
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-serif text-gray-900">Places with Shared Interests</h2>
                <div className="flex gap-3">
                  {mapData && mapData.places.length > 0 && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={prevLocation}
                        className="px-3 py-2 text-gray-600 hover:text-gray-900 border border-gray-300 rounded-md font-serif transition-colors duration-200"
                        disabled={loading}
                      >
                        ← Prev
                      </button>
                      <span className="text-sm text-gray-600 font-serif">
                        {currentLocationIndex + 1} / {mapData.places.length}
                      </span>
                      <button
                        onClick={nextLocation}
                        className="px-3 py-2 text-gray-600 hover:text-gray-900 border border-gray-300 rounded-md font-serif transition-colors duration-200"
                        disabled={loading}
                      >
                        Next →
                      </button>
                    </div>
                  )}
                  <button
                    onClick={handleRefresh}
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
                      <p className="text-lg font-medium mb-2 font-serif">Error loading map data</p>
                      <p className="text-sm text-gray-600 font-serif">{error}</p>
                      <p className="text-xs mt-4 text-gray-500 font-serif">
                        Make sure your FastAPI server is running on localhost:1234
                      </p>
                    </div>
                  </div>
                )}
                
                {!loading && !error && mapData && worldData && (
                  <div className="flex justify-center">
                    <svg ref={svgRef} className="border border-gray-100 rounded-lg bg-white shadow-sm"></svg>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Stats Card */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h3 className="text-lg font-serif text-gray-900 mb-4">Map Statistics</h3>
              {mapData ? (
                <div className="space-y-3">
                  <div className="flex justify-between text-gray-700">
                    <span className="font-serif">Places:</span>
                    <span className="font-semibold font-serif">{mapData.places.length}</span>
                  </div>
                  <div className="flex justify-between text-gray-700">
                    <span className="font-serif">Total People:</span>
                    <span className="font-semibold font-serif">
                      {mapData.places.reduce((sum, place) => sum + place.people_count, 0)}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-gray-600 font-serif">No data loaded</p>
              )}
            </div>

        
            {/* Instructions Card */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h3 className="text-lg font-serif text-gray-900 mb-4">Map Controls</h3>
              <ul className="space-y-3 text-gray-700 text-sm">
                <li className="flex items-start">
                  <span className="text-gray-400 mr-2 font-serif">•</span>
                  <span className="font-serif"><strong>Mouse wheel:</strong> Zoom in/out</span>
                </li>
                <li className="flex items-start">
                  <span className="text-gray-400 mr-2 font-serif">•</span>
                  <span className="font-serif"><strong>Click & drag:</strong> Pan view</span>
                </li>
                <li className="flex items-start">
                  <span className="text-gray-400 mr-2 font-serif">•</span>
                  <span className="font-serif"><strong>Prev/Next buttons:</strong> Jump between locations</span>
                </li>
                <li className="flex items-start">
                  <span className="text-gray-400 mr-2 font-serif">•</span>
                  <span className="font-serif"><strong>Hover markers:</strong> Show location info</span>
                </li>
                <li className="flex items-start">
                  <span className="text-gray-400 mr-2 font-serif">•</span>
                  <span className="font-serif"><strong>Click markers:</strong> View details</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Selected Place Modal */}
      {selectedPlace && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-serif font-bold text-gray-900">
                Location Details
              </h3>
              <button
                onClick={() => setSelectedPlace(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            
            <p className="text-sm text-gray-600 font-serif mb-3">
              {selectedPlace.latitude.toFixed(4)}, {selectedPlace.longitude.toFixed(4)}
            </p>
            <p className="text-sm font-medium text-gray-700 font-serif mb-4">
              {selectedPlace.people_count} {selectedPlace.people_count === 1 ? 'person' : 'people'} with shared interests
            </p>
            
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-700 font-serif">
                People at this location:
              </h4>
              {selectedPlace.people.map((person, personIndex) => (
                <div
                  key={personIndex}
                  className="flex items-center justify-between p-2 bg-gray-50 rounded-lg border border-gray-100"
                >
                  <div className="flex items-center space-x-2">
                    <div className="w-6 h-6 bg-blue-400 rounded-full flex items-center justify-center">
                      <span className="text-white text-xs font-medium">💬</span>
                    </div>
                    <div>
                      <button
                        onClick={() => openSMS(person.phone_number)}
                        className="text-sm font-medium text-gray-700 hover:text-gray-900 font-serif transition-colors duration-200 cursor-pointer"
                      >
                        {person.phone_number}
                      </button>
                      <div className="text-xs text-gray-500 font-serif">
                        Shared interests: {person.shared_interests.join(', ')}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

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

export default MapView;
