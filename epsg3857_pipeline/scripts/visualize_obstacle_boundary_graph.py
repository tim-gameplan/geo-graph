#!/usr/bin/env python3
"""
Visualize Obstacle Boundary Graph

This script visualizes the obstacle boundary graph created by the create_obstacle_boundary_graph.sql script.
It shows the water obstacle boundaries as graph edges and the boundary nodes as graph vertices.

Usage:
    python visualize_obstacle_boundary_graph.py [--output OUTPUT]

Options:
    --output OUTPUT    Output file (default: obstacle_boundary_graph.png)
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
    LIMIT 10000;
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
    LIMIT 10000;
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

def get_water_obstacles():
    """Get the water obstacles as a GeoDataFrame."""
    query = """
    SELECT 
        id,
        ST_AsText(geom) AS geom
    FROM 
        water_obstacles
    LIMIT 1000;
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

def visualize_obstacle_boundary_graph(output_file):
    """Visualize the obstacle boundary graph."""
    # Get the data
    edges = get_obstacle_boundary_edges()
    nodes = get_obstacle_boundary_nodes()
    obstacles = get_water_obstacles()
    
    if edges is None or nodes is None or obstacles is None:
        logger.error("Failed to get data for visualization")
        return False
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Plot the water obstacles
    obstacles.to_crs('EPSG:4326').plot(ax=ax, color='lightblue', alpha=0.5)
    
    # Plot the edges
    edges.to_crs('EPSG:4326').plot(ax=ax, color='blue', linewidth=1)
    
    # Plot the nodes
    nodes.to_crs('EPSG:4326').plot(ax=ax, color='red', markersize=2)
    
    # Set the title and labels
    ax.set_title('Obstacle Boundary Graph')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    
    # Save the plot
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"Visualization saved to {output_file}")
    
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Visualize Obstacle Boundary Graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--output",
        default="obstacle_boundary_graph.png",
        help="Output file (default: obstacle_boundary_graph.png)"
    )
    
    args = parser.parse_args()
    
    # Visualize the obstacle boundary graph
    if not visualize_obstacle_boundary_graph(args.output):
        logger.error("Failed to visualize the obstacle boundary graph")
        return 1
    
    logger.info("Visualization completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
