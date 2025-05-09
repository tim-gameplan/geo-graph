# EPSG:3857 Pipeline Execution Guide

*Date: April 24, 2025*

This document provides a step-by-step guide for executing the EPSG:3857 pipeline to generate a terrain graph with water obstacles using the direct water boundary conversion approach.

## Overview

The EPSG:3857 pipeline processes OpenStreetMap (OSM) data to create a terrain graph with water obstacles. The direct water boundary conversion approach converts water obstacle polygons directly to graph elements, creating a clean representation of water boundaries for navigation.

## Prerequisites

- PostgreSQL with PostGIS and pgRouting extensions
- Docker container running the database
- Python 3.8+ with required dependencies
- OSM data in PBF format

## Pipeline Execution Steps

### 1. Database Setup and OSM Data Import

First, we need to import the OSM data into the PostgreSQL database:

```bash
# Import OSM data
python epsg3857_pipeline/scripts/import_osm_data.py --osm-file data/subsets/iowa-latest.osm_ia-central_r10.0km.osm.pbf --container geo-graph-db-1
```

This script:
- Checks if the required PostgreSQL extensions (PostGIS, pgRouting, hstore) are installed
- Imports the OSM data using osm2pgsql
- Creates the planet_osm_* tables (point, line, polygon, roads)

### 2. Standard Pipeline Execution

Next, we run the standard pipeline with improved water edge creation:

```bash
# Run the standard pipeline
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --skip-reset
```

This executes the following SQL scripts in sequence:

1. **Extract Water Features** (`01_extract_water_features_3857.sql`):
   - Extracts water features from OSM data
   - Creates typed tables for polygon and line geometries
   - Creates a unified view for backward compatibility

2. **Create Water Buffers** (`02_create_water_buffers_3857.sql`):
   - Creates buffers around water features
   - Uses different buffer sizes for different water feature types

3. **Dissolve Water Buffers** (`03_dissolve_water_buffers_3857.sql`):
   - Dissolves overlapping water buffers
   - Simplifies the resulting geometry
   - Creates a table of water obstacles

4. **Create Terrain Grid** (`04_create_terrain_grid_3857.sql`):
   - Creates a hexagonal terrain grid
   - Filters out grid cells that intersect with water obstacles
   - Creates centroids for connectivity

5. **Create Terrain Edges** (`05_create_terrain_edges_3857.sql`):
   - Creates edges between terrain grid points
   - Calculates edge lengths and costs
   - Excludes edges that intersect with water obstacles

6. **Create Water Edges** (`06_create_water_edges_improved_3857.sql`):
   - Classifies water bodies based on shape, size, and type
   - Identifies optimal crossing points
   - Creates water edges with appropriate costs
   - Verifies graph connectivity

7. **Create Environmental Tables** (`07_create_environmental_tables_3857.sql`):
   - Adds environmental conditions to edges
   - Calculates speed factors based on conditions

### 3. Direct Water Obstacle Boundary Conversion

After the standard pipeline, we run the direct water obstacle boundary conversion:

```bash
# Run the direct water obstacle boundary conversion
python epsg3857_pipeline/scripts/run_obstacle_boundary_graph.py
```

This script executes the SQL in `epsg3857_pipeline/sql/create_obstacle_boundary_graph.sql`, which:

1. **Extract Boundary Nodes**:
   - Extracts vertices from water obstacles as graph nodes
   - Preserves the original order of vertices

2. **Create Boundary Edges**:
   - Creates edges between adjacent boundary nodes
   - Connects the last node back to the first node to close the loop

3. **Connect to Terrain Grid**:
   - Connects terrain grid points to the nearest obstacle boundary nodes
   - Ensures connections don't cross through water obstacles

4. **Create Unified Graph**:
   - Combines terrain edges, boundary edges, and connection edges
   - Assigns appropriate costs and attributes to each edge type

5. **Check Graph Connectivity**:
   - Verifies that the graph is fully connected
   - Reports connectivity statistics

### 4. Visualization

Finally, we visualize the obstacle boundary graph:

```bash
# Visualize the obstacle boundary graph
python epsg3857_pipeline/scripts/visualize_obstacle_boundary_graph.py --show-unified
```

This generates a visualization showing:
- The hexagonal terrain grid (dotted lines)
- Water obstacles (white areas)
- Obstacle boundary nodes (blue dots along water boundaries)
- Obstacle boundary edges (blue lines connecting boundary nodes)
- Connection edges (red lines connecting terrain to boundary)

The visualization is saved to `epsg3857_pipeline/visualizations/` with a timestamp in the filename.

## Results

The pipeline creates the following key tables:

1. **Water Feature Tables**:
   - `water_features_polygon`: Polygon water features (lakes, reservoirs)
   - `water_features_line`: Line water features (rivers, streams)
   - `water_features`: View that unifies both tables

2. **Water Processing Tables**:
   - `water_buffers`: Buffers around water features
   - `water_obstacles`: Dissolved water buffers

3. **Terrain Grid Tables**:
   - `terrain_grid`: Hexagonal grid cells
   - `terrain_grid_points`: Centroids of grid cells

4. **Edge Tables**:
   - `terrain_edges`: Edges between terrain grid points
   - `water_edges`: Edges for water crossings
   - `unified_edges`: Combined terrain and water edges

5. **Obstacle Boundary Tables**:
   - `obstacle_boundary_nodes`: Nodes along water obstacle boundaries
   - `obstacle_boundary_edges`: Edges connecting boundary nodes
   - `obstacle_boundary_connection_edges`: Edges connecting terrain to boundary
   - `unified_obstacle_edges`: Combined terrain, boundary, and connection edges

## Configuration

The pipeline uses the following configuration files:

- `epsg3857_pipeline/config/crs_standardized_config_improved.json`: Configuration for the standard pipeline with improved water edge creation
- Default parameters for the obstacle boundary graph:
  - `max_connection_distance`: 300 meters
  - `water_speed_factor`: 0.2

## Execution Summary

In our execution, we observed:
- 18,981 obstacle boundary nodes were created
- 18,981 obstacle boundary edges were created
- 1,058 obstacle boundary connection edges were created
- 142,785 total unified obstacle edges were created

The resulting graph provides a realistic representation of the terrain with water obstacles, allowing for navigation along water boundaries and efficient pathfinding.

## Next Steps

Potential next steps for improving the pipeline:
1. Add more sophisticated cost models for different types of water boundaries
2. Add support for multi-polygon water obstacles
3. Integrate the direct water obstacle boundary conversion with the main pipeline
4. Optimize the connection algorithm for large datasets
5. Add environmental conditions for more realistic edge costs
