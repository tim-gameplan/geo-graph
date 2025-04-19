#!/usr/bin/env python3
"""
Analyze OSM data attributes in the PostGIS database.

This script:
1. Connects to the PostgreSQL database
2. Queries the planet_osm_line and planet_osm_polygon tables
3. Shows statistics about which attributes are most commonly used
4. Provides recommendations for which attributes to include in the graph
"""

import argparse
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text
from tabulate import tabulate

def get_db_connection(host="localhost", port=5432, user="gis", password="gis", database="gis"):
    """Create a database connection."""
    connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    try:
        engine = create_engine(connection_string)
        return engine
    except Exception as e:
        print(f"Error connecting to database: {e}", file=sys.stderr)
        return None

def get_table_columns(engine, table_name):
    """Get a list of all columns in a table."""
    query = f"""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = '{table_name}'
    ORDER BY ordinal_position;
    """
    
    try:
        return pd.read_sql(query, engine)["column_name"].tolist()
    except Exception as e:
        print(f"Error getting columns for {table_name}: {e}", file=sys.stderr)
        return []

def get_column_stats(engine, table_name, column_name, limit=10):
    """Get statistics for a column."""
    query = f"""
    SELECT "{column_name}", COUNT(*) as count
    FROM {table_name}
    WHERE "{column_name}" IS NOT NULL
    GROUP BY "{column_name}"
    ORDER BY count DESC
    LIMIT {limit};
    """
    
    try:
        return pd.read_sql(query, engine)
    except Exception as e:
        print(f"Error getting stats for {table_name}.{column_name}: {e}", file=sys.stderr)
        return pd.DataFrame()

def get_column_null_counts(engine, table_name, columns):
    """Get the count of non-null values for each column."""
    results = []
    
    for column in columns:
        query = f"""
        SELECT 
            '{column}' as column_name,
            COUNT(*) as total_rows,
            COUNT("{column}") as non_null_rows,
            ROUND(COUNT("{column}")::float / COUNT(*) * 100, 2) as percentage
        FROM {table_name};
        """
        
        try:
            df = pd.read_sql(query, engine)
            results.append(df.iloc[0].to_dict())
        except Exception as e:
            print(f"Error getting null counts for {table_name}.{column}: {e}", file=sys.stderr)
    
    return pd.DataFrame(results)

def analyze_osm_table(engine, table_name, min_percentage=1.0, top_n=20, show_examples=False):
    """Analyze an OSM table and its attributes."""
    print(f"\n{'='*80}")
    print(f"Analyzing {table_name}")
    print(f"{'='*80}")
    
    # Get all columns
    columns = get_table_columns(engine, table_name)
    if not columns:
        print(f"No columns found for {table_name}")
        return
    
    print(f"Found {len(columns)} columns in {table_name}")
    
    # Get non-null counts for each column
    stats_df = get_column_null_counts(engine, table_name, columns)
    
    # Filter columns with non-null percentage above threshold
    filtered_stats = stats_df[stats_df["percentage"] >= min_percentage]
    filtered_stats = filtered_stats.sort_values("percentage", ascending=False)
    
    # Display top N columns by usage
    top_stats = filtered_stats.head(top_n)
    print("\nTop columns by usage percentage:")
    print(tabulate(top_stats, headers="keys", tablefmt="psql", showindex=False))
    
    # Show examples for selected columns
    if show_examples:
        for _, row in top_stats.iterrows():
            column = row["column_name"]
            if column not in ["way", "osm_id", "z_order"]:  # Skip geometry and internal columns
                examples = get_column_stats(engine, table_name, column)
                if not examples.empty:
                    print(f"\nTop values for {column}:")
                    print(tabulate(examples, headers="keys", tablefmt="psql", showindex=False))
    
    return top_stats

def plot_column_usage(stats_df, table_name, output_dir=None):
    """Create a bar chart of column usage."""
    if stats_df.empty:
        return
    
    # Filter out way and osm_id columns
    plot_df = stats_df[~stats_df["column_name"].isin(["way", "osm_id", "z_order"])]
    plot_df = plot_df.sort_values("percentage", ascending=False)
    
    plt.figure(figsize=(12, 8))
    plt.bar(plot_df["column_name"], plot_df["percentage"])
    plt.xticks(rotation=90)
    plt.xlabel("Column Name")
    plt.ylabel("Usage Percentage")
    plt.title(f"Column Usage in {table_name}")
    plt.tight_layout()
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(os.path.join(output_dir, f"{table_name}_column_usage.png"))
        print(f"Plot saved to {os.path.join(output_dir, f'{table_name}_column_usage.png')}")
    else:
        plt.show()

def recommend_attributes(line_stats, polygon_stats):
    """Recommend attributes to include in the graph."""
    print("\n" + "="*80)
    print("Attribute Recommendations")
    print("="*80)
    
    # Recommended attributes for roads
    road_attributes = [
        "highway",      # Road type (primary, secondary, etc.)
        "name",         # Road name
        "ref",          # Reference number (e.g., highway number)
        "maxspeed",     # Speed limit
        "oneway",       # One-way street
        "surface",      # Road surface type
        "bridge",       # Bridge
        "tunnel",       # Tunnel
        "layer",        # Layer for overlapping roads
        "access",       # Access restrictions
        "service",      # Service road type
        "junction"      # Junction type
    ]
    
    # Recommended attributes for water
    water_attributes = [
        "water",        # Water type
        "name",         # Water feature name
        "natural",      # Natural feature type
        "waterway",     # Waterway type
        "landuse",      # Land use
        "intermittent"  # Intermittent water feature
    ]
    
    # Check which recommended attributes are available
    available_road_attrs = []
    if not line_stats.empty:
        available_road_attrs = [attr for attr in road_attributes 
                               if attr in line_stats["column_name"].values]
    
    available_water_attrs = []
    if not polygon_stats.empty:
        available_water_attrs = [attr for attr in water_attributes 
                                if attr in polygon_stats["column_name"].values]
    
    # Print recommendations
    print("\nRecommended Road Attributes:")
    for attr in road_attributes:
        available = attr in available_road_attrs
        print(f"  - {attr:<10} {'[Available]' if available else '[Not Found]'}")
    
    print("\nRecommended Water Attributes:")
    for attr in water_attributes:
        available = attr in available_water_attrs
        print(f"  - {attr:<10} {'[Available]' if available else '[Not Found]'}")
    
    # SQL example for road_edges with recommended attributes
    road_sql = """
-- Example SQL for road_edges with recommended attributes
DROP TABLE IF EXISTS road_edges;
CREATE TABLE road_edges AS
SELECT
    osm_id AS id,
    way AS geom,
    ST_Length(ST_Transform(way, 4326)::geography) / 18 AS cost,   -- rough 18 m/s ≈ 40 mph
"""
    
    for attr in available_road_attrs:
        road_sql += f'    "{attr}",\n'
    
    road_sql = road_sql.rstrip(",\n") + """
FROM planet_osm_line
WHERE highway IS NOT NULL;

CREATE INDEX ON road_edges USING GIST(geom);
"""
    
    # SQL example for water_polys with recommended attributes
    water_sql = """
-- Example SQL for water_polys with recommended attributes
DROP TABLE IF EXISTS water_polys;
CREATE TABLE water_polys AS
SELECT
    osm_id AS id,
    way AS geom,
"""
    
    for attr in available_water_attrs:
        water_sql += f'    "{attr}",\n'
    
    water_sql = water_sql.rstrip(",\n") + """
FROM planet_osm_polygon
WHERE water IS NOT NULL
   OR "natural" = 'water'
   OR landuse = 'reservoir';

CREATE INDEX ON water_polys USING GIST(geom);
"""
    
    print("\nExample SQL for road_edges with recommended attributes:")
    print(road_sql)
    
    print("\nExample SQL for water_polys with recommended attributes:")
    print(water_sql)

def main():
    parser = argparse.ArgumentParser(description="Analyze OSM data attributes in the PostGIS database.")
    
    # Database connection options
    parser.add_argument("--host", default="localhost", help="Database host")
    parser.add_argument("--port", type=int, default=5432, help="Database port")
    parser.add_argument("--user", default="gis", help="Database user")
    parser.add_argument("--password", default="gis", help="Database password")
    parser.add_argument("--database", default="gis", help="Database name")
    
    # Analysis options
    parser.add_argument("--min-percentage", type=float, default=1.0,
                       help="Minimum percentage of non-null values to include in analysis")
    parser.add_argument("--top-n", type=int, default=20,
                       help="Number of top columns to display")
    parser.add_argument("--show-examples", action="store_true",
                       help="Show examples of values for each column")
    parser.add_argument("--output-dir", help="Directory to save plots")
    
    args = parser.parse_args()
    
    # Connect to the database
    engine = get_db_connection(args.host, args.port, args.user, args.password, args.database)
    if not engine:
        return 1
    
    # Check if OSM tables exist
    try:
        line_exists = pd.read_sql("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'planet_osm_line')", engine).iloc[0, 0]
        polygon_exists = pd.read_sql("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'planet_osm_polygon')", engine).iloc[0, 0]
        
        if not line_exists or not polygon_exists:
            print("Error: OSM tables not found. Make sure you have imported OSM data.", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error checking OSM tables: {e}", file=sys.stderr)
        return 1
    
    # Analyze OSM tables
    line_stats = analyze_osm_table(engine, "planet_osm_line", args.min_percentage, args.top_n, args.show_examples)
    polygon_stats = analyze_osm_table(engine, "planet_osm_polygon", args.min_percentage, args.top_n, args.show_examples)
    
    # Plot column usage
    if args.output_dir:
        plot_column_usage(line_stats, "planet_osm_line", args.output_dir)
        plot_column_usage(polygon_stats, "planet_osm_polygon", args.output_dir)
    
    # Recommend attributes
    recommend_attributes(line_stats, polygon_stats)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
