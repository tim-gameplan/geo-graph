# EPSG Consistency Implementation Plan - Part 4: Integration and Conclusion

**Date:** April 21, 2025  
**Author:** Cline  
**Project:** Terrain System - Geo-Graph  

This document is the final part of the EPSG Consistency Implementation Plan, focusing on integration with existing code and conclusion.

## Phase 7: Integration with Existing Code (Week 4)

### 7.1 Update Unified Pipeline Script

Update `scripts/run_unified_pipeline.py` to support CRS standardization:

```python
# Add CRS parameter to the main function
def main(
    mode: str = "all",
    config_file: str = "planning/config/default_config.json",
    sql_dir: str = "planning/sql",
    verbose: bool = False,
    crs: int = 3857  # Add CRS parameter with default 3857
):
    """
    Run the unified pipeline.
    
    Args:
        mode: Pipeline mode (all, water, terrain, unified)
        config_file: Configuration file
        sql_dir: SQL directory
        verbose: Enable verbose logging
        crs: Coordinate reference system (EPSG code)
    """
    # Set log level
    if verbose:
        logger.setLevel(logging.DEBUG)
    
    # Load configuration
    config = ConfigLoader(config_file).get_config()
    
    # Add CRS to configuration
    config["crs"] = crs
    logger.info(f"Using CRS: EPSG:{crs}")
    
    # Get database connection
    conn = get_db_connection()
    
    try:
        # Run the appropriate pipeline based on mode
        if mode in ["all", "water"]:
            # Use CRS-specific SQL files if available
            water_sql_dir = os.path.join(sql_dir, f"{crs}" if os.path.exists(os.path.join(sql_dir, f"{crs}")) else "")
            if not run_water_obstacle_pipeline(conn, config, water_sql_dir):
                return False
        
        if mode in ["all", "unified"]:
            if not run_unified_edges_pipeline(conn, config, sql_dir):
                return False
        
        logger.info(f"Unified pipeline ({mode}) completed successfully")
        return True
    
    finally:
        conn.close()
        logger.info("Database connection closed")

# Update the argument parser
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the unified pipeline")
    parser.add_argument(
        "--mode",
        choices=["all", "water", "terrain", "unified"],
        default="all",
        help="Pipeline mode"
    )
    parser.add_argument(
        "--config",
        default="planning/config/default_config.json",
        help="Configuration file"
    )
    parser.add_argument(
        "--sql-dir",
        default="planning/sql",
        help="SQL directory"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--crs",
        type=int,
        default=3857,
        help="Coordinate reference system (EPSG code)"
    )
    
    args = parser.parse_args()
    
    success = main(
        mode=args.mode,
        config_file=args.config,
        sql_dir=args.sql_dir,
        verbose=args.verbose,
        crs=args.crs
    )
    
    sys.exit(0 if success else 1)
```

### 7.2 Update Export Script

Update `tools/export_unified.py` to support CRS standardization:

```python
# Add CRS parameter to the main function
def main(
    mode: str = "graphml",
    input_file: str = None,
    output_file: str = None,
    lon: float = None,
    lat: float = None,
    minutes: int = 60,
    include_attributes: bool = True,
    include_geometry: bool = True,
    crs: int = 3857  # Add CRS parameter with default 3857
):
    """
    Export or visualize a graph.
    
    Args:
        mode: Export mode (graphml, water, terrain, combined)
        input_file: Input GraphML file (for visualization)
        output_file: Output file
        lon: Longitude coordinate
        lat: Latitude coordinate
        minutes: Travel time in minutes
        include_attributes: Whether to include attributes in the export
        include_geometry: Whether to include geometry in the export
        crs: Coordinate reference system (EPSG code)
    """
    if mode == "graphml":
        if input_file:
            # Visualize an existing GraphML file
            visualize_graphml(input_file, output_file)
        else:
            # Export a new GraphML file
            if lon is None or lat is None:
                logger.error("Longitude and latitude are required for GraphML export")
                return False
            
            # Use CRS-specific export script if available
            if crs == 3857 and os.path.exists("tools/export_slice_3857.py"):
                export_script = "tools/export_slice_3857.py"
            else:
                export_script = "tools/export_slice_enhanced_fixed.py"
            
            cmd = [
                "python", export_script,
                "--lon", str(lon),
                "--lat", str(lat),
                "--minutes", str(minutes)
            ]
            
            if output_file:
                cmd.extend(["--outfile", output_file])
            
            if not include_attributes:
                cmd.append("--no-attributes")
            
            if not include_geometry:
                cmd.append("--no-geometry")
            
            # Add CRS parameter if the script supports it
            if crs != 4326 and export_script == "tools/export_slice_3857.py":
                cmd.extend(["--crs", str(crs)])
            
            subprocess.run(cmd, check=True)
    
    elif mode == "water":
        # Use CRS-specific visualization script if available
        if crs == 3857 and os.path.exists("planning/scripts/visualize_water_obstacles_3857.py"):
            visualize_script = "planning/scripts/visualize_water_obstacles_3857.py"
        else:
            visualize_script = "planning/scripts/visualize_water_obstacles.py"
        
        cmd = ["python", visualize_script]
        
        if output_file:
            cmd.extend(["--output", output_file])
        
        # Add CRS parameter if the script supports it
        if crs != 4326 and visualize_script == "planning/scripts/visualize_water_obstacles_3857.py":
            cmd.extend(["--crs", str(crs)])
        
        subprocess.run(cmd, check=True)
    
    # ... (other modes)
    
    return True

# Update the argument parser
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export or visualize a graph")
    parser.add_argument(
        "--mode",
        choices=["graphml", "water", "terrain", "combined"],
        default="graphml",
        help="Export mode"
    )
    parser.add_argument(
        "--input",
        help="Input GraphML file (for visualization)"
    )
    parser.add_argument(
        "--output",
        help="Output file"
    )
    parser.add_argument(
        "--lon",
        type=float,
        help="Longitude coordinate"
    )
    parser.add_argument(
        "--lat",
        type=float,
        help="Latitude coordinate"
    )
    parser.add_argument(
        "--minutes",
        type=int,
        default=60,
        help="Travel time in minutes"
    )
    parser.add_argument(
        "--no-attributes",
        action="store_false",
        dest="include_attributes",
        help="Don't include attributes in the export"
    )
    parser.add_argument(
        "--no-geometry",
        action="store_false",
        dest="include_geometry",
        help="Don't include geometry in the export"
    )
    parser.add_argument(
        "--crs",
        type=int,
        default=3857,
        help="Coordinate reference system (EPSG code)"
    )
    
    args = parser.parse_args()
    
    success = main(
        mode=args.mode,
        input_file=args.input,
        output_file=args.output,
        lon=args.lon,
        lat=args.lat,
        minutes=args.minutes,
        include_attributes=args.include_attributes,
        include_geometry=args.include_geometry,
        crs=args.crs
    )
    
    sys.exit(0 if success else 1)
```

### 7.3 Update Visualization Script

Update `visualize_unified.py` to support CRS standardization:

```python
# Add CRS parameter to the main function
def main(
    mode: str = "graphml",
    input_file: str = None,
    output_file: str = None,
    title: str = None,
    dpi: int = 300,
    node_size: int = 5,
    edge_width: float = 0.5,
    color_by: str = "edge_type",
    crs: int = 4326  # Add CRS parameter with default 4326 for visualization
):
    """
    Visualize a graph or water obstacles.
    
    Args:
        mode: Visualization mode (graphml, water, terrain, combined)
        input_file: Input GraphML file
        output_file: Output PNG file
        title: Plot title
        dpi: DPI for the output image
        node_size: Size of nodes
        edge_width: Width of edges
        color_by: Attribute to color edges by
        crs: Coordinate reference system (EPSG code) for visualization
    """
    if mode == "graphml":
        if input_file is None:
            logger.error("Input file is required for GraphML visualization")
            return False
        
        # Use CRS-specific visualization script if available
        if os.path.exists("visualize_graph_3857.py"):
            visualize_script = "visualize_graph_3857.py"
        else:
            visualize_script = "visualize_graph.py"
        
        cmd = [
            "python", visualize_script,
            input_file
        ]
        
        if output_file:
            cmd.extend(["--output", output_file])
        
        if title:
            cmd.extend(["--title", title])
        
        cmd.extend(["--dpi", str(dpi)])
        cmd.extend(["--node-size", str(node_size)])
        cmd.extend(["--edge-width", str(edge_width)])
        cmd.extend(["--color-by", color_by])
        
        # Add CRS parameter if the script supports it
        if visualize_script == "visualize_graph_3857.py":
            cmd.extend(["--crs", str(crs)])
        
        subprocess.run(cmd, check=True)
    
    elif mode == "water":
        # Use CRS-specific visualization script if available
        if os.path.exists("planning/scripts/visualize_water_obstacles_3857.py"):
            visualize_script = "planning/scripts/visualize_water_obstacles_3857.py"
        else:
            visualize_script = "planning/scripts/visualize_water_obstacles.py"
        
        cmd = ["python", visualize_script]
        
        if output_file:
            cmd.extend(["--output", output_file])
        
        if title:
            cmd.extend(["--title", title])
        
        cmd.extend(["--dpi", str(dpi)])
        
        # Add CRS parameter if the script supports it
        if visualize_script == "planning/scripts/visualize_water_obstacles_3857.py":
            cmd.extend(["--crs", str(crs)])
        
        subprocess.run(cmd, check=True)
    
    # ... (other modes)
    
    return True

# Update the argument parser
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize a graph or water obstacles")
    parser.add_argument(
        "--mode",
        choices=["graphml", "water", "terrain", "combined"],
        default="graphml",
        help="Visualization mode"
    )
    parser.add_argument(
        "--input",
        help="Input GraphML file"
    )
    parser.add_argument(
        "--output",
        help="Output PNG file"
    )
    parser.add_argument(
        "--title",
        help="Plot title"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI for the output image"
    )
    parser.add_argument(
        "--node-size",
        type=int,
        default=5,
        help="Size of nodes"
    )
    parser.add_argument(
        "--edge-width",
        type=float,
        default=0.5,
        help="Width of edges"
    )
    parser.add_argument(
        "--color-by",
        choices=["edge_type", "cost"],
        default="edge_type",
        help="Attribute to color edges by"
    )
    parser.add_argument(
        "--crs",
        type=int,
        default=4326,
        help="Coordinate reference system (EPSG code) for visualization"
    )
    
    args = parser.parse_args()
    
    success = main(
        mode=args.mode,
        input_file=args.input,
        output_file=args.output,
        title=args.title,
        dpi=args.dpi,
        node_size=args.node_size,
        edge_width=args.edge_width,
        color_by=args.color_by,
        crs=args.crs
    )
    
    sys.exit(0 if success else 1)
```

## Phase 8: Documentation and Training (Week 4)

### 8.1 Update README.md

Update the project README.md to include information about the CRS standardization:

```markdown
## CRS Standardization

The project now uses EPSG:3857 (Web Mercator) for all internal processing and EPSG:4326 (WGS84) for export and visualization. This ensures consistent and accurate spatial operations across the entire pipeline.

### Using CRS Standardization

To use the CRS standardization:

```bash
# Run the water obstacle pipeline with CRS standardization
python planning/scripts/run_water_obstacle_pipeline_crs.py --config planning/config/crs_standardized_config.json

# Run the unified pipeline with CRS standardization
python scripts/run_unified_pipeline.py --crs 3857

# Export a slice with CRS standardization
python tools/export_unified.py --mode graphml --lon -93.63 --lat 41.99 --minutes 60 --crs 3857

# Visualize with CRS standardization
python visualize_unified.py --mode water --crs 4326
```

### Benefits of CRS Standardization

- **Improved accuracy**: Using EPSG:3857 for internal processing ensures that all spatial operations are performed in a metric coordinate system, which is more accurate for distance and area calculations.
- **Consistent buffer sizes**: Buffer sizes are now specified in meters, which is more intuitive and consistent across different latitudes.
- **Better performance**: Using a single CRS throughout the pipeline reduces the need for coordinate transformations, which can improve performance.
- **Simplified code**: Using a consistent CRS makes the code simpler and easier to maintain.
```

### 8.2 Create Training Materials

Create a training document for the team in `docs/
