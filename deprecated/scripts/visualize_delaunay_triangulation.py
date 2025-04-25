#!/usr/bin/env python3
"""
Delaunay Triangulation Visualization Script

This script visualizes the Delaunay triangulation used in the EPSG:3857 pipeline.
"""

import os
import sys
import argparse
import logging
import subprocess
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from pyproj import Transformer
import matplotlib.colors as mcolors
from matplotlib.collections import LineCollection, PolyCollection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('visualize_delaunay.log')
    ]
)
logger = logging.getLogger('visualize_delaunay')

def run_sql_query(query):
    """Run a SQL query and return the results."""
    logger.info(f"Running SQL query: {query}")
    
    cmd = [
        "psql",
        "-h", "localhost",
        "-U", "gis",
        "-d", "gis",
        "-t",  # Tuple only, no header
        "-A",  # Unaligned output
        "-c", query
    ]
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"SQL query executed successfully")
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing SQL query: {e.stderr}")
        return []

def parse_wkt_polygon(wkt):
    """Parse a WKT polygon string into a list of coordinates."""
    if wkt.startswith('POLYGON'):
        # Extract coordinates from POLYGON WKT
        coords_str = wkt.replace('POLYGON((', '').replace('))', '')
        coords = [
            [float(x) for x in point.split()]
            for point in coords_str.split(',')
        ]
        return coords
    return None

def parse_wkt_linestring(wkt):
    """Parse a WKT linestring string into a list of coordinates."""
    if wkt.startswith('LINESTRING'):
        # Extract coordinates from LINESTRING WKT
        coords_str = wkt.replace('LINESTRING(', '').replace(')', '')
        coords = [
            [float(x) for x in point.split()]
            for point in coords_str.split(',')
        ]
        return coords
    return None

def visualize_delaunay_triangulation(output_file=None, dpi=300):
    """Visualize Delaunay triangulation."""
    logger.info("Visualizing Delaunay triangulation")
    
    # Get Delaunay triangles
    triangles_query = """
    SELECT id, ST_AsText(ST_Transform(geom, 4326))
    FROM delaunay_triangles
    """
    
    triangles_rows = run_sql_query(triangles_query)
    
    if not triangles_rows:
        logger.error("No Delaunay triangles found")
        return False
    
    # Parse triangles
    triangles = []
    for row in triangles_rows:
        if not row:
            continue
        
        parts = row.split('|')
        if len(parts) < 2:
            continue
        
        triangle_id = int(parts[0])
        geom_wkt = parts[1]
        
        coords = parse_wkt_polygon(geom_wkt)
        if coords:
            triangles.append({
                'id': triangle_id,
                'coords': coords
            })
    
    # Get Delaunay edges
    edges_query = """
    SELECT id, ST_AsText(ST_Transform(geom, 4326))
    FROM delaunay_edges
    """
    
    edges_rows = run_sql_query(edges_query)
    
    # Parse edges
    edges = []
    for row in edges_rows:
        if not row:
            continue
        
        parts = row.split('|')
        if len(parts) < 2:
            continue
        
        edge_id = int(parts[0])
        geom_wkt = parts[1]
        
        coords = parse_wkt_linestring(geom_wkt)
        if coords:
            edges.append({
                'id': edge_id,
                'coords': coords
            })
    
    # Get water obstacles
    water_obstacles_query = """
    SELECT id, ST_AsText(ST_Transform(geom, 4326))
    FROM water_obstacles
    """
    
    water_obstacles_rows = run_sql_query(water_obstacles_query)
    
    # Parse water obstacles
    water_obstacles = []
    for row in water_obstacles_rows:
        if not row:
            continue
        
        parts = row.split('|')
        if len(parts) < 2:
            continue
        
        obstacle_id = int(parts[0])
        geom_wkt = parts[1]
        
        coords = parse_wkt_polygon(geom_wkt)
        if coords:
            water_obstacles.append({
                'id': obstacle_id,
                'coords': coords
            })
    
    # Create a figure
    plt.figure(figsize=(12, 10))
    
    # Draw triangles
    triangle_patches = []
    for triangle in triangles:
        triangle_patches.append(np.array(triangle['coords']))
    
    if triangle_patches:
        collection = PolyCollection(
            triangle_patches,
            facecolor='lightgreen',
            edgecolor='green',
            alpha=0.3
        )
        plt.gca().add_collection(collection)
    
    # Draw edges
    edge_segments = []
    for edge in edges:
        edge_segments.append(np.array(edge['coords']))
    
    if edge_segments:
        collection = LineCollection(
            edge_segments,
            colors='blue',
            linewidths=1.5,
            alpha=0.7
        )
        plt.gca().add_collection(collection)
    
    # Draw water obstacles
    for obstacle in water_obstacles:
        coords = np.array(obstacle['coords'])
        plt.fill(coords[:, 0], coords[:, 1], color='blue', alpha=0.5)
    
    # Set the title
    plt.title("Delaunay Triangulation Visualization")
    
    # Set axis limits
    if triangle_patches:
        all_coords = np.vstack([patch for patch in triangle_patches])
        min_x, max_x = all_coords[:, 0].min(), all_coords[:, 0].max()
        min_y, max_y = all_coords[:, 1].min(), all_coords[:, 1].max()
        plt.xlim(min_x - 0.01, max_x + 0.01)
        plt.ylim(min_y - 0.01, max_y + 0.01)
    
    # Add a legend
    legend_elements = [
        plt.Line2D([0], [0], color='green', lw=2, label='Delaunay Edge'),
        plt.Patch(facecolor='lightgreen', edgecolor='green', alpha=0.3, label='Delaunay Triangle'),
        plt.Patch(facecolor='blue', alpha=0.5, label='Water Obstacle')
    ]
    
    plt.legend(handles=legend_elements, loc='best')
    
    # Save the figure
    if output_file:
        plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
        logger.info(f"Visualization saved to {output_file}")
    else:
        output_file = "delaunay_triangulation_visualization.png"
        plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
        logger.info(f"Visualization saved to {output_file}")
    
    # Show the figure
    plt.show()
    
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Visualize Delaunay triangulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Visualize Delaunay triangulation
  python visualize_delaunay_triangulation.py
  
  # Visualize Delaunay triangulation with custom output file
  python visualize_delaunay_triangulation.py --output delaunay.png
"""
    )
    
    # Visualization options
    parser.add_argument(
        "--output",
        help="Output image file"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI for output image"
    )
    
    args = parser.parse_args()
    
    # Visualize Delaunay triangulation
    if not visualize_delaunay_triangulation(args.output, args.dpi):
        logger.error("Failed to visualize Delaunay triangulation")
        return 1
    
    logger.info("Visualization completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
