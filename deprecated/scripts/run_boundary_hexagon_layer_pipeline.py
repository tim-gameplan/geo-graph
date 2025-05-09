#!/usr/bin/env python3
"""
Boundary Hexagon Layer Pipeline Runner

This script runs the water obstacle pipeline with the boundary hexagon layer approach,
which preserves hexagons at water boundaries for better connectivity and uses land portions
of water hexagons to connect boundary nodes to water boundary nodes.
"""

import os
import sys
import json
import argparse
import logging
import subprocess
import time
from pathlib import Path

# Add the parent directory to the path so we can import from core packages
sys.path.append(str(Path(__file__).parent))

from core.utils.logging_utils import setup_logger
from core.scripts.config_loader_3857 import load_config

# Set up logging
logger = setup_logger('boundary_hexagon_layer_pipeline')

def run_sql_script(script_path, params, container_name='geo-graph-db-1', verbose=False):
    """
    Run a SQL script with parameters using psql in a Docker container.
    
    Args:
        script_path (str): Path to the SQL script
        params (dict): Parameters to replace in the SQL script
        container_name (str): Name of the Docker container
        verbose (bool): Whether to print verbose output
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Read the SQL script
        with open(script_path, 'r') as f:
            sql = f.read()
        
        # Replace parameters in the SQL script
        for key, value in params.items():
            if isinstance(value, str):
                # Escape single quotes in string values
                value = value.replace("'", "''")
                sql = sql.replace(f":{key}", f"'{value}'")
            else:
                sql = sql.replace(f":{key}", str(value))
        
        # Create a temporary file
        temp_file = f"temp_{int(time.time())}.sql"
        temp_path = os.path.abspath(temp_file)
        
        try:
            # Write the SQL script to the temporary file
            with open(temp_path, 'w') as f:
                f.write(sql)
            
            # Run the SQL script directly using psql in the Docker container
            cmd = [
                "docker", "exec", "-i", container_name,
                "psql", "-U", "gis", "-d", "gis"
            ]
            
            if verbose:
                logger.info(f"Running command: {' '.join(cmd)}")
            
            # Use subprocess.Popen to pipe the SQL file content to psql
            with open(temp_path, 'r') as sql_file:
                process = subprocess.Popen(
                    cmd,
                    stdin=sql_file,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Error executing {os.path.basename(script_path)}: {stderr}")
                return False
            
            if verbose:
                logger.info(f"SQL script output: {stdout}")
            
            return True
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        logger.error(f"Error running SQL script {os.path.basename(script_path)}: {str(e)}")
        return False

def run_pipeline(config_path, sql_dir, container_name='geo-graph-db-1', verbose=False):
    """
    Run the water obstacle pipeline with the boundary hexagon layer approach.
    
    Args:
        config_path (str): Path to the configuration file
        sql_dir (str): Path to the directory containing SQL scripts
        container_name (str): Name of the Docker container
        verbose (bool): Whether to print verbose output
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load configuration
        config_loader = load_config(config_path)
        if config_loader is None:
            logger.error(f"Failed to load configuration from {config_path}")
            return False
            
        # Get SQL parameters
        params = config_loader.get_sql_params()
        
        if verbose:
            logger.info(f"Loaded configuration from {config_path}")
            logger.info(f"Parameters: {json.dumps(params, indent=2)}")
        
        # Define SQL scripts to run
        sql_scripts = [
            "01_extract_water_features_3857.sql",
            "02_create_water_buffers_3857.sql",
            "03_dissolve_water_buffers_3857.sql",
            "04_create_terrain_grid_boundary_hexagon.sql",
            "04a_create_terrain_edges_hexagon.sql",
            "05_create_boundary_nodes_hexagon.sql",
            "06_create_boundary_edges_hexagon.sql",
            "07_create_unified_boundary_graph_hexagon.sql"
        ]
        
        # Add boundary hexagon layer parameters to the params dictionary
        boundary_hexagon_layer = config_loader.config.get('boundary_hexagon_layer', {})
        params['boundary_node_spacing'] = boundary_hexagon_layer.get('boundary_node_spacing', 100)
        params['boundary_edge_max_length'] = boundary_hexagon_layer.get('boundary_edge_max_length', 200)
        params['water_speed_factor'] = boundary_hexagon_layer.get('water_speed_factor', 0.2)
        params['max_edge_length'] = config_loader.config.get('terrain_grid', {}).get('max_edge_length', 500)
        params['boundary_extension_distance'] = boundary_hexagon_layer.get('boundary_extension_distance', 50)
        params['max_bridge_distance'] = boundary_hexagon_layer.get('max_bridge_distance', 300)
        params['max_bridge_length'] = boundary_hexagon_layer.get('max_bridge_length', 150)
        params['direction_count'] = boundary_hexagon_layer.get('direction_count', 8)
        params['max_connections_per_direction'] = boundary_hexagon_layer.get('max_connections_per_direction', 2)
        params['max_land_portion_connection_distance'] = boundary_hexagon_layer.get('max_land_portion_connection_distance', 300)
        params['land_portion_connection_modulo'] = boundary_hexagon_layer.get('land_portion_connection_modulo', 3)
        params['land_speed_factor'] = boundary_hexagon_layer.get('land_speed_factor', 1.0)
        
        # Run SQL scripts
        for script in sql_scripts:
            script_path = os.path.join(sql_dir, script)
            
            if not os.path.exists(script_path):
                logger.error(f"SQL script not found: {script_path}")
                return False
            
            logger.info(f"Running SQL script: {script}")
            start_time = time.time()
            
            if not run_sql_script(script_path, params, container_name, verbose):
                logger.error(f"Failed to run SQL script: {script}")
                return False
            
            elapsed_time = time.time() - start_time
            logger.info(f"Completed SQL script: {script} in {elapsed_time:.2f} seconds")
        
        logger.info("Boundary hexagon layer pipeline completed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error running boundary hexagon layer pipeline: {str(e)}")
        return False

def main():
    """
    Main function to parse arguments and run the pipeline.
    """
    parser = argparse.ArgumentParser(description='Run the water obstacle pipeline with the boundary hexagon layer approach')
    parser.add_argument('--config', type=str, default='epsg3857_pipeline/config/crs_standardized_config_boundary_hexagon.json',
                        help='Path to the configuration file')
    parser.add_argument('--sql-dir', type=str, default='epsg3857_pipeline/core/sql',
                        help='Path to the directory containing SQL scripts')
    parser.add_argument('--container', type=str, default='geo-graph-db-1',
                        help='Name of the Docker container')
    parser.add_argument('--verbose', action='store_true',
                        help='Print verbose output')
    
    args = parser.parse_args()
    
    # Run the pipeline
    success = run_pipeline(args.config, args.sql_dir, args.container, args.verbose)
    
    # Return exit code
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
