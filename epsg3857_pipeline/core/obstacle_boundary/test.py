#!/usr/bin/env python3
"""
Obstacle Boundary Graph Tests

This script tests the obstacle boundary graph implementation by:
1. Checking if the required tables exist
2. Verifying that the tables have the expected number of rows
3. Checking graph connectivity
4. Validating edge costs
"""

import os
import sys
import argparse
import logging
import subprocess
import tempfile
from pathlib import Path

# Add the parent directory to the path so we can import from sibling packages
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import our logging utility
from core.utils.logging_utils import get_logger

def run_sql_query(query, logger):
    """
    Run a SQL query and return the results.
    
    Args:
        query (str): SQL query to run
        logger: Logger instance
        
    Returns:
        str: Query results
    """
    # Write to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        temp_file = f.name
        f.write(query)
    
    # Execute the SQL query
    cmd = f'docker exec geo-graph-db-1 psql -U gis -d gis -f /tmp/{os.path.basename(temp_file)} -t -A'
    
    try:
        # Copy the temp file to the Docker container
        copy_cmd = f'docker cp {temp_file} geo-graph-db-1:/tmp/{os.path.basename(temp_file)}'
        subprocess.run(copy_cmd, shell=True, check=True)
        
        # Execute the SQL query
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Clean up
        os.remove(temp_file)
        
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing SQL query: {e}")
        logger.error(f"Error output: {e.stderr}")
        
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        return None

def check_table_exists(table_name, logger):
    """
    Check if a table exists.
    
    Args:
        table_name (str): Table name
        logger: Logger instance
        
    Returns:
        bool: True if the table exists, False otherwise
    """
    query = f"""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = '{table_name}'
    );
    """
    
    result = run_sql_query(query, logger)
    if result is None:
        return False
    
    return result.strip() == 't'

def count_rows(table_name, logger):
    """
    Count the number of rows in a table.
    
    Args:
        table_name (str): Table name
        logger: Logger instance
        
    Returns:
        int: Number of rows, or -1 if the query failed
    """
    query = f"""
    SELECT COUNT(*) FROM {table_name};
    """
    
    result = run_sql_query(query, logger)
    if result is None:
        return -1
    
    try:
        return int(result.strip())
    except ValueError:
        logger.error(f"Failed to parse row count for {table_name}: {result}")
        return -1

def check_graph_connectivity(logger):
    """
    Check if the graph is connected.
    
    Args:
        logger: Logger instance
        
    Returns:
        bool: True if the graph is connected, False otherwise
    """
    query = """
    WITH RECURSIVE connected_nodes AS (
        -- Start with the first node
        SELECT source_id AS node_id
        FROM unified_obstacle_edges
        LIMIT 1
        
        UNION
        
        -- Add all nodes that can be reached from the connected nodes
        SELECT e.target_id
        FROM unified_obstacle_edges e
        JOIN connected_nodes cn ON e.source_id = cn.node_id
        WHERE e.target_id NOT IN (SELECT node_id FROM connected_nodes)
    )
    SELECT
        (SELECT COUNT(DISTINCT source_id) FROM unified_obstacle_edges) AS total_nodes,
        COUNT(*) AS connected_nodes,
        (SELECT COUNT(DISTINCT source_id) FROM unified_obstacle_edges) = COUNT(*) AS is_connected
    FROM connected_nodes;
    """
    
    result = run_sql_query(query, logger)
    if result is None:
        return False
    
    # Parse the result
    try:
        parts = result.strip().split('|')
        total_nodes = int(parts[0])
        connected_nodes = int(parts[1])
        is_connected = parts[2] == 't'
        
        logger.info(f"Graph has {total_nodes} total nodes and {connected_nodes} connected nodes")
        logger.info(f"Graph is {'connected' if is_connected else 'not connected'}")
        
        return is_connected
    except (ValueError, IndexError):
        logger.error(f"Failed to parse graph connectivity result: {result}")
        return False

def validate_edge_costs(logger):
    """
    Validate edge costs.
    
    Args:
        logger: Logger instance
        
    Returns:
        bool: True if all edge costs are valid, False otherwise
    """
    query = """
    SELECT
        COUNT(*) AS total_edges,
        COUNT(*) FILTER (WHERE cost > 0) AS valid_cost_edges,
        COUNT(*) = COUNT(*) FILTER (WHERE cost > 0) AS all_costs_valid
    FROM unified_obstacle_edges;
    """
    
    result = run_sql_query(query, logger)
    if result is None:
        return False
    
    # Parse the result
    try:
        parts = result.strip().split('|')
        total_edges = int(parts[0])
        valid_cost_edges = int(parts[1])
        all_costs_valid = parts[2] == 't'
        
        logger.info(f"Graph has {total_edges} total edges and {valid_cost_edges} edges with valid costs")
        logger.info(f"All edge costs are {'valid' if all_costs_valid else 'not valid'}")
        
        return all_costs_valid
    except (ValueError, IndexError):
        logger.error(f"Failed to parse edge cost validation result: {result}")
        return False

def run_tests(logger):
    """
    Run all tests.
    
    Args:
        logger: Logger instance
        
    Returns:
        bool: True if all tests passed, False otherwise
    """
    # Check if the required tables exist
    tables = [
        'water_obstacles',
        'terrain_grid_points',
        'terrain_edges',
        'obstacle_boundary_nodes',
        'obstacle_boundary_edges',
        'obstacle_boundary_connection_edges',
        'unified_obstacle_edges'
    ]
    
    all_tables_exist = True
    for table in tables:
        exists = check_table_exists(table, logger)
        logger.info(f"Table {table} {'exists' if exists else 'does not exist'}")
        all_tables_exist = all_tables_exist and exists
    
    if not all_tables_exist:
        logger.error("Not all required tables exist")
        return False
    
    # Check if the tables have rows
    all_tables_have_rows = True
    for table in tables:
        row_count = count_rows(table, logger)
        logger.info(f"Table {table} has {row_count} rows")
        all_tables_have_rows = all_tables_have_rows and row_count > 0
    
    if not all_tables_have_rows:
        logger.error("Not all tables have rows")
        return False
    
    # Check graph connectivity
    is_connected = check_graph_connectivity(logger)
    if not is_connected:
        logger.error("Graph is not connected")
        return False
    
    # Validate edge costs
    all_costs_valid = validate_edge_costs(logger)
    if not all_costs_valid:
        logger.error("Not all edge costs are valid")
        return False
    
    logger.info("All tests passed!")
    return True

def main():
    """
    Main entry point for the script.
    
    Returns:
        int: 0 if all tests passed, 1 otherwise
    """
    parser = argparse.ArgumentParser(
        description="Obstacle Boundary Graph Tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = get_logger('obstacle_boundary_test', level=log_level)
    
    # Run the tests
    if not run_tests(logger):
        logger.error("Tests failed")
        return 1
    
    logger.info("Tests completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
