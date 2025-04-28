#!/usr/bin/env python3
"""
Reversed Voronoi Obstacle Boundary Pipeline

This script runs a pipeline that:
1. Creates a hexagonal terrain grid that includes water boundaries
2. Uses the original obstacle boundary approach to create water boundary nodes and edges
3. Generates Voronoi cells for boundary terrain points (instead of boundary nodes)
4. Connects the terrain grid to the water boundary nodes using reversed Voronoi partitioning
5. Creates a unified graph for navigation

The "reversed" approach creates Voronoi cells for boundary terrain points instead of boundary nodes,
which can lead to more natural connections and better distribution of connections across the water boundary.
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
from core.utils.voronoi_utils import create_voronoi_preprocessing_function, apply_voronoi_preprocessing_to_pipeline

# Set up logging
logger = setup_logger('reversed_voronoi_obstacle_boundary_pipeline')

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

def setup_database_connection(container_name='geo-graph-db-1'):
    """
    Set up a connection to the PostgreSQL database.

    Args:
        container_name (str): Name of the Docker container

    Returns:
        connection: Database connection object or None if connection failed
    """
    import psycopg2
    
    try:
        # Get the container's IP address
        cmd = f"docker inspect -f '{{{{.NetworkSettings.IPAddress}}}}' {container_name}"
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to get container IP: {result.stderr}")
            return None
        
        container_ip = result.stdout.strip()
        
        # If the IP is empty, try to get the host port mapping
        if not container_ip:
            cmd = f"docker port {container_name} 5432/tcp"
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to get container port mapping: {result.stderr}")
                return None
            
            # The output is like "0.0.0.0:49153"
            host_port = result.stdout.strip().split(':')[1]
            connection = psycopg2.connect(
                dbname="gis",
                user="gis",
                password="gis",
                host="localhost",
                port=host_port
            )
        else:
            # Connect using the container's IP
            connection = psycopg2.connect(
                dbname="gis",
                user="gis",
                password="gis",
                host=container_ip
            )
        
        logger.info("✅ Connected to the database")
        return connection
        
    except Exception as e:
        logger.error(f"Failed to connect to the database: {str(e)}")
        return None

def run_pipeline(config_file, sql_dir, container_name='geo-graph-db-1', verbose=False, use_robust_voronoi=True):
    """
    Run the Reversed Voronoi obstacle boundary pipeline.

    Args:
        config_file (str): Path to the configuration file
        sql_dir (str): Path to the directory containing SQL files
        container_name (str): Name of the Docker container
        verbose (bool): Whether to print verbose output
        use_robust_voronoi (bool): Whether to use robust Voronoi diagram generation

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
    
    # Add Voronoi preprocessing parameters
    voronoi_preprocessing = config_loader.config.get('voronoi_preprocessing', {})
    params['voronoi_preprocessing_tolerance'] = voronoi_preprocessing.get('tolerance', 0.1)
    params['voronoi_preprocessing_envelope_expansion'] = voronoi_preprocessing.get('envelope_expansion', 100)
    params['voronoi_preprocessing_add_jitter'] = 'TRUE' if voronoi_preprocessing.get('add_jitter', False) else 'FALSE'
    params['voronoi_preprocessing_jitter_amount'] = voronoi_preprocessing.get('jitter_amount', 0.01)
    params['voronoi_preprocessing_enable_fallback'] = 'TRUE' if voronoi_preprocessing.get('enable_fallback', True) else 'FALSE'
    params['voronoi_preprocessing_use_combined_approach'] = 'TRUE' if voronoi_preprocessing.get('use_combined_approach', True) else 'FALSE'
    
    # Add parameters for robust Voronoi generation
    params['voronoi_preprocessing_use_robust_voronoi'] = 'TRUE' if use_robust_voronoi else 'FALSE'
    params['voronoi_preprocessing_max_points_per_chunk'] = voronoi_preprocessing.get('max_points_per_chunk', 5000)
    params['voronoi_preprocessing_chunk_overlap'] = voronoi_preprocessing.get('chunk_overlap', 50)

    # Set up database connection for voronoi_utils
    conn = setup_database_connection(container_name)
    if not conn:
        logger.error("Failed to set up database connection")
        return False
    
    # Create Voronoi preprocessing functions in the database
    try:
        logger.info("Creating Voronoi preprocessing functions in the database...")
        create_voronoi_preprocessing_function(conn)
        logger.info("✅ Voronoi preprocessing functions created successfully")
    except Exception as e:
        logger.error(f"Failed to create Voronoi preprocessing functions: {str(e)}")
        conn.close()
        return False
    
    # Apply Voronoi preprocessing to the pipeline if using robust Voronoi
    if use_robust_voronoi:
        try:
            logger.info("Applying Voronoi preprocessing to the pipeline...")
            preprocessing_params = apply_voronoi_preprocessing_to_pipeline(conn, config_loader.config)
            logger.info(f"✅ Voronoi preprocessing applied with parameters: {preprocessing_params}")
        except Exception as e:
            logger.error(f"Failed to apply Voronoi preprocessing: {str(e)}")
            conn.close()
            return False
    
    # Close the database connection
    conn.close()

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
    
    # Run the Reversed Voronoi obstacle boundary graph creation
    reversed_voronoi_boundary_sql = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'obstacle_boundary', 'create_reversed_voronoi_obstacle_boundary_graph.sql')
    if not run_sql_file(reversed_voronoi_boundary_sql, params, container_name, verbose):
        logger.error(f"Failed to run Reversed Voronoi obstacle boundary graph creation")
        return False
    
    logger.info("✅ Reversed Voronoi obstacle boundary pipeline completed successfully")
    return True

def main():
    """
    Main function to parse arguments and run the pipeline.
    """
    parser = argparse.ArgumentParser(description='Run the Reversed Voronoi obstacle boundary pipeline')
    parser.add_argument('--config', default='epsg3857_pipeline/config/voronoi_obstacle_boundary_config.json', help='Path to the configuration file')
    parser.add_argument('--sql-dir', default='epsg3857_pipeline/core/sql', help='Path to the directory containing SQL files')
    parser.add_argument('--container', default='geo-graph-db-1', help='Name of the Docker container')
    parser.add_argument('--verbose', action='store_true', help='Print verbose output')
    parser.add_argument('--skip-reset', action='store_true', default=True, help='Skip database reset by default')
    parser.add_argument('--visualize', action='store_true', help='Visualize the results after running the pipeline')
    parser.add_argument('--output', help='Path to save the visualization (only used with --visualize)')
    parser.add_argument('--show-voronoi', action='store_true', help='Show Voronoi cells in the visualization')
    parser.add_argument('--use-robust-voronoi', action='store_true', default=True, help='Use robust Voronoi diagram generation (default: True)')
    
    args = parser.parse_args()
    
    # Reset the database if not skipped
    if not args.skip_reset:
        logger.info("Resetting the database...")
        reset_cmd = f"python epsg3857_pipeline/tools/database/reset_non_osm_tables.py --confirm"
        if not run_command(reset_cmd, args.verbose):
            logger.error("Failed to reset the database")
            return 1
    
    # Run the pipeline
    success = run_pipeline(
        args.config, 
        args.sql_dir, 
        args.container, 
        args.verbose, 
        args.use_robust_voronoi
    )
    
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
