# Direct Water Obstacle Boundary Conversion

This document describes the direct water obstacle boundary conversion approach for creating terrain graphs with water obstacles. This approach directly converts water obstacle polygons to graph elements, creating a clean representation of water boundaries for navigation.

## Overview

The direct water obstacle boundary conversion approach takes the water obstacle polygons and directly converts them to graph elements:
- Extracts vertices from water obstacles as graph nodes
- Creates edges between adjacent vertices
- Connects terrain grid points to obstacle boundary nodes
- Creates a unified graph for navigation

This approach preserves the exact shape of water obstacles and creates a clean representation of water boundaries for navigation, while ensuring full graph connectivity.

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

### 3. Connect to Terrain Grid

Connect terrain grid points to obstacle boundary nodes:

```sql
-- Connect terrain grid points to obstacle boundary nodes
WITH closest_connections AS (
    -- For each terrain point near water but outside water obstacles, find the closest boundary node
    SELECT DISTINCT ON (tgp.id)
        tgp.id AS terrain_node_id,
        obn.node_id AS boundary_node_id,
        obn.water_obstacle_id,
        ST_Distance(tgp.geom, obn.geom) AS distance,
        ST_MakeLine(tgp.geom, obn.geom) AS geom
    FROM 
        terrain_grid_points tgp
    CROSS JOIN 
        obstacle_boundary_nodes obn
    WHERE 
        ST_DWithin(tgp.geom, obn.geom, :max_connection_distance)
        -- Only connect terrain points that are outside water obstacles
        AND NOT EXISTS (
            SELECT 1
            FROM water_obstacles wo
            WHERE wo.id = obn.water_obstacle_id
            AND ST_Contains(wo.geom, tgp.geom)
        )
        -- Ensure the connection line doesn't cross through the water obstacle
        AND NOT EXISTS (
            SELECT 1
            FROM water_obstacles wo
            WHERE wo.id = obn.water_obstacle_id
            AND ST_Crosses(ST_MakeLine(tgp.geom, obn.geom), wo.geom)
        )
    ORDER BY 
        tgp.id, ST_Distance(tgp.geom, obn.geom)
)
SELECT 
    terrain_node_id,
    boundary_node_id,
    water_obstacle_id,
    distance AS length,
    geom
FROM 
    closest_connections;
```

This connects each terrain grid point to the closest obstacle boundary node, ensuring that the connection doesn't cross through a water obstacle.

### 4. Create Unified Graph

Create a unified graph that combines terrain edges, obstacle boundary edges, and connection edges:

```sql
-- Create a unified edges table
DROP TABLE IF EXISTS unified_obstacle_edges CASCADE;
CREATE TABLE unified_obstacle_edges (
    edge_id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    length NUMERIC,
    cost NUMERIC, -- Travel time cost
    edge_type TEXT, -- 'terrain', 'boundary', or 'connection'
    speed_factor NUMERIC,
    is_water BOOLEAN,
    geom GEOMETRY(LINESTRING, :storage_srid)
);

-- Insert terrain edges
INSERT INTO unified_obstacle_edges (source_id, target_id, length, cost, edge_type, speed_factor, is_water, geom)
SELECT 
    source_id,
    target_id,
    length,
    cost,
    'terrain' AS edge_type,
    1.0 AS speed_factor,
    is_water_crossing AS is_water,
    geom
FROM 
    terrain_edges;

-- Insert obstacle boundary edges
INSERT INTO unified_obstacle_edges (source_id, target_id, length, cost, edge_type, speed_factor, is_water, geom)
SELECT 
    source_node_id AS source_id,
    target_node_id AS target_id,
    length,
    length / (5.0 * :water_speed_factor) AS cost, -- Slower speed along water boundaries
    'boundary' AS edge_type,
    :water_speed_factor AS speed_factor,
    TRUE AS is_water,
    geom
FROM 
    obstacle_boundary_edges;

-- Insert connection edges
INSERT INTO unified_obstacle_edges (source_id, target_id, length, cost, edge_type, speed_factor, is_water, geom)
SELECT 
    terrain_node_id AS source_id,
    boundary_node_id AS target_id,
    length,
    length / 5.0 AS cost, -- Normal speed for connections
    'connection' AS edge_type,
    1.0 AS speed_factor,
    FALSE AS is_water,
    geom
FROM 
    obstacle_boundary_connection_edges;
```

This creates a unified graph that combines terrain edges, obstacle boundary edges, and connection edges, with appropriate costs and attributes for each edge type.

### 5. Check Graph Connectivity

Check if the unified graph is fully connected:

```sql
-- Check graph connectivity
WITH RECURSIVE
connected_nodes(node_id) AS (
    -- Start with the first node
    SELECT source_id FROM unified_obstacle_edges LIMIT 1
    UNION
    -- Add all nodes reachable from already connected nodes
    SELECT e.target_id
    FROM connected_nodes c
    JOIN unified_obstacle_edges e ON c.node_id = e.source_id
    WHERE e.target_id NOT IN (SELECT node_id FROM connected_nodes)
)
SELECT 
    (SELECT COUNT(DISTINCT source_id) FROM unified_obstacle_edges) AS total_nodes,
    COUNT(*) AS connected_nodes,
    COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT source_id) FROM unified_obstacle_edges) AS connectivity_percentage
FROM 
    connected_nodes;
```

This uses a recursive query to check if the graph is fully connected, starting from the first node and adding all reachable nodes.

## Usage

### Running the Direct Water Obstacle Boundary Conversion

```bash
# Reset the database (if needed)
python epsg3857_pipeline/scripts/reset_database.py --reset-derived

# Run the standard pipeline to create water_obstacles table
python epsg3857_pipeline/scripts/run_water_obstacle_pipeline_crs.py --config epsg3857_pipeline/config/crs_standardized_config.json --sql-dir epsg3857_pipeline/sql

# Run the direct water obstacle boundary conversion
python epsg3857_pipeline/scripts/run_obstacle_boundary_graph.py --max-connection-distance 300 --water-speed-factor 0.2
```

### Visualizing the Results

```bash
# Visualize the obstacle boundary graph
python epsg3857_pipeline/scripts/visualize_obstacle_boundary_graph.py --output obstacle_boundary_graph.png

# Visualize the unified graph
python epsg3857_pipeline/scripts/visualize_obstacle_boundary_graph.py --output unified_obstacle_graph.png --show-unified
```

## Benefits

1. **More Natural Water Boundaries**: The water edges follow the exact shape of water obstacles.
2. **Simpler Implementation**: The approach is more direct and easier to understand.
3. **Better Performance**: The algorithm is more efficient, especially for large datasets.
4. **More Accurate Representation**: The graph elements directly represent the water obstacle boundaries.
5. **Full Graph Connectivity**: The unified graph is fully connected, ensuring that all parts of the terrain are reachable.
6. **Realistic Navigation**: Vehicles can navigate along water boundaries and transition between terrain and water boundaries.
7. **Optimal Pathfinding**: The unified graph enables pathfinding algorithms to find optimal paths that may involve navigating along water boundaries.

## Configuration Parameters

The direct water obstacle boundary conversion approach has the following configuration parameters:

- `storage_srid`: SRID for storage (default: 3857)
- `max_connection_distance`: Maximum distance for connecting terrain points to boundary nodes (default: 300)
- `water_speed_factor`: Speed factor for water edges (default: 0.2)

## Testing

The direct water obstacle boundary conversion approach is tested using the `test_obstacle_boundary_graph.py` script, which:

1. Runs the standard pipeline to create water_obstacles table
2. Runs the direct water obstacle boundary conversion
3. Verifies that the obstacle_boundary_nodes and obstacle_boundary_edges tables are created and populated
4. Verifies that the obstacle_boundary_connection_edges and unified_obstacle_edges tables are created and populated
5. Checks that the edges form closed loops around water obstacles
6. Checks that the unified graph is fully connected
7. Visualizes the results

```bash
# Run the tests
python epsg3857_pipeline/tests/test_obstacle_boundary_graph.py --visualize
```

## Future Improvements

1. **Add Cost Models**: Add more sophisticated cost models for different types of water boundaries.
2. **Add Support for Multi-Polygon Water Obstacles**: Handle water obstacles with multiple polygons.
3. **Integrate with Main Pipeline**: Integrate the direct water obstacle boundary conversion with the main pipeline.
4. **Optimize Connection Algorithm**: Improve the algorithm for connecting terrain grid points to obstacle boundary nodes.
5. **Add Environmental Conditions**: Consider environmental conditions for more realistic edge costs.
