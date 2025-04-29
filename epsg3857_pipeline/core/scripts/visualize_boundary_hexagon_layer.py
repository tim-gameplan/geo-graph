#!/usr/bin/env python3
"""
Boundary Hexagon Layer Visualization

This script visualizes the boundary hexagon layer graph, showing the different types of nodes and edges,
including water boundary nodes, bridge nodes, and the enhanced connections between them.
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
logger = setup_logger('visualize_boundary_hexagon_layer')

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

    try:
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
            # Handle POLYGON format more robustly
            # Extract the outer ring coordinates (first set of parentheses)
            if '((' in wkt and '))' in wkt:
                # Extract content between the first (( and the matching ))
                outer_ring = wkt[wkt.find('((') + 2:wkt.rfind('))')]
                
                # If there are multiple rings (holes), take only the first one
                if '),(' in outer_ring:
                    outer_ring = outer_ring.split('),(')[0]
                
                coords = []
                for point_str in outer_ring.split(','):
                    try:
                        parts = point_str.strip().split()
                        if len(parts) >= 2:
                            x, y = float(parts[0]), float(parts[1])
                            coords.append((x, y))
                    except ValueError as e:
                        logger.warning(f"Error parsing point coordinates: {point_str} - {e}")
                        continue
                
                return geometry_type, coords
            else:
                logger.warning(f"Invalid POLYGON format: {wkt}")
                return None, []
        else:
            logger.warning(f"Unsupported geometry type: {geometry_type}")
            return None, []
    except Exception as e:
        logger.warning(f"Error parsing WKT: {wkt} - {e}")
        return None, []

def visualize_boundary_hexagon_layer(output_file=None, container_name='geo-graph-db-1', verbose=False):
    """
    Visualize the boundary hexagon layer pipeline results.

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
    ax.set_title('Boundary Hexagon Layer Visualization')

    # Get terrain grid data
    logger.info("Getting terrain grid data...")
    terrain_grid_wkts = get_geometry_data('terrain_grid', where_clause="hex_type = 'land'", container_name=container_name)
    boundary_grid_wkts = get_geometry_data('terrain_grid', where_clause="hex_type = 'boundary'", container_name=container_name)
    boundary_extension_wkts = get_geometry_data('terrain_grid', where_clause="hex_type = 'boundary_extension'", container_name=container_name)
    water_with_land_wkts = get_geometry_data('terrain_grid', where_clause="hex_type = 'water_with_land'", container_name=container_name)
    
    # Get water hexagons from classified_hex_grid
    water_grid_wkts = get_geometry_data('classified_hex_grid', where_clause="hex_type = 'water'", container_name=container_name)

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
            
    # Plot boundary extension grid
    for wkt in boundary_extension_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'POLYGON':
            polygon = patches.Polygon(coords, fill=True, alpha=0.2, edgecolor='yellow', facecolor='yellow')
            ax.add_patch(polygon)
            
    # Plot water with land grid
    for wkt in water_with_land_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'POLYGON':
            polygon = patches.Polygon(coords, fill=True, alpha=0.2, edgecolor='cyan', facecolor='cyan')
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

    # Get boundary nodes data
    logger.info("Getting boundary nodes data...")
    boundary_nodes_wkts = get_geometry_data('unified_boundary_nodes', where_clause="node_type = 'boundary'", container_name=container_name)

    # Plot boundary nodes
    for wkt in boundary_nodes_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'POINT' and coords:
            x, y = coords[0]
            ax.plot(x, y, 'ro', markersize=3)
            
    # Get water boundary nodes data
    logger.info("Getting water boundary nodes data...")
    water_boundary_nodes_wkts = get_geometry_data('unified_boundary_nodes', where_clause="node_type = 'water_boundary'", container_name=container_name)

    # Plot water boundary nodes
    for wkt in water_boundary_nodes_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'POINT' and coords:
            x, y = coords[0]
            ax.plot(x, y, 'bo', markersize=3)
            
    # Get bridge nodes data
    logger.info("Getting bridge nodes data...")
    bridge_nodes_wkts = get_geometry_data('unified_boundary_nodes', where_clause="node_type = 'bridge'", container_name=container_name)

    # Plot bridge nodes
    for wkt in bridge_nodes_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'POINT' and coords:
            x, y = coords[0]
            ax.plot(x, y, 'mo', markersize=5, markeredgecolor='black')

    # Get unified boundary edges data - split by type for better visualization
    logger.info("Getting unified boundary edges data...")
    
    # Land-land edges
    land_land_edges_wkts = get_geometry_data('unified_boundary_edges', where_clause="edge_type = 'land_land'", container_name=container_name)
    for wkt in land_land_edges_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'LINESTRING':
            xs, ys = zip(*coords)
            ax.plot(xs, ys, 'g-', linewidth=0.5, alpha=0.3)
    
    # Land-boundary edges
    land_boundary_edges_wkts = get_geometry_data('unified_boundary_edges', where_clause="edge_type = 'land_boundary'", container_name=container_name)
    for wkt in land_boundary_edges_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'LINESTRING':
            xs, ys = zip(*coords)
            ax.plot(xs, ys, color='orange', linestyle='-', linewidth=0.5, alpha=0.3)
    
    # Boundary-boundary edges
    boundary_boundary_edges_wkts = get_geometry_data('unified_boundary_edges', where_clause="edge_type = 'boundary_boundary'", container_name=container_name)
    for wkt in boundary_boundary_edges_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'LINESTRING':
            xs, ys = zip(*coords)
            ax.plot(xs, ys, 'r-', linewidth=0.7, alpha=0.5)

    # Get water boundary edges data - split by type for better visualization
    logger.info("Getting water boundary edges data...")
    
    # Boundary-water edges
    boundary_water_edges_wkts = get_geometry_data('unified_boundary_edges', where_clause="edge_type = 'boundary_water'", container_name=container_name)
    for wkt in boundary_water_edges_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'LINESTRING':
            xs, ys = zip(*coords)
            ax.plot(xs, ys, color='teal', linestyle='-', linewidth=0.7, alpha=0.5)
    
    # Water-boundary edges
    water_boundary_edges_wkts = get_geometry_data('unified_boundary_edges', where_clause="edge_type = 'water_boundary'", container_name=container_name)
    for wkt in water_boundary_edges_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'LINESTRING':
            xs, ys = zip(*coords)
            ax.plot(xs, ys, 'b-', linewidth=0.7, alpha=0.5)
    
    # Water-boundary-to-boundary edges
    water_boundary_to_boundary_edges_wkts = get_geometry_data('unified_boundary_edges', where_clause="edge_type = 'water_boundary_to_boundary'", container_name=container_name)
    for wkt in water_boundary_to_boundary_edges_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'LINESTRING':
            xs, ys = zip(*coords)
            ax.plot(xs, ys, color='cyan', linestyle='-', linewidth=0.7, alpha=0.5)
            
    # Get bridge edges data
    logger.info("Getting bridge edges data...")
    bridge_edges_wkts = get_geometry_data('unified_boundary_edges', where_clause="edge_type = 'bridge_to_boundary'", container_name=container_name)

    # Plot bridge edges
    for wkt in bridge_edges_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'LINESTRING':
            xs, ys = zip(*coords)
            ax.plot(xs, ys, 'm-', linewidth=1, alpha=0.5)

    # Get terrain grid points data
    logger.info("Getting terrain grid points data...")
    terrain_grid_points_wkts = get_geometry_data('terrain_grid_points', where_clause="hex_type = 'land'", container_name=container_name)

    # Plot terrain grid points
    for wkt in terrain_grid_points_wkts:
        geom_type, coords = parse_wkt(wkt)
        if geom_type == 'POINT' and coords:
            x, y = coords[0]
            ax.plot(x, y, 'go', markersize=3)

    # Add legend for nodes
    ax.plot([], [], 'go', markersize=6, label='Terrain Grid Points')
    ax.plot([], [], 'ro', markersize=6, label='Boundary Nodes')
    ax.plot([], [], 'bo', markersize=6, label='Water Boundary Nodes')
    ax.plot([], [], 'mo', markersize=6, markeredgecolor='black', label='Bridge Nodes')
    
    # Add legend for edges
    ax.plot([], [], 'g-', linewidth=2, alpha=0.6, label='Land-Land Edges')
    ax.plot([], [], color='orange', linestyle='-', linewidth=2, alpha=0.6, label='Land-Boundary Edges')
    ax.plot([], [], 'r-', linewidth=2, alpha=0.6, label='Boundary-Boundary Edges')
    ax.plot([], [], color='teal', linestyle='-', linewidth=2, alpha=0.6, label='Boundary-Water Edges')
    ax.plot([], [], 'b-', linewidth=2, alpha=0.6, label='Water Boundary Edges')
    ax.plot([], [], color='cyan', linestyle='-', linewidth=2, alpha=0.6, label='Water-Boundary-to-Boundary Edges')
    ax.plot([], [], 'm-', linewidth=2, alpha=0.6, label='Bridge Edges')
    
    # Create legend patches for the different hexagon types
    import matplotlib.patches as mpatches
    land_patch = mpatches.Rectangle((0, 0), 1, 1, facecolor='green', alpha=0.2, edgecolor='none')
    boundary_patch = mpatches.Rectangle((0, 0), 1, 1, facecolor='orange', alpha=0.2, edgecolor='none')
    boundary_extension_patch = mpatches.Rectangle((0, 0), 1, 1, facecolor='yellow', alpha=0.2, edgecolor='none')
    water_with_land_patch = mpatches.Rectangle((0, 0), 1, 1, facecolor='cyan', alpha=0.2, edgecolor='none')
    water_patch = mpatches.Rectangle((0, 0), 1, 1, facecolor='blue', alpha=0.2, edgecolor='none')
    water_obstacles_patch = mpatches.Rectangle((0, 0), 1, 1, facecolor='none', edgecolor='blue', linewidth=2)
    
    # Add the patches to the legend
    handles, labels = ax.get_legend_handles_labels()
    handles.extend([land_patch, boundary_patch, boundary_extension_patch, water_with_land_patch, water_patch, water_obstacles_patch])
    labels.extend(['Land Hexagons', 'Boundary Hexagons', 'Boundary Extension Hexagons', 'Water with Land Hexagons', 'Water Hexagons', 'Water Obstacles'])

    # Set axis limits
    ax.autoscale()
    
    # Add legend with all handles and labels
    ax.legend(handles=handles, labels=labels, loc='upper right')

    # Save or show the figure
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"Visualization saved to {output_file}")
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        output_file = f"epsg3857_pipeline/visualizations/{timestamp}_boundary_hexagon_layer.png"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"Visualization saved to {output_file}")

    plt.close()
    return True

def main():
    """
    Main function to parse arguments and run the visualization.
    """
    parser = argparse.ArgumentParser(description='Visualize the boundary hexagon layer pipeline results')
    parser.add_argument('--output', help='Path to save the visualization')
    parser.add_argument('--container', default='geo-graph-db-1', help='Name of the Docker container')
    parser.add_argument('--verbose', action='store_true', help='Print verbose output')

    args = parser.parse_args()

    # Run the visualization
    success = visualize_boundary_hexagon_layer(args.output, args.container, args.verbose)

    # Return exit code
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
