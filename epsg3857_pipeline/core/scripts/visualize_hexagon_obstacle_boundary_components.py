#!/usr/bin/env python3
"""
Visualize Hexagon Obstacle Boundary Components

This script visualizes the different components of the hexagon obstacle boundary graph:
1. Terrain grid (hexagons)
2. Terrain edges
3. Obstacle boundary nodes
4. Obstacle boundary edges
5. Connection edges
6. Unified graph

This helps to debug and understand the graph structure.
"""

import os
import sys
import time
import json
import logging
import argparse
import subprocess
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path
from matplotlib.collections import PatchCollection

# Add the parent directory to the path so we can import from core packages
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.utils.logging_utils import setup_logger

# Set up logging
logger = setup_logger('visualize_hexagon_obstacle_boundary_components')

def run_query(query, container_name='geo-graph-db-1'):
    """
    Run a SQL query and return the result.

    Args:
        query (str): SQL query to run
        container_name (str): Name of the Docker container

    Returns:
        str: Query result
    """
    # Write to a temporary file
    temp_file = f"temp_{int(time.time())}.sql"
    with open(temp_file, 'w') as f:
        f.write(query)

    # Copy the file to the container
    copy_cmd = f'docker cp {temp_file} {container_name}:/tmp/'
    subprocess.run(copy_cmd, shell=True, check=True)

    # Run the query
    cmd = f'docker exec {container_name} psql -U gis -d gis -f /tmp/{temp_file} -t'
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Clean up
    os.remove(temp_file)

    if result.returncode != 0:
        logger.error(f"Error executing query: {result.stderr}")
        return None

    return result.stdout

def get_terrain_grid(container_name='geo-graph-db-1'):
    """
    Get the terrain grid data.

    Args:
        container_name (str): Name of the Docker container

    Returns:
        list: List of terrain grid cells
    """
    query = """
    SELECT 
        id, 
        hex_type,
        ST_AsGeoJSON(geom) AS geom
    FROM 
        terrain_grid
    """
    result = run_query(query, container_name)
    if not result:
        return []

    grid_cells = []
    for line in result.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.strip().split('|')
        if len(parts) != 3:
            continue
        
        id = int(parts[0].strip())
        hex_type = parts[1].strip()
        geom = json.loads(parts[2].strip())
        
        grid_cells.append({
            'id': id,
            'hex_type': hex_type,
            'geom': geom
        })
    
    return grid_cells

def get_terrain_edges(container_name='geo-graph-db-1'):
    """
    Get the terrain edges data.

    Args:
        container_name (str): Name of the Docker container

    Returns:
        list: List of terrain edges
    """
    query = """
    SELECT 
        edge_id, 
        source_id,
        target_id,
        source_type,
        target_type,
        ST_AsGeoJSON(geom) AS geom
    FROM 
        terrain_edges
    """
    result = run_query(query, container_name)
    if not result:
        return []

    edges = []
    for line in result.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.strip().split('|')
        if len(parts) != 6:
            continue
        
        edge_id = int(parts[0].strip())
        source_id = int(parts[1].strip())
        target_id = int(parts[2].strip())
        source_type = parts[3].strip()
        target_type = parts[4].strip()
        geom = json.loads(parts[5].strip())
        
        edges.append({
            'edge_id': edge_id,
            'source_id': source_id,
            'target_id': target_id,
            'source_type': source_type,
            'target_type': target_type,
            'geom': geom
        })
    
    return edges

def get_boundary_nodes(container_name='geo-graph-db-1'):
    """
    Get the obstacle boundary nodes data.

    Args:
        container_name (str): Name of the Docker container

    Returns:
        list: List of obstacle boundary nodes
    """
    query = """
    SELECT 
        node_id, 
        water_obstacle_id,
        ST_AsGeoJSON(geom) AS geom
    FROM 
        obstacle_boundary_nodes
    """
    result = run_query(query, container_name)
    if not result:
        return []

    nodes = []
    for line in result.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.strip().split('|')
        if len(parts) != 3:
            continue
        
        node_id = int(parts[0].strip())
        water_obstacle_id = int(parts[1].strip())
        geom = json.loads(parts[2].strip())
        
        nodes.append({
            'node_id': node_id,
            'water_obstacle_id': water_obstacle_id,
            'geom': geom
        })
    
    return nodes

def get_boundary_edges(container_name='geo-graph-db-1'):
    """
    Get the obstacle boundary edges data.

    Args:
        container_name (str): Name of the Docker container

    Returns:
        list: List of obstacle boundary edges
    """
    query = """
    SELECT 
        edge_id, 
        source_node_id,
        target_node_id,
        water_obstacle_id,
        ST_AsGeoJSON(geom) AS geom
    FROM 
        obstacle_boundary_edges
    """
    result = run_query(query, container_name)
    if not result:
        return []

    edges = []
    for line in result.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.strip().split('|')
        if len(parts) != 5:
            continue
        
        edge_id = int(parts[0].strip())
        source_node_id = int(parts[1].strip())
        target_node_id = int(parts[2].strip())
        water_obstacle_id = int(parts[3].strip())
        geom = json.loads(parts[4].strip())
        
        edges.append({
            'edge_id': edge_id,
            'source_node_id': source_node_id,
            'target_node_id': target_node_id,
            'water_obstacle_id': water_obstacle_id,
            'geom': geom
        })
    
    return edges

def get_connection_edges(container_name='geo-graph-db-1'):
    """
    Get the obstacle boundary connection edges data.

    Args:
        container_name (str): Name of the Docker container

    Returns:
        list: List of obstacle boundary connection edges
    """
    query = """
    SELECT 
        edge_id, 
        terrain_node_id,
        boundary_node_id,
        water_obstacle_id,
        ST_AsGeoJSON(geom) AS geom
    FROM 
        obstacle_boundary_connection_edges
    """
    result = run_query(query, container_name)
    if not result:
        return []

    edges = []
    for line in result.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.strip().split('|')
        if len(parts) != 5:
            continue
        
        edge_id = int(parts[0].strip())
        terrain_node_id = int(parts[1].strip())
        boundary_node_id = int(parts[2].strip())
        water_obstacle_id = int(parts[3].strip())
        geom = json.loads(parts[4].strip())
        
        edges.append({
            'edge_id': edge_id,
            'terrain_node_id': terrain_node_id,
            'boundary_node_id': boundary_node_id,
            'water_obstacle_id': water_obstacle_id,
            'geom': geom
        })
    
    return edges

def get_unified_edges(container_name='geo-graph-db-1'):
    """
    Get the unified obstacle edges data.

    Args:
        container_name (str): Name of the Docker container

    Returns:
        list: List of unified obstacle edges
    """
    query = """
    SELECT 
        edge_id, 
        source_id,
        target_id,
        edge_type,
        is_water,
        ST_AsGeoJSON(geom) AS geom
    FROM 
        unified_obstacle_edges
    """
    result = run_query(query, container_name)
    if not result:
        return []

    edges = []
    for line in result.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.strip().split('|')
        if len(parts) != 6:
            continue
        
        edge_id = int(parts[0].strip())
        source_id = int(parts[1].strip())
        target_id = int(parts[2].strip())
        edge_type = parts[3].strip()
        is_water = parts[4].strip() == 't'
        geom = json.loads(parts[5].strip())
        
        edges.append({
            'edge_id': edge_id,
            'source_id': source_id,
            'target_id': target_id,
            'edge_type': edge_type,
            'is_water': is_water,
            'geom': geom
        })
    
    return edges

def get_terrain_grid_points(container_name='geo-graph-db-1'):
    """
    Get the terrain grid points data.

    Args:
        container_name (str): Name of the Docker container

    Returns:
        list: List of terrain grid points
    """
    query = """
    SELECT 
        id, 
        hex_type,
        ST_AsGeoJSON(geom) AS geom
    FROM 
        terrain_grid_points
    """
    result = run_query(query, container_name)
    if not result:
        return []

    points = []
    for line in result.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.strip().split('|')
        if len(parts) != 3:
            continue
        
        id = int(parts[0].strip())
        hex_type = parts[1].strip()
        geom = json.loads(parts[2].strip())
        
        points.append({
            'id': id,
            'hex_type': hex_type,
            'geom': geom
        })
    
    return points

def get_data_bounds(grid_cells):
    """
    Get the bounds of the data.

    Args:
        grid_cells (list): List of terrain grid cells

    Returns:
        tuple: (min_x, min_y, max_x, max_y)
    """
    if not grid_cells:
        return (0, 0, 1, 1)
    
    min_x = float('inf')
    min_y = float('inf')
    max_x = float('-inf')
    max_y = float('-inf')
    
    for cell in grid_cells:
        coords = cell['geom']['coordinates'][0]
        for coord in coords:
            min_x = min(min_x, coord[0])
            min_y = min(min_y, coord[1])
            max_x = max(max_x, coord[0])
            max_y = max(max_y, coord[1])
    
    return (min_x, min_y, max_x, max_y)

def visualize_components(container_name='geo-graph-db-1', output=None, verbose=False):
    """
    Visualize the hexagon obstacle boundary components.

    Args:
        container_name (str): Name of the Docker container
        output (str): Path to save the visualization
        verbose (bool): Whether to print verbose output

    Returns:
        bool: True if successful, False otherwise
    """
    # Get the data
    if verbose:
        logger.info("Getting terrain grid data...")
    grid_cells = get_terrain_grid(container_name)
    if not grid_cells:
        logger.error("Failed to get terrain grid data")
        return False
    
    if verbose:
        logger.info("Getting terrain grid points data...")
    grid_points = get_terrain_grid_points(container_name)
    if not grid_points:
        logger.error("Failed to get terrain grid points data")
        return False
    
    if verbose:
        logger.info("Getting terrain edges data...")
    terrain_edges = get_terrain_edges(container_name)
    if verbose:
        logger.info(f"Found {len(terrain_edges)} terrain edges")
    
    if verbose:
        logger.info("Getting boundary nodes data...")
    boundary_nodes = get_boundary_nodes(container_name)
    if not boundary_nodes:
        logger.error("Failed to get boundary nodes data")
        return False
    
    if verbose:
        logger.info("Getting boundary edges data...")
    boundary_edges = get_boundary_edges(container_name)
    if not boundary_edges:
        logger.error("Failed to get boundary edges data")
        return False
    
    if verbose:
        logger.info("Getting connection edges data...")
    connection_edges = get_connection_edges(container_name)
    if verbose:
        logger.info(f"Found {len(connection_edges)} connection edges")
    
    if verbose:
        logger.info("Getting unified edges data...")
    unified_edges = get_unified_edges(container_name)
    if not unified_edges:
        logger.error("Failed to get unified edges data")
        return False
    
    # Get the bounds of the data
    bounds = get_data_bounds(grid_cells)
    
    # Create the figure
    fig, axs = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Hexagon Obstacle Boundary Components', fontsize=16)
    
    # Plot the terrain grid
    ax = axs[0, 0]
    ax.set_title('Terrain Grid')
    
    for cell in grid_cells:
        coords = cell['geom']['coordinates'][0]
        polygon = patches.Polygon(coords, closed=True, alpha=0.5)
        if cell['hex_type'] == 'water':
            polygon.set_facecolor('lightblue')
        elif cell['hex_type'] == 'boundary':
            polygon.set_facecolor('lightgreen')
        else:
            polygon.set_facecolor('lavender')
        ax.add_patch(polygon)
    
    for point in grid_points:
        coords = point['geom']['coordinates']
        if point['hex_type'] == 'water':
            ax.plot(coords[0], coords[1], 'bo', markersize=2)
        elif point['hex_type'] == 'boundary':
            ax.plot(coords[0], coords[1], 'go', markersize=2)
        else:
            ax.plot(coords[0], coords[1], 'yo', markersize=2)
    
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])
    
    # Plot the terrain edges
    ax = axs[0, 1]
    ax.set_title('Terrain Edges')
    
    for cell in grid_cells:
        coords = cell['geom']['coordinates'][0]
        polygon = patches.Polygon(coords, closed=True, alpha=0.2)
        if cell['hex_type'] == 'water':
            polygon.set_facecolor('lightblue')
        elif cell['hex_type'] == 'boundary':
            polygon.set_facecolor('lightgreen')
        else:
            polygon.set_facecolor('lavender')
        ax.add_patch(polygon)
    
    # Count edges per hexagon to verify we have ~6 per hexagon (typical for hexagonal grid)
    edges_per_hexagon = {}
    for edge in terrain_edges:
        source_id = edge['source_id']
        target_id = edge['target_id']
        edges_per_hexagon[source_id] = edges_per_hexagon.get(source_id, 0) + 1
        edges_per_hexagon[target_id] = edges_per_hexagon.get(target_id, 0) + 1
    
    # Calculate average edges per hexagon
    total_edges = sum(edges_per_hexagon.values()) / 2  # Each edge is counted twice
    total_hexagons = len(edges_per_hexagon)
    avg_edges_per_hexagon = total_edges / total_hexagons if total_hexagons > 0 else 0
    
    # Add the average to the title
    ax.set_title(f'Terrain Edges (Avg: {avg_edges_per_hexagon:.2f} per hexagon)')
    
    for edge in terrain_edges:
        coords = edge['geom']['coordinates']
        x = [coords[0][0], coords[1][0]]
        y = [coords[0][1], coords[1][1]]
        if edge['source_type'] == 'water' or edge['target_type'] == 'water':
            ax.plot(x, y, 'b-', linewidth=1)
        elif edge['source_type'] == 'boundary' and edge['target_type'] == 'boundary':
            ax.plot(x, y, 'g-', linewidth=1)
        else:
            ax.plot(x, y, 'r-', linewidth=1)
    
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])
    
    # Plot the boundary nodes and edges
    ax = axs[0, 2]
    ax.set_title('Boundary Nodes and Edges')
    
    for cell in grid_cells:
        coords = cell['geom']['coordinates'][0]
        polygon = patches.Polygon(coords, closed=True, alpha=0.2)
        if cell['hex_type'] == 'water':
            polygon.set_facecolor('lightblue')
        elif cell['hex_type'] == 'boundary':
            polygon.set_facecolor('lightgreen')
        else:
            polygon.set_facecolor('lavender')
        ax.add_patch(polygon)
    
    for node in boundary_nodes:
        coords = node['geom']['coordinates']
        ax.plot(coords[0], coords[1], 'ro', markersize=2)
    
    for edge in boundary_edges:
        coords = edge['geom']['coordinates']
        x = [coords[0][0], coords[1][0]]
        y = [coords[0][1], coords[1][1]]
        ax.plot(x, y, 'r-', linewidth=1)
    
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])
    
    # Plot the connection edges
    ax = axs[1, 0]
    ax.set_title('Connection Edges')
    
    for cell in grid_cells:
        coords = cell['geom']['coordinates'][0]
        polygon = patches.Polygon(coords, closed=True, alpha=0.2)
        if cell['hex_type'] == 'water':
            polygon.set_facecolor('lightblue')
        elif cell['hex_type'] == 'boundary':
            polygon.set_facecolor('lightgreen')
        else:
            polygon.set_facecolor('lavender')
        ax.add_patch(polygon)
    
    for edge in connection_edges:
        coords = edge['geom']['coordinates']
        x = [coords[0][0], coords[1][0]]
        y = [coords[0][1], coords[1][1]]
        ax.plot(x, y, 'g--', linewidth=1)
    
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])
    
    # Plot the unified edges
    ax = axs[1, 1]
    ax.set_title('Unified Edges')
    
    for cell in grid_cells:
        coords = cell['geom']['coordinates'][0]
        polygon = patches.Polygon(coords, closed=True, alpha=0.2)
        if cell['hex_type'] == 'water':
            polygon.set_facecolor('lightblue')
        elif cell['hex_type'] == 'boundary':
            polygon.set_facecolor('lightgreen')
        else:
            polygon.set_facecolor('lavender')
        ax.add_patch(polygon)
    
    for edge in unified_edges:
        coords = edge['geom']['coordinates']
        x = [coords[0][0], coords[1][0]]
        y = [coords[0][1], coords[1][1]]
        if edge['edge_type'] == 'terrain':
            ax.plot(x, y, 'r-', linewidth=1)
        elif edge['edge_type'] == 'boundary':
            ax.plot(x, y, 'b-', linewidth=1)
        else:  # connection
            ax.plot(x, y, 'g--', linewidth=1)
    
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])
    
    # Plot the unified edges by type
    ax = axs[1, 2]
    ax.set_title('Unified Edges by Type')
    
    for cell in grid_cells:
        coords = cell['geom']['coordinates'][0]
        polygon = patches.Polygon(coords, closed=True, alpha=0.2)
        if cell['hex_type'] == 'water':
            polygon.set_facecolor('lightblue')
        elif cell['hex_type'] == 'boundary':
            polygon.set_facecolor('lightgreen')
        else:
            polygon.set_facecolor('lavender')
        ax.add_patch(polygon)
    
    # Plot terrain edges
    terrain_edges_list = [edge for edge in unified_edges if edge['edge_type'] == 'terrain']
    for edge in terrain_edges_list:
        coords = edge['geom']['coordinates']
        x = [coords[0][0], coords[1][0]]
        y = [coords[0][1], coords[1][1]]
        ax.plot(x, y, 'r-', linewidth=1, alpha=0.5)
    
    # Plot boundary edges
    boundary_edges_list = [edge for edge in unified_edges if edge['edge_type'] == 'boundary']
    for edge in boundary_edges_list:
        coords = edge['geom']['coordinates']
        x = [coords[0][0], coords[1][0]]
        y = [coords[0][1], coords[1][1]]
        ax.plot(x, y, 'b-', linewidth=1)
    
    # Plot connection edges
    connection_edges_list = [edge for edge in unified_edges if edge['edge_type'] == 'connection']
    for edge in connection_edges_list:
        coords = edge['geom']['coordinates']
        x = [coords[0][0], coords[1][0]]
        y = [coords[0][1], coords[1][1]]
        ax.plot(x, y, 'g--', linewidth=1)
    
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])
    
    # Add a legend
    fig.legend(
        [
            patches.Patch(facecolor='lightblue', alpha=0.5),
            patches.Patch(facecolor='lightgreen', alpha=0.5),
            patches.Patch(facecolor='lavender', alpha=0.5),
            plt.Line2D([0], [0], color='r', linestyle='-'),
            plt.Line2D([0], [0], color='b', linestyle='-'),
            plt.Line2D([0], [0], color='g', linestyle='--')
        ],
        [
            'Water Hexagons',
            'Boundary Hexagons',
            'Land Hexagons',
            'Terrain Edges',
            'Boundary Edges',
            'Connection Edges'
        ],
        loc='lower center',
        ncol=6
    )
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    # Save the figure
    if output:
        plt.savefig(output, dpi=300, bbox_inches='tight')
        logger.info(f"Visualization saved to {output}")
    else:
        plt.show()
    
    return True

def main():
    """
    Main function to parse arguments and run the visualization.
    """
    parser = argparse.ArgumentParser(description='Visualize hexagon obstacle boundary components')
    parser.add_argument('--container', default='geo-graph-db-1', help='Name of the Docker container')
    parser.add_argument('--output', help='Path to save the visualization')
    parser.add_argument('--verbose', action='store_true', help='Print verbose output')
    
    args = parser.parse_args()
    
    success = visualize_components(args.container, args.output, args.verbose)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
