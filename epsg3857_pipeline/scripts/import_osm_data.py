#!/usr/bin/env python3
"""
OSM Data Import Script

This script imports OpenStreetMap (OSM) data into a PostGIS database.
It handles the entire import process, including:
1. Checking if required extensions are installed in the database
2. Installing missing extensions
3. Checking if required tools are installed in the Docker container
4. Installing missing tools
5. Importing the OSM data using osm2pgsql
6. Providing detailed logging and error handling
"""

import os
import sys
import argparse
import logging
import subprocess
import tempfile
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('import_osm_data.log')
    ]
)
logger = logging.getLogger('import_osm_data')

def run_command(command, description, container=None, check=True):
    """Run a command and log the result."""
    if container:
        command = f"docker exec {container} {command}"
    
    logger.info(f"Running {description}: {command}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if check:
            logger.info(f"✅ {description} completed successfully")
        
        logger.debug(f"Output: {result.stdout}")
        if result.stderr:
            logger.debug(f"Error output: {result.stderr}")
        
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        if check:
            raise
        return e

def check_extension(extension, container, db, user):
    """Check if an extension is installed in the database."""
    logger.info(f"Checking if {extension} extension is installed...")
    
    result = run_command(
        f"psql -U {user} -d {db} -c \"SELECT extname FROM pg_extension WHERE extname = '{extension}'\"",
        f"Check {extension} extension",
        container,
        check=False
    )
    
    if extension in result.stdout:
        logger.info(f"✅ {extension} extension is already installed")
        return True
    else:
        logger.warning(f"⚠️ {extension} extension is not installed")
        return False

def install_extension(extension, container, db, user):
    """Install an extension in the database."""
    logger.info(f"Installing {extension} extension...")
    
    run_command(
        f"psql -U {user} -d {db} -c \"CREATE EXTENSION IF NOT EXISTS {extension}\"",
        f"Install {extension} extension",
        container
    )
    
    logger.info(f"✅ {extension} extension installed successfully")
    return True

def check_tool(tool, container):
    """Check if a tool is installed in the Docker container."""
    logger.info(f"Checking if {tool} is installed...")
    
    result = run_command(
        f"which {tool}",
        f"Check {tool}",
        container,
        check=False
    )
    
    if result.returncode == 0:
        logger.info(f"✅ {tool} is already installed")
        return True
    else:
        logger.warning(f"⚠️ {tool} is not installed")
        return False

def install_tool(tool, container):
    """Install a tool in the Docker container."""
    logger.info(f"Installing {tool}...")
    
    run_command(
        f"apt-get update && apt-get install -y {tool}",
        f"Install {tool}",
        container
    )
    
    logger.info(f"✅ {tool} installed successfully")
    return True

def copy_file_to_container(file_path, container, dest_path="/tmp"):
    """Copy a file to the Docker container."""
    logger.info(f"Copying {file_path} to {container}:{dest_path}...")
    
    run_command(
        f"docker cp {file_path} {container}:{dest_path}",
        f"Copy {file_path} to container"
    )
    
    container_file_path = f"{dest_path}/{os.path.basename(file_path)}"
    logger.info(f"✅ File copied to {container}:{container_file_path}")
    return container_file_path

def import_osm_data(osm_file, container, db, user):
    """Import OSM data into the database using osm2pgsql."""
    logger.info(f"Importing OSM data from {osm_file}...")
    
    # Copy the OSM file to the container
    container_file_path = copy_file_to_container(osm_file, container)
    
    # Import the OSM data
    run_command(
        f"osm2pgsql --create --database {db} --username {user} --hstore --latlong {container_file_path}",
        "Import OSM data",
        container
    )
    
    # Clean up the temporary file
    run_command(
        f"rm {container_file_path}",
        "Clean up temporary file",
        container
    )
    
    logger.info(f"✅ OSM data imported successfully")
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Import OpenStreetMap (OSM) data into a PostGIS database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import OSM data from a PBF file
  python import_osm_data.py --osm-file data/subsets/iowa-latest.osm_ia-central_r10.0km.osm.pbf
  
  # Specify a different container name
  python import_osm_data.py --osm-file data/subsets/iowa-latest.osm_ia-central_r10.0km.osm.pbf --container geo-graph-db-1
  
  # Enable verbose logging
  python import_osm_data.py --osm-file data/subsets/iowa-latest.osm_ia-central_r10.0km.osm.pbf --verbose
"""
    )
    
    parser.add_argument(
        "--osm-file",
        required=True,
        help="Path to the OSM data file (.osm, .osm.pbf, .osm.bz2)"
    )
    parser.add_argument(
        "--container",
        default="db",
        help="Name of the Docker container running PostgreSQL/PostGIS"
    )
    parser.add_argument(
        "--db",
        default="gis",
        help="Name of the database"
    )
    parser.add_argument(
        "--user",
        default="gis",
        help="Username for the database"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    try:
        # Check if the OSM file exists
        if not os.path.exists(args.osm_file):
            logger.error(f"❌ OSM file not found: {args.osm_file}")
            return 1
        
        # Check if the container is running
        result = run_command(
            f"docker ps --filter name={args.container} --format '{{{{.Names}}}}'",
            "Check if container is running",
            check=False
        )
        
        if args.container not in result.stdout:
            logger.error(f"❌ Container not found or not running: {args.container}")
            return 1
        
        # Check and install required extensions
        required_extensions = ["postgis", "pgrouting", "hstore"]
        for extension in required_extensions:
            if not check_extension(extension, args.container, args.db, args.user):
                install_extension(extension, args.container, args.db, args.user)
        
        # Check and install required tools
        required_tools = ["osm2pgsql"]
        for tool in required_tools:
            if not check_tool(tool, args.container):
                install_tool(tool, args.container)
        
        # Import the OSM data
        import_osm_data(args.osm_file, args.container, args.db, args.user)
        
        logger.info("✅ OSM data import completed successfully")
        return 0
    except Exception as e:
        logger.error(f"❌ An error occurred: {e}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
