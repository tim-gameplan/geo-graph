# EPSG Consistency Implementation Plan - Part 3: Testing and Integration

**Date:** April 21, 2025  
**Author:** Cline  
**Project:** Terrain System - Geo-Graph  

This document is the final part of the EPSG Consistency Implementation Plan, focusing on testing and integration components.

## Phase 6: Testing (Week 3)

### 6.1 Unit Tests

Create `planning/tests/test_crs_consistency.py`:

```python
#!/usr/bin/env python3
"""
Test script for the CRS consistency implementation.

This script:
1. Connects to the PostgreSQL database
2. Runs a series of tests to verify the CRS consistency
3. Reports the results
"""

import os
import sys
import argparse
import logging
import psycopg2
from psycopg2.extras import DictCursor

# Add the parent directory to the path so we can import config_loader
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config_loader import ConfigLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_crs_consistency.log')
    ]
)
logger = logging.getLogger('test_crs_consistency')


def get_db_connection(conn_string=None):
    """Create a database connection."""
    if conn_string is None:
        conn_string = os.environ.get('PG_URL', 'postgresql://gis:gis@localhost:5432/gis')
    
    try:
        conn = psycopg2.connect(conn_string)
        logger.info(f"Connected to database: {conn_string.split('@')[-1]}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise


def test_table_exists(conn, table_name):
    """Test if a table exists in the database."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')")
        exists = cur.fetchone()[0]
    
    if exists:
        logger.info(f"✅ Table '{table_name}' exists")
        return True
    else:
        logger.error(f"❌ Table '{table_name}' does not exist")
        return False


def test_geometry_srid(conn, table_name, geom_column='geom', expected_srid=3857):
    """Test if a geometry column has the expected SRID."""
    if not test_table_exists(conn, table_name):
        return False
    
    with conn.cursor() as cur:
        cur.execute(f"SELECT ST_SRID({geom_column}) FROM {table_name} LIMIT 1")
        srid = cur.fetchone()[0]
    
    if srid == expected_srid:
        logger.info(f"✅ Geometry column '{geom_column}' in table '{table_name}' has SRID {srid}")
        return True
    else:
        logger.error(f"❌ Geometry column '{geom_column}' in table '{table_name}' has SRID {srid}, expected {expected_srid}")
        return False


def test_buffer_distances(conn, buffer_table='water_buf', geom_column='geom'):
    """Test if buffer distances are reasonable in meters."""
    if not test_table_exists(conn, buffer_table):
        return False
    
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT 
                water_type, 
                buffer_rule_applied,
                buffer_size_m,
                ST_Area({geom_column}) / (PI() * buffer_size_m * buffer_size_m) AS area_ratio
            FROM {buffer_table}
            WHERE buffer_size_m > 0
            LIMIT 10
        """)
        results = cur.fetchall()
    
    if not results:
        logger.error(f"❌ No buffer results found in table '{buffer_table}'")
        return False
    
    all_valid = True
    for water_type, rule, size, ratio in results:
        # For a perfect circle, area / (pi * r^2) = 1
        # Allow some deviation due to geometry complexity
        if 0.5 <= ratio <= 2.0:
            logger.info(f"✅ Buffer for {water_type} ({rule}) with size {size}m has reasonable area ratio: {ratio:.2f}")
        else:
            logger.error(f"❌ Buffer for {water_type} ({rule}) with size {size}m has unusual area ratio: {ratio:.2f}")
            all_valid = False
    
    return all_valid


def test_unified_edges(conn, unified_table='unified_edges', geom_column='geom'):
    """Test if unified edges have valid source and target nodes."""
    if not test_table_exists(conn, unified_table):
        return False
    
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT 
                COUNT(*) AS total_edges,
                COUNT(CASE WHEN source IS NULL OR target IS NULL THEN 1 END) AS null_nodes
            FROM {unified_table}
        """)
        total_edges, null_nodes = cur.fetchone()
    
    if total_edges == 0:
        logger.error(f"❌ No edges found in table '{unified_table}'")
        return False
    
    if null_nodes == 0:
        logger.info(f"✅ All edges in '{unified_table}' have valid source and target nodes")
        return True
    else:
        logger.error(f"❌ {null_nodes} out of {total_edges} edges in '{unified_table}' have NULL source or target nodes")
        return False


def test_edge_types(conn, unified_table='unified_edges'):
    """Test if unified edges have valid edge types."""
    if not test_table_exists(conn, unified_table):
        return False
    
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT 
                edge_type,
                COUNT(*) AS count
            FROM {unified_table}
            GROUP BY edge_type
        """)
        results = cur.fetchall()
    
    if not results:
        logger.error(f"❌ No edge types found in table '{unified_table}'")
        return False
    
    all_valid = True
    valid_types = {'road', 'water', 'terrain'}
    for edge_type, count in results:
        if edge_type in valid_types:
            logger.info(f"✅ Found {count} edges of type '{edge_type}'")
        else:
            logger.error(f"❌ Found {count} edges with invalid type '{edge_type}'")
            all_valid = False
    
    return all_valid


def run_tests(conn_string=None):
    """Run all tests."""
    conn = get_db_connection(conn_string)
    
    try:
        # Test tables exist
        tables_exist = all([
            test_table_exists(conn, 'water_features'),
            test_table_exists(conn, 'water_buf'),
            test_table_exists(conn, 'water_buf_dissolved'),
            test_table_exists(conn, 'terrain_grid'),
            test_table_exists(conn, 'terrain_edges'),
            test_table_exists(conn, 'water_edges'),
            test_table_exists(conn, 'unified_edges'),
            test_table_exists(conn, 'unified_vertices')
        ])
        
        if not tables_exist:
            logger.error("❌ Required tables do not exist. Run the pipeline first.")
            return False
        
        # Test geometry SRIDs
        srids_correct = all([
            test_geometry_srid(conn, 'water_features'),
            test_geometry_srid(conn, 'water_buf'),
            test_geometry_srid(conn, 'water_buf_dissolved'),
            test_geometry_srid(conn, 'terrain_grid'),
            test_geometry_srid(conn, 'terrain_edges'),
            test_geometry_srid(conn, 'water_edges'),
            test_geometry_srid(conn, 'unified_edges'),
            test_geometry_srid(conn, 'unified_vertices')
        ])
        
        # Test buffer distances
        buffers_valid = test_buffer_distances(conn)
        
        # Test unified edges
        unified_valid = test_unified_edges(conn)
        
        # Test edge types
        edge_types_valid = test_edge_types(conn)
        
        # Overall result
        if srids_correct and buffers_valid and unified_valid and edge_types_valid:
            logger.info("✅ All tests passed! CRS consistency is working correctly.")
            return True
        else:
            logger.error("❌ Some tests failed. See log for details.")
            return False
    
    finally:
        conn.close()
        logger.info("Database connection closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test the CRS consistency implementation")
    parser.add_argument(
        "--conn-string",
        help="PostgreSQL connection string (default: from PG_URL environment variable)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    try:
        success = run_tests(args.conn_string)
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Tests failed with exception: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

### 6.2 Integration Tests

Create `planning/tests/test_pipeline_integration.py`:

```python
#!/usr/bin/env python3
"""
Integration test script for the CRS consistency implementation.

This script:
1. Runs the complete pipeline with CRS consistency
2. Exports a slice of the graph
3. Visualizes the exported graph
4. Verifies the results
"""

import os
import sys
import argparse
import logging
import subprocess
import time
import networkx as nx
from pathlib import Path

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_pipeline_integration.log')
    ]
)
logger = logging.getLogger('test_pipeline_integration')


def run_command(command, description):
    """Run a command and log the result."""
    logger.info(f"Running {description}: {command}")
    
    try:
        start_time = time.time()
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
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False, e.stderr


def test_reset_database():
    """Test resetting the database."""
    success, _ = run_command(
        "python scripts/reset_database.py --reset-derived",
        "Database reset"
    )
    return success


def test_water_obstacle_pipeline():
    """Test running the water obstacle pipeline."""
    success, _ = run_command(
        "python planning/scripts/run_water_obstacle_pipeline_crs.py --config planning/config/crs_standardized_config.json --sql-dir planning/sql",
        "Water obstacle pipeline"
    )
    return success


def test_unified_pipeline():
    """Test running the unified pipeline."""
    success, _ = run_command(
        "python scripts/run_unified_pipeline_3857.py --config planning/config/crs_standardized_config.json",
        "Unified pipeline"
    )
    return success


def test_export_slice():
    """Test exporting a slice of the graph."""
    success, output = run_command(
        "python tools/export_slice_3857.py --lon -93.63 --lat 41.99 --minutes 60 --outfile test_slice_3857.graphml",
        "Export slice"
    )
    
    if not success:
        return False
    
    # Verify the exported file exists
    if not os.path.exists("test_slice_3857.graphml"):
        logger.error("❌ Exported file does not exist")
        return False
    
    # Verify the exported file is a valid GraphML file
    try:
        G = nx.read_graphml("test_slice_3857.graphml")
        logger.info(f"✅ Exported graph has {len(G.nodes)} nodes and {len(G.edges)} edges")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to read exported graph: {e}")
        return False


def test_visualization():
    """Test visualizing the exported graph."""
    success, _ = run_command(
        "python visualize_graph_3857.py test_slice_3857.graphml --output test_slice_3857.png",
        "Graph visualization"
    )
    
    if not success:
        return False
    
    # Verify the visualization file exists
    if not os.path.exists("test_slice_3857.png"):
        logger.error("❌ Visualization file does not exist")
        return False
    
    logger.info("✅ Visualization file created successfully")
    return True


def run_integration_tests():
    """Run all integration tests."""
    # Reset the database
    if not test_reset_database():
        return False
    
    # Run the water obstacle pipeline
    if not test_water_obstacle_pipeline():
        return False
    
    # Run the unified pipeline
    if not test_unified_pipeline():
        return False
    
    # Export a slice of the graph
    if not test_export_slice():
        return False
    
    # Visualize the exported graph
    if not test_visualization():
        return False
    
    logger.info("✅ All integration tests passed!")
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run integration tests for the CRS consistency implementation")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    try:
        success = run_integration_tests()
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Integration tests failed with exception: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

## Phase 7: Integration with Existing Code (Week 4)

### 7.1 Update Unified Pipeline Script

Update `scripts/run_unified_pipeline.py` to support CRS standardization:

```python
# Add C
