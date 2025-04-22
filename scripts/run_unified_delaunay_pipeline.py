#!/usr/bin/env python3
"""
Unified Delaunay Triangulation Pipeline for Large Datasets

This script runs the complete pipeline for terrain grid generation using Delaunay triangulation,
optimized for large datasets. It includes:
1. Spatial partitioning for processing large areas in chunks
2. Memory-efficient processing
3. Parallel processing for independent operations
4. Progress tracking and logging

Usage:
    python run_unified_delaunay_pipeline.py [--config CONFIG] [--threads THREADS] [--chunk-size CHUNK_SIZE]
"""

import os
import sys
import argparse
import logging
import json
import time
import psycopg2
import multiprocessing
from datetime import datetime
from pathlib import Path
import concurrent.futures
from psycopg2.extras import DictCursor

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.file_management import get_log_path

# Configure logging
log_path = get_log_path("unified_delaunay_pipeline")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_path)
    ]
)
logger = logging.getLogger('unified_delaunay_pipeline')


def load_config(config_path):
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
    
    Returns:
        Configuration dictionary
    """
    logger.info(f"Loading configuration from {config_path}")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        sys.exit(1)


def connect_to_database(conn_string):
    """
    Connect to the database.
    
    Args:
        conn_string: Connection string for the database
    
    Returns:
        Database connection
    """
    logger.info("Connecting to database")
    try:
        conn = psycopg2.connect(conn_string)
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        sys.exit(1)


def execute_sql_file(conn, sql_file, params=None):
    """
    Execute a SQL file.
    
    Args:
        conn: Database connection
        sql_file: Path to the SQL file
        params: Parameters to substitute in the SQL file
    
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Executing SQL file: {sql_file}")
    try:
        with open(sql_file, 'r') as f:
            sql = f.read()
        
        # Substitute parameters if provided
        if params:
            sql = sql.format(**params)
        
        with conn.cursor() as cur:
            cur.execute(sql)
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error executing SQL file {sql_file}: {e}")
        conn.rollback()
        return False


def get_dataset_extent(conn):
    """
    Get the extent of the dataset.
    
    Args:
        conn: Database connection
    
    Returns:
        Dictionary with xmin, ymin, xmax, ymax
    """
    logger.info("Getting dataset extent")
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""
                SELECT 
                    ST_XMin(ST_Extent(way)) AS xmin,
                    ST_YMin(ST_Extent(way)) AS ymin,
                    ST_XMax(ST_Extent(way)) AS xmax,
                    ST_YMax(ST_Extent(way)) AS ymax
                FROM planet_osm_polygon
                WHERE waterway IS NOT NULL OR "natural" = 'water' OR landuse = 'reservoir'
            """)
            extent = cur.fetchone()
            return dict(extent)
    except Exception as e:
        logger.error(f"Error getting dataset extent: {e}")
        return None


def create_spatial_chunks(extent, chunk_size):
    """
    Create spatial chunks for processing.
    
    Args:
        extent: Dictionary with xmin, ymin, xmax, ymax
        chunk_size: Size of each chunk in meters
    
    Returns:
        List of chunk extents
    """
    logger.info(f"Creating spatial chunks with size {chunk_size}m")
    chunks = []
    
    xmin, ymin, xmax, ymax = extent['xmin'], extent['ymin'], extent['xmax'], extent['ymax']
    
    # Calculate number of chunks in each dimension
    x_chunks = max(1, int((xmax - xmin) / chunk_size))
    y_chunks = max(1, int((ymax - ymin) / chunk_size))
    
    # Calculate chunk dimensions
    x_chunk_size = (xmax - xmin) / x_chunks
    y_chunk_size = (ymax - ymin) / y_chunks
    
    # Create chunks with overlap
    overlap = chunk_size * 0.1  # 10% overlap
    
    for i in range(x_chunks):
        for j in range(y_chunks):
            chunk_xmin = xmin + i * x_chunk_size - (overlap if i > 0 else 0)
            chunk_ymin = ymin + j * y_chunk_size - (overlap if j > 0 else 0)
            chunk_xmax = xmin + (i + 1) * x_chunk_size + (overlap if i < x_chunks - 1 else 0)
            chunk_ymax = ymin + (j + 1) * y_chunk_size + (overlap if j < y_chunks - 1 else 0)
            
            chunks.append({
                'id': f"chunk_{i}_{j}",
                'xmin': chunk_xmin,
                'ymin': chunk_ymin,
                'xmax': chunk_xmax,
                'ymax': chunk_ymax
            })
    
    logger.info(f"Created {len(chunks)} spatial chunks")
    return chunks


def process_chunk(chunk, conn_string, sql_dir, config):
    """
    Process a spatial chunk.
    
    Args:
        chunk: Chunk extent
        conn_string: Connection string for the database
        sql_dir: Directory containing SQL files
        config: Configuration dictionary
    
    Returns:
        Dictionary with chunk ID and processing status
    """
    chunk_id = chunk['id']
    logger.info(f"Processing chunk {chunk_id}")
    
    # Connect to the database
    conn = connect_to_database(conn_string)
    
    try:
        # Create temporary schema for this chunk
        with conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {chunk_id}")
            conn.commit()
        
        # Set search path to the chunk schema
        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {chunk_id}, public")
            conn.commit()
        
        # Extract water features for this chunk
        params = {
            'xmin': chunk['xmin'],
            'ymin': chunk['ymin'],
            'xmax': chunk['xmax'],
            'ymax': chunk['ymax'],
            'buffer_distance': config.get('buffer_distance', 50)
        }
        
        # Execute SQL files in sequence
        sql_files = [
            "01_extract_water_features_3857.sql",
            "02_create_water_buffers_3857.sql",
            "03_dissolve_water_buffers_3857.sql",
            "04_create_terrain_grid_delaunay_3857.sql",
            "05_create_terrain_edges_delaunay_3857.sql",
            "06_create_water_edges_3857.sql",
            "07_create_environmental_tables_3857.sql"
        ]
        
        for sql_file in sql_files:
            sql_path = os.path.join(sql_dir, sql_file)
            if not execute_sql_file(conn, sql_path, params):
                logger.error(f"Failed to execute {sql_file} for chunk {chunk_id}")
                return {'chunk_id': chunk_id, 'status': 'failed'}
        
        logger.info(f"Successfully processed chunk {chunk_id}")
        return {'chunk_id': chunk_id, 'status': 'success'}
    
    except Exception as e:
        logger.error(f"Error processing chunk {chunk_id}: {e}")
        return {'chunk_id': chunk_id, 'status': 'failed'}
    
    finally:
        conn.close()


def merge_chunks(conn, chunks):
    """
    Merge processed chunks into final tables.
    
    Args:
        conn: Database connection
        chunks: List of chunk IDs
    
    Returns:
        True if successful, False otherwise
    """
    logger.info("Merging chunks into final tables")
    try:
        # Create final tables if they don't exist
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS terrain_grid (
                    id SERIAL PRIMARY KEY,
                    geom GEOMETRY(Point, 3857),
                    cost FLOAT
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS terrain_edges (
                    id SERIAL PRIMARY KEY,
                    source_id INTEGER,
                    target_id INTEGER,
                    source BIGINT,
                    target BIGINT,
                    cost FLOAT,
                    length_m FLOAT,
                    geom GEOMETRY(LineString, 3857)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS water_edges (
                    id SERIAL PRIMARY KEY,
                    source_id INTEGER,
                    target_id INTEGER,
                    source BIGINT,
                    target BIGINT,
                    cost FLOAT,
                    length_m FLOAT,
                    geom GEOMETRY(LineString, 3857)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS terrain_triangulation (
                    id SERIAL PRIMARY KEY,
                    geom GEOMETRY(Polygon, 3857)
                )
            """)
            
            conn.commit()
        
        # Merge terrain grid points
        for chunk in chunks:
            chunk_id = chunk['id']
            if chunk['status'] == 'success':
                with conn.cursor() as cur:
                    # Insert terrain grid points
                    cur.execute(f"""
                        INSERT INTO terrain_grid (geom, cost)
                        SELECT geom, cost
                        FROM {chunk_id}.terrain_grid
                    """)
                    
                    # Insert terrain triangulation
                    cur.execute(f"""
                        INSERT INTO terrain_triangulation (geom)
                        SELECT geom
                        FROM {chunk_id}.terrain_triangulation
                    """)
                    
                    conn.commit()
        
        # Update terrain edge source/target IDs to reference the merged terrain grid
        for chunk in chunks:
            chunk_id = chunk['id']
            if chunk['status'] == 'success':
                with conn.cursor() as cur:
                    # Create temporary mapping table
                    cur.execute(f"""
                        CREATE TEMP TABLE {chunk_id}_grid_mapping AS
                        WITH chunk_grid AS (
                            SELECT id AS chunk_id, geom
                            FROM {chunk_id}.terrain_grid
                        )
                        SELECT 
                            cg.chunk_id,
                            tg.id AS global_id
                        FROM chunk_grid cg
                        JOIN terrain_grid tg ON ST_Equals(cg.geom, tg.geom)
                    """)
                    
                    # Insert terrain edges with updated source/target IDs
                    cur.execute(f"""
                        INSERT INTO terrain_edges (source_id, target_id, cost, length_m, geom)
                        SELECT 
                            src_map.global_id AS source_id,
                            tgt_map.global_id AS target_id,
                            te.cost,
                            te.length_m,
                            te.geom
                        FROM {chunk_id}.terrain_edges te
                        JOIN {chunk_id}_grid_mapping src_map ON te.source_id = src_map.chunk_id
                        JOIN {chunk_id}_grid_mapping tgt_map ON te.target_id = tgt_map.chunk_id
                    """)
                    
                    # Insert water edges with updated source/target IDs
                    cur.execute(f"""
                        INSERT INTO water_edges (source_id, target_id, cost, length_m, geom)
                        SELECT 
                            src_map.global_id AS source_id,
                            tgt_map.global_id AS target_id,
                            we.cost,
                            we.length_m,
                            we.geom
                        FROM {chunk_id}.water_edges we
                        JOIN {chunk_id}_grid_mapping src_map ON we.source_id = src_map.chunk_id
                        JOIN {chunk_id}_grid_mapping tgt_map ON we.target_id = tgt_map.chunk_id
                    """)
                    
                    # Drop temporary mapping table
                    cur.execute(f"DROP TABLE {chunk_id}_grid_mapping")
                    
                    conn.commit()
        
        # Create spatial indexes
        with conn.cursor() as cur:
            cur.execute("CREATE INDEX IF NOT EXISTS terrain_grid_geom_idx ON terrain_grid USING GIST (geom)")
            cur.execute("CREATE INDEX IF NOT EXISTS terrain_edges_geom_idx ON terrain_edges USING GIST (geom)")
            cur.execute("CREATE INDEX IF NOT EXISTS water_edges_geom_idx ON water_edges USING GIST (geom)")
            cur.execute("CREATE INDEX IF NOT EXISTS terrain_triangulation_geom_idx ON terrain_triangulation USING GIST (geom)")
            conn.commit()
        
        # Create unified edges table
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS unified_edges AS
                SELECT id, source_id, target_id, source, target, cost, length_m, geom, 'terrain' AS edge_type
                FROM terrain_edges
                UNION ALL
                SELECT id, source_id, target_id, source, target, cost, length_m, geom, 'water' AS edge_type
                FROM water_edges
            """)
            
            cur.execute("CREATE INDEX IF NOT EXISTS unified_edges_geom_idx ON unified_edges USING GIST (geom)")
            conn.commit()
        
        # Create topology
        with conn.cursor() as cur:
            cur.execute("""
                SELECT pgr_createTopology(
                    'unified_edges',
                    0.0001,
                    'geom',
                    'id',
                    'source',
                    'target'
                )
            """)
            conn.commit()
        
        logger.info("Successfully merged chunks into final tables")
        return True
    
    except Exception as e:
        logger.error(f"Error merging chunks: {e}")
        conn.rollback()
        return False


def cleanup_chunks(conn, chunks):
    """
    Clean up temporary chunk schemas.
    
    Args:
        conn: Database connection
        chunks: List of chunk IDs
    
    Returns:
        True if successful, False otherwise
    """
    logger.info("Cleaning up temporary chunk schemas")
    try:
        for chunk in chunks:
            chunk_id = chunk['id']
            with conn.cursor() as cur:
                cur.execute(f"DROP SCHEMA IF EXISTS {chunk_id} CASCADE")
                conn.commit()
        
        logger.info("Successfully cleaned up temporary chunk schemas")
        return True
    
    except Exception as e:
        logger.error(f"Error cleaning up temporary chunk schemas: {e}")
        conn.rollback()
        return False


def run_pipeline(config_path, sql_dir=None, conn_string=None, threads=None, chunk_size=None):
    """
    Run the complete pipeline.
    
    Args:
        config_path: Path to the configuration file
        sql_dir: Directory containing SQL files
        conn_string: Connection string for the database
        threads: Number of threads to use for parallel processing
        chunk_size: Size of each chunk in meters
    
    Returns:
        True if successful, False otherwise
    """
    start_time = time.time()
    logger.info("Starting unified Delaunay triangulation pipeline")
    
    # Load configuration
    config = load_config(config_path)
    
    # Set default values
    if sql_dir is None:
        sql_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "planning/sql")
    
    if conn_string is None:
        conn_string = os.environ.get('PG_URL', 'postgresql://gis:gis@localhost:5432/gis')
    
    if threads is None:
        threads = config.get('threads', multiprocessing.cpu_count())
    
    if chunk_size is None:
        chunk_size = config.get('chunk_size', 5000)  # Default chunk size: 5km
    
    # Connect to the database
    conn = connect_to_database(conn_string)
    
    try:
        # Get dataset extent
        extent = get_dataset_extent(conn)
        if extent is None:
            logger.error("Failed to get dataset extent")
            return False
        
        # Create spatial chunks
        chunks = create_spatial_chunks(extent, chunk_size)
        
        # Process chunks in parallel
        logger.info(f"Processing {len(chunks)} chunks using {threads} threads")
        processed_chunks = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_chunk = {
                executor.submit(process_chunk, chunk, conn_string, sql_dir, config): chunk
                for chunk in chunks
            }
            
            for future in concurrent.futures.as_completed(future_to_chunk):
                chunk = future_to_chunk[future]
                try:
                    result = future.result()
                    processed_chunks.append(result)
                    logger.info(f"Completed chunk {result['chunk_id']} with status {result['status']}")
                except Exception as e:
                    logger.error(f"Error processing chunk {chunk['id']}: {e}")
                    processed_chunks.append({'chunk_id': chunk['id'], 'status': 'failed'})
        
        # Merge chunks
        if not merge_chunks(conn, processed_chunks):
            logger.error("Failed to merge chunks")
            return False
        
        # Clean up temporary chunk schemas
        if not cleanup_chunks(conn, processed_chunks):
            logger.warning("Failed to clean up temporary chunk schemas")
        
        # Log completion time
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"Pipeline completed in {elapsed_time:.2f} seconds")
        
        return True
    
    except Exception as e:
        logger.error(f"Error running pipeline: {e}")
        return False
    
    finally:
        conn.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Delaunay Triangulation Pipeline for Large Datasets"
    )
    parser.add_argument(
        "--config",
        default="planning/config/crs_standardized_config.json",
        help="Path to the configuration file"
    )
    parser.add_argument(
        "--threads",
        type=int,
        help="Number of threads to use for parallel processing"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        help="Size of each chunk in meters"
    )
    parser.add_argument(
        "--sql-dir",
        help="Directory containing SQL files"
    )
    parser.add_argument(
        "--conn-string",
        help="Connection string for the database"
    )
    
    args = parser.parse_args()
    
    # Run the pipeline
    success = run_pipeline(
        config_path=args.config,
        sql_dir=args.sql_dir,
        conn_string=args.conn_string,
        threads=args.threads,
        chunk_size=args.chunk_size
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
