#!/usr/bin/env python3
"""
Visualize Boundary Hexagon Layer with Simplified Water Obstacles

This script visualizes the boundary hexagon layer approach, showing:
1. Terrain grid (land, boundary, water_with_land hexagons)
2. Boundary nodes
3. Water boundary nodes
4. Land portion nodes
5. Connections between nodes
6. Simplified water obstacles
"""

import os
import sys
import argparse
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import psycopg2
import geopandas as gpd
from shapely import wkb
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path so we can import from core packages
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.utils.logging_utils import setup_logger

# Set up logging
logger = setup_logger('visualize_boundary_hexagon_layer_simplified')

def connect_to_database(host='localhost', port=5432, dbname='gis', user='gis', password='gis'):
    """
    Connect to the PostgreSQL database.
    
    Args:
        host (str): Database host
        port (int): Database port
        dbname (str): Database name
        user (str): Database user
        password (str): Database password
    
    Returns:
        connection: PostgreSQL connection object
    """
    try:
        connection = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        return connection
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        return None

def fetch_data(connection):
    """
    Fetch data from the database.
    
    Args:
        connection: PostgreSQL connection object
    
    Returns:
        dict: Dictionary containing GeoDataFrames for each element
    """
    try:
        # Create a cursor
        cursor = connection.cursor()
        
        # Fetch terrain grid
        logger.info("Fetching terrain grid...")
        cursor.execute("""
            SELECT id, hex_type, ST_AsBinary(geom) AS geom
            FROM terrain_grid
        """)
        terrain_grid_data = cursor.fetchall()
        
        # Fetch boundary nodes
        logger.info("Fetching boundary nodes...")
        cursor.execute("""
            SELECT id, node_type, ST_AsBinary(geom) AS geom
            FROM boundary_nodes
        """)
        boundary_nodes_data = cursor.fetchall()
        
        # Fetch water boundary nodes
        logger.info("Fetching water boundary nodes...")
        cursor.execute("""
            SELECT id, node_type, ST_AsBinary(geom) AS geom
            FROM water_boundary_nodes
        """)
        water_boundary_nodes_data = cursor.fetchall()
        
        # Fetch land portion nodes
        logger.info("Fetching land portion nodes...")
        cursor.execute("""
            SELECT id, node_type, ST_AsBinary(geom) AS geom
            FROM land_portion_nodes
        """)
        land_portion_nodes_data = cursor.fetchall()
        
        # Fetch boundary-to-boundary edges
        logger.info("Fetching boundary-to-boundary edges...")
        cursor.execute("""
            SELECT id, start_node_id, end_node_id, ST_AsBinary(geom) AS geom
            FROM boundary_boundary_edges
        """)
        boundary_boundary_edges_data = cursor.fetchall()
        
        # Fetch boundary-to-land-portion edges
        logger.info("Fetching boundary-to-land-portion edges...")
        cursor.execute("""
            SELECT id, start_node_id, end_node_id, ST_AsBinary(geom) AS geom
            FROM boundary_land_portion_edges
        """)
        boundary_land_portion_edges_data = cursor.fetchall()
        
        # Fetch land-portion-to-water-boundary edges
        logger.info("Fetching land-portion-to-water-boundary edges...")
        cursor.execute("""
            SELECT id, start_node_id, end_node_id, ST_AsBinary(geom) AS geom
            FROM land_portion_water_boundary_edges
        """)
        land_portion_water_boundary_edges_data = cursor.fetchall()
        
        # Fetch simple water obstacles
        logger.info("Fetching simple water obstacles...")
        cursor.execute("""
            SELECT id, ST_AsBinary(geom) AS geom
            FROM water_obstacles_simple
        """)
        water_obstacles_data = cursor.fetchall()
        
        # Close the cursor
        cursor.close()
        
        # Convert to GeoDataFrames
        terrain_grid_gdf = gpd.GeoDataFrame(
            [{'id': row[0], 'hex_type': row[1], 'geometry': wkb.loads(row[2])} for row in terrain_grid_data],
            geometry='geometry'
        )
        
        boundary_nodes_gdf = gpd.GeoDataFrame(
            [{'id': row[0], 'node_type': row[1], 'geometry': wkb.loads(row[2])} for row in boundary_nodes_data],
            geometry='geometry'
        )
        
        water_boundary_nodes_gdf = gpd.GeoDataFrame(
            [{'id': row[0], 'node_type': row[1], 'geometry': wkb.loads(row[2])} for row in water_boundary_nodes_data],
            geometry='geometry'
        )
        
        land_portion_nodes_gdf = gpd.GeoDataFrame(
            [{'id': row[0], 'node_type': row[1], 'geometry': wkb.loads(row[2])} for row in land_portion_nodes_data],
            geometry='geometry'
        )
        
        boundary_boundary_edges_gdf = gpd.GeoDataFrame(
            [{'id': row[0], 'start_node_id': row[1], 'end_node_id': row[2], 'geometry': wkb.loads(row[3])} for row in boundary_boundary_edges_data],
            geometry='geometry'
        )
        
        boundary_land_portion_edges_gdf = gpd.GeoDataFrame(
            [{'id': row[0], 'start_node_id': row[1], 'end_node_id': row[2], 'geometry': wkb.loads(row[3])} for row in boundary_land_portion_edges_data],
            geometry='geometry'
        )
        
        land_portion_water_boundary_edges_gdf = gpd.GeoDataFrame(
            [{'id': row[0], 'start_node_id': row[1], 'end_node_id': row[2], 'geometry': wkb.loads(row[3])} for row in land_portion_water_boundary_edges_data],
            geometry='geometry'
        )
        
        water_obstacles_gdf = gpd.GeoDataFrame(
            [{'id': row[0], 'geometry': wkb.loads(row[1])} for row in water_obstacles_data],
            geometry='geometry'
        )
        
        return {
            'terrain_grid': terrain_grid_gdf,
            'boundary_nodes': boundary_nodes_gdf,
            'water_boundary_nodes': water_boundary_nodes_gdf,
            'land_portion_nodes': land_portion_nodes_gdf,
            'boundary_boundary_edges': boundary_boundary_edges_gdf,
            'boundary_land_portion_edges': boundary_land_portion_edges_gdf,
            'land_portion_water_boundary_edges': land_portion_water_boundary_edges_gdf,
            'water_obstacles': water_obstacles_gdf
        }
    
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        return None

def visualize_boundary_hexagon_layer(data, output_dir=None, show_plot=True):
    """
    Visualize the boundary hexagon layer.
    
    Args:
        data (dict): Dictionary containing GeoDataFrames for each element
        output_dir (str): Directory to save the visualization
        show_plot (bool): Whether to show the plot
    
    Returns:
        str: Path to the saved visualization file
    """
    try:
        # Create a figure
        fig, ax = plt.subplots(figsize=(15, 15))
        
        # Plot terrain grid
        terrain_grid_gdf = data['terrain_grid']
        land_hexagons = terrain_grid_gdf[terrain_grid_gdf['hex_type'] == 'land']
        boundary_hexagons = terrain_grid_gdf[terrain_grid_gdf['hex_type'] == 'boundary']
        water_with_land_hexagons = terrain_grid_gdf[terrain_grid_gdf['hex_type'] == 'water_with_land']
        
        land_hexagons.plot(ax=ax, color='lightgreen', alpha=0.5, edgecolor='black', linewidth=0.5)
        boundary_hexagons.plot(ax=ax, color='yellow', alpha=0.5, edgecolor='black', linewidth=0.5)
        water_with_land_hexagons.plot(ax=ax, color='lightblue', alpha=0.5, edgecolor='black', linewidth=0.5)
        
        # Plot water obstacles
        water_obstacles_gdf = data['water_obstacles']
        water_obstacles_gdf.plot(ax=ax, color='blue', alpha=0.3, edgecolor='blue', linewidth=0.5)
        
        # Plot boundary nodes
        boundary_nodes_gdf = data['boundary_nodes']
        boundary_nodes_gdf.plot(ax=ax, color='orange', markersize=20, marker='o')
        
        # Plot water boundary nodes
        water_boundary_nodes_gdf = data['water_boundary_nodes']
        water_boundary_nodes_gdf.plot(ax=ax, color='blue', markersize=20, marker='o')
        
        # Plot land portion nodes
        land_portion_nodes_gdf = data['land_portion_nodes']
        land_portion_nodes_gdf.plot(ax=ax, color='green', markersize=20, marker='o')
        
        # Plot boundary-to-boundary edges
        boundary_boundary_edges_gdf = data['boundary_boundary_edges']
        boundary_boundary_edges_gdf.plot(ax=ax, color='orange', linewidth=1.5)
        
        # Plot boundary-to-land-portion edges
        boundary_land_portion_edges_gdf = data['boundary_land_portion_edges']
        boundary_land_portion_edges_gdf.plot(ax=ax, color='green', linewidth=1.5)
        
        # Plot land-portion-to-water-boundary edges
        land_portion_water_boundary_edges_gdf = data['land_portion_water_boundary_edges']
        land_portion_water_boundary_edges_gdf.plot(ax=ax, color='blue', linewidth=1.5)
        
        # Add legend
        legend_elements = [
            mpatches.Patch(color='lightgreen', alpha=0.5, label='Land Hexagons'),
            mpatches.Patch(color='yellow', alpha=0.5, label='Boundary Hexagons'),
            mpatches.Patch(color='lightblue', alpha=0.5, label='Water with Land Hexagons'),
            mpatches.Patch(color='blue', alpha=0.3, label='Water Obstacles (Simplified)'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', markersize=10, label='Boundary Nodes'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=10, label='Water Boundary Nodes'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='green', markersize=10, label='Land Portion Nodes'),
            plt.Line2D([0], [0], color='orange', linewidth=1.5, label='Boundary-to-Boundary Edges'),
            plt.Line2D([0], [0], color='green', linewidth=1.5, label='Boundary-to-Land-Portion Edges'),
            plt.Line2D([0], [0], color='blue', linewidth=1.5, label='Land-Portion-to-Water-Boundary Edges')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        # Set title
        ax.set_title('Boundary Hexagon Layer Visualization (Simplified Water Obstacles)', fontsize=16)
        
        # Set axis labels
        ax.set_xlabel('X Coordinate', fontsize=12)
        ax.set_ylabel('Y Coordinate', fontsize=12)
        
        # Set aspect ratio
        ax.set_aspect('equal')
        
        # Save the figure
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
            output_file = os.path.join(output_dir, f'{timestamp}_boundary_hexagon_layer_simplified.png')
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            logger.info(f"Visualization saved to {output_file}")
        
        # Show the plot
        if show_plot:
            plt.show()
        
        return output_file if output_dir else None
    
    except Exception as e:
        logger.error(f"Error visualizing boundary hexagon layer: {str(e)}")
        return None

def main():
    """
    Main function to parse arguments and run the visualization.
    """
    parser = argparse.ArgumentParser(description='Visualize the boundary hexagon layer with simplified water obstacles')
    parser.add_argument('--host', type=str, default='localhost',
                        help='Database host')
    parser.add_argument('--port', type=int, default=5432,
                        help='Database port')
    parser.add_argument('--dbname', type=str, default='gis',
                        help='Database name')
    parser.add_argument('--user', type=str, default='gis',
                        help='Database user')
    parser.add_argument('--password', type=str, default='gis',
                        help='Database password')
    parser.add_argument('--output-dir', type=str, default='epsg3857_pipeline/visualizations',
                        help='Directory to save the visualization')
    parser.add_argument('--no-show', action='store_true',
                        help='Do not show the plot')
    
    args = parser.parse_args()
    
    # Connect to the database
    connection = connect_to_database(
        host=args.host,
        port=args.port,
        dbname=args.dbname,
        user=args.user,
        password=args.password
    )
    
    if connection is None:
        logger.error("Failed to connect to the database")
        return 1
    
    # Fetch data
    data = fetch_data(connection)
    
    if data is None:
        logger.error("Failed to fetch data")
        connection.close()
        return 1
    
    # Visualize the boundary hexagon layer
    output_file = visualize_boundary_hexagon_layer(
        data,
        output_dir=args.output_dir,
        show_plot=not args.no_show
    )
    
    if output_file is None:
        logger.error("Failed to visualize the boundary hexagon layer")
        connection.close()
        return 1
    
    # Close the connection
    connection.close()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
