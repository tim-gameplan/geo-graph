#!/usr/bin/env python3
"""
Delaunay Triangulation Visualization Script

This script visualizes the Delaunay triangulation used for terrain grid generation,
comparing it with the regular grid approach. It shows:
1. The original water buffers
2. The Delaunay triangulation
3. The terrain grid points
4. The terrain edges

Usage:
    python visualize_delaunay_triangulation.py [--output OUTPUT] [--dpi DPI] [--title TITLE]
"""

import os
import sys
import argparse
import logging
import time
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import geopandas as gpd
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from matplotlib.collections import LineCollection, PatchCollection

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.file_management import get_visualization_path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('visualize_delaunay.log')
    ]
)
logger = logging.getLogger('visualize_delaunay')


def connect():
    """
    Connect to the database.
    
    Returns:
        SQLAlchemy engine
    """
    conn_string = os.environ.get('PG_URL', 'postgresql://gis:gis@localhost:5432/gis')
    return create_engine(conn_string)


def fetch_data(engine):
    """
    Fetch data from the database.
    
    Args:
        engine: SQLAlchemy engine
    
    Returns:
        Dictionary of GeoDataFrames
    """
    logger.info("Fetching data from database")
    
    # Check if the Delaunay tables exist
    try:
        with engine.connect() as conn:
            result = conn.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'terrain_triangulation'
                )
            """)
            has_delaunay = result.fetchone()[0]
            
            if not has_delaunay:
                logger.error("Delaunay triangulation tables not found. Run the pipeline first.")
                return None
    except Exception as e:
        logger.error(f"Error checking for Delaunay tables: {e}")
        return None
    
    try:
        # Fetch water buffers
        water_buffers = gpd.read_postgis(
            "SELECT geom FROM water_buf_dissolved",
            engine,
            geom_col='geom'
        )
        
        # Fetch Delaunay triangulation
        triangulation = gpd.read_postgis(
            "SELECT geom FROM terrain_triangulation",
            engine,
            geom_col='geom'
        )
        
        # Fetch terrain grid points
        terrain_grid = gpd.read_postgis(
            "SELECT id, geom FROM terrain_grid",
            engine,
            geom_col='geom'
        )
        
        # Fetch terrain edges
        terrain_edges = gpd.read_postgis(
            "SELECT id, source_id, target_id, length_m, geom FROM terrain_edges",
            engine,
            geom_col='geom'
        )
        
        # Fetch regular grid points (if they exist)
        try:
            regular_grid = gpd.read_postgis(
                """
                SELECT id, geom FROM terrain_grid_regular
                UNION ALL
                SELECT 0 AS id, ST_Centroid(geom) AS geom 
                FROM (
                    SELECT ST_HexagonGrid(200, ST_Transform(ST_Extent(geom), 3857)) AS geom
                    FROM water_buf_dissolved
                ) AS grid
                WHERE NOT EXISTS (
                    SELECT 1 
                    FROM water_buf_dissolved wb
                    WHERE ST_Intersects(ST_Centroid(grid.geom), wb.geom)
                )
                LIMIT 1000
                """,
                engine,
                geom_col='geom'
            )
        except Exception as e:
            logger.warning(f"Could not fetch regular grid: {e}")
            regular_grid = None
        
        return {
            'water_buffers': water_buffers,
            'triangulation': triangulation,
            'terrain_grid': terrain_grid,
            'terrain_edges': terrain_edges,
            'regular_grid': regular_grid
        }
    
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return None


def create_visualization(data, output_path, dpi=300, title=None):
    """
    Create a visualization of the Delaunay triangulation.
    
    Args:
        data: Dictionary of GeoDataFrames
        output_path: Path to save the visualization
        dpi: DPI for the output image
        title: Title for the visualization
    
    Returns:
        Path to the saved visualization
    """
    logger.info("Creating visualization")
    
    if data is None:
        logger.error("No data to visualize")
        return None
    
    # Create figure and axes
    fig, axes = plt.subplots(2, 2, figsize=(20, 16))
    fig.subplots_adjust(hspace=0.3, wspace=0.3)
    
    # Set the title
    if title:
        fig.suptitle(title, fontsize=16)
    else:
        fig.suptitle('Delaunay Triangulation for Terrain Grid', fontsize=16)
    
    # Plot water buffers in all subplots
    for ax in axes.flat:
        data['water_buffers'].plot(
            ax=ax,
            color='lightblue',
            edgecolor='blue',
            alpha=0.5,
            label='Water Buffers'
        )
    
    # Plot 1: Water buffers and triangulation
    axes[0, 0].set_title('Delaunay Triangulation')
    data['triangulation'].boundary.plot(
        ax=axes[0, 0],
        color='black',
        linewidth=0.5,
        alpha=0.7,
        label='Triangulation'
    )
    
    # Plot 2: Terrain grid points
    axes[0, 1].set_title('Terrain Grid Points')
    data['terrain_grid'].plot(
        ax=axes[0, 1],
        color='red',
        markersize=10,
        alpha=0.7,
        label='Grid Points'
    )
    
    # Plot 3: Terrain edges
    axes[1, 0].set_title('Terrain Edges')
    data['terrain_edges'].plot(
        ax=axes[1, 0],
        color='green',
        linewidth=1,
        alpha=0.7,
        label='Edges'
    )
    
    # Plot 4: Comparison with regular grid (if available)
    axes[1, 1].set_title('Comparison with Regular Grid')
    if data['regular_grid'] is not None and len(data['regular_grid']) > 0:
        data['regular_grid'].plot(
            ax=axes[1, 1],
            color='purple',
            markersize=10,
            alpha=0.5,
            label='Regular Grid'
        )
        data['terrain_grid'].plot(
            ax=axes[1, 1],
            color='red',
            markersize=5,
            alpha=0.7,
            label='Delaunay Grid'
        )
    else:
        # If regular grid is not available, show edge statistics
        axes[1, 1].set_title('Edge Length Distribution')
        axes[1, 1].hist(
            data['terrain_edges']['length_m'],
            bins=30,
            color='green',
            alpha=0.7
        )
        axes[1, 1].set_xlabel('Edge Length (m)')
        axes[1, 1].set_ylabel('Count')
    
    # Add legends
    for ax in axes.flat:
        ax.legend()
    
    # Add statistics
    stats_text = (
        f"Triangulation Statistics:\n"
        f"- Number of triangles: {len(data['triangulation'])}\n"
        f"- Number of grid points: {len(data['terrain_grid'])}\n"
        f"- Number of edges: {len(data['terrain_edges'])}\n"
        f"- Average edge length: {data['terrain_edges']['length_m'].mean():.2f} m\n"
        f"- Min edge length: {data['terrain_edges']['length_m'].min():.2f} m\n"
        f"- Max edge length: {data['terrain_edges']['length_m'].max():.2f} m"
    )
    fig.text(0.02, 0.02, stats_text, fontsize=12, verticalalignment='bottom')
    
    # Save the figure
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    logger.info(f"Visualization saved to {output_path}")
    
    return output_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Visualize Delaunay triangulation for terrain grid"
    )
    parser.add_argument(
        "--output",
        help="Path to save the visualization"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI for the output image"
    )
    parser.add_argument(
        "--title",
        help="Title for the visualization"
    )
    
    args = parser.parse_args()
    
    # Connect to the database
    engine = connect()
    
    # Fetch data
    data = fetch_data(engine)
    
    if data is None:
        logger.error("Failed to fetch data")
        return 1
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = get_visualization_path(
            viz_type='terrain',
            description='delaunay_triangulation',
            parameters={'dpi': args.dpi}
        )
    
    # Create visualization
    result = create_visualization(
        data,
        output_path,
        dpi=args.dpi,
        title=args.title
    )
    
    if result is None:
        logger.error("Failed to create visualization")
        return 1
    
    logger.info("Visualization completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
