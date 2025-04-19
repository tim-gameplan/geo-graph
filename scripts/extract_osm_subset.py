#!/usr/bin/env python3
"""
Extract a subset of OSM data around a specified location.

This script uses osmium to extract a bounding box around a specified location,
making it easier to work with smaller datasets during development.
"""

import argparse
import os
import subprocess
import math
import sys
from pathlib import Path

# Benchmark locations from the project plan
BENCHMARK_LOCATIONS = {
    "la-contrail": (-92.95, 31.14, "Region around Fort Johnson/JRTC in western Louisiana"),
    "ia-central": (-93.63, 41.99, "Iowa State → rural & interstate mix"),
    "ia-west": (-95.86, 41.26, "Council Bluffs / Omaha approaches"),
    "ca-ntc": (-116.68, 35.31, "Fort Irwin & National Training Center desert")
}

def km_to_degrees(km, latitude):
    """Convert kilometers to approximate degrees at the given latitude."""
    # Earth's radius in km
    earth_radius = 6371.0
    
    # Convert km to degrees longitude (varies with latitude)
    degrees_longitude = (km / (earth_radius * math.cos(math.radians(abs(latitude))) * math.pi / 180))
    
    # Convert km to degrees latitude (roughly constant)
    degrees_latitude = km / (earth_radius * math.pi / 180)
    
    return degrees_latitude, degrees_longitude

def create_bbox(lon, lat, radius_km):
    """Create a bounding box around the specified coordinates."""
    dlat, dlon = km_to_degrees(radius_km, lat)
    
    return {
        "min_lon": lon - dlon,
        "min_lat": lat - dlat,
        "max_lon": lon + dlon,
        "max_lat": lat + dlat
    }

def check_osmium():
    """Check if osmium is installed."""
    try:
        subprocess.run(["osmium", "--version"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def extract_osm_data(input_file, output_file, bbox):
    """Extract OSM data within the specified bounding box."""
    bbox_str = f"{bbox['min_lon']},{bbox['min_lat']},{bbox['max_lon']},{bbox['max_lat']}"
    
    cmd = [
        "osmium", "extract",
        "--bbox", bbox_str,
        "--strategy", "complete_ways",
        "-o", output_file,
        input_file
    ]
    
    print(f"Executing: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Successfully extracted data to {output_file}")
        return True
    except subprocess.SubprocessError as e:
        print(f"Error extracting data: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Extract a subset of OSM data around a specified location.")
    
    # Input/output options
    parser.add_argument("--input", "-i", required=True, help="Input OSM PBF file")
    parser.add_argument("--output-dir", "-o", default="data/subsets", help="Output directory for extracted data")
    
    # Location specification (either benchmark or coordinates)
    location_group = parser.add_mutually_exclusive_group(required=True)
    location_group.add_argument("--benchmark", "-b", choices=BENCHMARK_LOCATIONS.keys(),
                               help="Use a predefined benchmark location")
    location_group.add_argument("--coordinates", "-c", nargs=2, type=float, metavar=("LON", "LAT"),
                               help="Center coordinates (longitude latitude)")
    
    # Additional options
    parser.add_argument("--radius", "-r", type=float, default=10.0,
                       help="Radius in kilometers around the center point (default: 10)")
    parser.add_argument("--name", "-n", help="Custom name for the output file")
    
    args = parser.parse_args()
    
    # Check if osmium is installed
    if not check_osmium():
        print("Error: osmium is not installed or not in PATH.", file=sys.stderr)
        print("Please install osmium-tool: https://osmcode.org/osmium-tool/", file=sys.stderr)
        return 1
    
    # Get coordinates
    if args.benchmark:
        lon, lat, _ = BENCHMARK_LOCATIONS[args.benchmark]
        location_name = args.benchmark
    else:
        lon, lat = args.coordinates
        location_name = args.name or f"custom_{lon}_{lat}"
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate output filename
    input_filename = os.path.basename(args.input)
    input_basename = os.path.splitext(input_filename)[0]
    output_filename = f"{input_basename}_{location_name}_r{args.radius}km.osm.pbf"
    output_path = output_dir / output_filename
    
    # Create bounding box
    bbox = create_bbox(lon, lat, args.radius)
    
    # Print extraction information
    print(f"Extracting data around {lon}, {lat} with radius {args.radius} km")
    print(f"Bounding box: {bbox['min_lon']},{bbox['min_lat']},{bbox['max_lon']},{bbox['max_lat']}")
    print(f"Input file: {args.input}")
    print(f"Output file: {output_path}")
    
    # Extract data
    success = extract_osm_data(args.input, str(output_path), bbox)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
