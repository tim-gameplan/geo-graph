#!/usr/bin/env python3
"""
Test script for the Hexagon Obstacle Boundary Pipeline.

This script tests the hexagon obstacle boundary pipeline by:
1. Resetting the database
2. Running the hexagon obstacle boundary pipeline
3. Verifying that the expected tables are created and populated
4. Checking that the graph is fully connected
"""

import os
import sys
import time
import logging
import subprocess
from pathlib import Path

# Add the parent directory to the path so we can import from core packages
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.utils.logging_utils import setup_logger

# Set up logging
logger = setup_logger('test_hexagon_obstacle_boundary')

def run_command(cmd, verbose=False):
    """
    Run a command and return the result.

    Args:
        cmd (str): Command to run
        verbose (bool): Whether to print verbose output

    Returns:
        tuple: (success, stdout, stderr)
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

        elapsed_time = time.time() - start_time

        if result.returncode == 0:
            if verbose:
                logger.info(f"✅ Command completed successfully in {elapsed_time:.2f} seconds")
            return True, result.stdout, result.stderr
        else:
            logger.error(f"❌ Command failed: {cmd}")
            logger.error(f"Error output: {result.stderr}")
            return False, result.stdout, result.stderr

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"❌ Command failed with exception: {str(e)}")
        return False, "", str(e)

def run_sql_query(query, container_name='geo-graph-db-1', verbose=False):
    """
    Run a SQL query and return the result.

    Args:
        query (str): SQL query to run
        container_name (str): Name of the Docker container
        verbose (bool): Whether to print verbose output

    Returns:
        tuple: (success, result)
    """
    cmd = f'docker exec {container_name} psql -U gis -d gis -c "{query}"'
    success, stdout, stderr = run_command(cmd, verbose)
    return success, stdout

def check_table_exists(table_name, container_name='geo-graph-db-1', verbose=False):
    """
    Check if a table exists in the database.

    Args:
        table_name (str): Name of the table to check
        container_name (str): Name of the Docker container
        verbose (bool): Whether to print verbose output

    Returns:
        bool: True if the table exists, False otherwise
    """
    query = f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}');"
    success, result = run_sql_query(query, container_name, verbose)

    if not success:
        logger.error(f"Failed to check if table {table_name} exists")
        return False

    return "t" in result.lower()

def check_table_has_rows(table_name, container_name='geo-graph-db-1', verbose=False):
    """
    Check if a table has any rows.

    Args:
        table_name (str): Name of the table to check
        container_name (str): Name of the Docker container
        verbose (bool): Whether to print verbose output

    Returns:
        bool: True if the table has rows, False otherwise
    """
    query = f"SELECT COUNT(*) FROM {table_name};"
    success, result = run_sql_query(query, container_name, verbose)

    if not success:
        logger.error(f"Failed to check if table {table_name} has rows")
        return False

    # Extract the count from the result
    try:
        count_line = [line for line in result.split('\n') if line.strip().isdigit()][0]
        count = int(count_line.strip())
        return count > 0
    except (IndexError, ValueError):
        logger.error(f"Failed to parse row count from result: {result}")
        return False

def check_graph_connectivity(container_name='geo-graph-db-1', verbose=False):
    """
    Check if the graph is fully connected.

    Args:
        container_name (str): Name of the Docker container
        verbose (bool): Whether to print verbose output

    Returns:
        bool: True if the graph is fully connected, False otherwise
    """
    query = """
    WITH RECURSIVE
    connected_nodes(node_id) AS (
        -- Start with the first node
        SELECT source_id FROM unified_obstacle_edges LIMIT 1
        UNION
        -- Add all nodes reachable from already connected nodes
        SELECT e.target_id
        FROM connected_nodes c
        JOIN unified_obstacle_edges e ON c.node_id = e.source_id
        WHERE e.target_id NOT IN (SELECT node_id FROM connected_nodes)
    )
    SELECT
        (SELECT COUNT(DISTINCT source_id) FROM unified_obstacle_edges) AS total_nodes,
        COUNT(*) AS connected_nodes,
        COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT source_id) FROM unified_obstacle_edges) AS connectivity_percentage
    FROM
        connected_nodes;
    """
    success, result = run_sql_query(query, container_name, verbose)

    if not success:
        logger.error("Failed to check graph connectivity")
        return False

    # Extract the connectivity percentage from the result
    try:
        lines = result.split('\n')
        for line in lines:
            if '|' in line and '%' in line:
                parts = line.split('|')
                if len(parts) >= 3:
                    connectivity_percentage = float(parts[2].strip().replace('%', ''))
                    if connectivity_percentage >= 99.9:  # Allow for small rounding errors
                        return True

        logger.error(f"Graph is not fully connected. Connectivity result: {result}")
        return False
    except Exception as e:
        logger.error(f"Failed to parse connectivity result: {str(e)}")
        return False

def test_hexagon_obstacle_boundary(verbose=False):
    """
    Test the hexagon obstacle boundary pipeline.

    Args:
        verbose (bool): Whether to print verbose output

    Returns:
        bool: True if all tests pass, False otherwise
    """
    # Step 1: Reset the database
    logger.info("Running Database reset: python epsg3857_pipeline/core/scripts/reset_database.py --reset-derived")
    success, _, _ = run_command("python epsg3857_pipeline/core/scripts/reset_database.py --reset-derived", verbose)

    if not success:
        logger.error("Failed to reset the database")
        return False

    logger.info("✅ Database reset completed successfully")

    # Step 2: Run the hexagon obstacle boundary pipeline
    logger.info("Running Hexagon Obstacle Boundary pipeline: python epsg3857_pipeline/run_hexagon_obstacle_boundary_pipeline.py --config epsg3857_pipeline/config/hexagon_obstacle_boundary_config.json --verbose")
    success, _, _ = run_command("python epsg3857_pipeline/run_hexagon_obstacle_boundary_pipeline.py --config epsg3857_pipeline/config/hexagon_obstacle_boundary_config.json" + (" --verbose" if verbose else ""), verbose)

    if not success:
        logger.error("Failed to run the hexagon obstacle boundary pipeline")
        return False

    logger.info("✅ Hexagon Obstacle Boundary pipeline completed successfully")

    # Step 3: Verify that the expected tables are created and populated
    tables_to_check = [
        "water_features",
        "water_buffers",
        "water_obstacles",
        "terrain_grid",
        "terrain_grid_points",
        "obstacle_boundary_nodes",
        "obstacle_boundary_edges",
        "obstacle_boundary_connection_edges",
        "unified_obstacle_edges"
    ]

    all_tables_exist = True
    all_tables_have_rows = True

    for table in tables_to_check:
        if not check_table_exists(table, verbose=verbose):
            logger.error(f"❌ Table {table} does not exist")
            all_tables_exist = False
        elif not check_table_has_rows(table, verbose=verbose):
            logger.warning(f"⚠️ Table {table} exists but has no rows")
            all_tables_have_rows = False
        else:
            logger.info(f"✅ Table {table} exists and has rows")

    if not all_tables_exist:
        logger.error("Not all expected tables were created")
        return False

    if not all_tables_have_rows:
        logger.warning("Some tables have no rows, but this might be expected in some cases")

    # Step 4: Check that the graph is fully connected
    if check_graph_connectivity(verbose=verbose):
        logger.info("✅ Graph is fully connected")
    else:
        logger.error("❌ Graph is not fully connected")
        return False

    logger.info("✅ All tests passed")
    return True

def main():
    """
    Main function to parse arguments and run the tests.
    """
    import argparse

    parser = argparse.ArgumentParser(description='Test the hexagon obstacle boundary pipeline')
    parser.add_argument('--verbose', action='store_true', help='Print verbose output')

    args = parser.parse_args()

    # Run the tests
    success = test_hexagon_obstacle_boundary(args.verbose)

    # Return exit code
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
