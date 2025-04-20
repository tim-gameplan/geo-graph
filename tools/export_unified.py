#!/usr/bin/env python3
"""
Unified Export Script

This script combines the functionality of all export scripts:
1. Simple radius-based export
2. Isochrone-based export
3. Export with attributes
4. Export with water obstacle information

It provides a unified interface for all export operations.
"""

import os
import sys
import argparse
import logging
import importlib.util
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('unified_export.log')
    ]
)
logger = logging.getLogger('unified_export')


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


def export_simple(args):
    """
    Export a simple radius-based graph slice.
    
    Args:
        args: Command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("Exporting simple radius-based graph slice")
    
    # Import the export_slice_simple module
    export_path = os.path.join(os.path.dirname(__file__), "export_slice_simple.py")
    export_module = import_module_from_path("export_slice_simple", export_path)
    
    # Prepare arguments for export_slice_simple.main()
    export_args = argparse.Namespace(
        lon=args.lon,
        lat=args.lat,
        radius_km=args.radius,
        outfile=args.output
    )
    
    # Run the export
    try:
        return export_module.main(export_args)
    except Exception as e:
        logger.error(f"Error exporting simple slice: {e}")
        return 1


def export_enhanced(args):
    """
    Export an isochrone-based graph slice.
    
    Args:
        args: Command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("Exporting isochrone-based graph slice")
    
    # Import the export_slice_enhanced_fixed module
    export_path = os.path.join(os.path.dirname(__file__), "export_slice_enhanced_fixed.py")
    export_module = import_module_from_path("export_slice_enhanced_fixed", export_path)
    
    # Prepare arguments for export_slice_enhanced_fixed.main()
    export_args = argparse.Namespace(
        lon=args.lon,
        lat=args.lat,
        minutes=args.minutes,
        outfile=args.output,
        valhalla=args.valhalla,
        include_geometry=args.include_geometry
    )
    
    # Run the export
    try:
        return export_module.main(export_args)
    except Exception as e:
        logger.error(f"Error exporting enhanced slice: {e}")
        return 1


def export_with_attributes(args):
    """
    Export a graph slice with OSM attributes preserved.
    
    Args:
        args: Command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("Exporting graph slice with OSM attributes")
    
    # Import the export_slice_with_attributes module
    export_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "scripts/export_slice_with_attributes.py"
    )
    export_module = import_module_from_path("export_slice_with_attributes", export_path)
    
    # Prepare arguments for export_slice_with_attributes.main()
    export_args = argparse.Namespace(
        lon=args.lon,
        lat=args.lat,
        radius=args.radius,
        outfile=args.output,
        conn_string=args.conn_string
    )
    
    # Run the export
    try:
        return export_module.main(export_args)
    except Exception as e:
        logger.error(f"Error exporting slice with attributes: {e}")
        return 1


def export_with_water_obstacles(args):
    """
    Export a graph slice with water obstacle information.
    
    Args:
        args: Command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("Exporting graph slice with water obstacle information")
    
    # This is a placeholder for future implementation
    # Currently, we don't have a dedicated export script for water obstacles
    # Instead, we'll use the export_with_attributes script and add a note
    
    logger.warning("Export with water obstacles is not yet implemented")
    logger.warning("Using export with attributes as a fallback")
    
    return export_with_attributes(args)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Export Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export a simple radius-based slice
  python tools/export_unified.py --mode simple --lon -93.63 --lat 41.99 --radius 5
  
  # Export an isochrone-based slice
  python tools/export_unified.py --mode enhanced --lon -93.63 --lat 41.99 --minutes 60
  
  # Export a slice with OSM attributes
  python tools/export_unified.py --mode attributes --lon -93.63 --lat 41.99 --radius 5
  
  # Export a slice with water obstacle information
  python tools/export_unified.py --mode water --lon -93.63 --lat 41.99 --radius 5
"""
    )
    
    # Mode selection
    parser.add_argument(
        "--mode",
        choices=["simple", "enhanced", "attributes", "water"],
        default="simple",
        help="Export mode to use"
    )
    
    # Common arguments
    parser.add_argument(
        "--lon",
        type=float,
        required=True,
        help="Longitude coordinate"
    )
    parser.add_argument(
        "--lat",
        type=float,
        required=True,
        help="Latitude coordinate"
    )
    parser.add_argument(
        "--output",
        default="slice.graphml",
        help="Output file path"
    )
    parser.add_argument(
        "--conn-string",
        help="PostgreSQL connection string (default: from PG_URL environment variable)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    # Simple and attributes mode arguments
    parser.add_argument(
        "--radius",
        type=float,
        default=5.0,
        help="Radius in kilometers (for simple and attributes modes)"
    )
    
    # Enhanced mode arguments
    parser.add_argument(
        "--minutes",
        type=int,
        default=60,
        help="Travel time in minutes (for enhanced mode)"
    )
    parser.add_argument(
        "--valhalla",
        action="store_true",
        help="Export Valhalla tiles (for enhanced mode)"
    )
    parser.add_argument(
        "--include-geometry",
        action="store_true",
        help="Include geometry in the GraphML file (for enhanced mode)"
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Run the selected export mode
    if args.mode == "simple":
        return export_simple(args)
    elif args.mode == "enhanced":
        return export_enhanced(args)
    elif args.mode == "attributes":
        return export_with_attributes(args)
    elif args.mode == "water":
        return export_with_water_obstacles(args)
    else:
        logger.error(f"Unknown mode: {args.mode}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
