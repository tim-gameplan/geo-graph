# Comprehensive Terrain Graph Pipeline Plan

*Created: April 21, 2025*

This document provides a detailed walkthrough of the comprehensive terrain graph pipeline, including each step, the specific scripts used, the data they start with, and the data they produce.

## Pipeline Overview

```
┌─────────────────────┐
│ 1. Database Reset   │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 2. Enhanced Pipeline│
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 3. Water Obstacle   │
│    Pipeline         │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 4. Export Graph     │
│    Slice            │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 5. Visualization    │
└─────────────────────┘
```

## Detailed Pipeline Steps

### 1. Database Reset

**Script**: `scripts/reset_database.py`

**Command**:
```bash
python scripts/reset_database.py --reset-derived
```

**Input**: None (operates on the PostgreSQL database)

**Process**:
- Connects to the PostgreSQL database container using Docker commands
- Executes SQL to drop derived tables:
  ```sql
  DROP TABLE IF EXISTS road_edges CASCADE;
  DROP TABLE IF EXISTS water_polys CASCADE;
  DROP TABLE IF EXISTS water_buf CASCADE;
  DROP TABLE IF EXISTS terrain_grid CASCADE;
  DROP TABLE IF EXISTS water_edges CASCADE;
  DROP TABLE IF EXISTS terrain_edges CASCADE;
  DROP TABLE IF EXISTS unified_edges CASCADE;
  DROP TABLE IF EXISTS grid_profile CASCADE;
  ```

**Output**: Clean PostgreSQL database with all derived tables removed, but OSM base data preserved

### 2. Enhanced Terrain Graph Pipeline

**Script**: `scripts/run_pipeline_enhanced.py` or `scripts/run_unified_pipeline.py --mode enhanced`

**Command**:
```bash
python scripts/run_unified_pipeline.py --mode enhanced
```

**Input**: OSM data in PostgreSQL database (planet_osm_line, planet_osm_polygon tables)

**Process**:
Executes the following SQL scripts in sequence:

1. **derive_road_and_water_enhanced_fixed.sql**:
   - Input: Raw OSM data (planet_osm_line, planet_osm_polygon)
   - Process: Extracts road and water features with OSM attributes
   - Output: road_edges and water_polys tables with attributes

2. **build_water_buffers_simple.sql**:
   - Input: water_polys table
   - Process: Creates 50m buffers around water features
   - Output: water_buf table with buffer geometries

3. **create_grid_profile.sql**:
   - Input: None
   - Process: Creates a table with grid cell size profiles
   - Output: grid_profile table with cell size definitions

4. **build_terrain_grid_simple.sql**:
   - Input: water_buf table (for extent), grid_profile table
   - Process: Creates a hexagonal grid covering the area
   - Output: terrain_grid table with hexagonal cells

5. **create_edge_tables_enhanced.sql**:
   - Input: water_buf and terrain_grid tables
   - Process: Creates edge tables for water and terrain
   - Output: water_edges and terrain_edges tables

6. **add_source_target_columns.sql**:
   - Input: road_edges, water_edges, terrain_edges tables
   - Process: Adds source and target columns to edge tables
   - Output: Updated edge tables with source/target columns

7. **create_unified_edges_enhanced_fixed_v2.sql**:
   - Input: road_edges, water_edges, terrain_edges tables
   - Process: Combines all edge tables into a unified graph
   - Output: unified_edges table with all edges and attributes

8. **refresh_topology_fixed_v2.sql**:
   - Input: unified_edges table
   - Process: Creates topology for the unified graph
   - Output: Updated unified_edges table with valid topology

**Output**:
- road_edges: Table with road edges and OSM attributes
- water_polys: Table with water polygons and OSM attributes
- water_buf: Table with water buffers
- terrain_grid: Table with hexagonal terrain grid
- water_edges: Table with water edges
- terrain_edges: Table with terrain edges
- unified_edges: Table with all edges combined, with topology and OSM attributes

### 3. Water Obstacle Pipeline

**Script**: `scripts/run_unified_pipeline.py --mode water` or `planning/scripts/run_water_obstacle_pipeline_fixed.py`

**Command**:
```bash
python scripts/run_unified_pipeline.py --mode water --config planning/config/default_config.json
```

**Input**: 
- OSM data in PostgreSQL database
- Configuration file (planning/config/default_config.json)

**Process**:
Executes the following SQL scripts in sequence:

1. **01_extract_water_features.sql**:
   - Input: Raw OSM data (planet_osm_line, planet_osm_polygon)
   - Process: Extracts water features based on configuration
   - Output: water_features table with water polygons and lines

2. **02_create_water_buffers.sql**:
   - Input: water_features table, buffer configuration
   - Process: Creates buffers around water features with varying sizes
   - Output: water_buf table with detailed buffer attributes

3. **03_dissolve_water_buffers_improved.sql**:
   - Input: water_buf table
   - Process: Dissolves overlapping water buffers with improved algorithm
   - Output: water_buf_dissolved table with simplified buffers

4. **04_create_terrain_grid.sql**:
   - Input: water_buf_dissolved table (for extent), grid configuration
   - Process: Creates a hexagonal grid covering the area
   - Output: terrain_grid table with hexagonal cells

5. **05_create_terrain_edges.sql**:
   - Input: terrain_grid table
   - Process: Creates terrain edges connecting grid cells
   - Output: terrain_edges table with connections

6. **06_create_water_edges.sql**:
   - Input: water_buf_dissolved table
   - Process: Creates water edges representing water obstacles
   - Output: water_edges table with crossability attributes

7. **07_create_environmental_tables.sql**:
   - Input: None
   - Process: Creates tables for environmental conditions
   - Output: environmental_conditions table

**Output**:
- water_features: Table with water features from OSM
- water_buf: Table with detailed water buffers
- water_buf_dissolved: Table with dissolved water buffers
- terrain_grid: Table with hexagonal terrain grid
- terrain_edges: Table with terrain edges
- water_edges: Table with water edges and crossability attributes
- environmental_conditions: Table with environmental conditions

### 4. Export Graph Slice

**Script**: `tools/export_slice_enhanced_fixed.py`

**Command**:
```bash
python tools/export_slice_enhanced_fixed.py --lon -93.63 --lat 41.99 --minutes 60 --outfile enhanced_test.graphml
```

**Input**: 
- unified_edges table in PostgreSQL database
- Coordinates (longitude, latitude)
- Travel time (minutes)

**Process**:
1. Finds the nearest vertex to the specified coordinates
2. Uses pgRouting's `pgr_drivingDistance` function to calculate reachable nodes
3. Creates a convex hull of the reachable nodes to approximate an isochrone
4. Extracts edges that intersect with the isochrone polygon
5. Creates a NetworkX graph with nodes and edges
6. Preserves all OSM attributes in the graph
7. Exports the graph to GraphML format

**Output**:
- GraphML file (enhanced_test.graphml) containing:
  - Nodes with positions (x, y coordinates)
  - Edges with costs
  - OSM attributes (highway type, name, surface, etc.)
  - Water crossability attributes
  - Edge types (road, water, terrain)

### 5. Visualization

**Script**: `visualize_unified.py`

**Commands**:
```bash
# Visualize the graph slice
python visualize_unified.py --mode graphml --input enhanced_test.graphml

# Visualize the water obstacles
python visualize_unified.py --mode water
```

**Input**:
- GraphML file (for graph visualization)
- Water edges and buffers in PostgreSQL database (for water visualization)

**Process**:
1. For GraphML visualization:
   - Imports the visualize_graph module
   - Loads the GraphML file into a NetworkX graph
   - Creates a visualization with matplotlib
   - Saves the visualization to a PNG file

2. For water visualization:
   - Calls the visualize_water_obstacles.py script
   - Queries the water_buf_dissolved and water_edges tables
   - Creates a visualization with matplotlib
   - Saves the visualization to a PNG file

**Output**:
- PNG visualization files in the output/visualizations/ directory:
  - Graph visualization: output/visualizations/graphml/YYYY-MM-DD_HH-MM-SS_description_dpi-300.png
  - Water visualization: output/visualizations/water/YYYY-MM-DD_HH-MM-SS_water_obstacles_dpi-300.png

## Data Flow Through the Pipeline

The data flows through the complete pipeline as follows:

1. **OSM Data** → Database Reset → **Clean PostgreSQL Database**
   - Starting with raw OSM data in the PostgreSQL database
   - Reset clears derived tables while preserving base OSM data

2. **Clean PostgreSQL Database** → Enhanced Pipeline → **Unified Edges Table**
   - Extracts road and water features from OSM data
   - Creates water buffers and terrain grid
   - Combines all edges into a unified graph with topology
   - Preserves OSM attributes throughout the process

3. **Unified Edges Table** → Water Obstacle Pipeline → **Water Edges with Crossability**
   - Creates more detailed water buffers with varying sizes
   - Dissolves overlapping buffers for simplification
   - Creates water edges with crossability attributes
   - Adds environmental conditions

4. **Unified Edges + Water Edges** → Export Graph Slice → **GraphML File**
   - Calculates isochrone based on travel time
   - Extracts edges within the isochrone
   - Creates a NetworkX graph with all attributes
   - Exports to GraphML format

5. **GraphML File / Water Edges** → Visualization → **PNG Visualization Files**
   - Creates visualizations of the graph and water obstacles
   - Saves visualizations to the output directory

## Database Schema Evolution

Throughout the pipeline, the database schema evolves as follows:

1. **Initial State**:
   - planet_osm_line: Raw OSM line features
   - planet_osm_polygon: Raw OSM polygon features

2. **After Enhanced Pipeline**:
   - road_edges: Road edges with OSM attributes
   - water_polys: Water polygons with OSM attributes
   - water_buf: Water buffers
   - terrain_grid: Hexagonal terrain grid
   - water_edges: Water edges
   - terrain_edges: Terrain edges
   - unified_edges: All edges combined with topology

3. **After Water Obstacle Pipeline**:
   - water_features: Detailed water features
   - water_buf: Detailed water buffers
   - water_buf_dissolved: Dissolved water buffers
   - terrain_grid: Hexagonal terrain grid (possibly updated)
   - terrain_edges: Terrain edges (possibly updated)
   - water_edges: Water edges with crossability
   - environmental_conditions: Environmental conditions

## Recommended Workflow

For future development, we recommend the following workflow:

1. **Reset the Database**:
```bash
python scripts/reset_database.py --reset-derived
```

2. **Run the Enhanced Pipeline**:
```bash
python scripts/run_pipeline_enhanced.py
```

3. **Run the Water Obstacle Pipeline**:
```bash
python scripts/run_unified_pipeline.py --mode water --config planning/config/default_config.json
```

4. **Export a Graph Slice**:
```bash
python tools/export_slice_enhanced_fixed.py --lon -93.63 --lat 41.99 --minutes 60 --outfile enhanced_test.graphml
```

5. **Visualize the Results**:
```bash
# Visualize the graph slice
python visualize_unified.py --mode graphml --input enhanced_test.graphml

# Visualize the water obstacles
python visualize_unified.py --mode water
```

This comprehensive pipeline creates a terrain graph that includes roads, water obstacles, and terrain features, with OSM attributes preserved and water crossability modeled. The final GraphML file can be used for routing, analysis, and visualization.
