#!/usr/bin/env python3
"""
Unified Pipeline Script

This script can run any of the three pipelines:
1. Standard terrain graph pipeline
2. Enhanced terrain graph pipeline
3. Water obstacle modeling pipeline

It provides a unified interface for all pipeline operations.
"""

import os
import sys
import argparse
import logging
import importlib.util
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('unified_pipeline.log')
    ]
)
logger = logging.getLogger('unified_pipeline')


def import_module_from_path(module_name, file_path):
    """
    Import a module from a file path.
    
    Args:
        module_name: Name to give the imported module
        file_path: Path to the Python file
    
    Returns:
        The imported module
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_standard_pipeline(args):
    """
    Run the standard terrain graph pipeline.
    
    Args:
        args: Command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("Running standard terrain graph pipeline")
    
    # Import the run_pipeline module
    run_pipeline_path = os.path.join(os.path.dirname(__file__), "run_pipeline.py")
    run_pipeline = import_module_from_path("run_pipeline", run_pipeline_path)
    
    # Prepare arguments for run_pipeline.main()
    pipeline_args = argparse.Namespace(
        sql_dir=args.sql_dir,
        preserve_attributes=args.preserve_attributes,
        export=args.export,
        lon=args.lon,
        lat=args.lat,
        radius=args.radius,
        output=args.output
    )
    
    # Run the pipeline
    try:
        return run_pipeline.main(pipeline_args)
    except Exception as e:
        logger.error(f"Error running standard pipeline: {e}")
        return 1


def run_enhanced_pipeline(args):
    """
    Run the enhanced terrain graph pipeline.
    
    Args:
        args: Command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("Running enhanced terrain graph pipeline")
    
    # Import the run_pipeline_enhanced module
    run_pipeline_path = os.path.join(os.path.dirname(__file__), "run_pipeline_enhanced.py")
    run_pipeline = import_module_from_path("run_pipeline_enhanced", run_pipeline_path)
    
    # Prepare arguments for run_pipeline_enhanced.main()
    pipeline_args = argparse.Namespace(
        sql_dir=args.sql_dir,
        enhanced=True,
        export=args.export,
        lon=args.lon,
        lat=args.lat,
        minutes=args.minutes,
        output=args.output
    )
    
    # Run the pipeline
    try:
        return run_pipeline.main(pipeline_args)
    except Exception as e:
        logger.error(f"Error running enhanced pipeline: {e}")
        return 1


def run_water_obstacle_pipeline(args):
    """
    Run the water obstacle modeling pipeline.
    
    Args:
        args: Command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("Running water obstacle modeling pipeline")
    
    # Import the run_water_obstacle_pipeline module
    run_pipeline_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "planning/scripts/run_water_obstacle_pipeline.py"
    )
    run_pipeline = import_module_from_path("run_water_obstacle_pipeline", run_pipeline_path)
    
    # Prepare arguments for run_water_obstacle_pipeline.main()
    pipeline_args = argparse.Namespace(
        config=args.config,
        sql_dir=args.water_sql_dir,
        conn_string=args.conn_string,
        skip=args.skip,
        verbose=args.verbose
    )
    
    # Run the pipeline
    try:
        # Set the command-line arguments
        sys.argv = [
            "run_water_obstacle_pipeline.py",
            "--config", os.path.join(os.path.dirname(os.path.dirname(__file__)), args.config),
            "--sql-dir", os.path.join(os.path.dirname(os.path.dirname(__file__)), args.water_sql_dir)
        ]
        
        if args.conn_string:
            sys.argv.extend(["--conn-string", args.conn_string])
        
        if args.skip:
            sys.argv.extend(["--skip"] + args.skip)
        
        if args.verbose:
            sys.argv.append("--verbose")
        
        # Run the main function
        return run_pipeline.main()
    except Exception as e:
        logger.error(f"Error running water obstacle pipeline: {e}")
        return 1


def run_test_pipeline(args):
    """
    Run the test pipeline for water obstacle modeling.
    
    Args:
        args: Command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("Running water obstacle test pipeline")
    
    # Import the test_water_obstacle_pipeline module
    test_pipeline_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "planning/scripts/test_water_obstacle_pipeline.py"
    )
    
    # Build command
    cmd = [
        "python", test_pipeline_path,
        "--subset", args.subset,
        "--config", args.config,
        "--sql-dir", args.water_sql_dir,
        "--output-dir", args.output_dir
    ]
    
    if args.skip_reset:
        cmd.append("--skip-reset")
    
    if args.skip_pipeline:
        cmd.append("--skip-pipeline")
    
    if args.skip_visualization:
        cmd.append("--skip-visualization")
    
    if args.skip_environmental:
        cmd.append("--skip-environmental")
    
    if args.verbose:
        cmd.append("--verbose")
    
    # Run the command
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        logger.info(result.stdout)
        if result.stderr:
            logger.warning(result.stderr)
        
        return 0
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running test pipeline: {e}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command error output: {e.stderr}")
        return e.returncode


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Pipeline Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run standard pipeline
  python scripts/run_unified_pipeline.py --mode standard
  
  # Run enhanced pipeline with export
  python scripts/run_unified_pipeline.py --mode enhanced --export --lon -93.63 --lat 41.99 --minutes 60
  
  # Run water obstacle pipeline
  python scripts/run_unified_pipeline.py --mode water --config planning/config/default_config.json
  
  # Run water obstacle test pipeline
  python scripts/run_unified_pipeline.py --mode test --skip-reset
"""
    )
    
    # Mode selection
    parser.add_argument(
        "--mode",
        choices=["standard", "enhanced", "water", "test"],
        default="standard",
        help="Pipeline mode to run"
    )
    
    # Common arguments
    parser.add_argument(
        "--sql-dir",
        default="sql",
        help="Directory containing SQL scripts for standard/enhanced pipelines"
    )
    parser.add_argument(
        "--water-sql-dir",
        default="planning/sql",
        help="Directory containing SQL scripts for water pipeline"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    # Standard pipeline arguments
    parser.add_argument(
        "--preserve-attributes",
        action="store_true",
        help="Preserve OSM attributes in the road and water tables (standard pipeline)"
    )
    
    # Export arguments
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export a slice after running the pipeline"
    )
    parser.add_argument(
        "--lon",
        type=float,
        help="Longitude for export"
    )
    parser.add_argument(
        "--lat",
        type=float,
        help="Latitude for export"
    )
    parser.add_argument(
        "--radius",
        type=float,
        default=5.0,
        help="Radius in kilometers for export (standard pipeline)"
    )
    parser.add_argument(
        "--minutes",
        type=int,
        default=60,
        help="Travel time in minutes for export (enhanced pipeline)"
    )
    parser.add_argument(
        "--output",
        default="slice.graphml",
        help="Output file for export"
    )
    
    # Water pipeline arguments
    parser.add_argument(
        "--config",
        default="planning/config/default_config.json",
        help="Path to configuration JSON file (water pipeline)"
    )
    parser.add_argument(
        "--conn-string",
        help="PostgreSQL connection string (water pipeline)"
    )
    parser.add_argument(
        "--skip",
        nargs="+",
        help="Steps to skip in water pipeline (e.g., 01 02)"
    )
    
    # Test pipeline arguments
    parser.add_argument(
        "--subset",
        default="data/subsets/iowa-latest.osm_ia-central_r10.0km.osm.pbf",
        help="Path to the subset data (test pipeline)"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory to save visualizations to (test pipeline)"
    )
    parser.add_argument(
        "--skip-reset",
        action="store_true",
        help="Skip database reset and import (test pipeline)"
    )
    parser.add_argument(
        "--skip-pipeline",
        action="store_true",
        help="Skip running the pipeline (test pipeline)"
    )
    parser.add_argument(
        "--skip-visualization",
        action="store_true",
        help="Skip visualization (test pipeline)"
    )
    parser.add_argument(
        "--skip-environmental",
        action="store_true",
        help="Skip environmental condition updates (test pipeline)"
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Run the selected pipeline
    if args.mode == "standard":
        return run_standard_pipeline(args)
    elif args.mode == "enhanced":
        return run_enhanced_pipeline(args)
    elif args.mode == "water":
        return run_water_obstacle_pipeline(args)
    elif args.mode == "test":
        return run_test_pipeline(args)
    else:
        logger.error(f"Unknown mode: {args.mode}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
