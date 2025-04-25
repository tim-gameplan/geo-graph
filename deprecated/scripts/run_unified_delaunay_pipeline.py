#!/usr/bin/env python3
"""
Unified Delaunay Pipeline for Large Datasets

This script runs the unified Delaunay pipeline for large datasets by partitioning the data into manageable chunks.
"""

import os
import sys
import argparse
import logging
import subprocess
import json
import time
import multiprocessing
from pathlib import Path
import concurrent.futures

# Add parent directory to path for importing config_loader_3857
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config_loader_3857 import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('unified_delaunay_pipeline.log')
    ]
)
logger = logging.getLogger('unified_delaunay_pipeline')

def run_sql_file(sql_file, params, description):
    """Run a SQL file with parameters."""
    logger.info(f"Running {description}: {sql_file}")
    
    # Read the SQL file
    try:
        with open(sql_file, 'r') as f:
            sql = f.read()
    except Exception as e:
        logger.error(f"Error reading SQL file {sql_file}: {e}")
        return False
    
    # Replace parameters
    for key, value in params.items():
        placeholder = f":{key}"
        sql = sql.replace(placeholder, str(value))
    
    # Write the SQL to a temporary file
    temp_file = f"temp_{int(time.time())}_{os.getpid()}.sql"
    try:
        with open(temp_file, 'w') as f:
            f.write(sql)
    except Exception as e:
        logger.error(f"Error writing temporary SQL file: {e}")
        return False
    
    # Run the SQL file
    cmd = [
        "psql",
        "-h", "localhost",
        "-U", "gis",
        "-d", "gis",
        "-f", temp_file
    ]
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"✅ {description} completed successfully")
        
        # Clean up temporary file
        os.remove(temp_file)
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        
        # Clean up temporary file
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        return False

def run_sql_query(query, description):
    """Run a SQL query and return the results."""
    logger.info(f"Running {description}: {query}")
    
    cmd = [
        "psql",
        "-h", "localhost",
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
        
        logger.info(f"✅ {description} completed successfully")
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return []

def get_bounding_box():
    """Get the bounding box of the data."""
    query = """
    SELECT 
        ST_XMin(ST_Extent(geom)) AS min_x,
        ST_YMin(ST_Extent(geom)) AS min_y,
        ST_XMax(ST_Extent(geom)) AS max_x,
        ST_YMax(ST_Extent(geom)) AS max_y
    FROM 
        planet_osm_polygon
    """
    
    results = run_sql_query(query, "Get bounding box")
    
    if not results or not results[0]:
        logger.error("No results for bounding box")
        return None
    
    parts = results[0].split('|')
    if len(parts) < 4:
        logger.error("Invalid results for bounding box")
        return None
    
    min_x = float(parts[0])
    min_y = float(parts[1])
    max_x = float(parts[2])
    max_y = float(parts[3])
    
    return (min_x, min_y, max_x, max_y)

def create_chunks(bbox, chunk_size):
    """Create chunks from the bounding box."""
    min_x, min_y, max_x, max_y = bbox
    
    chunks = []
    for x in range(int(min_x), int(max_x), chunk_size):
        for y in range(int(min_y), int(max_y), chunk_size):
            chunk_min_x = x
            chunk_min_y = y
            chunk_max_x = min(x + chunk_size, max_x)
            chunk_max_y = min(y + chunk_size, max_y)
            
            chunks.append((chunk_min_x, chunk_min_y, chunk_max_x, chunk_max_y))
    
    return chunks

def process_chunk(chunk, chunk_id, config_file, sql_dir):
    """Process a chunk of the data."""
    chunk_min_x, chunk_min_y, chunk_max_x, chunk_max_y = chunk
    
    logger.info(f"Processing chunk {chunk_id}: {chunk}")
    
    # Load configuration
    loader = load_config(config_file)
    if not loader:
        logger.error("Failed to load configuration")
        return False
    
    # Get SQL parameters
    params = loader.get_sql_params()
    
    # Get water feature types
    polygon_types, line_types = loader.get_water_feature_types()
    
    # Add water feature types to parameters
    params['polygon_types'] = "'" + "','".join(polygon_types) + "'"
    params['line_types'] = "'" + "','".join(line_types) + "'"
    
    # Add chunk parameters
    params['chunk_min_x'] = chunk_min_x
    params['chunk_min_y'] = chunk_min_y
    params['chunk_max_x'] = chunk_max_x
    params['chunk_max_y'] = chunk_max_y
    params['chunk_id'] = chunk_id
    
    # Run SQL files in order
    sql_files = [
        ("01_extract_water_features_chunk.sql", f"Extract water features for chunk {chunk_id}"),
        ("02_create_water_buffers_chunk.sql", f"Create water buffers for chunk {chunk_id}"),
        ("03_dissolve_water_buffers_chunk.sql", f"Dissolve water buffers for chunk {chunk_id}"),
        ("04_create_terrain_grid_delaunay_chunk.sql", f"Create terrain grid with Delaunay triangulation for chunk {chunk_id}"),
        ("05_create_terrain_edges_delaunay_chunk.sql", f"Create terrain edges from Delaunay triangulation for chunk {chunk_id}"),
        ("06_create_water_edges_chunk.sql", f"Create water edges for chunk {chunk_id}"),
        ("07_create_environmental_tables_chunk.sql", f"Create environmental tables for chunk {chunk_id}")
    ]
    
    for sql_file, description in sql_files:
        sql_path = os.path.join(sql_dir, sql_file)
        if not run_sql_file(sql_path, params, description):
            logger.error(f"Failed to run {sql_file} for chunk {chunk_id}")
            return False
    
    logger.info(f"Chunk {chunk_id} processed successfully")
    return True

def merge_chunks():
    """Merge the processed chunks."""
    logger.info("Merging chunks")
    
    # Merge tables
    tables = [
        "water_features",
        "water_buffers",
        "dissolved_water_buffers",
        "water_obstacles",
        "terrain_grid",
        "delaunay_triangles",
        "delaunay_edges",
        "terrain_edges",
        "water_edges",
        "environmental_conditions"
    ]
    
    for table in tables:
        query = f"""
        INSERT INTO {table}
        SELECT * FROM {table}_chunk
        """
        
        if not run_sql_query(query, f"Merge {table}"):
            logger.error(f"Failed to merge {table}")
            return False
    
    logger.info("Chunks merged successfully")
    return True

def run_pipeline(config_file, sql_dir, threads, chunk_size):
    """Run the unified Delaunay pipeline."""
    # Get the bounding box
    bbox = get_bounding_box()
    if not bbox:
        logger.error("Failed to get bounding box")
        return False
    
    # Create chunks
    chunks = create_chunks(bbox, chunk_size)
    logger.info(f"Created {len(chunks)} chunks")
    
    # Process chunks in parallel
    with concurrent.futures.ProcessPoolExecutor(max_workers=threads) as executor:
        futures = []
        for i, chunk in enumerate(chunks):
            future = executor.submit(process_chunk, chunk, i, config_file, sql_dir)
            futures.append(future)
        
        # Wait for all chunks to be processed
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            if not future.result():
                logger.error(f"Failed to process chunk {i}")
                return False
    
    # Merge chunks
    if not merge_chunks():
        logger.error("Failed to merge chunks")
        return False
    
    logger.info("Unified Delaunay pipeline completed successfully")
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the unified Delaunay pipeline for large datasets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run the pipeline with default settings
  python run_unified_delaunay_pipeline.py
  
  # Run the pipeline with custom settings
  python run_unified_delaunay_pipeline.py --threads 8 --chunk-size 10000
"""
    )
    
    # Configuration options
    parser.add_argument(
        "--config",
        default="epsg3857_pipeline/config/delaunay_config.json",
        help="Configuration file"
    )
    parser.add_argument(
        "--sql-dir",
        default="epsg3857_pipeline/sql",
        help="SQL directory"
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=multiprocessing.cpu_count(),
        help="Number of threads"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=5000,
        help="Chunk size in meters"
    )
    
    args = parser.parse_args()
    
    # Run the pipeline
    if not run_pipeline(args.config, args.sql_dir, args.threads, args.chunk_size):
        logger.error("Failed to run the unified Delaunay pipeline")
        return 1
    
    logger.info("Unified Delaunay pipeline completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
