#!/usr/bin/env python3
"""
Unified Visualization Script

This script can visualize:
1. GraphML files (terrain graph)
2. Water obstacles and terrain grid
3. Combined visualizations

It provides a unified interface for all visualization operations.
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
        logging.FileHandler('unified_visualization.log')
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
    visualize_path = os.path.join(os.path.dirname(__file__), "visualize_graph.py")
    visualize_module = import_module_from_path("visualize_graph", visualize_path)
    
    # Prepare arguments for visualize_graph.main()
    visualize_args = argparse.Namespace(
        input=args.input,
        output=args.output,
        title=args.title,
        dpi=args.dpi,
        node_size=args.node_size,
        edge_width=args.edge_width,
        show_labels=args.show_labels
    )
    
    # Run the visualization
    try:
        return visualize_module.main(visualize_args)
    except Exception as e:
        logger.error(f"Error visualizing GraphML file: {e}")
        return 1


def visualize_water_obstacles(args):
    """
    Visualize water obstacles and terrain grid.
    
    Args:
        args: Command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("Visualizing water obstacles and terrain grid")
    
    # Import the visualize_water_obstacles module
    visualize_path = os.path.join(
        os.path.dirname(__file__),
        "planning/scripts/visualize_water_obstacles.py"
    )
    
    # Build command
    cmd = [
        "python", visualize_path,
        "--output", args.output
    ]
    
    if args.title:
        cmd.extend(["--title", args.title])
    
    if args.conn_string:
        cmd.extend(["--conn-string", args.conn_string])
    
    if args.extent:
        cmd.extend(["--extent", args.extent])
    
    if args.no_terrain_grid:
        cmd.append("--no-terrain-grid")
    
    if args.no_terrain_edges:
        cmd.append("--no-terrain-edges")
    
    if args.no_water_edges:
        cmd.append("--no-water-edges")
    
    if args.no_decision_info:
        cmd.append("--no-decision-info")
    
    if args.dpi:
        cmd.extend(["--dpi", str(args.dpi)])
    
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
        logger.error(f"Error visualizing water obstacles: {e}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command error output: {e.stderr}")
        return e.returncode


def visualize_combined(args):
    """
    Create a combined visualization of GraphML and water obstacles.
    
    Args:
        args: Command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("Creating combined visualization")
    
    # This is a placeholder for future implementation
    # Currently, we don't have a dedicated combined visualization
    # Instead, we'll create separate visualizations
    
    logger.warning("Combined visualization is not yet implemented")
    logger.warning("Creating separate visualizations instead")
    
    # Create water obstacles visualization
    water_result = visualize_water_obstacles(args)
    if water_result != 0:
        return water_result
    
    # If a GraphML file is provided, visualize it too
    if args.input:
        # Modify the output filename for the GraphML visualization
        base, ext = os.path.splitext(args.output)
        graphml_output = f"{base}_graphml{ext}"
        
        # Create a copy of args with the modified output
        graphml_args = argparse.Namespace(**vars(args))
        graphml_args.output = graphml_output
        
        graphml_result = visualize_graphml(graphml_args)
        if graphml_result != 0:
            return graphml_result
    
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Visualization Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Visualize a GraphML file
  python visualize_unified.py --mode graphml --input slice.graphml --output slice_viz.png
  
  # Visualize water obstacles
  python visualize_unified.py --mode water --output water_viz.png
  
  # Create a combined visualization
  python visualize_unified.py --mode combined --input slice.graphml --output combined_viz.png
"""
    )
    
    # Mode selection
    parser.add_argument(
        "--mode",
        choices=["graphml", "water", "combined"],
        default="graphml",
        help="Visualization mode to use"
    )
    
    # Common arguments
    parser.add_argument(
        "--output",
        default="visualization.png",
        help="Output file path"
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
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    # GraphML mode arguments
    parser.add_argument(
        "--input",
        help="Input GraphML file (for graphml and combined modes)"
    )
    parser.add_argument(
        "--node-size",
        type=int,
        default=10,
        help="Node size for GraphML visualization"
    )
    parser.add_argument(
        "--edge-width",
        type=float,
        default=0.5,
        help="Edge width for GraphML visualization"
    )
    parser.add_argument(
        "--show-labels",
        action="store_true",
        help="Show node labels in GraphML visualization"
    )
    
    # Water obstacles mode arguments
    parser.add_argument(
        "--conn-string",
        help="PostgreSQL connection string (for water and combined modes)"
    )
    parser.add_argument(
        "--extent",
        help="Bounding box to limit the visualization (min_x,min_y,max_x,max_y)"
    )
    parser.add_argument(
        "--no-terrain-grid",
        action="store_true",
        help="Don't show the terrain grid"
    )
    parser.add_argument(
        "--no-terrain-edges",
        action="store_true",
        help="Don't show the terrain edges"
    )
    parser.add_argument(
        "--no-water-edges",
        action="store_true",
        help="Don't show the water edges"
    )
    parser.add_argument(
        "--no-decision-info",
        action="store_true",
        help="Don't show the decision tracking information"
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Validate arguments
    if args.mode in ["graphml", "combined"] and not args.input:
        logger.error(f"Input GraphML file is required for {args.mode} mode")
        return 1
    
    # Run the selected visualization mode
    if args.mode == "graphml":
        return visualize_graphml(args)
    elif args.mode == "water":
        return visualize_water_obstacles(args)
    elif args.mode == "combined":
        return visualize_combined(args)
    else:
        logger.error(f"Unknown mode: {args.mode}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
