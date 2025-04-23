#!/usr/bin/env python3
"""
Unified EPSG:3857 Pipeline Runner

This script runs the complete EPSG:3857 pipeline:
1. Reset the database
2. Run the water obstacle pipeline with EPSG:3857
3. Export a graph slice
4. Visualize the results
"""

import os
import sys
import argparse
import logging
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('epsg3857_pipeline.log')
    ]
)
logger = logging.getLogger('epsg3857_pipeline')

def run_command(command, description):
    """Run a command and log the result."""
    logger.info(f"Running {description}: {command}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"✅ {description} completed successfully")
        logger.debug(f"Output: {result.stdout}")
        if result.stderr:
            logger.debug(f"Error output: {result.stderr}")
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False

def reset_database():
    """Reset the database."""
    return run_command(
        "python epsg3857_pipeline/scripts/reset_database.py --reset-derived",
        "Database reset"
    )

def run_water_obstacle_pipeline(mode="standard", config=None):
    """Run the water obstacle pipeline."""
    if mode == "standard":
        cmd = f"python epsg3857_pipeline/scripts/run_water_obstacle_pipeline_crs.py"
    elif mode == "delaunay":
        cmd = f"python epsg3857_pipeline/scripts/run_water_obstacle_pipeline_delaunay.py"
    else:
        logger.error(f"Unknown mode: {mode}")
        return False
    
    if config:
        cmd += f" --config {config}"
    
    cmd += f" --sql-dir epsg3857_pipeline/sql"
    
    return run_command(
        cmd,
        f"Water obstacle pipeline ({mode})"
    )

def run_unified_delaunay_pipeline(threads=4, chunk_size=5000):
    """Run the unified Delaunay pipeline."""
    cmd = f"python epsg3857_pipeline/scripts/run_unified_delaunay_pipeline.py"
    cmd += f" --threads {threads} --chunk-size {chunk_size}"
    cmd += f" --sql-dir epsg3857_pipeline/sql"
    
    return run_command(
        cmd,
        "Unified Delaunay pipeline"
    )

def export_slice(lon, lat, minutes, outfile):
    """Export a graph slice."""
    # Use our local copy of the export_slice script
    cmd = f"python epsg3857_pipeline/scripts/export_slice.py"
    cmd += f" --lon {lon} --lat {lat} --minutes {minutes} --outfile {outfile}"
    
    return run_command(
        cmd,
        "Export slice"
    )

def visualize_results(mode, input_file=None):
    """Visualize the results."""
    if mode == "graphml" and input_file:
        cmd = f"python epsg3857_pipeline/scripts/visualize.py --mode graphml --input {input_file}"
    elif mode == "water":
        cmd = f"python epsg3857_pipeline/scripts/visualize.py --mode water"
    elif mode == "delaunay":
        cmd = f"python epsg3857_pipeline/scripts/visualize_delaunay_triangulation.py"
    else:
        logger.error(f"Unknown visualization mode: {mode}")
        return False
    
    return run_command(
        cmd,
        f"Visualization ({mode})"
    )

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the EPSG:3857 pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run the standard EPSG:3857 pipeline
  python run_epsg3857_pipeline.py
  
  # Run the Delaunay triangulation pipeline
  python run_epsg3857_pipeline.py --mode delaunay
  
  # Run the unified Delaunay pipeline
  python run_epsg3857_pipeline.py --mode unified-delaunay
  
  # Export a graph slice
  python run_epsg3857_pipeline.py --export --lon -93.63 --lat 41.99 --minutes 60
"""
    )
    
    # Pipeline mode
    parser.add_argument(
        "--mode",
        choices=["standard", "delaunay", "unified-delaunay"],
        default="standard",
        help="Pipeline mode"
    )
    
    # Configuration
    parser.add_argument(
        "--config",
        default="epsg3857_pipeline/config/crs_standardized_config.json",
        help="Configuration file"
    )
    
    # Export options
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export a graph slice"
    )
    parser.add_argument(
        "--lon",
        type=float,
        default=-93.63,
        help="Longitude coordinate"
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=41.99,
        help="Latitude coordinate"
    )
    parser.add_argument(
        "--minutes",
        type=int,
        default=60,
        help="Travel time in minutes"
    )
    parser.add_argument(
        "--outfile",
        default="epsg3857_test.graphml",
        help="Output GraphML file"
    )
    
    # Visualization options
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Visualize the results"
    )
    parser.add_argument(
        "--viz-mode",
        choices=["graphml", "water", "delaunay"],
        default="graphml",
        help="Visualization mode"
    )
    
    # Unified Delaunay options
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Number of threads for unified Delaunay pipeline"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=5000,
        help="Chunk size in meters for unified Delaunay pipeline"
    )
    
    # Skip options
    parser.add_argument(
        "--skip-reset",
        action="store_true",
        help="Skip database reset"
    )
    parser.add_argument(
        "--skip-pipeline",
        action="store_true",
        help="Skip pipeline execution"
    )
    
    args = parser.parse_args()
    
    # Reset the database
    if not args.skip_reset:
        if not reset_database():
            logger.error("Failed to reset the database")
            return 1
    
    # Run the pipeline
    if not args.skip_pipeline:
        if args.mode == "standard" or args.mode == "delaunay":
            if not run_water_obstacle_pipeline(args.mode, args.config):
                logger.error(f"Failed to run the {args.mode} pipeline")
                return 1
        elif args.mode == "unified-delaunay":
            if not run_unified_delaunay_pipeline(args.threads, args.chunk_size):
                logger.error("Failed to run the unified Delaunay pipeline")
                return 1
    
    # Export a graph slice
    if args.export:
        if not export_slice(args.lon, args.lat, args.minutes, args.outfile):
            logger.error("Failed to export a graph slice")
            return 1
    
    # Visualize the results
    if args.visualize:
        input_file = args.outfile if args.viz_mode == "graphml" and args.export else None
        if not visualize_results(args.viz_mode, input_file):
            logger.error("Failed to visualize the results")
            return 1
    
    logger.info("EPSG:3857 pipeline completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
