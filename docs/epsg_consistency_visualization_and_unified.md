# EPSG Consistency Implementation Plan - Part 2: Visualization and Unified Pipeline

**Date:** April 21, 2025  
**Author:** Cline  
**Project:** Terrain System - Geo-Graph  

This document is a continuation of the EPSG Consistency Implementation Plan, focusing on the visualization and unified pipeline components.

## Phase 4: Visualization (Week 2)

### 4.2 Visualization Script

Create `planning/scripts/visualize_water_obstacles_3857.py`:

```python
#!/usr/bin/env python3
"""
Visualize water obstacles with consistent CRS handling.
Uses EPSG:3857 for internal processing and EPSG:4326 for visualization.
"""
import os
import sys
import argparse
import logging
import matplotlib.pyplot as plt
import geopandas as gpd
from sqlalchemy import create_engine
from pathlib import Path

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.file_management import get_visualization_path

def connect():
    """Connect to the database."""
    return create_engine(os.getenv("PG_URL", "postgresql://gis:gis@localhost:5432/gis"))

def main(
    output: str = None,
    title: str = "Water Obstacles",
    dpi: int = 300,
    figsize: tuple = (12, 10),
    crs: int = 4326
):
    """
    Visualize water obstacles.
    
    Args:
        output: Output PNG file
        title: Plot title
        dpi: DPI for the output image
        figsize: Figure size (width, height) in inches
        crs: CRS for visualization (default: EPSG:4326)
    """
    engine = connect()
    
    # Load water buffers
    water_buffers = gpd.read_postgis(
        """
        SELECT 
            id, 
            crossability, 
            water_type, 
            avg_buffer_size_m,
            ST_Transform(geom, :crs) AS geom
        FROM water_buf_dissolved
        """,
        engine,
        params={"crs": crs},
        geom_col="geom"
    )
    
    # Load terrain grid
    terrain_grid = gpd.read_postgis(
        """
        SELECT 
            cost, 
            ST_Transform(geom, :crs) AS geom
        FROM terrain_grid
        """,
        engine,
        params={"crs": crs},
        geom_col="geom"
    )
    
    # Load water edges
    water_edges = gpd.read_postgis(
        """
        SELECT 
            id, 
            cost, 
            crossability, 
            water_type,
            ST_Transform(geom, :crs) AS geom
        FROM water_edges
        """,
        engine,
        params={"crs": crs},
        geom_col="geom"
    )
    
    # Create figure and axes
    fig, ax = plt.subplots(figsize=figsize)
    
    # Plot terrain grid
    terrain_grid.plot(
        ax=ax,
        color="lightgray",
        alpha=0.3,
        edgecolor="gray",
        linewidth=0.5
    )
    
    # Plot water buffers
    water_buffers.plot(
        ax=ax,
        column="crossability",
        cmap="Blues",
        alpha=0.7,
        edgecolor="blue",
        linewidth=0.5,
        legend=True,
        legend_kwds={"label": "Crossability"}
    )
    
    # Plot water edges
    water_edges.plot(
        ax=ax,
        column="cost",
        cmap="plasma",
        linewidth=1.5,
        legend=True,
        legend_kwds={"label": "Edge Cost"}
    )
    
    # Set title and labels
    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    
    # Add grid
    ax.grid(True, linestyle="--", alpha=0.5)
    
    # Determine the output file path
    if output is None:
        output = get_visualization_path(
            viz_type="water",
            description="water_obstacles_3857",
            parameters={"dpi": dpi}
        )
    
    # Save the figure
    plt.savefig(output, dpi=dpi, bbox_inches="tight")
    print(f"Visualization saved to {output}")
    
    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize water obstacles")
    parser.add_argument("--output", help="Output PNG file")
    parser.add_argument("--title", default="Water Obstacles", help="Plot title")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for the output image")
    parser.add_argument("--crs", type=int, default=4326, help="CRS for visualization")
    args = parser.parse_args()
    
    main(
        output=args.output,
        title=args.title,
        dpi=args.dpi,
        crs=args.crs
    )
```

### 4.3 Graph Visualization Script

Create `visualize_graph_3857.py`:

```python
#!/usr/bin/env python3
"""
Visualize a GraphML file with consistent CRS handling.
"""
import os
import sys
import argparse
import logging
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from pathlib import Path

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.file_management import get_visualization_path

def main(
    input_file: str,
    output_file: str = None,
    title: str = None,
    dpi: int = 300,
    figsize: tuple = (12, 10),
    node_size: int = 5,
    edge_width: float = 0.5,
    color_by: str = "edge_type"
):
    """
    Visualize a GraphML file.
    
    Args:
        input_file: Input GraphML file
        output_file: Output PNG file
        title: Plot title
        dpi: DPI for the output image
        figsize: Figure size (width, height) in inches
        node_size: Size of nodes
        edge_width: Width of edges
        color_by: Attribute to color edges by
    """
    # Load the graph
    G = nx.read_graphml(input_file)
    
    # Extract node positions
    pos = {n: (float(G.nodes[n]['x']), float(G.nodes[n]['y'])) for n in G.nodes()}
    
    # Create figure and axes
    fig, ax = plt.subplots(figsize=figsize)
    
    # Define edge colors based on edge_type
    edge_colors = []
    if color_by == "edge_type":
        for u, v, data in G.edges(data=True):
            if data.get('edge_type') == 'road':
                edge_colors.append('black')
            elif data.get('edge_type') == 'water':
                edge_colors.append('blue')
            elif data.get('edge_type') == 'terrain':
                edge_colors.append('green')
            else:
                edge_colors.append('gray')
    elif color_by == "cost":
        costs = [float(data.get('cost', 1.0)) for u, v, data in G.edges(data=True)]
        edge_colors = costs
    else:
        edge_colors = 'gray'
    
    # Draw the graph
    nx.draw(
        G,
        pos=pos,
        ax=ax,
        node_size=node_size,
        node_color='red',
        edge_color=edge_colors,
        width=edge_width,
        with_labels=False,
        arrows=False
    )
    
    # Set title
    if title is None:
        title = f"Graph Visualization: {os.path.basename(input_file)}"
    ax.set_title(title)
    
    # Determine the output file path
    if output_file is None:
        description = os.path.splitext(os.path.basename(input_file))[0]
        output_file = get_visualization_path(
            viz_type='graphml',
            description=description,
            parameters={'dpi': dpi}
        )
    
    # Save the figure
    plt.savefig(output_file, dpi=dpi, bbox_inches="tight")
    print(f"Visualization saved to {output_file}")
    
    return output_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize a GraphML file")
    parser.add_argument("input", help="Input GraphML file")
    parser.add_argument("--output", help="Output PNG file")
    parser.add_argument("--title", help="Plot title")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for the output image")
    parser.add_argument("--node-size", type=int, default=5, help="Size of nodes")
    parser.add_argument("--edge-width", type=float, default=0.5, help="Width of edges")
    parser.add_argument("--color-by", choices=["edge_type", "cost"], default="edge_type", help="Attribute to color edges by")
    args = parser.parse_args()
    
    main(
        input_file=args.input,
        output_file=args.output,
        title=args.title,
        dpi=args.dpi,
        node_size=args.node_size,
        edge_width=args.edge_width,
        color_by=args.color_by
    )
```

## Phase 5: Unified Pipeline (Week 3)

### 5.1 Unified Pipeline Script

Create `scripts/run_unified_pipeline_3857.py`:

```python
#!/usr/bin/env python3
"""
Run the unified pipeline with consistent CRS handling.
Uses EPSG:3857 for all internal processing.
"""
import os
import sys
import argparse
import logging
import psycopg2
from psycopg2.extras import DictCursor
import subprocess
from pathlib import Path

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from planning.scripts.config_loader import ConfigLoader
from utils.file_management import get_export_path, get_visualization_path, get_log_path

# Configure logging
log_path = get_log_path("unified_pipeline_3857")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_path)
    ]
)
logger = logging.getLogger('unified_pipeline_3857')

def get_db_connection(conn_string=None):
    """Create a database connection."""
    if conn_string is None:
        conn_string = os.environ.get('PG_URL', 'postgresql://gis:gis@localhost:5432/gis')
    
    try:
        conn = psycopg2.connect(conn_string)
        logger.info(f"Connected to database: {conn_string.split('@')[-1]}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise

def run_sql_file(conn, sql_file, params=None):
    """Run a SQL file with parameters."""
    logger.info(f"Running SQL file: {sql_file}")
    
    try:
        with open(sql_file, 'r') as f:
            sql = f.read()
        
        with conn.cursor() as cur:
            cur.execute(sql, params)
        
        conn.commit()
        logger.info(f"SQL file executed successfully: {sql_file}")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error executing SQL file {sql_file}: {e}")
        return False

def run_water_obstacle_pipeline(conn, config, sql_dir):
    """Run the water obstacle pipeline with consistent CRS handling."""
    logger.info("Running water obstacle pipeline with EPSG:3857")
    
    # Extract water features
    if not run_sql_file(
        conn,
        os.path.join(sql_dir, "01_extract_water_features_3857.sql"),
        params=config.get("water_features", {})
    ):
        return False
    
    # Create water buffers
    if not run_sql_file(
        conn,
        os.path.join(sql_dir, "02_create_water_buffers_3857.sql"),
        params=config.get("water_buffers", {})
    ):
        return False
    
    # Dissolve water buffers
    if not run_sql_file(
        conn,
        os.path.join(sql_dir, "03_dissolve_water_buffers_3857.sql"),
        params=config.get("dissolve", {})
    ):
        return False
    
    # Create terrain grid
    if not run_sql_file(
        conn,
        os.path.join(sql_dir, "04_create_terrain_grid_3857.sql"),
        params=config.get("terrain_grid", {})
    ):
        return False
    
    # Create terrain edges
    if not run_sql_file(
        conn,
        os.path.join(sql_dir, "05_create_terrain_edges_3857.sql"),
        params=config.get("terrain_grid", {})
    ):
        return False
    
    # Create water edges
    if not run_sql_file(
        conn,
        os.path.join(sql_dir, "06_create_water_edges_3857.sql"),
        params=config.get("water_edges", {})
    ):
        return False
    
    # Create environmental tables
    if not run_sql_file(
        conn,
        os.path.join(sql_dir, "07_create_environmental_tables_3857.sql"),
        params=config.get("environmental_conditions", {})
    ):
        return False
    
    logger.info("Water obstacle pipeline completed successfully")
    return True

def run_unified_edges_pipeline(conn, config, sql_dir):
    """Run the unified edges pipeline with consistent CRS handling."""
    logger.info("Running unified edges pipeline with EPSG:3857")
    
    # Create unified edges
    if not run_sql_file(
        conn,
        os.path.join(sql_dir, "create_unified_edges_3857.sql"),
        params=config.get("unified_edges", {})
    ):
        return False
    
    # Refresh topology
    if not run_sql_file(
        conn,
        os.path.join(sql_dir, "refresh_topology_3857.sql"),
        params=config.get("topology", {})
    ):
        return False
    
    logger.info("Unified edges pipeline completed successfully")
    return True

def export_slice(config, lon, lat, minutes, outfile=None):
    """Export a slice of the unified graph."""
    logger.info(f"Exporting slice at ({lon}, {lat}) with {minutes} minutes travel time")
    
    if outfile is None:
        outfile = get_export_
