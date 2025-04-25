#!/usr/bin/env python3
"""
Visualize Obstacle Boundary Graph

This script visualizes the obstacle boundary graph created by the create_obstacle_boundary_graph.sql script.
It shows:
- Water obstacle boundaries as graph edges
- Boundary nodes as graph vertices
- Connection edges between terrain grid points and boundary nodes
- Unified graph with terrain edges, boundary edges, and connection edges

Usage:
    python visualize_obstacle_boundary_graph.py [--output OUTPUT] [--show-unified]

Options:
    --output OUTPUT    Output file (default: obstacle_boundary_graph.png)
    --show-unified     Show the unified graph (default: False)
"""

import os
import sys
import argparse
import logging
import subprocess
import tempfile
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.wkt import loads
from pathlib import Path
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('visualize_obstacle_boundary_graph.log')
    ]
)
logger = logging.getLogger('visualize_obstacle_boundary_graph')

# Visualization directory
VISUALIZATION_DIR = Path("epsg3857_pipeline/visualizations")

def run_sql_query(query):
    """Run a SQL query and return the result."""
    # Write to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        temp_file = f.name
        f.write(query)
    
    # Execute the SQL query
    cmd = f'docker exec geo-graph-db-1 psql -U gis -d gis -f /tmp/{os.path.basename(temp_file)} -t -A'
    
    try:
        # Copy the temp file to the Docker container
        copy_cmd = f'docker cp {temp_file} geo-graph-db-1:/tmp/{os.path.basename(temp_file)}'
        subprocess.run(copy_cmd, shell=True, check=True)
        
        # Execute the SQL query
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Clean up
        os.remove(temp_file)
        
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing SQL query: {e}")
        logger.error(f"Error output: {e.stderr}")
        
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        return None

def get_obstacle_boundary_edges():
    """Get the obstacle boundary edges as a GeoDataFrame."""
    query = """
    SELECT 
        edge_id,
        source_node_id,
        target_node_id,
        water_obstacle_id,
        length,
        ST_AsText(geom) AS geom
    FROM 
        obstacle_boundary_edges
    LIMIT 20000;
    """
    
    result = run_sql_query(query)
    if not result:
        return None
    
    # Parse the result
    edges = []
    for line in result.strip().split('\n'):
        if not line:
            continue
        
        parts = line.split('|')
        if len(parts) != 6:
            continue
        
        edge_id, source_node_id, target_node_id, water_obstacle_id, length, geom = parts
        
        edges.append({
            'edge_id': int(edge_id),
            'source_node_id': int(source_node_id),
            'target_node_id': int(target_node_id),
            'water_obstacle_id': int(water_obstacle_id),
            'length': float(length),
            'geometry': loads(geom)
        })
    
    if not edges:
        return None
    
    return gpd.GeoDataFrame(edges, geometry='geometry', crs='EPSG:3857')

def get_obstacle_boundary_nodes():
    """Get the obstacle boundary nodes as a GeoDataFrame."""
    query = """
    SELECT 
        node_id,
        water_obstacle_id,
        point_order,
        ST_AsText(geom) AS geom
    FROM 
        obstacle_boundary_nodes
    LIMIT 20000;
    """
    
    result = run_sql_query(query)
    if not result:
        return None
    
    # Parse the result
    nodes = []
    for line in result.strip().split('\n'):
        if not line:
            continue
        
        parts = line.split('|')
        if len(parts) != 4:
            continue
        
        node_id, water_obstacle_id, point_order, geom = parts
        
        nodes.append({
            'node_id': int(node_id),
            'water_obstacle_id': int(water_obstacle_id),
            'point_order': int(point_order),
            'geometry': loads(geom)
        })
    
    if not nodes:
        return None
    
    return gpd.GeoDataFrame(nodes, geometry='geometry', crs='EPSG:3857')

def get_obstacle_boundary_connection_edges():
    """Get the obstacle boundary connection edges as a GeoDataFrame."""
    query = """
    SELECT 
        edge_id,
        terrain_node_id,
        boundary_node_id,
        water_obstacle_id,
        length,
        ST_AsText(geom) AS geom
    FROM 
        obstacle_boundary_connection_edges
    LIMIT 20000;
    """
    
    result = run_sql_query(query)
    if not result:
        return None
    
    # Parse the result
    edges = []
    for line in result.strip().split('\n'):
        if not line:
            continue
        
        parts = line.split('|')
        if len(parts) != 6:
            continue
        
        edge_id, terrain_node_id, boundary_node_id, water_obstacle_id, length, geom = parts
        
        edges.append({
            'edge_id': int(edge_id),
            'terrain_node_id': int(terrain_node_id),
            'boundary_node_id': int(boundary_node_id),
            'water_obstacle_id': int(water_obstacle_id),
            'length': float(length),
            'geometry': loads(geom)
        })
    
    if not edges:
        return None
    
    return gpd.GeoDataFrame(edges, geometry='geometry', crs='EPSG:3857')

def get_unified_obstacle_edges():
    """Get the unified obstacle edges as a GeoDataFrame."""
    query = """
    SELECT 
        edge_id,
        source_id,
        target_id,
        length,
        cost,
        edge_type,
        speed_factor,
        is_water,
        ST_AsText(geom) AS geom
    FROM 
        unified_obstacle_edges
    LIMIT 50000;
    """
    
    result = run_sql_query(query)
    if not result:
        return None
    
    # Parse the result
    edges = []
    for line in result.strip().split('\n'):
        if not line:
            continue
        
        parts = line.split('|')
        if len(parts) != 9:
            continue
        
        edge_id, source_id, target_id, length, cost, edge_type, speed_factor, is_water, geom = parts
        
        edges.append({
            'edge_id': int(edge_id),
            'source_id': int(source_id),
            'target_id': int(target_id),
            'length': float(length),
            'cost': float(cost),
            'edge_type': edge_type,
            'speed_factor': float(speed_factor),
            'is_water': is_water.lower() == 'true',
            'geometry': loads(geom)
        })
    
    if not edges:
        return None
    
    return gpd.GeoDataFrame(edges, geometry='geometry', crs='EPSG:3857')

def get_terrain_grid_points():
    """Get the terrain grid points as a GeoDataFrame."""
    query = """
    SELECT 
        id,
        ST_AsText(geom) AS geom
    FROM 
        terrain_grid_points
    LIMIT 20000;
    """
    
    result = run_sql_query(query)
    if not result:
        return None
    
    # Parse the result
    points = []
    for line in result.strip().split('\n'):
        if not line:
            continue
        
        parts = line.split('|')
        if len(parts) != 2:
            continue
        
        point_id, geom = parts
        
        points.append({
            'id': int(point_id),
            'geometry': loads(geom)
        })
    
    if not points:
        return None
    
    return gpd.GeoDataFrame(points, geometry='geometry', crs='EPSG:3857')

def get_water_obstacles():
    """Get the water obstacles as a GeoDataFrame."""
    query = """
    SELECT 
        id,
        ST_AsText(geom) AS geom
    FROM 
        water_obstacles
    LIMIT 2000;
    """
    
    result = run_sql_query(query)
    if not result:
        return None
    
    # Parse the result
    obstacles = []
    for line in result.strip().split('\n'):
        if not line:
            continue
        
        parts = line.split('|')
        if len(parts) != 2:
            continue
        
        obstacle_id, geom = parts
        
        obstacles.append({
            'id': int(obstacle_id),
            'geometry': loads(geom)
        })
    
    if not obstacles:
        return None
    
    return gpd.GeoDataFrame(obstacles, geometry='geometry', crs='EPSG:3857')

def get_timestamped_filename(base_filename):
    """Generate a timestamped filename."""
    # Get current timestamp
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H%M")
    
    # Split the base filename into name and extension
    name, ext = os.path.splitext(base_filename)
    
    # Create the timestamped filename
    return f"{timestamp}_{name}{ext}"

def visualize_obstacle_boundary_graph(output_file, show_unified=False):
    """Visualize the obstacle boundary graph."""
    # Ensure the visualization directory exists
    VISUALIZATION_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamped filename
    timestamped_filename = get_timestamped_filename(output_file)
    output_path = VISUALIZATION_DIR / timestamped_filename
    
    # Get the data
    edges = get_obstacle_boundary_edges()
    nodes = get_obstacle_boundary_nodes()
    obstacles = get_water_obstacles()
    
    if edges is None or nodes is None or obstacles is None:
        logger.error("Failed to get data for visualization")
        return False
    
    # Get additional data if showing unified graph
    connection_edges = None
    unified_edges = None
    terrain_points = None
    
    if show_unified:
        connection_edges = get_obstacle_boundary_connection_edges()
        unified_edges = get_unified_obstacle_edges()
        terrain_points = get_terrain_grid_points()
        
        if connection_edges is None or unified_edges is None or terrain_points is None:
            logger.error("Failed to get data for unified graph visualization")
            return False
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Plot the water obstacles
    obstacles.to_crs('EPSG:4326').plot(ax=ax, color='lightblue', alpha=0.5)
    
    if show_unified:
        # Plot the unified edges by type
        terrain_edges = unified_edges[unified_edges['edge_type'] == 'terrain']
        boundary_edges = unified_edges[unified_edges['edge_type'] == 'boundary']
        connection_edges_unified = unified_edges[unified_edges['edge_type'] == 'connection']
        
        # Plot terrain edges
        if not terrain_edges.empty:
            terrain_edges.to_crs('EPSG:4326').plot(ax=ax, color='green', linewidth=0.5, alpha=0.5)
        
        # Plot boundary edges
        if not boundary_edges.empty:
            boundary_edges.to_crs('EPSG:4326').plot(ax=ax, color='blue', linewidth=1)
        
        # Plot connection edges
        if not connection_edges_unified.empty:
            connection_edges_unified.to_crs('EPSG:4326').plot(ax=ax, color='purple', linewidth=0.5)
        
        # Plot terrain points
        terrain_points.to_crs('EPSG:4326').plot(ax=ax, color='green', markersize=2)
    else:
        # Plot the boundary edges
        edges.to_crs('EPSG:4326').plot(ax=ax, color='blue', linewidth=1)
        
        # Plot the connection edges if available
        if connection_edges is not None:
            connection_edges.to_crs('EPSG:4326').plot(ax=ax, color='purple', linewidth=0.5)
    
    # Plot the boundary nodes
    nodes.to_crs('EPSG:4326').plot(ax=ax, color='red', markersize=2)
    
    # Set the title and labels
    title = 'Unified Obstacle Boundary Graph' if show_unified else 'Obstacle Boundary Graph'
    ax.set_title(title)
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    
    # Add a legend
    if show_unified:
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='lightblue', lw=4, alpha=0.5, label='Water Obstacles'),
            Line2D([0], [0], color='blue', lw=2, label='Boundary Edges'),
            Line2D([0], [0], color='purple', lw=1, label='Connection Edges'),
            Line2D([0], [0], color='green', lw=1, alpha=0.5, label='Terrain Edges'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=5, label='Boundary Nodes'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='green', markersize=5, label='Terrain Nodes')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
    else:
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='lightblue', lw=4, alpha=0.5, label='Water Obstacles'),
            Line2D([0], [0], color='blue', lw=2, label='Boundary Edges'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=5, label='Boundary Nodes')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
    
    # Save the plot
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logger.info(f"Visualization saved to {output_path}")
    return True

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Visualize the obstacle boundary graph",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--output",
        default="obstacle_boundary_graph.png",
        help="Output file (default: obstacle_boundary_graph.png)"
    )
    
    parser.add_argument(
        "--show-unified",
        action="store_true",
        help="Show the unified graph (default: False)"
    )
    
    args = parser.parse_args()
    
    # Visualize the obstacle boundary graph
    success = visualize_obstacle_boundary_graph(args.output, args.show_unified)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
