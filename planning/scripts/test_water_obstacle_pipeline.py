#!/usr/bin/env python3
"""
Test script for the water obstacle modeling pipeline.

This script:
1. Resets the database
2. Imports the Iowa subset data
3. Runs the water obstacle pipeline with the default configuration
4. Visualizes the results
5. Updates environmental conditions and visualizes again
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
        logging.FileHandler('test_pipeline.log')
    ]
)
logger = logging.getLogger('test_pipeline')


def run_command(cmd, check=True):
    """
    Run a command and log the output.
    
    Args:
        cmd: Command to run
        check: Whether to check the return code
    
    Returns:
        CompletedProcess object
    
    Raises:
        Exception: If command fails and check is True
    """
    logger.info(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=check
        )
        
        if result.stdout:
            logger.info(f"Command output: {result.stdout}")
        
        if result.stderr:
            logger.warning(f"Command error output: {result.stderr}")
        
        return result
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with return code {e.returncode}: {e}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command error output: {e.stderr}")
        
        if check:
            raise
        
        return e


def reset_database(subset_path):
    """
    Reset the database and import the subset data.
    
    Args:
        subset_path: Path to the subset data
    
    Raises:
        Exception: If reset fails
    """
    logger.info("Resetting database and importing subset data")
    
    # Reset the database
    run_command([
        "python", "scripts/reset_database.py",
        "--reset-all"
    ])
    
    # Import the subset data
    run_command([
        "python", "scripts/reset_database.py",
        "--reset-derived",
        "--import", subset_path
    ])


def run_pipeline(config_path, sql_dir):
    """
    Run the water obstacle pipeline.
    
    Args:
        config_path: Path to the configuration file
        sql_dir: Path to the SQL directory
    
    Raises:
        Exception: If pipeline fails
    """
    logger.info(f"Running water obstacle pipeline with config {config_path}")
    
    run_command([
        "python", "planning/scripts/run_water_obstacle_pipeline.py",
        "--config", config_path,
        "--sql-dir", sql_dir,
        "--verbose"
    ])


def visualize_results(output_file, title=None):
    """
    Visualize the results.
    
    Args:
        output_file: Path to save the visualization to
        title: Optional title for the visualization
    
    Raises:
        Exception: If visualization fails
    """
    logger.info(f"Visualizing results to {output_file}")
    
    cmd = [
        "python", "planning/scripts/visualize_water_obstacles.py",
        "--output", output_file,
        "--verbose"
    ]
    
    if title:
        cmd.extend(["--title", title])
    
    run_command(cmd)


def update_environmental_conditions(rainfall=None, temperature=None, snow_depth=None):
    """
    Update environmental conditions.
    
    Args:
        rainfall: Rainfall value (0.0-1.0)
        temperature: Temperature value (degrees C)
        snow_depth: Snow depth value (meters)
    
    Raises:
        Exception: If update fails
    """
    logger.info("Updating environmental conditions")
    
    cmd = [
        "python", "planning/scripts/update_environmental_conditions.py",
        "--verbose"
    ]
    
    if rainfall is not None:
        cmd.extend(["--rainfall", str(rainfall)])
    
    if temperature is not None:
        cmd.extend(["--temperature", str(temperature)])
    
    if snow_depth is not None:
        cmd.extend(["--snow-depth", str(snow_depth)])
    
    run_command(cmd)


def analyze_water_features():
    """
    Analyze water features and print statistics.
    
    Raises:
        Exception: If analysis fails
    """
    logger.info("Analyzing water features")
    
    # Create SQL queries to analyze water features
    queries = [
        """
        -- Analyze water features extraction
        SELECT feature_type, water_type, COUNT(*) 
        FROM water_features 
        GROUP BY feature_type, water_type 
        ORDER BY feature_type, water_type;
        """,
        """
        -- Analyze buffer decisions
        SELECT 
            buffer_rule_applied, 
            COUNT(*), 
            AVG(buffer_size_m) as avg_buffer_size,
            MIN(buffer_size_m) as min_buffer_size,
            MAX(buffer_size_m) as max_buffer_size
        FROM water_buf 
        GROUP BY buffer_rule_applied 
        ORDER BY buffer_rule_applied;
        """,
        """
        -- Analyze crossability decisions
        SELECT 
            crossability_rule_applied, 
            COUNT(*), 
            AVG(crossability) as avg_crossability,
            MIN(crossability) as min_crossability,
            MAX(crossability) as max_crossability
        FROM water_buf 
        GROUP BY crossability_rule_applied 
        ORDER BY crossability_rule_applied;
        """,
        """
        -- Analyze dissolved buffers
        SELECT 
            crossability_group, 
            buffer_rules_applied,
            crossability_rules_applied,
            COUNT(*) as count,
            MIN(crossability) as min_crossability,
            MAX(crossability) as max_crossability
        FROM water_buf_dissolved 
        GROUP BY crossability_group, buffer_rules_applied, crossability_rules_applied
        ORDER BY crossability_group;
        """
    ]
    
    # Create a temporary SQL file
    with open("temp_analysis.sql", "w") as f:
        f.write("\n".join(queries))
    
    # Run the SQL file
    run_command([
        "docker", "compose", "cp", "temp_analysis.sql", "db:/tmp/temp_analysis.sql"
    ])
    
    run_command([
        "docker", "compose", "exec", "db",
        "psql", "-U", "gis", "-d", "gis", "-f", "/tmp/temp_analysis.sql"
    ])
    
    # Clean up
    os.remove("temp_analysis.sql")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test the water obstacle modeling pipeline")
    parser.add_argument(
        "--subset",
        default="data/subsets/iowa-latest.osm_ia-central_r10.0km.osm.pbf",
        help="Path to the subset data"
    )
    parser.add_argument(
        "--config",
        default="planning/config/default_config.json",
        help="Path to the configuration file"
    )
    parser.add_argument(
        "--sql-dir",
        default="planning/sql",
        help="Path to the SQL directory"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory to save visualizations to"
    )
    parser.add_argument(
        "--skip-reset",
        action="store_true",
        help="Skip database reset and import"
    )
    parser.add_argument(
        "--skip-pipeline",
        action="store_true",
        help="Skip running the pipeline"
    )
    parser.add_argument(
        "--skip-visualization",
        action="store_true",
        help="Skip visualization"
    )
    parser.add_argument(
        "--skip-environmental",
        action="store_true",
        help="Skip environmental condition updates"
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
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        # Step 1: Reset database and import subset data
        if not args.skip_reset:
            reset_database(args.subset)
        
        # Step 2: Run the water obstacle pipeline
        if not args.skip_pipeline:
            run_pipeline(args.config, args.sql_dir)
        
        # Step 3: Analyze water features
        analyze_water_features()
        
        # Step 4: Visualize the results
        if not args.skip_visualization:
            visualize_results(
                os.path.join(args.output_dir, "water_obstacles_default.png"),
                "Water Obstacles - Default Conditions"
            )
        
        # Step 5: Update environmental conditions and visualize again
        if not args.skip_environmental:
            # Rainy conditions
            update_environmental_conditions(rainfall=0.8, temperature=20.0)
            
            if not args.skip_visualization:
                visualize_results(
                    os.path.join(args.output_dir, "water_obstacles_rainy.png"),
                    "Water Obstacles - Rainy Conditions"
                )
            
            # Winter conditions
            update_environmental_conditions(rainfall=0.0, temperature=-5.0, snow_depth=0.3)
            
            if not args.skip_visualization:
                visualize_results(
                    os.path.join(args.output_dir, "water_obstacles_winter.png"),
                    "Water Obstacles - Winter Conditions"
                )
        
        logger.info("Test completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
