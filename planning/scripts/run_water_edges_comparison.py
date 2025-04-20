#!/usr/bin/env python3
"""
Script to run the water edges comparison pipeline.

This script:
1. Runs the SQL file to create water edges from both original and dissolved buffers
2. Runs the visualization script to compare the results
"""

import os
import sys
import argparse
import logging
import subprocess
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import file management utilities
from utils.file_management import get_log_path

# Configure logging
log_path = get_log_path("water_edges_comparison")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_path)
    ]
)
logger = logging.getLogger('water_edges_comparison')


def run_sql_file(sql_file: str) -> bool:
    """
    Run a SQL file using the run_sql_queries.py script.
    
    Args:
        sql_file: Path to the SQL file
    
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Running SQL file: {sql_file}")
    
    try:
        # Get the absolute path to the SQL file
        sql_file_path = os.path.abspath(sql_file)
        
        # Get the path to the run_sql_queries.py script
        run_sql_queries_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', '..', 'scripts', 'run_sql_queries.py'
        ))
        
        # Run the SQL file
        cmd = [
            'python',
            run_sql_queries_path,
            '--file',
            sql_file_path
        ]
        
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Error running SQL file: {result.stderr}")
            return False
        
        logger.info(f"SQL file executed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error running SQL file: {e}")
        return False


def run_visualization(output_file: str = None, dpi: int = 300) -> bool:
    """
    Run the visualization script.
    
    Args:
        output_file: Path to save the visualization to
        dpi: DPI for the output image
    
    Returns:
        True if successful, False otherwise
    """
    logger.info("Running visualization script")
    
    try:
        # Get the path to the visualization script
        visualization_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 'visualize_water_edges_comparison.py'
        ))
        
        # Build the command
        cmd = [
            'python',
            visualization_path,
            '--dpi',
            str(dpi)
        ]
        
        if output_file:
            cmd.extend(['--output', output_file])
        
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Error running visualization script: {result.stderr}")
            return False
        
        logger.info(f"Visualization script executed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error running visualization script: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run the water edges comparison pipeline")
    parser.add_argument(
        "--sql-file",
        default="planning/sql/06_create_water_edges_comparison.sql",
        help="Path to the SQL file (default: planning/sql/06_create_water_edges_comparison.sql)"
    )
    parser.add_argument(
        "--output",
        help="Output file path for the visualization (default: auto-generated with timestamp)"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI for the output image (default: 300)"
    )
    parser.add_argument(
        "--skip-sql",
        action="store_true",
        help="Skip running the SQL file"
    )
    parser.add_argument(
        "--skip-visualization",
        action="store_true",
        help="Skip running the visualization script"
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
    
    # Run the SQL file
    if not args.skip_sql:
        if not run_sql_file(args.sql_file):
            logger.error("Failed to run SQL file")
            return 1
    
    # Run the visualization script
    if not args.skip_visualization:
        if not run_visualization(args.output, args.dpi):
            logger.error("Failed to run visualization script")
            return 1
    
    logger.info("Water edges comparison pipeline completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
