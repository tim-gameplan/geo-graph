#!/usr/bin/env python3
"""
Graph Visualization Script

This script visualizes the terrain graph, water obstacles, and Delaunay triangulation.
"""

import os
import sys
import argparse
import subprocess
import json
from pathlib import Path
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from pyproj import Transformer
import matplotlib.colors as mcolors

# Add the parent directory to the path so we can import from sibling packages
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import our logging utility
from core.utils.logging_utils import get_logger

# Configure logging
logger = get_logger('visualize')

def run_sql_query(query):
    """Run a SQL query and return the results."""
    logger.info(f"Running SQL query: {query}")
    
    # Use docker exec to run psql inside the container
    cmd = [
        "docker", "exec", "geo-graph-db-1",
        "psql",
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
        logger.debug(f"Output: {result.stdout}")
        if result.stderr:
            logger.debug(f"Error output: {result.stderr}")
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing SQL query: {e.stderr}")
        return []

def visualize_graphml(input_file, output_file=None, dpi=300):
    """Visualize a GraphML file."""
    logger.info(f"Visualizing GraphML file: {input_file}")
    
    # Load the graph
    G = nx.read_graphml(input_file)
    
    # Extract node positions
    pos = {}
    for node, data in G.nodes(data=True):
        if 'x_4326' in data and 'y_4326' in data:
            pos[node] = (float(data['x_4326']), float(data['y_4326']))
    
    # Create a figure
    plt.figure(figsize=(12, 10))
    
    # Draw edges by type
    edge_types = set(nx.get_edge_attributes(G, 'edge_type').values())
    
    # Define colors for edge types
    colors = {
        'terrain': 'green',
        'water': 'blue'
    }
    
    # Draw edges by type
    for edge_type in edge_types:
        edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('edge_type') == edge_type]
        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=edges,
            edge_color=colors.get(edge_type, 'gray'),
            alpha=0.7,
            width=1.5
        )
    
    # Draw nodes
    nx.draw_networkx_nodes(
        G,
        pos,
        node_size=20,
        node_color='red',
        alpha=0.7
    )
    
    # Add a legend
    legend_elements = [
        plt.Line2D([0], [0], color=colors.get(edge_type, 'gray'), lw=2, label=edge_type)
        for edge_type in edge_types
    ]
    legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=8, label='Node'))
    
    plt.legend(handles=legend_elements, loc='best')
    
    # Set the title
    plt.title(f"Graph Visualization: {input_file}")
    
    # Remove axis
    plt.axis('off')
    
    # Save the figure
    if output_file:
        plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
        logger.info(f"Visualization saved to {output_file}")
    else:
        output_file = f"{os.path.splitext(input_file)[0]}_visualization.png"
        plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
        logger.info(f"Visualization saved to {output_file}")
    
    # Show the figure
    plt.show()
    
    return True

def visualize_water_obstacles(output_file=None, dpi=300):
    """Visualize water obstacles."""
    logger.info("Visualizing water obstacles")
    
    # Get water obstacles
    water_obstacles_query = """
    SELECT id, ST_AsText(ST_Transform(geom, 4326))
    FROM water_obstacles
    """
    
    water_obstacles_rows = run_sql_query(water_obstacles_query)
    
    if not water_obstacles_rows:
        logger.error("No water obstacles found")
        return False
    
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
        
        # Parse WKT
        if geom_wkt.startswith('POLYGON'):
            # Extract coordinates from POLYGON WKT
            coords_str = geom_wkt.replace('POLYGON((', '').replace('))', '')
            coords = [
                [float(x) for x in point.split()]
                for point in coords_str.split(',')
            ]
            
            water_obstacles.append({
                'id': obstacle_id,
                'coords': coords
            })
    
    # Create a figure
    plt.figure(figsize=(12, 10))
    
    # Draw water obstacles
    for obstacle in water_obstacles:
        coords = np.array(obstacle['coords'])
        plt.fill(coords[:, 0], coords[:, 1], color='blue', alpha=0.5)
    
    # Set the title
    plt.title("Water Obstacles Visualization")
    
    # Save the figure
    if output_file:
        plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
        logger.info(f"Visualization saved to {output_file}")
    else:
        output_file = "water_obstacles_visualization.png"
        plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
        logger.info(f"Visualization saved to {output_file}")
    
    # Show the figure
    plt.show()
    
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Visualize the terrain graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Visualize a GraphML file
  python visualize.py --mode graphml --input graph_slice.graphml
  
  # Visualize water obstacles
  python visualize.py --mode water
"""
    )
    
    # Visualization options
    parser.add_argument(
        "--mode",
        choices=["graphml", "water"],
        default="graphml",
        help="Visualization mode"
    )
    parser.add_argument(
        "--input",
        help="Input GraphML file (required for graphml mode)"
    )
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
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set verbose logging if requested
    if args.verbose:
        logger.setLevel('DEBUG')
    
    # Visualize based on mode
    if args.mode == "graphml":
        if not args.input:
            logger.error("Input GraphML file is required for graphml mode")
            return 1
        
        if not visualize_graphml(args.input, args.output, args.dpi):
            logger.error("Failed to visualize GraphML file")
            return 1
    elif args.mode == "water":
        if not visualize_water_obstacles(args.output, args.dpi):
            logger.error("Failed to visualize water obstacles")
            return 1
    else:
        logger.error(f"Unknown visualization mode: {args.mode}")
        return 1
    
    logger.info("Visualization completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
