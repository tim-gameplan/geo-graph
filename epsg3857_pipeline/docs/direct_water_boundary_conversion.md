# Direct Water Obstacle Boundary Conversion

This document describes the direct water obstacle boundary conversion approach for creating terrain graphs with water obstacles. This approach directly converts water obstacle polygons to graph elements, creating a clean representation of water boundaries for navigation.

## Overview

The direct water obstacle boundary conversion approach takes the water obstacle polygons and directly converts them to graph elements:
- Extracts vertices from water obstacles as graph nodes
- Creates edges between adjacent vertices

This approach preserves the exact shape of water obstacles and creates a clean representation of water boundaries for navigation.

## Implementation Details

### 1. Extract Boundary Nodes

Extract boundary nodes directly from water obstacles:

```sql
-- Extract boundary nodes from water obstacles
INSERT INTO obstacle_boundary_nodes (water_obstacle_id, point_order, geom)
SELECT 
    id AS water_obstacle_id,
    (ST_DumpPoints(ST_ExteriorRing(geom))).path[1] AS point_order,
    (ST_DumpPoints(ST_ExteriorRing(geom))).geom AS geom
FROM 
    water_obstacles;
```

This extracts all vertices from the exterior ring of each water obstacle polygon, preserving their original order.

### 2. Create Boundary Edges

Create edges between adjacent boundary nodes:

```sql
-- Create edges between adjacent boundary nodes
WITH ordered_nodes AS (
    SELECT 
        node_id,
        water_obstacle_id,
        point_order,
        geom,
        LEAD(node_id) OVER (PARTITION BY water_obstacle_id ORDER BY point_order) AS next_node_id,
        LEAD(geom) OVER (PARTITION BY water_obstacle_id ORDER BY point_order) AS next_geom,
        MAX(point_order) OVER (PARTITION BY water_obstacle_id) AS max_order
    FROM 
        obstacle_boundary_nodes
)
-- Connect consecutive nodes
SELECT 
    node_id AS source_node_id,
    next_node_id AS target_node_id,
    water_obstacle_id,
    ST_Length(ST_MakeLine(geom, next_geom)) AS length,
    ST_MakeLine(geom, next_geom) AS geom
FROM 
    ordered_nodes
WHERE 
    next_node_id IS NOT NULL
UNION ALL
-- Connect last node back to first node to close the loop
SELECT 
    n1.node_id AS source_node_id,
    n2.node_id AS target_node_id,
    n1.water_obstacle_id,
    ST_Length(ST_MakeLine(n1.geom, n2.geom)) AS length,
    ST_MakeLine(n1.geom, n2.geom) AS geom
FROM 
    ordered_nodes n1
JOIN 
    obstacle_boundary_nodes n2 
    ON n1.water_obstacle_id = n2.water_obstacle_id AND n2.point_order = 1
WHERE 
    n1.point_order = n1.max_order;
```

This creates edges between adjacent nodes based on their point_order, and connects the last node back to the first node to close the loop.

## Usage

### Running the Direct Water Obstacle Boundary Conversion

```bash
# Reset the database (if needed)
python epsg3857_pipeline/scripts/reset_database.py --reset-derived

# Run the standard pipeline to create water_obstacles table
python epsg3857_pipeline/scripts/run_water_obstacle_pipeline_crs.py --config epsg3857_pipeline/config/crs_standardized_config.json --sql-dir epsg3857_pipeline/sql

# Run the direct water obstacle boundary conversion
python epsg3857_pipeline/scripts/run_obstacle_boundary_graph.py
```

### Visualizing the Results

```bash
# Visualize the obstacle boundary graph
python epsg3857_pipeline/scripts/visualize_obstacle_boundary_graph.py --output obstacle_boundary_graph.png
```

## Benefits

1. **More Natural Water Boundaries**: The water edges follow the exact shape of water obstacles.
2. **Simpler Implementation**: The approach is more direct and easier to understand.
3. **Better Performance**: The algorithm is more efficient, especially for large datasets.
4. **More Accurate Representation**: The graph elements directly represent the water obstacle boundaries.

## Future Improvements

1. **Connect to Terrain Grid**: Connect the obstacle boundary nodes to the terrain grid points.
2. **Add Cost Models**: Add cost models for different types of water boundaries.
3. **Implement Graph Connectivity Check**: Ensure the graph is fully connected.
4. **Add Support for Multi-Polygon Water Obstacles**: Handle water obstacles with multiple polygons.
5. **Integrate with Main Pipeline**: Integrate the direct water obstacle boundary conversion with the main pipeline.
