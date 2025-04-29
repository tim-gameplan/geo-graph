#!/usr/bin/env python3
"""
Voronoi Connection Test Runner

This script runs the Voronoi Connection Test SQL script and visualizes the results.
It compares different strategies for connecting terrain grid points to water obstacle boundaries.
"""

import os
import sys
import argparse
import subprocess
import psycopg2
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import matplotlib.colors as mcolors
from datetime import datetime

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run Voronoi Connection Test')
    parser.add_argument('--container', default='geo-graph-db-1',
                        help='Docker container name (default: geo-graph-db-1)')
    parser.add_argument('--output', default='voronoi_connection_test_results.png',
                        help='Output file name (default: voronoi_connection_test_results.png)')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--no-visualization', action='store_true',
                        help='Skip visualization and only run the SQL test')
    return parser.parse_args()

def get_connection_string(container):
    """Get the PostgreSQL connection string for the Docker container."""
    return f"postgresql://postgres:postgres@localhost:5432/postgres"

def run_sql_script(conn_string, script_path, verbose=False):
    """Run the SQL script and return the results."""
    if verbose:
        print(f"Running SQL script: {script_path}")
    
    # Run the SQL script using psql
    cmd = [
        "psql",
        conn_string,
        "-f", script_path,
        "-v", "ON_ERROR_STOP=1"
    ]
    
    if not verbose:
        cmd.append("-q")  # Quiet mode
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if verbose:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running SQL script: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False

def fetch_data(conn_string):
    """Fetch the test data and results from the database."""
    conn = psycopg2.connect(conn_string)
    try:
        # Fetch water obstacles
        water_obstacles = pd.read_sql(
            "SELECT id, ST_AsText(geom) AS geom FROM test_water_obstacles",
            conn
        )
        
        # Fetch terrain points
        terrain_points = pd.read_sql(
            "SELECT id, hex_type, ST_AsText(geom) AS geom FROM test_terrain_points",
            conn
        )
        
        # Fetch boundary nodes
        boundary_nodes = pd.read_sql(
            "SELECT id, water_obstacle_id, ST_AsText(geom) AS geom FROM test_boundary_nodes",
            conn
        )
        
        # Fetch connection results
        nearest_neighbor = pd.read_sql(
            """
            SELECT 
                nnc.terrain_point_id, 
                nnc.boundary_node_id, 
                nnc.distance,
                ST_AsText((SELECT geom FROM test_terrain_points WHERE id = nnc.terrain_point_id)) AS terrain_point_geom,
                ST_AsText((SELECT geom FROM test_boundary_nodes WHERE id = nnc.boundary_node_id)) AS boundary_node_geom
            FROM 
                nearest_neighbor_connections nnc
            """,
            conn
        )
        
        buffer_based_voronoi = pd.read_sql(
            """
            SELECT 
                bbvc.terrain_point_id, 
                bbvc.boundary_node_id, 
                bbvc.distance,
                ST_AsText((SELECT geom FROM test_terrain_points WHERE id = bbvc.terrain_point_id)) AS terrain_point_geom,
                ST_AsText((SELECT geom FROM test_boundary_nodes WHERE id = bbvc.boundary_node_id)) AS boundary_node_geom,
                ST_AsText(bbvc.voronoi_cell) AS voronoi_cell
            FROM 
                buffer_based_voronoi_connections bbvc
            """,
            conn
        )
        
        true_voronoi = pd.read_sql(
            """
            SELECT 
                tvc.terrain_point_id, 
                tvc.boundary_node_id, 
                tvc.distance,
                ST_AsText((SELECT geom FROM test_terrain_points WHERE id = tvc.terrain_point_id)) AS terrain_point_geom,
                ST_AsText((SELECT geom FROM test_boundary_nodes WHERE id = tvc.boundary_node_id)) AS boundary_node_geom,
                ST_AsText(tvc.voronoi_cell) AS voronoi_cell
            FROM 
                true_voronoi_connections tvc
            """,
            conn
        )
        
        reversed_voronoi = pd.read_sql(
            """
            SELECT 
                rvc.terrain_point_id, 
                rvc.boundary_node_id, 
                rvc.distance,
                ST_AsText((SELECT geom FROM test_terrain_points WHERE id = rvc.terrain_point_id)) AS terrain_point_geom,
                ST_AsText((SELECT geom FROM test_boundary_nodes WHERE id = rvc.boundary_node_id)) AS boundary_node_geom,
                ST_AsText(rvc.voronoi_cell) AS voronoi_cell
            FROM 
                reversed_voronoi_connections rvc
            """,
            conn
        )
        
        # Fetch metrics
        metrics = pd.read_sql(
            "SELECT * FROM connection_metrics ORDER BY evenness_score DESC",
            conn
        )
        
        return {
            'water_obstacles': water_obstacles,
            'terrain_points': terrain_points,
            'boundary_nodes': boundary_nodes,
            'nearest_neighbor': nearest_neighbor,
            'buffer_based_voronoi': buffer_based_voronoi,
            'true_voronoi': true_voronoi,
            'reversed_voronoi': reversed_voronoi,
            'metrics': metrics
        }
    finally:
        conn.close()

def parse_wkt(wkt):
    """Parse WKT geometry into coordinates."""
    if wkt.startswith('POINT'):
        # Extract coordinates from POINT(x y)
        coords_str = wkt.replace('POINT(', '').replace(')', '')
        x, y = map(float, coords_str.split())
        return (x, y)
    elif wkt.startswith('POLYGON'):
        # Extract coordinates from POLYGON((x1 y1, x2 y2, ...))
        coords_str = wkt.replace('POLYGON((', '').replace('))', '')
        coords = []
        for point_str in coords_str.split(','):
            x, y = map(float, point_str.strip().split())
            coords.append((x, y))
        return coords
    else:
        raise ValueError(f"Unsupported WKT geometry: {wkt}")

def visualize_results(data, output_file, verbose=False):
    """Visualize the test results."""
    if verbose:
        print("Visualizing results...")
    
    # Create a figure with 2x2 subplots
    fig, axs = plt.subplots(2, 2, figsize=(20, 20))
    fig.suptitle('Voronoi Connection Strategy Comparison', fontsize=16)
    
    # Define strategies and their corresponding data and axes
    strategies = [
        ('Nearest Neighbor', data['nearest_neighbor'], axs[0, 0]),
        ('Buffer-Based Voronoi', data['buffer_based_voronoi'], axs[0, 1]),
        ('True Voronoi', data['true_voronoi'], axs[1, 0]),
        ('Reversed Voronoi', data['reversed_voronoi'], axs[1, 1])
    ]
    
    # Plot each strategy
    for strategy_name, strategy_data, ax in strategies:
        # Set title
        ax.set_title(strategy_name)
        
        # Plot water obstacles
        for _, row in data['water_obstacles'].iterrows():
            coords = parse_wkt(row['geom'])
            polygon = Polygon(coords, closed=True, fill=True, alpha=0.2, color='blue')
            ax.add_patch(polygon)
        
        # Plot terrain points
        for _, row in data['terrain_points'].iterrows():
            x, y = parse_wkt(row['geom'])
            if row['hex_type'] == 'boundary':
                ax.plot(x, y, 'go', markersize=4)  # Green for boundary
            elif row['hex_type'] == 'land':
                ax.plot(x, y, 'yo', markersize=2)  # Yellow for land
            else:  # water
                ax.plot(x, y, 'bo', markersize=2)  # Blue for water
        
        # Plot boundary nodes
        for _, row in data['boundary_nodes'].iterrows():
            x, y = parse_wkt(row['geom'])
            ax.plot(x, y, 'ro', markersize=3)  # Red for boundary nodes
        
        # Plot connections
        for _, row in strategy_data.iterrows():
            terrain_point = parse_wkt(row['terrain_point_geom'])
            boundary_node = parse_wkt(row['boundary_node_geom'])
            ax.plot([terrain_point[0], boundary_node[0]], 
                    [terrain_point[1], boundary_node[1]], 
                    'g-', linewidth=0.5, alpha=0.5)
        
        # Plot Voronoi cells if available
        if 'voronoi_cell' in strategy_data.columns:
            # Only plot for Buffer-Based Voronoi, True Voronoi, and Reversed Voronoi
            if strategy_name != 'Nearest Neighbor':
                # Sample a subset of cells to avoid overcrowding
                sample_size = min(20, len(strategy_data))
                sampled_data = strategy_data.sample(sample_size)
                
                for _, row in sampled_data.iterrows():
                    if pd.notna(row['voronoi_cell']):
                        try:
                            coords = parse_wkt(row['voronoi_cell'])
                            polygon = Polygon(coords, closed=True, fill=False, 
                                             edgecolor='purple', linewidth=0.5, alpha=0.3)
                            ax.add_patch(polygon)
                        except Exception as e:
                            if verbose:
                                print(f"Error plotting Voronoi cell: {e}")
        
        # Set equal aspect ratio
        ax.set_aspect('equal')
        
        # Remove axis ticks for cleaner visualization
        ax.set_xticks([])
        ax.set_yticks([])
    
    # Add metrics table
    metrics_df = data['metrics']
    
    # Create a table at the bottom of the figure
    table_data = []
    for _, row in metrics_df.iterrows():
        table_data.append([
            row['strategy'],
            f"{row['connection_count']}",
            f"{row['avg_connection_length']:.2f}",
            f"{row['execution_time_ms']:.2f}",
            f"{row['evenness_score']:.4f}"
        ])
    
    # Add the table
    table = plt.table(
        cellText=table_data,
        colLabels=['Strategy', 'Connection Count', 'Avg Length', 'Execution Time (ms)', 'Evenness Score'],
        loc='bottom',
        bbox=[0.0, -0.3, 1.0, 0.2]
    )
    
    # Adjust font size
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0, 1, 0.9])
    
    # Save the figure
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    
    if verbose:
        print(f"Visualization saved to: {output_file}")

def main():
    """Main function."""
    args = parse_args()
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set the SQL script path
    sql_script_path = os.path.join(script_dir, 'voronoi_connection_test.sql')
    
    # Set the output file path
    output_file = os.path.join(script_dir, args.output)
    
    # Get the connection string
    conn_string = get_connection_string(args.container)
    
    # Run the SQL script
    if not run_sql_script(conn_string, sql_script_path, args.verbose):
        sys.exit(1)
    
    # Skip visualization if requested
    if args.no_visualization:
        if args.verbose:
            print("Skipping visualization as requested.")
        return
    
    # Fetch the data
    data = fetch_data(conn_string)
    
    # Visualize the results
    visualize_results(data, output_file, args.verbose)

if __name__ == '__main__':
    main()
