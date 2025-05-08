#!/usr/bin/env python3
"""
Visualize Unified Boundary Graph (Simple Version)

This script visualizes the unified boundary graph without water obstacles.
It includes error handling for invalid geometries.
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
logger = setup_logger('visualize_unified_boundary_graph_simple_fixed')

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
        
        # Fetch unified boundary nodes
        logger.info("Fetching unified boundary nodes...")
        cursor.execute("""
            SELECT id, element_type, element_subtype, ST_AsBinary(geom) AS geom
            FROM unified_boundary_graph
            WHERE element_type = 'node'
        """)
        unified_boundary_nodes_data = cursor.fetchall()
        
        # Fetch unified boundary edges
        logger.info("Fetching unified boundary edges...")
        cursor.execute("""
            SELECT id, element_id, element_type, element_subtype, ST_AsBinary(geom) AS geom
            FROM unified_boundary_graph
            WHERE element_type = 'edge'
        """)
        unified_boundary_edges_data = cursor.fetchall()
        
        # Close the cursor
        cursor.close()
        
        # Convert to GeoDataFrames with error handling
        unified_boundary_nodes_list = []
        for row in unified_boundary_nodes_data:
            try:
                geometry = wkb.loads(row[3])
                unified_boundary_nodes_list.append({
                    'id': row[0], 
                    'element_type': row[1], 
                    'element_subtype': row[2], 
                    'geometry': geometry
                })
            except Exception as e:
                logger.warning(f"Skipping invalid node geometry for id {row[0]}: {str(e)}")
        
        unified_boundary_edges_list = []
        for row in unified_boundary_edges_data:
            try:
                geometry = wkb.loads(row[4])
                unified_boundary_edges_list.append({
                    'id': row[0], 
                    'element_id': row[1], 
                    'element_type': row[2], 
                    'element_subtype': row[3], 
                    'geometry': geometry
                })
            except Exception as e:
                logger.warning(f"Skipping invalid edge geometry for id {row[0]}: {str(e)}")
        
        # Create GeoDataFrames
        unified_boundary_nodes_gdf = gpd.GeoDataFrame(
            unified_boundary_nodes_list,
            geometry='geometry'
        )
        
        unified_boundary_edges_gdf = gpd.GeoDataFrame(
            unified_boundary_edges_list,
            geometry='geometry'
        )
        
        logger.info(f"Successfully loaded {len(unified_boundary_nodes_gdf)} nodes and {len(unified_boundary_edges_gdf)} edges")
        
        return {
            'unified_boundary_nodes': unified_boundary_nodes_gdf,
            'unified_boundary_edges': unified_boundary_edges_gdf
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
        
        # Plot unified boundary nodes
        unified_boundary_nodes_gdf = data['unified_boundary_nodes']
        
        # Filter nodes by type
        boundary_nodes = unified_boundary_nodes_gdf[unified_boundary_nodes_gdf['element_subtype'] == 'boundary']
        water_boundary_nodes = unified_boundary_nodes_gdf[unified_boundary_nodes_gdf['element_subtype'] == 'water_boundary']
        land_portion_nodes = unified_boundary_nodes_gdf[unified_boundary_nodes_gdf['element_subtype'] == 'land_portion']
        
        # Plot nodes
        if not boundary_nodes.empty:
            boundary_nodes.plot(ax=ax, color='orange', markersize=20, marker='o')
        if not water_boundary_nodes.empty:
            water_boundary_nodes.plot(ax=ax, color='blue', markersize=20, marker='o')
        if not land_portion_nodes.empty:
            land_portion_nodes.plot(ax=ax, color='green', markersize=20, marker='o')
        
        # Plot unified boundary edges
        unified_boundary_edges_gdf = data['unified_boundary_edges']
        
        # Filter edges by type
        boundary_boundary_edges = unified_boundary_edges_gdf[unified_boundary_edges_gdf['element_subtype'] == 'boundary_boundary']
        boundary_land_portion_edges = unified_boundary_edges_gdf[unified_boundary_edges_gdf['element_subtype'] == 'boundary_land_portion']
        land_portion_water_boundary_edges = unified_boundary_edges_gdf[unified_boundary_edges_gdf['element_subtype'] == 'land_portion_water_boundary']
        
        # Plot edges
        if not boundary_boundary_edges.empty:
            boundary_boundary_edges.plot(ax=ax, color='orange', linewidth=1.5)
        if not boundary_land_portion_edges.empty:
            boundary_land_portion_edges.plot(ax=ax, color='green', linewidth=1.5)
        if not land_portion_water_boundary_edges.empty:
            land_portion_water_boundary_edges.plot(ax=ax, color='blue', linewidth=1.5)
        
        # Add legend
        legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', markersize=10, label='Boundary Nodes'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=10, label='Water Boundary Nodes'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='green', markersize=10, label='Land Portion Nodes'),
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
            output_file = os.path.join(output_dir, f'{timestamp}_unified_boundary_graph_simple.png')
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
    parser = argparse.ArgumentParser(description='Visualize the unified boundary graph (simple version)')
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
