#!/usr/bin/env python3
"""
Test Direct Water Obstacle Boundary Conversion

This script tests the direct water obstacle boundary conversion approach:
1. Runs the standard pipeline to create water_obstacles table
2. Runs the direct water obstacle boundary conversion
3. Verifies that the obstacle_boundary_nodes and obstacle_boundary_edges tables are created and populated
4. Checks that the edges form closed loops around water obstacles
5. Visualizes the results
"""

import os
import sys
import argparse
import logging
import subprocess
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_obstacle_boundary_graph.log')
    ]
)
logger = logging.getLogger('test_obstacle_boundary_graph')

def run_command(command, description):
    """Run a command and log the result."""
    logger.info(f"Running {description}: {command}")
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"✅ {description} completed successfully in {elapsed_time:.2f} seconds")
        logger.debug(f"Output: {result.stdout}")
        if result.stderr:
            logger.debug(f"Error output: {result.stderr}")
        
        return True
    except subprocess.CalledProcessError as e:
        elapsed_time = time.time() - start_time
        logger.error(f"❌ {description} failed in {elapsed_time:.2f} seconds: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False

def run_sql_query(query):
    """Run a SQL query and return the result."""
    # Write to a temporary file
    temp_file = f'temp_{os.getpid()}.sql'
    with open(temp_file, 'w') as f:
        f.write(query)
    
    # Execute the SQL query
    cmd = f'docker exec geo-graph-db-1 psql -U gis -d gis -f /tmp/{temp_file} -t -A'
    
    try:
        # Copy the temp file to the Docker container
        copy_cmd = f'docker cp {temp_file} geo-graph-db-1:/tmp/{temp_file}'
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

def check_table_exists(table_name):
    """Check if a table exists in the database."""
    query = f"""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = '{table_name}'
    );
    """
    
    result = run_sql_query(query)
    if not result:
        return False
    
    return result.strip() == 't'

def check_table_row_count(table_name):
    """Check the row count of a table."""
    query = f"""
    SELECT COUNT(*) FROM {table_name};
    """
    
    result = run_sql_query(query)
    if not result:
        return 0
    
    try:
        return int(result.strip())
    except ValueError:
        return 0

def check_unified_edges():
    """Check if the unified edges table has entries for all edge types."""
    query = """
    SELECT 
        edge_type, 
        COUNT(*) 
    FROM 
        unified_obstacle_edges 
    GROUP BY 
        edge_type 
    ORDER BY 
        edge_type;
    """
    
    result = run_sql_query(query)
    if not result:
        return False
    
    lines = result.strip().split('\n')
    edge_types = set()
    
    for line in lines:
        if not line:
            continue
        
        parts = line.split('|')
        if len(parts) != 2:
            continue
        
        edge_type, count = parts
        edge_types.add(edge_type)
    
    # Check if all required edge types are present
    required_edge_types = {'boundary', 'connection', 'terrain'}
    missing_edge_types = required_edge_types - edge_types
    
    if missing_edge_types:
        logger.warning(f"Missing edge types in unified_obstacle_edges: {missing_edge_types}")
        return False
    
    return True

def check_closed_loops():
    """Check if the edges form closed loops around water obstacles."""
    query = """
    WITH edge_counts AS (
        SELECT 
            water_obstacle_id,
            COUNT(*) AS edge_count
        FROM 
            obstacle_boundary_edges
        GROUP BY 
            water_obstacle_id
    ),
    node_counts AS (
        SELECT 
            water_obstacle_id,
            COUNT(*) AS node_count
        FROM 
            obstacle_boundary_nodes
        GROUP BY 
            water_obstacle_id
    )
    SELECT 
        e.water_obstacle_id,
        e.edge_count,
        n.node_count,
        CASE 
            WHEN e.edge_count = n.node_count THEN 'Closed Loop'
            ELSE 'Not Closed'
        END AS loop_status
    FROM 
        edge_counts e
    JOIN 
        node_counts n ON e.water_obstacle_id = n.water_obstacle_id
    ORDER BY 
        e.water_obstacle_id;
    """
    
    result = run_sql_query(query)
    if not result:
        return False
    
    lines = result.strip().split('\n')
    closed_loops = 0
    total_loops = len(lines)
    
    for line in lines:
        if 'Closed Loop' in line:
            closed_loops += 1
    
    if total_loops == 0:
        return False
    
    closed_percentage = (closed_loops / total_loops) * 100
    logger.info(f"Closed loops: {closed_loops}/{total_loops} ({closed_percentage:.2f}%)")
    
    return closed_percentage >= 99

def check_graph_connectivity():
    """Check if the unified graph is fully connected."""
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
    
    result = run_sql_query(query)
    if not result:
        return False
    
    lines = result.strip().split('\n')
    if not lines:
        return False
    
    parts = lines[0].split('|')
    if len(parts) != 3:
        return False
    
    total_nodes, connected_nodes, connectivity_percentage = parts
    
    try:
        total_nodes = int(total_nodes)
        connected_nodes = int(connected_nodes)
        connectivity_percentage = float(connectivity_percentage)
    except ValueError:
        return False
    
    logger.info(f"Graph connectivity: {connected_nodes}/{total_nodes} nodes ({connectivity_percentage:.2f}%)")
    
    return connectivity_percentage >= 99

def run_tests(args):
    """Run the tests."""
    # Reset the database
    if not args.skip_reset:
        if not run_command(
            "python epsg3857_pipeline/scripts/reset_database.py --reset-derived",
            "Database reset"
        ):
            logger.error("Failed to reset the database")
            return False
    
    # Run the standard pipeline to create water_obstacles table
    if not args.skip_pipeline:
        if not run_command(
            "python epsg3857_pipeline/scripts/run_water_obstacle_pipeline_crs.py --config epsg3857_pipeline/config/crs_standardized_config.json --sql-dir epsg3857_pipeline/sql",
            "Water obstacle pipeline"
        ):
            logger.error("Failed to run the water obstacle pipeline")
            return False
    
    # Run the direct water obstacle boundary conversion
    if not run_command(
        "python epsg3857_pipeline/scripts/run_obstacle_boundary_graph.py",
        "Direct water obstacle boundary conversion"
    ):
        logger.error("Failed to run the direct water obstacle boundary conversion")
        return False
    
    # Verify that the obstacle_boundary_nodes table exists and is populated
    if not check_table_exists('obstacle_boundary_nodes'):
        logger.error("obstacle_boundary_nodes table does not exist")
        return False
    
    node_count = check_table_row_count('obstacle_boundary_nodes')
    if node_count == 0:
        logger.error("obstacle_boundary_nodes table is empty")
        return False
    
    logger.info(f"obstacle_boundary_nodes table has {node_count} rows")
    
    # Verify that the obstacle_boundary_edges table exists and is populated
    if not check_table_exists('obstacle_boundary_edges'):
        logger.error("obstacle_boundary_edges table does not exist")
        return False
    
    edge_count = check_table_row_count('obstacle_boundary_edges')
    if edge_count == 0:
        logger.error("obstacle_boundary_edges table is empty")
        return False
    
    logger.info(f"obstacle_boundary_edges table has {edge_count} rows")
    
    # Verify that the obstacle_boundary_connection_edges table exists and is populated
    if not check_table_exists('obstacle_boundary_connection_edges'):
        logger.error("obstacle_boundary_connection_edges table does not exist")
        return False
    
    connection_edge_count = check_table_row_count('obstacle_boundary_connection_edges')
    if connection_edge_count == 0:
        logger.error("obstacle_boundary_connection_edges table is empty")
        return False
    
    logger.info(f"obstacle_boundary_connection_edges table has {connection_edge_count} rows")
    
    # Verify that the unified_obstacle_edges table exists and is populated
    if not check_table_exists('unified_obstacle_edges'):
        logger.error("unified_obstacle_edges table does not exist")
        return False
    
    unified_edge_count = check_table_row_count('unified_obstacle_edges')
    if unified_edge_count == 0:
        logger.error("unified_obstacle_edges table is empty")
        return False
    
    logger.info(f"unified_obstacle_edges table has {unified_edge_count} rows")
    
    # Check that the unified edges table has entries for all edge types
    if not check_unified_edges():
        logger.error("Unified edges table does not have entries for all edge types")
        return False
    
    logger.info("Unified edges table has entries for all edge types")
    
    # Check that the edges form closed loops around water obstacles
    if not check_closed_loops():
        logger.error("Edges do not form closed loops around water obstacles")
        return False
    
    logger.info("Edges form closed loops around water obstacles")
    
    # Check that the graph is fully connected
    if not check_graph_connectivity():
        logger.error("Graph is not fully connected")
        return False
    
    logger.info("Graph is fully connected")
    
    # Visualize the results
    if args.visualize:
        # Visualize the obstacle boundary graph
        if not run_command(
            "python epsg3857_pipeline/scripts/visualize_obstacle_boundary_graph.py --output test_obstacle_boundary_graph.png",
            "Visualization of obstacle boundary graph"
        ):
            logger.error("Failed to visualize the obstacle boundary graph")
            return False
        
        # Visualize the unified graph
        if not run_command(
            "python epsg3857_pipeline/scripts/visualize_obstacle_boundary_graph.py --output test_unified_obstacle_graph.png --show-unified",
            "Visualization of unified obstacle graph"
        ):
            logger.error("Failed to visualize the unified obstacle graph")
            return False
    
    logger.info("All tests passed!")
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Direct Water Obstacle Boundary Conversion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--skip-reset",
        action="store_true",
        help="Skip database reset"
    )
    
    parser.add_argument(
        "--skip-pipeline",
        action="store_true",
        help="Skip running the water obstacle pipeline"
    )
    
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Visualize the results"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    logger.info("Starting direct water obstacle boundary conversion test")
    
    if not run_tests(args):
        logger.error("Tests failed")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
