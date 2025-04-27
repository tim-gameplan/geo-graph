#!/usr/bin/env python3
"""
Voronoi Obstacle Boundary Pipeline

This script runs a pipeline that:
1. Creates a hexagonal terrain grid that includes water boundaries
2. Uses the original obstacle boundary approach to create water boundary nodes and edges
3. Generates Voronoi cells for water boundary nodes
4. Connects the terrain grid to the water boundary nodes using Voronoi partitioning
5. Creates a unified graph for navigation

This approach uses Voronoi diagrams to create more natural connections between
terrain and water obstacles, ensuring better coverage and more intuitive navigation.
"""

import os
import sys
import time
import json
import logging
import argparse
import subprocess
from pathlib import Path

# Add the parent directory to the path so we can import from core packages
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.scripts.config_loader_3857 import load_config
from core.utils.logging_utils import setup_logger

# Set up logging
logger = setup_logger('voronoi_obstacle_boundary_pipeline')

def run_sql_file(sql_file, params, container_name='geo-graph-db-1', verbose=False):
    """
    Run a SQL file with parameters.

    Args:
        sql_file (str): Path to the SQL file
        params (dict): Parameters to replace in the SQL file
        container_name (str): Name of the Docker container
        verbose (bool): Whether to print verbose output

    Returns:
        bool: True if successful, False otherwise
    """
    if verbose:
        logger.info(f"Running SQL file: {sql_file}")
        logger.info(f"Parameters: {params}")

    # Read the SQL file
    with open(sql_file, 'r') as f:
        sql = f.read()

    # Replace parameters
    for key, value in params.items():
        placeholder = f":{key}"
        if isinstance(value, str):
            replacement = f"'{value}'"
        else:
            replacement = str(value)
        sql = sql.replace(placeholder, replacement)

    # Write to a temporary file
    temp_file = f"temp_{int(time.time())}.sql"
    with open(temp_file, 'w') as f:
        f.write(sql)

    # Run the SQL file
    cmd = f'docker exec {container_name} psql -U gis -d gis -f /tmp/{temp_file}'
    
    # Copy the file to the container
    copy_cmd = f'docker cp {temp_file} {container_name}:/tmp/'
    try:
        subprocess.run(copy_cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to copy SQL file to container: {e}")
        os.remove(temp_file)
        return False

    # Execute the SQL
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Error executing {sql_file}: {result.stderr}")
            os.remove(temp_file)
            return False
        
        if verbose:
            logger.info(f"SQL output: {result.stdout}")
        
        elapsed_time = time.time() - start_time
        logger.info(f"✅ SQL file {sql_file} executed successfully in {elapsed_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error executing {sql_file}: {str(e)}")
        os.remove(temp_file)
        return False

    # Clean up
    os.remove(temp_file)
    return True

def run_command(cmd, verbose=False):
    """
    Run a command and return the result.

    Args:
        cmd (str): Command to run
        verbose (bool): Whether to print verbose output

    Returns:
        bool: True if successful, False otherwise
    """
    if verbose:
        logger.info(f"Running command: {cmd}")

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            logger.error(f"❌ Command failed: {cmd}")
            logger.error(f"Error output: {result.stderr}")
            return False

        elapsed_time = time.time() - start_time
        logger.info(f"✅ Command completed successfully in {elapsed_time:.2f} seconds")
        
        if verbose:
            logger.info(f"Command output: {result.stdout}")
            
        return True

    except Exception as e:
        logger.error(f"❌ Command failed with exception: {str(e)}")
        return False

def run_pipeline(config_file, sql_dir, container_name='geo-graph-db-1', verbose=False):
    """
    Run the Voronoi obstacle boundary pipeline.

    Args:
        config_file (str): Path to the configuration file
        sql_dir (str): Path to the directory containing SQL files
        container_name (str): Name of the Docker container
        verbose (bool): Whether to print verbose output

    Returns:
        bool: True if successful, False otherwise
    """
    # Load configuration
    config_loader = load_config(config_file)
    if not config_loader:
        logger.error(f"Failed to load configuration from {config_file}")
        return False

    # Use the config_loader's get_sql_params method to get all parameters
    params = config_loader.get_sql_params()
    
    # Add additional parameters from the obstacle_boundary section
    obstacle_boundary = config_loader.config.get('obstacle_boundary', {})
    params['boundary_node_spacing'] = obstacle_boundary.get('boundary_node_spacing', 100)
    params['boundary_edge_max_length'] = obstacle_boundary.get('boundary_edge_max_length', 200)
    params['max_connection_distance'] = obstacle_boundary.get('connection_distance', 1000)
    params['max_connections_per_boundary_node'] = obstacle_boundary.get('max_connections_per_boundary_node', 5)
    params['max_connections_per_terrain_point'] = obstacle_boundary.get('max_connections_per_terrain_point', 2)
    params['node_tolerance'] = obstacle_boundary.get('node_tolerance', 10)
    
    # Add Voronoi-specific parameters
    voronoi_connection = config_loader.config.get('voronoi_connection', {})
    params['voronoi_buffer_distance'] = voronoi_connection.get('voronoi_buffer_distance', 500)
    params['voronoi_max_distance'] = voronoi_connection.get('voronoi_max_distance', 1000)
    params['voronoi_connection_limit'] = voronoi_connection.get('voronoi_connection_limit', 2)
    params['voronoi_tolerance'] = voronoi_connection.get('voronoi_tolerance', 10)

    # Define SQL files to run
    sql_files = [
        os.path.join(sql_dir, '01_extract_water_features_3857.sql'),
        os.path.join(sql_dir, '02_create_water_buffers_3857.sql'),
        os.path.join(sql_dir, '03_dissolve_water_buffers_3857.sql'),
        os.path.join(sql_dir, '04_create_terrain_grid_hexagon.sql'),
        os.path.join(sql_dir, '05_create_terrain_edges_3857.sql')  # Add terrain edges creation
    ]
    
    # Run the SQL files
    for sql_file in sql_files:
        if not run_sql_file(sql_file, params, container_name, verbose):
            logger.error(f"Failed to run SQL file: {sql_file}")
            return False
    
    # Run the Voronoi obstacle boundary graph creation
    voronoi_boundary_sql = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'obstacle_boundary', 'create_voronoi_obstacle_boundary_graph.sql')
    if not run_sql_file(voronoi_boundary_sql, params, container_name, verbose):
        logger.error(f"Failed to run Voronoi obstacle boundary graph creation")
        return False
    
    logger.info("✅ Voronoi obstacle boundary pipeline completed successfully")
    return True

def main():
    """
    Main function to parse arguments and run the pipeline.
    """
    parser = argparse.ArgumentParser(description='Run the Voronoi obstacle boundary pipeline')
    parser.add_argument('--config', default='epsg3857_pipeline/config/voronoi_obstacle_boundary_config.json', help='Path to the configuration file')
    parser.add_argument('--sql-dir', default='epsg3857_pipeline/core/sql', help='Path to the directory containing SQL files')
    parser.add_argument('--container', default='geo-graph-db-1', help='Name of the Docker container')
    parser.add_argument('--verbose', action='store_true', help='Print verbose output')
    parser.add_argument('--skip-reset', action='store_true', default=True, help='Skip database reset by default')
    parser.add_argument('--visualize', action='store_true', help='Visualize the results after running the pipeline')
    parser.add_argument('--output', help='Path to save the visualization (only used with --visualize)')
    parser.add_argument('--show-voronoi', action='store_true', help='Show Voronoi cells in the visualization')
    
    args = parser.parse_args()
    
    # Reset the database if not skipped
    if not args.skip_reset:
        logger.info("Resetting the database...")
        reset_cmd = f"python epsg3857_pipeline/tools/database/reset_non_osm_tables.py --confirm"
        if not run_command(reset_cmd, args.verbose):
            logger.error("Failed to reset the database")
            return 1
    
    # Run the pipeline
    success = run_pipeline(args.config, args.sql_dir, args.container, args.verbose)
    
    if success and args.visualize:
        logger.info("Visualizing the results...")
        visualize_cmd = f"python epsg3857_pipeline/core/scripts/visualize_voronoi_obstacle_boundary.py"
        if args.output:
            visualize_cmd += f" --output {args.output}"
        if args.container != 'geo-graph-db-1':
            visualize_cmd += f" --container {args.container}"
        if args.verbose:
            visualize_cmd += " --verbose"
        if args.show_voronoi:
            visualize_cmd += " --show-voronoi"
        
        if not run_command(visualize_cmd, args.verbose):
            logger.error("Failed to visualize the results")
            return 1
        
        logger.info("✅ Visualization completed successfully")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
