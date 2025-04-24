#!/usr/bin/env python3
"""
Obstacle Boundary Pipeline Runner

This script runs the complete pipeline to generate a terrain graph with water obstacles
using the direct water boundary conversion approach.
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
        logging.FileHandler('obstacle_boundary_pipeline.log')
    ]
)
logger = logging.getLogger('obstacle_boundary_pipeline')

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
        
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        elapsed_time = time.time() - start_time
        logger.error(f"❌ {description} failed after {elapsed_time:.2f} seconds: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False, e.stderr

def reset_database(args):
    """Reset the database."""
    if args.skip_reset:
        logger.info("Skipping database reset")
        return True
    
    return run_command(
        f"python {args.scripts_dir}/reset_database.py --reset-derived",
        "Database reset"
    )[0]

def import_osm_data(args):
    """Import OSM data."""
    if args.skip_import:
        logger.info("Skipping OSM data import")
        return True
    
    if not args.osm_file:
        logger.error("OSM file not specified")
        return False
    
    return run_command(
        f"python {args.scripts_dir}/import_osm_data.py --osm-file {args.osm_file} --container {args.container}",
        "OSM data import"
    )[0]

def run_standard_pipeline(args):
    """Run the standard pipeline."""
    if args.skip_standard:
        logger.info("Skipping standard pipeline")
        return True
    
    return run_command(
        f"python {args.pipeline_dir}/run_epsg3857_pipeline.py --mode standard --skip-reset --config {args.config}",
        "Standard pipeline"
    )[0]

def run_obstacle_boundary_graph(args):
    """Run the obstacle boundary graph creation."""
    if args.skip_boundary:
        logger.info("Skipping obstacle boundary graph creation")
        return True
    
    cmd = f"python {args.scripts_dir}/run_obstacle_boundary_graph.py"
    if args.max_connection_distance:
        cmd += f" --max-connection-distance {args.max_connection_distance}"
    if args.water_speed_factor:
        cmd += f" --water-speed-factor {args.water_speed_factor}"
    
    return run_command(
        cmd,
        "Obstacle boundary graph creation"
    )[0]

def visualize_results(args):
    """Visualize the results."""
    if args.skip_visualize:
        logger.info("Skipping visualization")
        return True
    
    cmd = f"python {args.scripts_dir}/visualize_obstacle_boundary_graph.py"
    if args.show_unified:
        cmd += " --show-unified"
    if args.output:
        cmd += f" --output {args.output}"
    
    success, _ = run_command(
        cmd,
        "Visualization"
    )
    
    if success and args.open_visualization:
        # Find the most recent visualization file
        visualizations_dir = Path(f"{args.pipeline_dir}/visualizations")
        if not visualizations_dir.exists():
            logger.warning(f"Visualizations directory not found: {visualizations_dir}")
            return success
        
        visualization_files = list(visualizations_dir.glob("*_obstacle_boundary_graph.png"))
        if not visualization_files:
            logger.warning("No visualization files found")
            return success
        
        most_recent = max(visualization_files, key=os.path.getctime)
        run_command(
            f"open {most_recent}",
            "Opening visualization"
        )
    
    return success

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the obstacle boundary pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run the complete pipeline
  python run_obstacle_boundary_pipeline.py --osm-file data/subsets/iowa-latest.osm_ia-central_r10.0km.osm.pbf
  
  # Skip database reset and OSM import
  python run_obstacle_boundary_pipeline.py --skip-reset --skip-import
  
  # Run only the obstacle boundary graph creation and visualization
  python run_obstacle_boundary_pipeline.py --skip-reset --skip-import --skip-standard
  
  # Customize the obstacle boundary graph parameters
  python run_obstacle_boundary_pipeline.py --max-connection-distance 500 --water-speed-factor 0.3
"""
    )
    
    # Directory options
    parser.add_argument(
        "--pipeline-dir",
        default="epsg3857_pipeline",
        help="Pipeline directory"
    )
    parser.add_argument(
        "--scripts-dir",
        default="epsg3857_pipeline/scripts",
        help="Scripts directory"
    )
    parser.add_argument(
        "--config",
        default="epsg3857_pipeline/config/crs_standardized_config_improved.json",
        help="Configuration file for the standard pipeline"
    )
    
    # OSM data options
    parser.add_argument(
        "--osm-file",
        help="OSM file to import"
    )
    parser.add_argument(
        "--container",
        default="geo-graph-db-1",
        help="Docker container name"
    )
    
    # Obstacle boundary graph options
    parser.add_argument(
        "--max-connection-distance",
        type=float,
        help="Maximum distance for connecting terrain points to boundary nodes"
    )
    parser.add_argument(
        "--water-speed-factor",
        type=float,
        help="Speed factor for water edges"
    )
    
    # Visualization options
    parser.add_argument(
        "--show-unified",
        action="store_true",
        help="Show unified graph in visualization"
    )
    parser.add_argument(
        "--output",
        help="Output file for visualization"
    )
    parser.add_argument(
        "--open-visualization",
        action="store_true",
        help="Open the visualization after creating it"
    )
    
    # Skip options
    parser.add_argument(
        "--skip-reset",
        action="store_true",
        help="Skip database reset"
    )
    parser.add_argument(
        "--skip-import",
        action="store_true",
        help="Skip OSM data import"
    )
    parser.add_argument(
        "--skip-standard",
        action="store_true",
        help="Skip standard pipeline"
    )
    parser.add_argument(
        "--skip-boundary",
        action="store_true",
        help="Skip obstacle boundary graph creation"
    )
    parser.add_argument(
        "--skip-visualize",
        action="store_true",
        help="Skip visualization"
    )
    
    args = parser.parse_args()
    
    # Run the pipeline
    if not reset_database(args):
        logger.error("Failed to reset the database")
        return 1
    
    if not import_osm_data(args):
        logger.error("Failed to import OSM data")
        return 1
    
    if not run_standard_pipeline(args):
        logger.error("Failed to run the standard pipeline")
        return 1
    
    if not run_obstacle_boundary_graph(args):
        logger.error("Failed to create the obstacle boundary graph")
        return 1
    
    if not visualize_results(args):
        logger.error("Failed to visualize the results")
        return 1
    
    logger.info("Obstacle boundary pipeline completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
