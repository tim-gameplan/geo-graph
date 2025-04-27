#!/usr/bin/env python3
"""
Visualize Voronoi Obstacle Boundary Graph

This script visualizes the Voronoi obstacle boundary graph, including:
- Terrain grid points (classified as land, boundary, or water)
- Water obstacles
- Boundary nodes
- Boundary edges
- Connection edges
- Voronoi cells (optional)

The visualization helps understand how the Voronoi partitioning creates
more natural and evenly distributed connections between terrain and water obstacles.
"""

import os
import sys
import time
import logging
import argparse
import subprocess
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path
from datetime import datetime

# Add the parent directory to the path so we can import from core packages
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.utils.logging_utils import setup_logger

# Set up logging
logger = setup_logger('visualize_voronoi_obstacle_boundary')

def run_query(query, container_name='geo-graph-db-1', verbose=False):
    """
    Run a SQL query and return the result.

    Args:
        query (str): SQL query to run
        container_name (str): Name of the Docker container
        verbose (bool): Whether to print verbose output

    Returns:
        str: Query result
    """
    if verbose:
        logger.info(f"Running query: {query}")

    # Write to a temporary file
    temp_file = f"temp_{int(time.time())}.sql"
    with open(temp_file, 'w') as f:
        f.write(query)

    # Copy the file to the container
    copy_cmd = f'docker cp {temp_file} {container_name}:/tmp/'
    try:
        subprocess.run(copy_cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to copy SQL file to container: {e}")
        os.remove(temp_file)
        return None

    # Run the query
    cmd = f'docker exec {container_name} psql -U gis -d gis -f /tmp/{temp_file} -t'
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            logger.error(f"Error executing query: {result.stderr}")
            os.remove(temp_file)
            return None

        # Clean up
        os.remove(temp_file)
        return result.stdout.strip()

    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        os.remove(temp_file)
        return None

def parse_wkt(wkt):
    """
    Parse a WKT geometry string into a list of coordinates.

    Args:
        wkt (str): WKT geometry string

    Returns:
        list: List of coordinates
    """
    if not wkt:
        return []

    # Extract coordinates from WKT
    if wkt.startswith('POINT'):
        # Extract coordinates from POINT(x y)
        coords_str = wkt.replace('POINT(', '').replace(')', '')
        x, y = map(float, coords_str.split())
        return [(x, y)]
    elif wkt.startswith('LINESTRING'):
        # Extract coordinates from LINESTRING(x1 y1, x2 y2, ...)
        coords_str = wkt.replace('LINESTRING(', '').replace(')', '')
        coords = []
        for point_str in coords_str.split(','):
            x, y = map(float, point_str.strip().split())
            coords.append((x, y))
        return coords
    elif wkt.startswith('POLYGON'):
        # Extract coordinates from POLYGON((x1 y1, x2 y2, ...))
        coords_str = wkt.replace('POLYGON((', '').replace('))', '')
        coords = []
        for point_str in coords_str.split(','):
            x, y = map(float, point_str.strip().split())
            coords.append((x, y))
        return coords
    else:
        logger.error(f"Unsupported WKT geometry: {wkt}")
        return []

def visualize_voronoi_obstacle_boundary(container_name='geo-graph-db-1', output=None, show_voronoi=False, verbose=False):
    """
    Visualize the Voronoi obstacle boundary graph.

    Args:
        container_name (str): Name of the Docker container
        output (str): Path to save the visualization
        show_voronoi (bool): Whether to show Voronoi cells
        verbose (bool): Whether to print verbose output

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Fetching data for visualization...")

    # Fetch terrain grid points
    terrain_query = """
    SELECT 
        id, 
        ST_AsText(geom) AS geom,
        hex_type
    FROM 
        terrain_grid_points
    """
    terrain_result = run_query(terrain_query, container_name, verbose)
    if not terrain_result:
        logger.error("Failed to fetch terrain grid points")
        return False

    # Fetch water obstacles
    water_query = """
    SELECT 
        id, 
        ST_AsText(ST_ExteriorRing(geom)) AS geom
    FROM 
        water_obstacles
    """
    water_result = run_query(water_query, container_name, verbose)
    if not water_result:
        logger.error("Failed to fetch water obstacles")
        return False

    # Fetch boundary nodes
    boundary_nodes_query = """
    SELECT 
        node_id, 
        ST_AsText(geom) AS geom
    FROM 
        obstacle_boundary_nodes
    """
    boundary_nodes_result = run_query(boundary_nodes_query, container_name, verbose)
    if not boundary_nodes_result:
        logger.error("Failed to fetch boundary nodes")
        return False

    # Fetch boundary edges
    boundary_edges_query = """
    SELECT 
        edge_id, 
        source_id,
        target_id,
        ST_AsText(geom) AS geom
    FROM 
        obstacle_boundary_edges
    """
    boundary_edges_result = run_query(boundary_edges_query, container_name, verbose)
    if not boundary_edges_result:
        logger.error("Failed to fetch boundary edges")
        return False

    # Fetch connection edges
    connection_edges_query = """
    SELECT 
        edge_id, 
        source_id,
        target_id,
        ST_AsText(geom) AS geom
    FROM 
        obstacle_boundary_connection_edges
    """
    connection_edges_result = run_query(connection_edges_query, container_name, verbose)
    if not connection_edges_result:
        logger.warning("No connection edges found or failed to fetch them")
        connection_edges_result = ""

    # Fetch Voronoi cells if requested
    voronoi_cells_result = None
    if show_voronoi:
        voronoi_cells_query = """
        SELECT 
            cell_id,
            node_id,
            ST_AsText(cell_geom) AS geom
        FROM 
            voronoi_cells
        """
        voronoi_cells_result = run_query(voronoi_cells_query, container_name, verbose)
        if not voronoi_cells_result:
            logger.warning("No Voronoi cells found or failed to fetch them")
            voronoi_cells_result = ""

    # Parse the results
    terrain_points = {'land': [], 'boundary': [], 'water': []}
    for line in terrain_result.splitlines():
        if not line.strip():
            continue
        parts = line.strip().split('|')
        if len(parts) >= 3:
            id = parts[0].strip()
            geom = parts[1].strip()
            hex_type = parts[2].strip()
            coords = parse_wkt(geom)
            if coords:
                terrain_points[hex_type].append(coords[0])

    water_obstacles = []
    for line in water_result.splitlines():
        if not line.strip():
            continue
        parts = line.strip().split('|')
        if len(parts) >= 2:
            water_id = parts[0].strip()
            geom = parts[1].strip()
            coords = parse_wkt(geom)
            if coords:
                water_obstacles.append(coords)

    boundary_nodes = []
    for line in boundary_nodes_result.splitlines():
        if not line.strip():
            continue
        parts = line.strip().split('|')
        if len(parts) >= 2:
            node_id = parts[0].strip()
            geom = parts[1].strip()
            coords = parse_wkt(geom)
            if coords:
                boundary_nodes.append(coords[0])

    boundary_edges = []
    for line in boundary_edges_result.splitlines():
        if not line.strip():
            continue
        parts = line.strip().split('|')
        if len(parts) >= 4:
            edge_id = parts[0].strip()
            source_id = parts[1].strip()
            target_id = parts[2].strip()
            geom = parts[3].strip()
            coords = parse_wkt(geom)
            if coords:
                boundary_edges.append(coords)

    connection_edges = []
    for line in connection_edges_result.splitlines():
        if not line.strip():
            continue
        parts = line.strip().split('|')
        if len(parts) >= 4:
            edge_id = parts[0].strip()
            source_id = parts[1].strip()
            target_id = parts[2].strip()
            geom = parts[3].strip()
            coords = parse_wkt(geom)
            if coords:
                connection_edges.append(coords)

    voronoi_cells = []
    if show_voronoi and voronoi_cells_result:
        for line in voronoi_cells_result.splitlines():
            if not line.strip():
                continue
            parts = line.strip().split('|')
            if len(parts) >= 3:
                cell_id = parts[0].strip()
                node_id = parts[1].strip()
                geom = parts[2].strip()
                coords = parse_wkt(geom)
                if coords:
                    voronoi_cells.append(coords)

    # Create the visualization
    logger.info("Creating visualization...")
    plt.figure(figsize=(12, 10))

    # Plot terrain grid points
    if terrain_points['land']:
        x, y = zip(*terrain_points['land'])
        plt.scatter(x, y, c='green', s=10, alpha=0.7, label='Land')
    if terrain_points['boundary']:
        x, y = zip(*terrain_points['boundary'])
        plt.scatter(x, y, c='orange', s=10, alpha=0.7, label='Boundary')
    if terrain_points['water']:
        x, y = zip(*terrain_points['water'])
        plt.scatter(x, y, c='blue', s=10, alpha=0.7, label='Water')

    # Plot water obstacles
    for obstacle in water_obstacles:
        x, y = zip(*obstacle)
        plt.plot(x, y, 'b-', linewidth=1.5, alpha=0.5)

    # Plot Voronoi cells if requested
    if show_voronoi and voronoi_cells:
        for cell in voronoi_cells:
            x, y = zip(*cell)
            plt.plot(x, y, 'c-', linewidth=0.5, alpha=0.3)

    # Plot boundary nodes
    if boundary_nodes:
        x, y = zip(*boundary_nodes)
        plt.scatter(x, y, c='red', s=20, alpha=0.7, label='Boundary Nodes')

    # Plot boundary edges
    for edge in boundary_edges:
        x, y = zip(*edge)
        plt.plot(x, y, 'r-', linewidth=1.5, alpha=0.7)

    # Plot connection edges
    for edge in connection_edges:
        x, y = zip(*edge)
        plt.plot(x, y, 'y-', linewidth=1, alpha=0.5)

    # Add legend
    legend_elements = [
        mpatches.Patch(color='green', alpha=0.7, label='Land'),
        mpatches.Patch(color='orange', alpha=0.7, label='Boundary'),
        mpatches.Patch(color='blue', alpha=0.7, label='Water'),
        mpatches.Patch(color='red', alpha=0.7, label='Boundary Nodes'),
        mpatches.Patch(color='yellow', alpha=0.7, label='Connection Edges')
    ]
    if show_voronoi:
        legend_elements.append(mpatches.Patch(color='cyan', alpha=0.3, label='Voronoi Cells'))
    
    plt.legend(handles=legend_elements, loc='upper right')

    # Set title and labels
    plt.title('Voronoi Obstacle Boundary Graph')
    plt.xlabel('X Coordinate (EPSG:3857)')
    plt.ylabel('Y Coordinate (EPSG:3857)')

    # Set equal aspect ratio
    plt.axis('equal')

    # Save or show the visualization
    if output:
        plt.savefig(output, dpi=300, bbox_inches='tight')
        logger.info(f"Visualization saved to {output}")
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = f"epsg3857_pipeline/visualizations/{timestamp}_voronoi_obstacle_boundary.png"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        logger.info(f"Visualization saved to {filename}")

    plt.close()
    return True

def main():
    """
    Main function to parse arguments and run the visualization.
    """
    parser = argparse.ArgumentParser(description='Visualize the Voronoi obstacle boundary graph')
    parser.add_argument('--container', default='geo-graph-db-1', help='Name of the Docker container')
    parser.add_argument('--output', help='Path to save the visualization')
    parser.add_argument('--show-voronoi', action='store_true', help='Show Voronoi cells in the visualization')
    parser.add_argument('--verbose', action='store_true', help='Print verbose output')
    
    args = parser.parse_args()
    
    success = visualize_voronoi_obstacle_boundary(
        container_name=args.container,
        output=args.output,
        show_voronoi=args.show_voronoi,
        verbose=args.verbose
    )
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
