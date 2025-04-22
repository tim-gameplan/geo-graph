#!/usr/bin/env python3
"""
Script to visualize water obstacles and terrain grid.

This script:
1. Connects to the PostgreSQL database
2. Extracts water buffers, terrain grid, and edges
3. Creates a visualization using matplotlib
4. Saves the visualization to a file with a timestamp

The visualization is saved to the output/visualizations/water directory
with a timestamp in the filename.
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
log_path = get_log_path("water_visualization")
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
                FROM water_buf_dissolved
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
                    ST_SetSRID(ST_MakeEnvelope({min_x}, {min_y}, {max_x}, {max_y}), ST_SRID(geom))
                )
            """

        # Get water buffers
        water_query = f"""
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

        data['water_buffers'] = gpd.read_postgis(
            water_query,
            conn,
            geom_col='geom'
        )
        logger.info(f"Retrieved {len(data['water_buffers'])} water buffers")

        # Get terrain grid
        limit_clause = "LIMIT 10000" if limit_rows else ""
        terrain_query = f"""
            SELECT
                ROW_NUMBER() OVER() as id,
                cost,
                geom
            FROM terrain_grid
            {spatial_filter}
            {limit_clause}
        """

        data['terrain_grid'] = gpd.read_postgis(
            terrain_query,
            conn,
            geom_col='geom'
        )
        logger.info(f"Retrieved {len(data['terrain_grid'])} terrain grid cells")

        # Get terrain edges
        limit_clause = "LIMIT 20000" if limit_rows else ""
        terrain_edges_query = f"""
            SELECT
                id,
                cost,
                ST_Length(ST_Transform(geom, 4326)::geography) AS length_m,
                geom
            FROM terrain_edges
            {spatial_filter}
            {limit_clause}
        """

        data['terrain_edges'] = gpd.read_postgis(
            terrain_edges_query,
            conn,
            geom_col='geom'
        )
        logger.info(f"Retrieved {len(data['terrain_edges'])} terrain edges")

        # Get water edges - FIXED to use actual columns in the water_edges table
        limit_clause = "LIMIT 20000" if limit_rows else ""
        water_edges_query = f"""
            SELECT
                id,
                cost,
                crossability,
                crossability_group,
                buffer_rules_applied,
                crossability_rules_applied,
                avg_buffer_size_m,
                edge_type,
                length_m,
                geom
            FROM water_edges
            {spatial_filter}
            {limit_clause}
        """

        data['water_edges'] = gpd.read_postgis(
            water_edges_query,
            conn,
            geom_col='geom'
        )
        logger.info(f"Retrieved {len(data['water_edges'])} water edges")

        # Get environmental conditions
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM environmental_conditions")
                env_conditions = cur.fetchall()
                data['env_conditions'] = {row[0]: (row[1], str(row[2])) for row in env_conditions}
        except Exception as e:
            logger.warning(f"Could not retrieve environmental conditions: {e}")
            data['env_conditions'] = {}

        return data

    except Exception as e:
        logger.error(f"Error getting data for visualization: {e}")
        raise


def create_visualization(
    data: Dict[str, Any],
    output_file: Optional[str] = None,
    title: Optional[str] = None,
    show_terrain_grid: bool = True,
    show_terrain_edges: bool = True,
    show_water_edges: bool = True,
    show_decision_info: bool = True,
    dpi: int = 300,
    description: str = "water_obstacles"
) -> None:
    """
    Create a visualization of water obstacles and terrain grid.

    Args:
        data: Dictionary of GeoDataFrames
        output_file: Path to save the visualization to
        title: Optional title for the visualization
        show_terrain_grid: Whether to show the terrain grid
        show_terrain_edges: Whether to show the terrain edges
        show_water_edges: Whether to show the water edges
        show_decision_info: Whether to show decision tracking information
        dpi: DPI for the output image
        description: Description for the visualization filename

    Raises:
        Exception: If visualization fails
    """
    try:
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(12, 10))

        # Plot water buffers
        water_buffers = data['water_buffers']
        water_cmap = plt.cm.Blues
        water_norm = mcolors.Normalize(vmin=0, vmax=100)

        water_buffers.plot(
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

        # Plot terrain grid if requested
        if show_terrain_grid and 'terrain_grid' in data and not data['terrain_grid'].empty:
            terrain_grid = data['terrain_grid']
            terrain_grid.plot(
                ax=ax,
                color='lightgreen',
                alpha=0.3,
                edgecolor='darkgreen',
                linewidth=0.1
            )

        # Plot terrain edges if requested
        if show_terrain_edges and 'terrain_edges' in data and not data['terrain_edges'].empty:
            terrain_edges = data['terrain_edges']
            terrain_edges.plot(
                ax=ax,
                color='green',
                linewidth=0.5,
                alpha=0.5
            )

        # Plot water edges if requested
        if show_water_edges and 'water_edges' in data and not data['water_edges'].empty:
            water_edges = data['water_edges']

            # Color by cost
            water_edge_cmap = plt.cm.Reds
            min_cost = water_edges['cost'].min()
            max_cost = min(water_edges['cost'].max(), 1000)  # Cap at 1000 for better visualization

            # Ensure min and max are different to avoid normalization error
            if min_cost >= max_cost:
                max_cost = min_cost + 1

            water_edge_norm = mcolors.Normalize(vmin=min_cost, vmax=max_cost)

            water_edges.plot(
                ax=ax,
                column='cost',
                cmap=water_edge_cmap,
                norm=water_edge_norm,
                linewidth=1.0,
                alpha=0.7
            )

        # Add environmental conditions as text
        if 'env_conditions' in data and data['env_conditions']:
            env_text = "Environmental Conditions:\n"
            for condition, (value, description) in data['env_conditions'].items():
                env_text += f"{condition}: {value:.2f} ({description})\n"

            plt.figtext(
                0.02, 0.02,
                env_text,
                fontsize=8,
                bbox=dict(facecolor='white', alpha=0.8)
            )

        # Add decision tracking information if requested
        if show_decision_info and 'water_buffers' in data and not data['water_buffers'].empty:
            # Get unique buffer rules and crossability rules
            buffer_rules = set()
            crossability_rules = set()

            for rules in data['water_buffers']['buffer_rules_applied']:
                if rules:
                    buffer_rules.update(rule.strip() for rule in rules.split(','))

            for rules in data['water_buffers']['crossability_rules_applied']:
                if rules:
                    crossability_rules.update(rule.strip() for rule in rules.split(','))

            # Create decision tracking text
            decision_text = "Water Modeling Decisions:\n\n"

            decision_text += "Buffer Rules Applied:\n"
            for rule in sorted(buffer_rules):
                decision_text += f"• {rule}\n"

            decision_text += "\nCrossability Rules Applied:\n"
            for rule in sorted(crossability_rules):
                decision_text += f"• {rule}\n"

            # Add statistics
            decision_text += "\nCrossability Groups:\n"
            for group, count in data['water_buffers']['crossability_group'].value_counts().items():
                decision_text += f"• {group}: {count} features\n"

            plt.figtext(
                0.75, 0.02,
                decision_text,
                fontsize=8,
                bbox=dict(facecolor='white', alpha=0.8),
                verticalalignment='bottom'
            )

        # Set title
        if title:
            ax.set_title(title)
        else:
            ax.set_title("Water Obstacle Modeling Visualization")

        # Remove axis labels
        ax.set_xlabel("")
        ax.set_ylabel("")

        # Determine output file path
        if output_file is None:
            # Get visualization path with timestamp
            output_file = get_visualization_path(
                viz_type="water",
                description=description,
                parameters={"dpi": dpi},
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
    parser = argparse.ArgumentParser(description="Visualize water obstacles and terrain grid")
    parser.add_argument(
        "--output",
        help="Output file path (default: auto-generated with timestamp)"
    )
    parser.add_argument(
        "--description",
        default="water_obstacles_fixed",
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
                show_terrain_grid=not args.no_terrain_grid,
                show_terrain_edges=not args.no_terrain_edges,
                show_water_edges=not args.no_water_edges,
                show_decision_info=not args.no_decision_info,
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
