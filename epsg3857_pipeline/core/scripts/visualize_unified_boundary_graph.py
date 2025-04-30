#!/usr/bin/env python3
"""
Visualize Unified Boundary Graph

This script visualizes the unified boundary graph, showing:
1. Terrain grid (land, boundary, water_with_land hexagons)
2. Terrain edges
3. Boundary nodes
4. Water boundary nodes
5. Land portion nodes
6. All connections between nodes
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
logger = setup_logger('visualize_unified_boundary_graph')

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
        
        # Fetch unified boundary nodes
        logger.info("Fetching unified boundary nodes...")
        cursor.execute("""
            SELECT id, node_type, ST_AsBinary(geom) AS geom
            FROM unified_boundary_nodes
        """)
        unified_nodes_data = cursor.fetchall()
        
        # Fetch unified boundary edges
        logger.info("Fetching unified boundary edges...")
        cursor.execute("""
            SELECT id, start_node_type, end_node_type, ST_AsBinary(geom) AS geom
            FROM unified_boundary_edges
        """)
        unified_edges_data = cursor.fetchall()
        
        # Fetch water obstacles
        logger.info("Fetching water obstacles...")
        cursor.execute("""
            SELECT id, ST_AsBinary(geom) AS geom
            FROM water_obstacles
        """)
        water_obstacles_data = cursor.fetchall()
        
        # Close the cursor
        cursor.close()
        
        # Convert to GeoDataFrames
        terrain_grid_gdf = gpd.GeoDataFrame(
            [{'id': row[0], 'hex_type': row[1], 'geometry': wkb.loads(row[2])} for row in terrain_grid_data],
            geometry='geometry'
        )
        
        unified_nodes_gdf = gpd.GeoDataFrame(
            [{'id': row[0], 'node_type': row[1], 'geometry': wkb.loads(row[2])} for row in unified_nodes_data],
            geometry='geometry'
        )
        
        unified_edges_gdf = gpd.GeoDataFrame(
            [{'id': row[0], 'start_node_type': row[1], 'end_node_type': row[2], 'geometry': wkb.loads(row[3])} for row in unified_edges_data],
            geometry='geometry'
        )
        
        water_obstacles_gdf = gpd.GeoDataFrame(
            [{'id': row[0], 'geometry': wkb.loads(row[1])} for row in water_obstacles_data],
            geometry='geometry'
        )
        
        return {
            'terrain_grid': terrain_grid_gdf,
            'unified_nodes': unified_nodes_gdf,
            'unified_edges': unified_edges_gdf,
            'water_obstacles': water_obstacles_gdf
        }
    
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        return None

def visualize_unified_boundary_graph(data, output_dir=None, show_plot=True):
    """
    Visualize the unified boundary graph.
    
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
        
        land_hexagons.plot(ax=ax, color='lightgreen', alpha=0.3, edgecolor='black', linewidth=0.5)
        boundary_hexagons.plot(ax=ax, color='yellow', alpha=0.3, edgecolor='black', linewidth=0.5)
        water_with_land_hexagons.plot(ax=ax, color='lightblue', alpha=0.3, edgecolor='black', linewidth=0.5)
        
        # Plot water obstacles
        water_obstacles_gdf = data['water_obstacles']
        water_obstacles_gdf.plot(ax=ax, color='blue', alpha=0.3, edgecolor='blue', linewidth=0.5)
        
        # Plot nodes by type
        unified_nodes_gdf = data['unified_nodes']
        
        # Terrain nodes (land and boundary)
        terrain_nodes = unified_nodes_gdf[unified_nodes_gdf['node_type'].isin(['land', 'boundary'])]
        terrain_nodes.plot(ax=ax, color='darkgreen', markersize=10, marker='o')
        
        # Boundary nodes
        boundary_nodes = unified_nodes_gdf[unified_nodes_gdf['node_type'] == 'boundary_node']
        boundary_nodes.plot(ax=ax, color='orange', markersize=20, marker='o')
        
        # Water boundary nodes
        water_boundary_nodes = unified_nodes_gdf[unified_nodes_gdf['node_type'] == 'water_boundary']
        water_boundary_nodes.plot(ax=ax, color='blue', markersize=20, marker='o')
        
        # Land portion nodes
        land_portion_nodes = unified_nodes_gdf[unified_nodes_gdf['node_type'] == 'land_portion']
        land_portion_nodes.plot(ax=ax, color='green', markersize=20, marker='o')
        
        # Plot edges by type
        unified_edges_gdf = data['unified_edges']
        
        # Terrain edges
        terrain_edges = unified_edges_gdf[(unified_edges_gdf['start_node_type'] == 'terrain') & 
                                         (unified_edges_gdf['end_node_type'] == 'terrain')]
        terrain_edges.plot(ax=ax, color='darkgreen', linewidth=1.0)
        
        # Boundary-to-boundary edges
        boundary_boundary_edges = unified_edges_gdf[(unified_edges_gdf['start_node_type'] == 'boundary_node') & 
                                                   (unified_edges_gdf['end_node_type'] == 'boundary_node')]
        boundary_boundary_edges.plot(ax=ax, color='orange', linewidth=1.5)
        
        # Boundary-to-land-portion edges
        boundary_land_portion_edges = unified_edges_gdf[(unified_edges_gdf['start_node_type'] == 'boundary_node') & 
                                                       (unified_edges_gdf['end_node_type'] == 'land_portion')]
        boundary_land_portion_edges.plot(ax=ax, color='green', linewidth=1.5)
        
        # Land-portion-to-water-boundary edges
        land_portion_water_boundary_edges = unified_edges_gdf[(unified_edges_gdf['start_node_type'] == 'land_portion') & 
                                                             (unified_edges_gdf['end_node_type'] == 'water_boundary')]
        land_portion_water_boundary_edges.plot(ax=ax, color='blue', linewidth=1.5)
        
        # Add legend
        legend_elements = [
            mpatches.Patch(color='lightgreen', alpha=0.3, label='Land Hexagons'),
            mpatches.Patch(color='yellow', alpha=0.3, label='Boundary Hexagons'),
            mpatches.Patch(color='lightblue', alpha=0.3, label='Water with Land Hexagons'),
            mpatches.Patch(color='blue', alpha=0.3, label='Water Obstacles'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='darkgreen', markersize=10, label='Terrain Nodes'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', markersize=10, label='Boundary Nodes'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=10, label='Water Boundary Nodes'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='green', markersize=10, label='Land Portion Nodes'),
            plt.Line2D([0], [0], color='darkgreen', linewidth=1.0, label='Terrain Edges'),
            plt.Line2D([0], [0], color='orange', linewidth=1.5, label='Boundary-to-Boundary Edges'),
            plt.Line2D([0], [0], color='green', linewidth=1.5, label='Boundary-to-Land-Portion Edges'),
            plt.Line2D([0], [0], color='blue', linewidth=1.5, label='Land-Portion-to-Water-Boundary Edges')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        # Set title
        ax.set_title('Unified Boundary Graph Visualization', fontsize=16)
        
        # Set axis labels
        ax.set_xlabel('X Coordinate', fontsize=12)
        ax.set_ylabel('Y Coordinate', fontsize=12)
        
        # Set aspect ratio
        ax.set_aspect('equal')
        
        # Save the figure
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
            output_file = os.path.join(output_dir, f'{timestamp}_unified_boundary_graph.png')
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            logger.info(f"Visualization saved to {output_file}")
        
        # Show the plot
        if show_plot:
            plt.show()
        
        return output_file if output_dir else None
    
    except Exception as e:
        logger.error(f"Error visualizing unified boundary graph: {str(e)}")
        return None

def main():
    """
    Main function to parse arguments and run the visualization.
    """
    parser = argparse.ArgumentParser(description='Visualize the unified boundary graph')
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
    
    # Visualize the unified boundary graph
    output_file = visualize_unified_boundary_graph(
        data,
        output_dir=args.output_dir,
        show_plot=not args.no_show
    )
    
    if output_file is None:
        logger.error("Failed to visualize the unified boundary graph")
        connection.close()
        return 1
    
    # Close the connection
    connection.close()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
