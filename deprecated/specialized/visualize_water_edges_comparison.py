#!/usr/bin/env python3
"""
Script to visualize and compare different water edge generation methods.

This script:
1. Connects to the PostgreSQL database
2. Extracts water buffers, water_edges_original, and water_edges_dissolved
3. Creates a visualization comparing the different edge generation methods
4. Saves the visualization to a file with a timestamp
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import psycopg2
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from shapely.geometry import box

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import file management utilities
from utils.file_management import get_visualization_path, get_log_path

# Configure logging
log_path = get_log_path("water_edges_comparison")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_path)
    ]
)
logger = logging.getLogger('visualization')


def get_db_connection(conn_string: Optional[str] = None) -> psycopg2.extensions.connection:
    """
    Create a database connection.
    
    Args:
        conn_string: PostgreSQL connection string
    
    Returns:
        Database connection
    
    Raises:
        Exception: If connection fails
    """
    if conn_string is None:
        conn_string = os.environ.get('PG_URL', 'postgresql://gis:gis@localhost:5432/gis')
    
    try:
        conn = psycopg2.connect(conn_string)
        logger.info(f"Connected to database: {conn_string.split('@')[-1]}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise


def get_data_extent(conn: psycopg2.extensions.connection) -> Tuple[float, float, float, float]:
    """
    Get the extent of the data.
    
    Args:
        conn: Database connection
    
    Returns:
        Tuple of (min_x, min_y, max_x, max_y)
    
    Raises:
        Exception: If query fails
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    ST_XMin(ST_Extent(geom)) as min_x,
                    ST_YMin(ST_Extent(geom)) as min_y,
                    ST_XMax(ST_Extent(geom)) as max_x,
                    ST_YMax(ST_Extent(geom)) as max_y
                FROM (
                    SELECT geom FROM water_buf_dissolved
                    UNION ALL
                    SELECT geom FROM water_buf
                ) AS combined_geoms
            """)
            extent = cur.fetchone()
            
            if extent is None or None in extent:
                logger.error("Could not determine data extent")
                raise Exception("Could not determine data extent")
            
            return extent
    except Exception as e:
        logger.error(f"Error getting data extent: {e}")
        raise


def get_data_for_visualization(
    conn: psycopg2.extensions.connection,
    extent: Optional[Tuple[float, float, float, float]] = None,
    limit_rows: bool = True
) -> Dict[str, gpd.GeoDataFrame]:
    """
    Get data for visualization.
    
    Args:
        conn: Database connection
        extent: Optional bounding box to limit the data
        limit_rows: Whether to limit the number of rows returned
    
    Returns:
        Dictionary of GeoDataFrames
    
    Raises:
        Exception: If query fails
    """
    data = {}
    
    try:
        # Create a spatial filter if extent is provided
        spatial_filter = ""
        if extent:
            min_x, min_y, max_x, max_y = extent
            spatial_filter = f"""
                WHERE ST_Intersects(
                    geom,
                    ST_MakeEnvelope({min_x}, {min_y}, {max_x}, {max_y}, 4326)
                )
            """
        
        # Get water buffers (original)
        water_buf_query = f"""
            SELECT 
                id,
                crossability,
                buffer_rule_applied,
                crossability_rule_applied,
                buffer_size_m,
                geom
            FROM water_buf
            {spatial_filter}
        """
        
        data['water_buf'] = gpd.read_postgis(
            water_buf_query,
            conn,
            geom_col='geom'
        )
        logger.info(f"Retrieved {len(data['water_buf'])} water buffers (original)")
        
        # Get water buffers (dissolved)
        water_buf_dissolved_query = f"""
            SELECT 
                id,
                crossability_group,
                crossability,
                buffer_rules_applied,
                crossability_rules_applied,
                avg_buffer_size_m,
                geom
            FROM water_buf_dissolved
            {spatial_filter}
        """
        
        data['water_buf_dissolved'] = gpd.read_postgis(
            water_buf_dissolved_query,
            conn,
            geom_col='geom'
        )
        logger.info(f"Retrieved {len(data['water_buf_dissolved'])} water buffers (dissolved)")
        
        # Get water edges (original)
        limit_clause = "LIMIT 20000" if limit_rows else ""
        water_edges_original_query = f"""
            SELECT 
                id,
                cost,
                crossability,
                buffer_rules_applied,
                crossability_rules_applied,
                avg_buffer_size_m,
                edge_type,
                length_m,
                geom
            FROM water_edges_original
            {spatial_filter}
            {limit_clause}
        """
        
        try:
            data['water_edges_original'] = gpd.read_postgis(
                water_edges_original_query,
                conn,
                geom_col='geom'
            )
            logger.info(f"Retrieved {len(data['water_edges_original'])} water edges (original)")
        except Exception as e:
            logger.warning(f"Could not retrieve water_edges_original: {e}")
            data['water_edges_original'] = None
        
        # Get water edges (dissolved)
        limit_clause = "LIMIT 20000" if limit_rows else ""
        water_edges_dissolved_query = f"""
            SELECT 
                id,
                cost,
                crossability,
                buffer_rules_applied,
                crossability_rules_applied,
                avg_buffer_size_m,
                edge_type,
                length_m,
                geom
            FROM water_edges_dissolved
            {spatial_filter}
            {limit_clause}
        """
        
        try:
            data['water_edges_dissolved'] = gpd.read_postgis(
                water_edges_dissolved_query,
                conn,
                geom_col='geom'
            )
            logger.info(f"Retrieved {len(data['water_edges_dissolved'])} water edges (dissolved)")
        except Exception as e:
            logger.warning(f"Could not retrieve water_edges_dissolved: {e}")
            data['water_edges_dissolved'] = None
        
        return data
    
    except Exception as e:
        logger.error(f"Error getting data for visualization: {e}")
        raise


def create_visualization(
    data: Dict[str, Any],
    output_file: Optional[str] = None,
    title: Optional[str] = None,
    show_original_buffers: bool = True,
    show_dissolved_buffers: bool = True,
    show_original_edges: bool = True,
    show_dissolved_edges: bool = True,
    dpi: int = 300,
    description: str = "water_edges_comparison"
) -> None:
    """
    Create a visualization comparing different water edge generation methods.
    
    Args:
        data: Dictionary of GeoDataFrames
        output_file: Path to save the visualization to
        title: Optional title for the visualization
        show_original_buffers: Whether to show the original water buffers
        show_dissolved_buffers: Whether to show the dissolved water buffers
        show_original_edges: Whether to show the original water edges
        show_dissolved_edges: Whether to show the dissolved water edges
        dpi: DPI for the output image
        description: Description for the visualization filename
    
    Raises:
        Exception: If visualization fails
    """
    try:
        # Create figure with 2x2 subplots
        fig, axs = plt.subplots(2, 2, figsize=(20, 16))
        
        # Plot original buffers in top-left
        if show_original_buffers and 'water_buf' in data and data['water_buf'] is not None:
            ax = axs[0, 0]
            water_buf = data['water_buf']
            water_cmap = plt.cm.Blues
            water_norm = mcolors.Normalize(vmin=0, vmax=100)
            
            water_buf.plot(
                ax=ax,
                column='crossability',
                cmap=water_cmap,
                norm=water_norm,
                alpha=0.7,
                legend=True,
                legend_kwds={
                    'label': 'Water Crossability',
                    'orientation': 'horizontal',
                    'shrink': 0.8,
                    'pad': 0.01
                }
            )
            
            ax.set_title("Original Water Buffers")
            ax.set_xlabel("")
            ax.set_ylabel("")
        
        # Plot dissolved buffers in top-right
        if show_dissolved_buffers and 'water_buf_dissolved' in data and data['water_buf_dissolved'] is not None:
            ax = axs[0, 1]
            water_buf_dissolved = data['water_buf_dissolved']
            water_cmap = plt.cm.Blues
            water_norm = mcolors.Normalize(vmin=0, vmax=100)
            
            water_buf_dissolved.plot(
                ax=ax,
                column='crossability',
                cmap=water_cmap,
                norm=water_norm,
                alpha=0.7,
                legend=True,
                legend_kwds={
                    'label': 'Water Crossability',
                    'orientation': 'horizontal',
                    'shrink': 0.8,
                    'pad': 0.01
                }
            )
            
            ax.set_title("Dissolved Water Buffers")
            ax.set_xlabel("")
            ax.set_ylabel("")
        
        # Plot original edges in bottom-left
        if show_original_edges and 'water_edges_original' in data and data['water_edges_original'] is not None:
            ax = axs[1, 0]
            
            # First plot the original buffers as background
            if show_original_buffers and 'water_buf' in data and data['water_buf'] is not None:
                water_buf = data['water_buf']
                water_buf.plot(
                    ax=ax,
                    column='crossability',
                    cmap=plt.cm.Blues,
                    norm=mcolors.Normalize(vmin=0, vmax=100),
                    alpha=0.3
                )
            
            # Then plot the edges
            water_edges_original = data['water_edges_original']
            water_edge_cmap = plt.cm.Reds
            water_edge_norm = mcolors.Normalize(
                vmin=water_edges_original['cost'].min(),
                vmax=min(water_edges_original['cost'].max(), 100)
            )
            
            water_edges_original.plot(
                ax=ax,
                column='cost',
                cmap=water_edge_cmap,
                norm=water_edge_norm,
                linewidth=1.0,
                alpha=0.7,
                legend=True,
                legend_kwds={
                    'label': 'Edge Cost',
                    'orientation': 'horizontal',
                    'shrink': 0.8,
                    'pad': 0.01
                }
            )
            
            ax.set_title(f"Original Water Edges ({len(water_edges_original)} edges)")
            ax.set_xlabel("")
            ax.set_ylabel("")
            
            # Add edge count and total length
            edge_count = len(water_edges_original)
            total_length_km = water_edges_original['length_m'].sum() / 1000
            avg_cost = water_edges_original['cost'].mean()
            
            ax.text(
                0.02, 0.02,
                f"Edge Count: {edge_count}\nTotal Length: {total_length_km:.2f} km\nAvg Cost: {avg_cost:.2f}",
                transform=ax.transAxes,
                fontsize=10,
                bbox=dict(facecolor='white', alpha=0.8)
            )
        
        # Plot dissolved edges in bottom-right
        if show_dissolved_edges and 'water_edges_dissolved' in data and data['water_edges_dissolved'] is not None:
            ax = axs[1, 1]
            
            # First plot the dissolved buffers as background
            if show_dissolved_buffers and 'water_buf_dissolved' in data and data['water_buf_dissolved'] is not None:
                water_buf_dissolved = data['water_buf_dissolved']
                water_buf_dissolved.plot(
                    ax=ax,
                    column='crossability',
                    cmap=plt.cm.Blues,
                    norm=mcolors.Normalize(vmin=0, vmax=100),
                    alpha=0.3
                )
            
            # Then plot the edges
            water_edges_dissolved = data['water_edges_dissolved']
            water_edge_cmap = plt.cm.Reds
            water_edge_norm = mcolors.Normalize(
                vmin=water_edges_dissolved['cost'].min(),
                vmax=min(water_edges_dissolved['cost'].max(), 100)
            )
            
            water_edges_dissolved.plot(
                ax=ax,
                column='cost',
                cmap=water_edge_cmap,
                norm=water_edge_norm,
                linewidth=1.0,
                alpha=0.7,
                legend=True,
                legend_kwds={
                    'label': 'Edge Cost',
                    'orientation': 'horizontal',
                    'shrink': 0.8,
                    'pad': 0.01
                }
            )
            
            ax.set_title(f"Dissolved Water Edges ({len(water_edges_dissolved)} edges)")
            ax.set_xlabel("")
            ax.set_ylabel("")
            
            # Add edge count and total length
            edge_count = len(water_edges_dissolved)
            total_length_km = water_edges_dissolved['length_m'].sum() / 1000
            avg_cost = water_edges_dissolved['cost'].mean()
            
            ax.text(
                0.02, 0.02,
                f"Edge Count: {edge_count}\nTotal Length: {total_length_km:.2f} km\nAvg Cost: {avg_cost:.2f}",
                transform=ax.transAxes,
                fontsize=10,
                bbox=dict(facecolor='white', alpha=0.8)
            )
        
        # Set overall title
        if title:
            fig.suptitle(title, fontsize=16)
        else:
            fig.suptitle("Water Edge Generation Methods Comparison", fontsize=16)
        
        # Determine output file path
        if output_file is None:
            # Get visualization path with timestamp
            output_file = get_visualization_path(
                viz_type="water",
                description=description,
                parameters={'dpi': dpi},
                extension="png"
            )
        
        # Save the visualization
        plt.tight_layout()
        plt.savefig(output_file, dpi=dpi)
        logger.info(f"Visualization saved to {output_file}")
        
        # Close the figure to free memory
        plt.close(fig)
        
    except Exception as e:
        logger.error(f"Error creating visualization: {e}")
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Visualize and compare water edge generation methods")
    parser.add_argument(
        "--output",
        help="Output file path (default: auto-generated with timestamp)"
    )
    parser.add_argument(
        "--description",
        default="water_edges_comparison",
        help="Description for the visualization filename"
    )
    parser.add_argument(
        "--title",
        help="Title for the visualization"
    )
    parser.add_argument(
        "--conn-string",
        help="PostgreSQL connection string (default: from PG_URL environment variable)"
    )
    parser.add_argument(
        "--extent",
        help="Bounding box to limit the visualization (min_x,min_y,max_x,max_y)"
    )
    parser.add_argument(
        "--no-original-buffers",
        action="store_true",
        help="Don't show the original water buffers"
    )
    parser.add_argument(
        "--no-dissolved-buffers",
        action="store_true",
        help="Don't show the dissolved water buffers"
    )
    parser.add_argument(
        "--no-original-edges",
        action="store_true",
        help="Don't show the original water edges"
    )
    parser.add_argument(
        "--no-dissolved-edges",
        action="store_true",
        help="Don't show the dissolved water edges"
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
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Parse extent if provided
    extent = None
    if args.extent:
        try:
            extent = tuple(float(x) for x in args.extent.split(','))
            if len(extent) != 4:
                logger.error("Extent must be in the format min_x,min_y,max_x,max_y")
                return 1
        except ValueError:
            logger.error("Invalid extent format. Must be min_x,min_y,max_x,max_y")
            return 1
    
    try:
        # Connect to database
        conn = get_db_connection(args.conn_string)
        
        try:
            # Get data extent if not provided
            if extent is None:
                extent = get_data_extent(conn)
                logger.info(f"Using data extent: {extent}")
            
            # Get data for visualization
            data = get_data_for_visualization(conn, extent)
            
            # Create visualization
            create_visualization(
                data,
                args.output,
                title=args.title,
                show_original_buffers=not args.no_original_buffers,
                show_dissolved_buffers=not args.no_dissolved_buffers,
                show_original_edges=not args.no_original_edges,
                show_dissolved_edges=not args.no_dissolved_edges,
                dpi=args.dpi,
                description=args.description
            )
            
            return 0
        
        finally:
            conn.close()
            logger.info("Database connection closed")
    
    except Exception as e:
        logger.error(f"Visualization failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
