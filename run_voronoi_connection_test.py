#!/usr/bin/env python3
"""
Voronoi Connection Strategies Test Runner

This script runs the voronoi_connection_test.sql script and visualizes the results
using matplotlib. It provides a visual comparison of different connection strategies
for connecting terrain grid points to water obstacle boundaries.
"""

import os
import sys
import argparse
import subprocess
import psycopg2
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap, BoundaryNorm

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run Voronoi Connection Strategies Test')
    parser.add_argument('--host', default='localhost', help='PostgreSQL host')
    parser.add_argument('--port', default='5432', help='PostgreSQL port')
    parser.add_argument('--dbname', default='postgres', help='PostgreSQL database name')
    parser.add_argument('--user', default='postgres', help='PostgreSQL user')
    parser.add_argument('--password', default='postgres', help='PostgreSQL password')
    parser.add_argument('--container', default='geo-graph-db-1', help='Docker container name')
    parser.add_argument('--sql-file', default='voronoi_connection_test.sql', help='SQL test file')
    parser.add_argument('--output-dir', default='visualizations', help='Output directory for visualizations')
    parser.add_argument('--skip-sql', action='store_true', help='Skip running SQL script (use existing data)')
    parser.add_argument('--show-cells', action='store_true', help='Show Voronoi cells in visualizations')
    return parser.parse_args()

def run_sql_script(args):
    """Run the SQL script in the PostgreSQL container."""
    print(f"Running SQL script {args.sql_file} in container {args.container}...")
    
    # Check if the container is running
    result = subprocess.run(
        ['docker', 'ps', '--filter', f'name={args.container}', '--format', '{{.Names}}'],
        capture_output=True, text=True
    )
    
    if args.container not in result.stdout:
        print(f"Error: Container {args.container} is not running.")
        sys.exit(1)
    
    # Copy the SQL file to the container
    subprocess.run(
        ['docker', 'cp', args.sql_file, f"{args.container}:/tmp/"],
        check=True
    )
    
    # Run the SQL script in the container
    result = subprocess.run(
        ['docker', 'exec', args.container, 'psql', 
         '-U', args.user, '-d', args.dbname, 
         '-f', f"/tmp/{os.path.basename(args.sql_file)}"],
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print(f"Error running SQL script: {result.stderr}")
        sys.exit(1)
    
    print("SQL script executed successfully.")
    return result.stdout

def connect_to_db(args):
    """Connect to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=args.host,
            port=args.port,
            dbname=args.dbname,
            user=args.user,
            password=args.password
        )
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def fetch_data(conn):
    """Fetch data from the database for visualization."""
    data = {}
    
    with conn.cursor() as cur:
        # Fetch water obstacle
        cur.execute("SELECT geom FROM test_water_obstacles")
        water_geom = cur.fetchone()[0]
        data['water_obstacle'] = water_geom
        
        # Fetch terrain points
        cur.execute("SELECT id, hex_type, ST_X(geom), ST_Y(geom) FROM test_terrain_points")
        terrain_points = cur.fetchall()
        data['terrain_points'] = terrain_points
        
        # Fetch boundary nodes
        cur.execute("SELECT node_id, ST_X(geom), ST_Y(geom) FROM test_boundary_nodes")
        boundary_nodes = cur.fetchall()
        data['boundary_nodes'] = boundary_nodes
        
        # Fetch connections for each strategy
        strategies = ['nearest', 'line_to_point', 'voronoi', 'reversed_voronoi']
        for strategy in strategies:
            cur.execute(f"""
                SELECT 
                    tp.id, ST_X(tp.geom), ST_Y(tp.geom),
                    CASE 
                        WHEN '{strategy}' = 'line_to_point' THEN 
                            ST_X(tc.closest_point), ST_Y(tc.closest_point)
                        ELSE 
                            ST_X(bn.geom), ST_Y(bn.geom)
                    END,
                    tc.distance
                FROM 
                    test_connections_{strategy} tc
                JOIN 
                    test_terrain_points tp ON tc.terrain_point_id = tp.id
                LEFT JOIN 
                    test_boundary_nodes bn ON 
                        CASE 
                            WHEN '{strategy}' = 'line_to_point' THEN FALSE
                            ELSE tc.boundary_node_id = bn.node_id
                        END
            """)
            connections = cur.fetchall()
            data[f'{strategy}_connections'] = connections
        
        # Fetch Voronoi cells if requested
        cur.execute("SELECT boundary_node_id, ST_AsText(cell_geom) FROM test_voronoi_cells")
        voronoi_cells = cur.fetchall()
        data['voronoi_cells'] = voronoi_cells
        
        cur.execute("SELECT terrain_point_id, ST_AsText(cell_geom) FROM test_reversed_voronoi_cells")
        reversed_voronoi_cells = cur.fetchall()
        data['reversed_voronoi_cells'] = reversed_voronoi_cells
        
        # Fetch statistics
        cur.execute("""
            SELECT strategy, connection_count FROM (
                SELECT 'Nearest Neighbor' AS strategy, COUNT(*) AS connection_count FROM test_connections_nearest
                UNION ALL
                SELECT 'Line-to-Point' AS strategy, COUNT(*) AS connection_count FROM test_connections_line_to_point
                UNION ALL
                SELECT 'Voronoi' AS strategy, COUNT(*) AS connection_count FROM test_connections_voronoi
                UNION ALL
                SELECT 'Reversed Voronoi' AS strategy, COUNT(*) AS connection_count FROM test_connections_reversed_voronoi
            ) AS stats
        """)
        connection_counts = cur.fetchall()
        data['connection_counts'] = connection_counts
        
        cur.execute("""
            SELECT strategy, avg_distance FROM (
                SELECT 'Nearest Neighbor' AS strategy, AVG(distance) AS avg_distance FROM test_connections_nearest
                UNION ALL
                SELECT 'Line-to-Point' AS strategy, AVG(distance) AS avg_distance FROM test_connections_line_to_point
                UNION ALL
                SELECT 'Voronoi' AS strategy, AVG(distance) AS avg_distance FROM test_connections_voronoi
                UNION ALL
                SELECT 'Reversed Voronoi' AS strategy, AVG(distance) AS avg_distance FROM test_connections_reversed_voronoi
            ) AS stats
        """)
        avg_distances = cur.fetchall()
        data['avg_distances'] = avg_distances
        
        # Fetch node distribution
        cur.execute("""
            SELECT 'Nearest Neighbor' AS strategy, boundary_node_id, COUNT(*) AS connection_count
            FROM test_connections_nearest
            GROUP BY boundary_node_id
            UNION ALL
            SELECT 'Voronoi' AS strategy, boundary_node_id, COUNT(*) AS connection_count
            FROM test_connections_voronoi
            GROUP BY boundary_node_id
            UNION ALL
            SELECT 'Reversed Voronoi' AS strategy, boundary_node_id, COUNT(*) AS connection_count
            FROM test_connections_reversed_voronoi
            GROUP BY boundary_node_id
            ORDER BY strategy, connection_count DESC
        """)
        node_distribution = cur.fetchall()
        data['node_distribution'] = node_distribution
    
    return data

def parse_wkt_polygon(wkt):
    """Parse WKT polygon string into a list of coordinates."""
    # Simple WKT parser for POLYGON
    if wkt.startswith('POLYGON'):
        # Extract coordinates
        coords_str = wkt.replace('POLYGON((', '').replace('))', '')
        coords = []
        for point_str in coords_str.split(','):
            x, y = map(float, point_str.strip().split())
            coords.append((x, y))
        return coords
    return []

def visualize_connections(data, args):
    """Visualize the different connection strategies."""
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Set up the figure
    fig, axs = plt.subplots(2, 2, figsize=(16, 16))
    axs = axs.flatten()
    
    # Define colors
    colors = {
        'water': 'lightblue',
        'land': 'lightgreen',
        'boundary': 'yellow',
        'boundary_node': 'red',
        'connection': 'blue'
    }
    
    # Plot each strategy
    strategies = ['nearest', 'line_to_point', 'voronoi', 'reversed_voronoi']
    titles = ['Nearest Neighbor', 'Line-to-Point', 'Voronoi', 'Reversed Voronoi']
    
    for i, (strategy, title) in enumerate(zip(strategies, titles)):
        ax = axs[i]
        
        # Plot water obstacle
        water_coords = parse_wkt_polygon(data['water_obstacle'])
        water_x, water_y = zip(*water_coords)
        ax.fill(water_x, water_y, color=colors['water'], alpha=0.5, label='Water Obstacle')
        
        # Plot terrain points
        for point in data['terrain_points']:
            _, hex_type, x, y = point
            color = colors[hex_type]
            ax.scatter(x, y, color=color, s=20, alpha=0.7)
        
        # Plot boundary nodes
        for node in data['boundary_nodes']:
            _, x, y = node
            ax.scatter(x, y, color=colors['boundary_node'], s=30, alpha=0.7)
        
        # Plot connections
        for conn in data[f'{strategy}_connections']:
            _, x1, y1, x2, y2, _ = conn
            ax.plot([x1, x2], [y1, y2], color=colors['connection'], linewidth=0.5, alpha=0.7)
        
        # Plot Voronoi cells if requested
        if args.show_cells:
            if strategy == 'voronoi':
                for cell in data['voronoi_cells']:
                    _, wkt = cell
                    cell_coords = parse_wkt_polygon(wkt)
                    if cell_coords:
                        cell_x, cell_y = zip(*cell_coords)
                        ax.plot(cell_x, cell_y, color='purple', linewidth=0.5, alpha=0.3)
            
            if strategy == 'reversed_voronoi':
                for cell in data['reversed_voronoi_cells']:
                    _, wkt = cell
                    cell_coords = parse_wkt_polygon(wkt)
                    if cell_coords:
                        cell_x, cell_y = zip(*cell_coords)
                        ax.plot(cell_x, cell_y, color='purple', linewidth=0.5, alpha=0.3)
        
        # Set title and labels
        ax.set_title(title)
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_aspect('equal')
        
        # Add connection count and average distance
        conn_count = next((count for strat, count in data['connection_counts'] if strat == title), 0)
        avg_dist = next((dist for strat, dist in data['avg_distances'] if strat == title), 0)
        ax.text(0.05, 0.95, f"Connections: {conn_count}\nAvg Distance: {avg_dist:.2f}",
                transform=ax.transAxes, fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.5))
    
    # Create legend
    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=colors['water'], markersize=10, label='Water'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=colors['land'], markersize=10, label='Land'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=colors['boundary'], markersize=10, label='Boundary'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=colors['boundary_node'], markersize=10, label='Boundary Node'),
        plt.Line2D([0], [0], color=colors['connection'], label='Connection')
    ]
    
    if args.show_cells:
        legend_elements.append(plt.Line2D([0], [0], color='purple', label='Voronoi Cell'))
    
    fig.legend(handles=legend_elements, loc='lower center', ncol=len(legend_elements), bbox_to_anchor=(0.5, 0.02))
    
    # Adjust layout and save
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.suptitle('Voronoi Connection Strategies Comparison', fontsize=16)
    plt.savefig(os.path.join(args.output_dir, 'connection_strategies_comparison.png'), dpi=300)
    print(f"Saved visualization to {os.path.join(args.output_dir, 'connection_strategies_comparison.png')}")
    
    # Create a bar chart for node distribution
    visualize_node_distribution(data, args)

def visualize_node_distribution(data, args):
    """Visualize the distribution of connections per boundary node."""
    # Group data by strategy
    node_dist_by_strategy = {}
    for strategy, node_id, count in data['node_distribution']:
        if strategy not in node_dist_by_strategy:
            node_dist_by_strategy[strategy] = []
        node_dist_by_strategy[strategy].append((node_id, count))
    
    # Create a figure
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Set up bar positions
    strategies = ['Nearest Neighbor', 'Voronoi', 'Reversed Voronoi']
    colors = ['blue', 'green', 'red']
    
    # Calculate statistics for each strategy
    stats = []
    for strategy in strategies:
        if strategy in node_dist_by_strategy:
            counts = [count for _, count in node_dist_by_strategy[strategy]]
            stats.append({
                'strategy': strategy,
                'min': min(counts),
                'max': max(counts),
                'mean': sum(counts) / len(counts),
                'std': np.std(counts),
                'count': len(counts)
            })
    
    # Plot bar chart for each strategy
    bar_width = 0.25
    index = np.arange(len(strategies))
    
    for i, strategy in enumerate(strategies):
        if strategy in node_dist_by_strategy:
            # Sort by node_id to ensure consistent ordering
            sorted_data = sorted(node_dist_by_strategy[strategy], key=lambda x: x[0])
            node_ids = [node_id for node_id, _ in sorted_data]
            counts = [count for _, count in sorted_data]
            
            # Plot bars
            bars = ax.bar(index[i], counts[:10] if len(counts) > 10 else counts, 
                   bar_width, alpha=0.7, color=colors[i], 
                   label=f"{strategy} (mean={stats[i]['mean']:.2f}, std={stats[i]['std']:.2f})")
    
    # Add labels and title
    ax.set_xlabel('Boundary Node ID')
    ax.set_ylabel('Number of Connections')
    ax.set_title('Distribution of Connections per Boundary Node')
    ax.set_xticks(index + bar_width / 2)
    ax.set_xticklabels(['Top Nodes'] * len(strategies))
    ax.legend()
    
    # Add a table with statistics
    table_data = []
    for stat in stats:
        table_data.append([
            stat['strategy'],
            f"{stat['min']}",
            f"{stat['max']}",
            f"{stat['mean']:.2f}",
            f"{stat['std']:.2f}",
            f"{stat['count']}"
        ])
    
    table = ax.table(
        cellText=table_data,
        colLabels=['Strategy', 'Min', 'Max', 'Mean', 'Std Dev', 'Node Count'],
        loc='bottom',
        bbox=[0, -0.35, 1, 0.2]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    
    # Adjust layout and save
    plt.subplots_adjust(bottom=0.25)
    plt.tight_layout(rect=[0, 0.25, 1, 0.95])
    plt.savefig(os.path.join(args.output_dir, 'node_distribution.png'), dpi=300)
    print(f"Saved node distribution visualization to {os.path.join(args.output_dir, 'node_distribution.png')}")

def main():
    """Main function to run the test and visualize results."""
    args = parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Run SQL script if not skipped
    if not args.skip_sql:
        run_sql_script(args)
    
    # Connect to database and fetch data
    conn = connect_to_db(args)
    data = fetch_data(conn)
    conn.close()
    
    # Visualize connections
    visualize_connections(data, args)
    
    print("Voronoi connection strategies test completed successfully.")

if __name__ == "__main__":
    main()
