#!/usr/bin/env python3
"""
Boundary Hexagon Layer Visualization

This script visualizes the boundary hexagon layer graph, showing the different types of nodes and edges.
"""

import os
import sys
import argparse
import logging
import subprocess
import tempfile
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# Add the parent directory to the path so we can import from core packages
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.utils.logging_utils import setup_logger

# Set up logging
logger = setup_logger('boundary_hexagon_visualize')

def run_sql_query(query, container_name='geo-graph-db-1'):
    """
    Run a SQL query in the Docker container and return the results.
    
    Args:
        query (str): SQL query to run
        container_name (str): Name of the Docker container
    
    Returns:
        list: List of tuples containing the query results
    """
    try:
        # Create a temporary file for the query
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file:
            temp_file.write(query)
            temp_path = temp_file.name
        
        # Copy the file to the container
        copy_cmd = ["docker", "cp", temp_path, f"{container_name}:/tmp/"]
        subprocess.run(copy_cmd, check=True, capture_output=True)
        
        # Run the query in the container
        cmd = [
            "docker", "exec", container_name,
            "psql", "-U", "gis", "-d", "gis", "-t", "-A", "-F", "|", "-f", f"/tmp/{os.path.basename(temp_path)}"
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Parse the results
        lines = result.stdout.strip().split('\n')
        results = []
        for line in lines:
            if line:
                results.append(tuple(line.split('|')))
        
        # Clean up the temporary file
        os.unlink(temp_path)
        
        return results
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running SQL query: {e}")
        logger.error(f"Error output: {e.stderr}")
        return []
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return []

def visualize_boundary_hexagon_layer(output_file=None):
    """
    Visualize the boundary hexagon layer graph.
    
    Args:
        output_file (str): Path to save the visualization image
    """
    try:
        # Query water obstacles
        logger.info("Querying water obstacles...")
        water_obstacles_query = """
        SELECT ST_AsText(geom) FROM water_obstacles;
        """
        water_obstacles = run_sql_query(water_obstacles_query)
        
        # Query terrain grid
        logger.info("Querying terrain grid...")
        terrain_grid_query = """
        SELECT hex_type, ST_AsText(geom) FROM terrain_grid;
        """
        terrain_grid = run_sql_query(terrain_grid_query)
        
        # Query terrain grid points
        logger.info("Querying terrain grid points...")
        terrain_grid_points_query = """
        SELECT hex_type, ST_AsText(geom) FROM terrain_grid_points;
        """
        terrain_grid_points = run_sql_query(terrain_grid_points_query)
        
        # Query boundary nodes
        logger.info("Querying boundary nodes...")
        boundary_nodes_query = """
        SELECT node_type, ST_AsText(geom) FROM unified_boundary_nodes WHERE node_type = 'boundary';
        """
        boundary_nodes = run_sql_query(boundary_nodes_query)
        
        # Query water boundary nodes
        logger.info("Querying water boundary nodes...")
        water_boundary_nodes_query = """
        SELECT node_type, ST_AsText(geom) FROM unified_boundary_nodes WHERE node_type = 'water_boundary';
        """
        water_boundary_nodes = run_sql_query(water_boundary_nodes_query)
        
        # Query unified boundary edges
        logger.info("Querying unified boundary edges...")
        unified_boundary_edges_query = """
        SELECT edge_type, ST_AsText(geom) FROM unified_boundary_edges;
        """
        unified_boundary_edges = run_sql_query(unified_boundary_edges_query)
        
        # Debug the results
        logger.info(f"First few unified boundary edges: {unified_boundary_edges[:5] if unified_boundary_edges else 'None'}")
        
        # If we got no results, try a different query
        if not unified_boundary_edges:
            logger.info("No results from first query, trying a more specific query...")
            unified_boundary_edges_query = """
            SELECT edge_type, ST_AsText(geom) FROM unified_boundary_edges ORDER BY source_id, target_id LIMIT 10;
            """
            unified_boundary_edges = run_sql_query(unified_boundary_edges_query)
            logger.info(f"Results from specific query: {unified_boundary_edges[:5] if unified_boundary_edges else 'None'}")
        
        # Parse the results
        water_obstacles_geoms = []
        for row in water_obstacles:
            wkt = row[0]
            if wkt.startswith('POLYGON') or wkt.startswith('MULTIPOLYGON'):
                water_obstacles_geoms.append(wkt)
        
        terrain_grid_geoms = {'land': [], 'boundary': []}
        for row in terrain_grid:
            hex_type, wkt = row
            if wkt.startswith('POLYGON') or wkt.startswith('MULTIPOLYGON'):
                terrain_grid_geoms[hex_type].append(wkt)
        
        terrain_grid_points_geoms = {'land': [], 'boundary': []}
        for row in terrain_grid_points:
            hex_type, wkt = row
            if wkt.startswith('POINT'):
                terrain_grid_points_geoms[hex_type].append(wkt)
        
        boundary_nodes_geoms = []
        for row in boundary_nodes:
            node_type, wkt = row
            if wkt.startswith('POINT'):
                boundary_nodes_geoms.append(wkt)
        
        water_boundary_nodes_geoms = []
        for row in water_boundary_nodes:
            node_type, wkt = row
            if wkt.startswith('POINT'):
                water_boundary_nodes_geoms.append(wkt)
        
        unified_boundary_edges_geoms = {
            'land_land': [],
            'land_boundary': [],
            'boundary_boundary': [],
            'boundary_water': [],
            'water_boundary': [],
            'connectivity': []
        }
        for row in unified_boundary_edges:
            edge_type, wkt = row
            if wkt.startswith('LINESTRING'):
                if edge_type in unified_boundary_edges_geoms:
                    unified_boundary_edges_geoms[edge_type].append(wkt)
                else:
                    unified_boundary_edges_geoms['connectivity'].append(wkt)
        
        logger.info(f"Got {len(water_obstacles_geoms)} water obstacles")
        logger.info(f"Got {len(terrain_grid_geoms['land'])} land hexagons")
        logger.info(f"Got {len(terrain_grid_geoms['boundary'])} boundary hexagons")
        logger.info(f"Got {len(terrain_grid_points_geoms['land'])} land grid points")
        logger.info(f"Got {len(terrain_grid_points_geoms['boundary'])} boundary grid points")
        logger.info(f"Got {len(boundary_nodes_geoms)} boundary nodes")
        logger.info(f"Got {len(water_boundary_nodes_geoms)} water boundary nodes")
        logger.info(f"Got {len(unified_boundary_edges_geoms['land_land'])} land-land edges")
        logger.info(f"Got {len(unified_boundary_edges_geoms['land_boundary'])} land-boundary edges")
        logger.info(f"Got {len(unified_boundary_edges_geoms['boundary_boundary'])} boundary-boundary edges")
        logger.info(f"Got {len(unified_boundary_edges_geoms['boundary_water'])} boundary-water edges")
        logger.info(f"Got {len(unified_boundary_edges_geoms['water_boundary'])} water-boundary edges")
        logger.info(f"Got {len(unified_boundary_edges_geoms['connectivity'])} connectivity edges")
        
        # Create the visualization
        plt.figure(figsize=(15, 15))
        
        # Plot water obstacles
        for wkt in water_obstacles_geoms:
            coords = parse_wkt_polygon(wkt)
            for polygon in coords:
                plt.fill(polygon[:, 0], polygon[:, 1], color='lightblue', alpha=0.5)
        
        # Plot terrain grid
        for wkt in terrain_grid_geoms['land']:
            coords = parse_wkt_polygon(wkt)
            for polygon in coords:
                plt.fill(polygon[:, 0], polygon[:, 1], color='lightgreen', alpha=0.2)
        
        for wkt in terrain_grid_geoms['boundary']:
            coords = parse_wkt_polygon(wkt)
            for polygon in coords:
                plt.fill(polygon[:, 0], polygon[:, 1], color='yellow', alpha=0.2)
        
        # Plot unified boundary edges
        for wkt in unified_boundary_edges_geoms['land_land']:
            coords = parse_wkt_linestring(wkt)
            plt.plot(coords[:, 0], coords[:, 1], color='black', linewidth=0.5, alpha=0.5)
        
        for wkt in unified_boundary_edges_geoms['land_boundary']:
            coords = parse_wkt_linestring(wkt)
            plt.plot(coords[:, 0], coords[:, 1], color='green', linewidth=0.5, alpha=0.5)
        
        for wkt in unified_boundary_edges_geoms['boundary_boundary']:
            coords = parse_wkt_linestring(wkt)
            plt.plot(coords[:, 0], coords[:, 1], color='orange', linewidth=0.5, alpha=0.5)
        
        for wkt in unified_boundary_edges_geoms['boundary_water']:
            coords = parse_wkt_linestring(wkt)
            plt.plot(coords[:, 0], coords[:, 1], color='blue', linewidth=0.5, alpha=0.5)
        
        for wkt in unified_boundary_edges_geoms['water_boundary']:
            coords = parse_wkt_linestring(wkt)
            plt.plot(coords[:, 0], coords[:, 1], color='purple', linewidth=0.5, alpha=0.5)
        
        for wkt in unified_boundary_edges_geoms['connectivity']:
            coords = parse_wkt_linestring(wkt)
            plt.plot(coords[:, 0], coords[:, 1], color='red', linewidth=0.5, alpha=0.5)
        
        # Plot terrain grid points
        for wkt in terrain_grid_points_geoms['land']:
            coords = parse_wkt_point(wkt)
            plt.scatter(coords[0], coords[1], color='darkgreen', s=5, alpha=0.5)
        
        for wkt in terrain_grid_points_geoms['boundary']:
            coords = parse_wkt_point(wkt)
            plt.scatter(coords[0], coords[1], color='orange', s=5, alpha=0.5)
        
        # Plot boundary nodes
        for wkt in boundary_nodes_geoms:
            coords = parse_wkt_point(wkt)
            plt.scatter(coords[0], coords[1], color='red', s=10, alpha=0.8)
        
        # Plot water boundary nodes
        for wkt in water_boundary_nodes_geoms:
            coords = parse_wkt_point(wkt)
            plt.scatter(coords[0], coords[1], color='blue', s=10, alpha=0.8)
        
        # Add legend
        legend_elements = [
            mpatches.Patch(color='lightblue', alpha=0.5, label='Water Obstacles'),
            mpatches.Patch(color='lightgreen', alpha=0.2, label='Land Hexagons'),
            mpatches.Patch(color='yellow', alpha=0.2, label='Boundary Hexagons'),
            plt.Line2D([0], [0], color='black', linewidth=0.5, alpha=0.5, label='Land-Land Edges'),
            plt.Line2D([0], [0], color='green', linewidth=0.5, alpha=0.5, label='Land-Boundary Edges'),
            plt.Line2D([0], [0], color='orange', linewidth=0.5, alpha=0.5, label='Boundary-Boundary Edges'),
            plt.Line2D([0], [0], color='blue', linewidth=0.5, alpha=0.5, label='Boundary-Water Edges'),
            plt.Line2D([0], [0], color='purple', linewidth=0.5, alpha=0.5, label='Water-Boundary Edges'),
            plt.Line2D([0], [0], color='red', linewidth=0.5, alpha=0.5, label='Connectivity Edges'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='darkgreen', markersize=5, alpha=0.5, label='Land Grid Points'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', markersize=5, alpha=0.5, label='Boundary Grid Points'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=10, alpha=0.8, label='Boundary Nodes'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=10, alpha=0.8, label='Water Boundary Nodes')
        ]
        plt.legend(handles=legend_elements, loc='upper right')
        
        # Set title and labels
        plt.title('Boundary Hexagon Layer Graph')
        plt.xlabel('X')
        plt.ylabel('Y')
        
        # Set equal aspect ratio
        plt.axis('equal')
        
        # Save or show the visualization
        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            logger.info(f"Visualization saved to {output_file}")
        else:
            plt.show()
        
        logger.info("Boundary hexagon layer visualization completed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error visualizing boundary hexagon layer: {str(e)}")
        return False

def parse_wkt_point(wkt):
    """
    Parse a WKT point string into coordinates.
    
    Args:
        wkt (str): WKT point string
    
    Returns:
        numpy.ndarray: Point coordinates
    """
    # Extract coordinates from POINT(x y)
    coords_str = wkt.replace('POINT(', '').replace(')', '')
    coords = [float(x) for x in coords_str.split()]
    return np.array(coords)

def parse_wkt_linestring(wkt):
    """
    Parse a WKT linestring into coordinates.
    
    Args:
        wkt (str): WKT linestring
    
    Returns:
        numpy.ndarray: Line coordinates
    """
    # Extract coordinates from LINESTRING(x1 y1, x2 y2, ...)
    coords_str = wkt.replace('LINESTRING(', '').replace(')', '')
    coords = []
    for point_str in coords_str.split(','):
        point = [float(x) for x in point_str.strip().split()]
        coords.append(point)
    return np.array(coords)

def parse_wkt_polygon(wkt):
    """
    Parse a WKT polygon into coordinates.
    
    Args:
        wkt (str): WKT polygon
    
    Returns:
        list: List of numpy.ndarray polygon coordinates
    """
    try:
        polygons = []
        
        if wkt.startswith('MULTIPOLYGON'):
            # Extract coordinates from MULTIPOLYGON(((x1 y1, x2 y2, ...)), ((x1 y1, x2 y2, ...)), ...)
            # First, remove the MULTIPOLYGON( prefix and the trailing )
            wkt = wkt[len('MULTIPOLYGON('):-1]
            
            # Split the string by )),((
            polygon_strings = []
            depth = 0
            start = 0
            for i, char in enumerate(wkt):
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                    if depth == 0 and i < len(wkt) - 1:
                        polygon_strings.append(wkt[start:i+1])
                        start = i + 3  # Skip the )),( characters
            
            # Add the last polygon
            if start < len(wkt):
                polygon_strings.append(wkt[start:])
            
            # Process each polygon
            for polygon_str in polygon_strings:
                # Remove the outer parentheses
                polygon_str = polygon_str[1:-1]
                
                # Process each ring
                ring_strings = []
                depth = 0
                start = 0
                for i, char in enumerate(polygon_str):
                    if char == '(':
                        depth += 1
                        if depth == 1:
                            start = i + 1
                    elif char == ')':
                        depth -= 1
                        if depth == 0:
                            ring_strings.append(polygon_str[start:i])
                
                # Process the outer ring
                if ring_strings:
                    coords = []
                    for point_str in ring_strings[0].split(','):
                        point = [float(x) for x in point_str.strip().split()]
                        coords.append(point)
                    polygons.append(np.array(coords))
        else:
            # Extract coordinates from POLYGON((x1 y1, x2 y2, ...))
            # First, remove the POLYGON(( prefix and the trailing ))
            wkt = wkt[len('POLYGON(('):-2]
            
            # Process the coordinates
            coords = []
            for point_str in wkt.split(','):
                point = [float(x) for x in point_str.strip().split()]
                coords.append(point)
            polygons.append(np.array(coords))
        
        return polygons
    except Exception as e:
        logger.error(f"Error parsing WKT polygon: {e}")
        logger.error(f"WKT: {wkt}")
        return []

def main():
    """
    Main function to parse arguments and run the visualization.
    """
    parser = argparse.ArgumentParser(description='Visualize the boundary hexagon layer graph')
    parser.add_argument('--output', type=str, default='boundary_hexagon_layer.png',
                        help='Path to save the visualization image')
    parser.add_argument('--container', type=str, default='geo-graph-db-1',
                        help='Name of the Docker container')
    
    args = parser.parse_args()
    
    # Run the visualization
    success = visualize_boundary_hexagon_layer(args.output)
    
    # Return exit code
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
