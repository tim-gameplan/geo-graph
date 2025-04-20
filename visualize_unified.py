#!/usr/bin/env python3
"""
Unified Visualization Script

This script provides a unified interface for all visualization operations:
1. GraphML visualization
2. Water obstacle visualization
3. Combined visualization
"""

import os
import sys
import argparse
import logging
import importlib.util
import subprocess
from pathlib import Path
from utils.file_management import get_visualization_path, get_log_path

# Configure logging
log_path = get_log_path("unified_visualization")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_path)
    ]
)
logger = logging.getLogger('unified_visualization')


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


def visualize_graphml(args):
    """
    Visualize a GraphML file.
    
    Args:
        args: Command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info(f"Visualizing GraphML file: {args.input}")
    
    # Import the visualize_graph module
    visualize_graph_path = os.path.join(os.path.dirname(__file__), "visualize_graph.py")
    visualize_graph = import_module_from_path("visualize_graph", visualize_graph_path)
    
    # Prepare arguments for visualize_graph.visualize_graph()
    try:
        output_file = visualize_graph.visualize_graph(
            args.input,
            args.output,
            args.title,
            args.dpi,
            args.show_labels
        )
        
        return 0
    except Exception as e:
        logger.error(f"Error visualizing GraphML: {e}")
        return 1


def visualize_water(args):
    """
    Visualize water obstacles.
    
    Args:
        args: Command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("Visualizing water obstacles")
    
    # Import the visualize_water_obstacles module
    visualize_water_path = os.path.join(
        os.path.dirname(__file__),
        "planning/scripts/visualize_water_obstacles.py"
    )
    
    # Build command
    cmd = [
        "python", visualize_water_path,
        "--output", args.output if args.output else get_visualization_path(
            viz_type='water',
            description='water_obstacles',
            parameters={'dpi': args.dpi}
        ),
        "--dpi", str(args.dpi)
    ]
    
    if args.title:
        cmd.extend(["--title", args.title])
    
    if args.show_labels:
        cmd.append("--show-labels")
    
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
        logger.error(f"Error visualizing water obstacles: {e}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command error output: {e.stderr}")
        return e.returncode


def visualize_combined(args):
    """
    Create a combined visualization.
    
    Args:
        args: Command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("Creating combined visualization")
    
    # First, visualize the GraphML file
    graphml_result = visualize_graphml(args)
    if graphml_result != 0:
        logger.error("Failed to visualize GraphML file")
        return graphml_result
    
    # Then, visualize the water obstacles
    water_result = visualize_water(args)
    if water_result != 0:
        logger.error("Failed to visualize water obstacles")
        return water_result
    
    logger.info("Combined visualization completed successfully")
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Visualization Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Visualize a GraphML file
  python visualize_unified.py --mode graphml --input slice.graphml
  
  # Visualize water obstacles
  python visualize_unified.py --mode water
  
  # Create a combined visualization
  python visualize_unified.py --mode combined --input slice.graphml
"""
    )
    
    # Mode selection
    parser.add_argument(
        "--mode",
        choices=["graphml", "water", "combined"],
        default="graphml",
        help="Visualization mode"
    )
    
    # Common arguments
    parser.add_argument(
        "--input",
        help="Path to the input file (required for graphml and combined modes)"
    )
    parser.add_argument(
        "--output",
        help="Path to save the visualization"
    )
    parser.add_argument(
        "--title",
        help="Title for the visualization"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI for the output image"
    )
    parser.add_argument(
        "--show-labels",
        action="store_true",
        help="Show node labels"
    )
    
    args = parser.parse_args()
    
    # Check required arguments
    if args.mode in ["graphml", "combined"] and not args.input:
        parser.error(f"--input is required for {args.mode} mode")
    
    # Run the selected visualization
    if args.mode == "graphml":
        return visualize_graphml(args)
    elif args.mode == "water":
        return visualize_water(args)
    elif args.mode == "combined":
        return visualize_combined(args)
    else:
        logger.error(f"Unknown mode: {args.mode}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
