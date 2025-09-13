"use client"
import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

const GraphVisualization = () => {
  const svgRef = useRef(null);
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchGraphData();
  }, []);

  const fetchGraphData = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/graph-data');
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

    const width = 600;
    const height = 400;
    
    svg.attr('width', width).attr('height', height);

    console.log(graphData.nodes)
    // Create simulation
    const simulation = d3.forceSimulation(graphData.nodes)
      .force('link', d3.forceLink(graphData.edges).id(d => d.id).distance(80))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2));

    // Create gradient definitions
    const defs = svg.append('defs');
    
    const gradient = defs.append('radialGradient')
      .attr('id', 'nodeGradient')
      .attr('cx', '30%')
      .attr('cy', '30%');
    
    gradient.append('stop')
      .attr('offset', '0%')
      .attr('stop-color', '#ffffff')
      .attr('stop-opacity', 0.8);
    
    gradient.append('stop')
      .attr('offset', '100%')
      .attr('stop-color', '#3b82f6')
      .attr('stop-opacity', 0.6);

    // Create glow filter
    const filter = defs.append('filter')
      .attr('id', 'glow');
    
    filter.append('feGaussianBlur')
      .attr('stdDeviation', '3')
      .attr('result', 'coloredBlur');
    
    const feMerge = filter.append('feMerge');
    feMerge.append('feMergeNode')
      .attr('in', 'coloredBlur');
    feMerge.append('feMergeNode')
      .attr('in', 'SourceGraphic');

    // Create links
    const link = svg.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(graphData.edges)
      .enter().append('line')
      .attr('stroke', 'rgba(255, 255, 255, 0.6)')
      .attr('stroke-width', 2)
      .attr('filter', 'url(#glow)');

    // Create nodes
    const node = svg.append('g')
      .attr('class', 'nodes')
      .selectAll('circle')
      .data(graphData.nodes)
      .enter().append('circle')
      .attr('r', 20)
      .attr('fill', 'url(#nodeGradient)')
      .attr('stroke', 'rgba(255, 255, 255, 0.8)')
      .attr('stroke-width', 2)
      .attr('filter', 'url(#glow)')
      .style('cursor', 'pointer')
      .call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended));

    // Add labels
    const label = svg.append('g')
      .attr('class', 'labels')
      .selectAll('text')
      .data(graphData.nodes)
      .enter().append('text')
      .text(d => d.label)
      .attr('text-anchor', 'middle')
      .attr('dy', '.35em')
      .attr('fill', 'rgba(255, 255, 255, 0.9)')
      .attr('font-size', '12px')
      .attr('font-weight', 'bold')
      .attr('filter', 'url(#glow)')
      .style('pointer-events', 'none');

    // Add hover effects
    node
      .on('mouseover', function(event, d) {
        d3.select(this)
          .transition()
          .duration(200)
          .attr('r', 25)
          .attr('stroke-width', 3);
      })
      .on('mouseout', function(event, d) {
        d3.select(this)
          .transition()
          .duration(200)
          .attr('r', 20)
          .attr('stroke-width', 2);
      });

    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      node
        .attr('cx', d => d.x)
        .attr('cy', d => d.y);

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

  }, [graphData]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 p-8">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-white mb-4 drop-shadow-lg">
          cutewels finder
        </h1>
        <p className="text-lg text-blue-200 max-w-2xl mx-auto">
            your interests
        </p>
      </div>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Graph Container - Centered */}
          <div className="lg:col-span-2">
            <div className="backdrop-blur-lg bg-white/10 border border-white/20 rounded-2xl p-6 shadow-2xl">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-white">Graph Visualization</h2>
                <button
                  onClick={fetchGraphData}
                  className="px-4 py-2 bg-white/20 hover:bg-white/30 border border-white/30 rounded-lg text-white font-medium transition-all duration-200 backdrop-blur-sm"
                  disabled={loading}
                >
                  {loading ? 'Loading...' : 'Refresh'}
                </button>
              </div>
              
              <div className="bg-black/20 rounded-xl p-4 border border-white/10">
                {loading && (
                  <div className="flex items-center justify-center h-96">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white"></div>
                  </div>
                )}
                
                {error && (
                  <div className="flex items-center justify-center h-96 text-center">
                    <div className="text-red-300">
                      <p className="text-lg font-medium mb-2">Error loading graph</p>
                      <p className="text-sm opacity-80">{error}</p>
                      <p className="text-xs mt-4 opacity-60">
                        Make sure your FastAPI server is running on localhost:8000
                      </p>
                    </div>
                  </div>
                )}
                
                {!loading && !error && graphData && (
                  <div className="flex justify-center">
                    <svg ref={svgRef}></svg>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Stats Card */}
            <div className="backdrop-blur-lg bg-white/10 border border-white/20 rounded-2xl p-6 shadow-2xl">
              <h3 className="text-lg font-semibold text-white mb-4">Graph Statistics</h3>
              {graphData ? (
                <div className="space-y-3">
                  <div className="flex justify-between text-blue-200">
                    <span>Nodes:</span>
                    <span className="font-bold">{graphData.nodes.length}</span>
                  </div>
                  <div className="flex justify-between text-blue-200">
                    <span>Edges:</span>
                    <span className="font-bold">{graphData.edges.length}</span>
                  </div>
                  <div className="flex justify-between text-blue-200">
                    <span>Density:</span>
                    <span className="font-bold">
                      {graphData.nodes.length > 1 
                        ? ((2 * graphData.edges.length) / (graphData.nodes.length * (graphData.nodes.length - 1))).toFixed(2)
                        : '0.00'
                      }
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-blue-200">No data loaded</p>
              )}
            </div>

            {/* Instructions Card */}
            <div className="backdrop-blur-lg bg-white/10 border border-white/20 rounded-2xl p-6 shadow-2xl">
              <h3 className="text-lg font-semibold text-white mb-4">Instructions</h3>
              <ul className="space-y-2 text-blue-200 text-sm">
                <li className="flex items-start">
                  <span className="text-blue-400 mr-2">•</span>
                  Drag nodes to reposition them
                </li>
                <li className="flex items-start">
                  <span className="text-blue-400 mr-2">•</span>
                  Hover over nodes to see effects
                </li>
                <li className="flex items-start">
                  <span className="text-blue-400 mr-2">•</span>
                  Click refresh to reload data
                </li>
                <li className="flex items-start">
                  <span className="text-blue-400 mr-2">•</span>
                  Nodes auto-arrange using physics simulation
                </li>
              </ul>
            </div>

            {/* API Info Card */}
            <div className="backdrop-blur-lg bg-white/10 border border-white/20 rounded-2xl p-6 shadow-2xl">
              <h3 className="text-lg font-semibold text-white mb-4">API Endpoint</h3>
              <div className="bg-black/30 rounded-lg p-3 border border-white/10">
                <code className="text-green-300 text-sm break-all">
                  GET localhost:8000/api/graph_data
                </code>
              </div>
              <p className="text-blue-200 text-sm mt-3">
                Fetches graph data with nodes and edges from your FastAPI backend
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="text-center mt-12 text-blue-300">
        <p className="opacity-80">cutewels</p>
      </div>
    </div>
  );
};

export default GraphVisualization;