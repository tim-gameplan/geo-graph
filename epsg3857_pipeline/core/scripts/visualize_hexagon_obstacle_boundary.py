#!/usr/bin/env python3
"""
Visualization script for the Hexagon Obstacle Boundary Pipeline.

This script visualizes the results of the hexagon obstacle boundary pipeline,
showing the terrain grid, water obstacles, boundary nodes, and edges.
"""

import os
import sys
import time
import argparse
import subprocess
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
from datetime import datetime

# Add the parent directory to the path so we can import from core packages
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.utils.logging_utils import setup_logger

# Set up logging
logger = setup_logger('visualize_hexagon_obstacle_boundary')

def run_sql_query(query, container_name='geo-graph-db-1', verbose=False):
    """
    Run a SQL query and return the result.

    Args:
        query (str): SQL query to run
        container_name (str): Name of the Docker container
        verbose (bool): Whether to print verbose output

    Returns:
        str: Query result
    """
    # Write the query to a temporary file
    temp_file = f"temp_{int(time.time())}.sql"
    with open(temp_file, 'w') as f:
        f.write(query)

    # Copy the file to the container
    copy_cmd = f'docker cp {temp_file} {container_name}:/tmp/'
    subprocess.run(copy_cmd, shell=True, check=True)

    # Run the query
    cmd = f'docker exec {container_name} psql -U gis -d gis -f /tmp/{temp_file} -t -A'
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Clean up
    os.remove(temp_file)

    if result.returncode != 0:
        logger.error(f"Error executing query: {result.stderr}")
        return ""

    return result.stdout

def get_geometry_data(table_name, geom_column='geom', where_clause='', limit=10000, container_name='geo-graph-db-1'):
    """
    Get geometry data from a table.

    Args:
        table_name (str): Name of the table
        geom_column (str): Name of the geometry column
        where_clause (str): WHERE clause for the query
        limit (int): Maximum number of rows to return
        container_name (str): Name of the Docker container

    Returns:
        list: List of geometry data
    """
    where_sql = f"WHERE {where_clause}" if where_clause else ""
    query = f"""
    SELECT ST_AsText({geom_column}) FROM {table_name} {where_sql} LIMIT {limit};
    """
    result = run_sql_query(query, container_name)
    return result.strip().split('\n')

def parse_wkt(wkt):
    """
    Parse WKT geometry into coordinates.

    Args:
        wkt (str): WKT geometry string

    Returns:
        tuple: (geometry_type, coordinates)
    """
    if not wkt:
        return None, []

    # Extract geometry type
    geometry_type = wkt.split('(')[0].strip()

    # Extract coordinates
    if geometry_type == 'POINT':
        coords_str = wkt.replace('POINT(', '').replace(')', '')
        x, y = map(float, coords_str.split())
        return geometry_type, [(x, y)]
    elif geometry_type == 'LINESTRING':
        coords_str = wkt.replace('LINESTRING(', '').replace(')', '')
        coords = []
        for point_str in coords_str.split(','):
            x, y = map(float, point_str.strip().split())
            coords.append((x, y))
        return geometry_type, coords
    elif geometry_type == 'POLYGON':
        coords_str = wkt.replace('POLYGON((', '').replace('))', '')
        coords = []
        for point_str in coords_str.split(','):
            x, y = map(float, point_str.strip().split())
            coords.append((x, y))
        return geometry_type, coords
    else:
        logger.warning(f"Unsupported geometry type: {geometry_type}")
        return None, []

def visualize_hexagon_obstacle_boundary(output_file=None, container_name='geo-graph-db-1', verbose=False):
    """
    Visualize the hexagon obstacle boundary pipeline results.

    Args:
        output_file (str): Path to save the visualization
        container_name (str): Name of the Docker container
        verbose (bool): Whether to print verbose output

    Returns:
        bool: True if successful, False otherwise
    """
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_aspect('equal')
    ax.set_title('Hexagon Obstacle Boundary Pipeline Visualization')

    # Get terrain grid data
    logger.info("Getting terrain grid data...")
    terrain_grid_wkts = get_geometry_data('terrain_grid', where_clause="hex_type = 'land'", container_name=container_name)
    boundary_grid_wkts = get_geometry_data('terrain_grid', where_clause="hex_type = 'boundary'", container_name=container_name)
    water_grid_wkts = get_geometry_data('terrain_grid', where_clause="hex_type = 'water'", container_name=container_name)

    # Plot terrain grid
    for wkt in terrain_grid_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'POLYGON':
            polygon = patches.Polygon(coords, fill=True, alpha=0.2, edgecolor='green', facecolor='green')
            ax.add_patch(polygon)

    # Plot boundary grid
    for wkt in boundary_grid_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'POLYGON':
            polygon = patches.Polygon(coords, fill=True, alpha=0.2, edgecolor='orange', facecolor='orange')
            ax.add_patch(polygon)

    # Plot water grid
    for wkt in water_grid_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'POLYGON':
            polygon = patches.Polygon(coords, fill=True, alpha=0.2, edgecolor='blue', facecolor='blue')
            ax.add_patch(polygon)

    # Get water obstacles data
    logger.info("Getting water obstacles data...")
    water_obstacles_wkts = get_geometry_data('water_obstacles', container_name=container_name)

    # Plot water obstacles
    for wkt in water_obstacles_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'POLYGON':
            polygon = patches.Polygon(coords, fill=False, edgecolor='blue', linewidth=2)
            ax.add_patch(polygon)

    # Get obstacle boundary nodes data
    logger.info("Getting obstacle boundary nodes data...")
    obstacle_boundary_nodes_wkts = get_geometry_data('obstacle_boundary_nodes', container_name=container_name)

    # Plot obstacle boundary nodes
    for wkt in obstacle_boundary_nodes_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'POINT' and coords:
            x, y = coords[0]
            ax.plot(x, y, 'ro', markersize=3)

    # Get obstacle boundary edges data
    logger.info("Getting obstacle boundary edges data...")
    obstacle_boundary_edges_wkts = get_geometry_data('obstacle_boundary_edges', container_name=container_name)

    # Plot obstacle boundary edges
    for wkt in obstacle_boundary_edges_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'LINESTRING':
            xs, ys = zip(*coords)
            ax.plot(xs, ys, 'r-', linewidth=1, alpha=0.5)

    # Get obstacle boundary connection edges data
    logger.info("Getting obstacle boundary connection edges data...")
    connection_edges_wkts = get_geometry_data('obstacle_boundary_connection_edges', container_name=container_name)

    # Plot obstacle boundary connection edges
    for wkt in connection_edges_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'LINESTRING':
            xs, ys = zip(*coords)
            ax.plot(xs, ys, 'g-', linewidth=1, alpha=0.5)

    # Get terrain grid points data
    logger.info("Getting terrain grid points data...")
    terrain_grid_points_wkts = get_geometry_data('terrain_grid_points', where_clause="hex_type = 'land'", container_name=container_name)

    # Plot terrain grid points
    for wkt in terrain_grid_points_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'POINT' and coords:
            x, y = coords[0]
            ax.plot(x, y, 'go', markersize=3)

    # Add legend
    ax.plot([], [], 'go', markersize=6, label='Terrain Grid Points')
    ax.plot([], [], 'ro', markersize=6, label='Obstacle Boundary Nodes')
    ax.plot([], [], 'r-', linewidth=2, label='Obstacle Boundary Edges')
    ax.plot([], [], 'g-', linewidth=2, label='Connection Edges')
    ax.add_patch(patches.Patch(facecolor='green', alpha=0.2, label='Land Hexagons'))
    ax.add_patch(patches.Patch(facecolor='orange', alpha=0.2, label='Boundary Hexagons'))
    ax.add_patch(patches.Patch(facecolor='blue', alpha=0.2, label='Water Hexagons'))
    ax.add_patch(patches.Patch(facecolor='none', edgecolor='blue', linewidth=2, label='Water Obstacles'))

    # Set axis limits
    ax.autoscale()
    
    # Add legend
    ax.legend(loc='upper right')

    # Save or show the figure
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"Visualization saved to {output_file}")
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        output_file = f"epsg3857_pipeline/visualizations/{timestamp}_hexagon_obstacle_boundary.png"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"Visualization saved to {output_file}")

    plt.close()
    return True

def main():
    """
    Main function to parse arguments and run the visualization.
    """
    parser = argparse.ArgumentParser(description='Visualize the hexagon obstacle boundary pipeline results')
    parser.add_argument('--output', help='Path to save the visualization')
    parser.add_argument('--container', default='geo-graph-db-1', help='Name of the Docker container')
    parser.add_argument('--verbose', action='store_true', help='Print verbose output')

    args = parser.parse_args()

    # Run the visualization
    success = visualize_hexagon_obstacle_boundary(args.output, args.container, args.verbose)

    # Return exit code
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
