# Boundary Hexagon Layer Implementation Plan

## Overview

The Boundary Hexagon Layer approach is a new method for extending the terrain graph to water boundaries. Unlike the standard approach which removes hexagons that intersect with water obstacles, this approach preserves these boundary hexagons and creates a more natural transition between land and water. This document outlines the implementation plan for this approach.

## Goals

1. Fill the "white space" between terrain and water obstacles
2. Improve graph connectivity at water boundaries
3. Create a more natural representation of water boundaries
4. Maintain the hexagonal grid structure for consistency
5. Ensure optimal pathfinding around water obstacles

## Technical Approach

### 1. Terrain Grid Creation with Boundary Preservation

Unlike the standard approach which filters out grid cells that intersect with water obstacles, the Boundary Hexagon Layer approach will:

1. Generate a complete hexagonal grid covering the extent of the data
2. Identify hexagons that intersect with water obstacles as "boundary hexagons"
3. Classify hexagons as:
   - **Land hexagons**: Hexagons that don't intersect with water obstacles
   - **Boundary hexagons**: Hexagons that partially intersect with water obstacles
   - **Water hexagons**: Hexagons that are completely within water obstacles (these will be filtered out)

```sql
-- Create a complete hexagonal grid
CREATE TABLE complete_hex_grid AS
SELECT (ST_HexagonGrid(:grid_spacing, ST_Extent(geom))).*
FROM planet_osm_polygon
WHERE ST_IsValid(geom);

-- Classify hexagons
CREATE TABLE classified_hex_grid AS
SELECT
    hg.geom,
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM water_obstacles wo
            WHERE ST_Contains(wo.geom, hg.geom)
        ) THEN 'water'
        WHEN EXISTS (
            SELECT 1
            FROM water_obstacles wo
            WHERE ST_Intersects(wo.geom, hg.geom)
        ) THEN 'boundary'
        ELSE 'land'
    END AS hex_type
FROM complete_hex_grid hg;

-- Create the terrain grid (excluding water hexagons)
CREATE TABLE terrain_grid AS
SELECT geom, hex_type
FROM classified_hex_grid
WHERE hex_type IN ('land', 'boundary');
```

### 2. Boundary Node Creation

For each boundary hexagon, we need to create nodes that represent the land portion of the hexagon:

1. Compute the intersection of each boundary hexagon with land (the difference between the hexagon and water obstacles)
2. Create nodes at strategic locations within this land portion:
   - For simple cases: Use the centroid of the land portion
   - For complex cases: Create multiple nodes based on the shape of the land portion

```sql
-- Create land portions of boundary hexagons
CREATE TABLE boundary_land_portions AS
SELECT
    hg.geom AS hex_geom,
    ST_Difference(hg.geom, ST_Union(wo.geom)) AS land_portion
FROM
    classified_hex_grid hg
JOIN
    water_obstacles wo ON ST_Intersects(hg.geom, wo.geom)
WHERE
    hg.hex_type = 'boundary'
GROUP BY
    hg.geom;

-- Create boundary nodes
CREATE TABLE boundary_nodes AS
-- Simple case: Use centroid if it falls within the land portion
SELECT
    ROW_NUMBER() OVER () AS node_id,
    'boundary' AS node_type,
    CASE
        WHEN ST_Contains(land_portion, ST_Centroid(hex_geom)) THEN ST_Centroid(hex_geom)
        ELSE ST_PointOnSurface(land_portion)
    END AS geom
FROM
    boundary_land_portions;
```

### 3. Water Boundary Node Creation

We also need to create nodes along the water boundaries to represent the interface between land and water:

1. Extract the intersection lines between boundary hexagons and water obstacles
2. Create nodes at regular intervals along these intersection lines
3. Ensure that nodes are properly spaced and don't create redundant connections
4. Create additional water boundary nodes in water hexagons to improve connectivity
5. Create bridge nodes at strategic locations to connect across narrow water obstacles

```sql
-- Extract intersection lines between boundary hexagons and water obstacles
CREATE TABLE boundary_intersection_lines AS
SELECT
    hg.geom AS hex_geom,
    ST_Intersection(hg.geom, wo.geom) AS intersection_line,
    wo.id AS water_obstacle_id
FROM
    classified_hex_grid hg
JOIN
    water_obstacles wo ON ST_Intersects(hg.geom, wo.geom)
WHERE
    hg.hex_type = 'boundary'
    AND ST_Dimension(ST_Intersection(hg.geom, wo.geom)) = 1; -- Only keep line intersections

-- Create water boundary nodes at regular intervals
CREATE TABLE water_boundary_nodes AS
WITH line_points AS (
    SELECT
        water_obstacle_id,
        (ST_DumpPoints(ST_Segmentize(intersection_line, :boundary_node_spacing))).geom AS geom
    FROM
        boundary_intersection_lines
)
SELECT
    ROW_NUMBER() OVER () AS node_id,
    'water_boundary' AS node_type,
    water_obstacle_id,
    geom
FROM
    line_points;
```

### 4. Edge Creation

Now we need to create edges between the various node types:

1. **Land-to-Land Edges**: Connect land hexagon centroids to other land hexagon centroids
2. **Land-to-Boundary Edges**: Connect land hexagon centroids to boundary nodes
3. **Boundary-to-Boundary Edges**: Connect boundary nodes to other boundary nodes
4. **Boundary-to-Water Edges**: Connect boundary nodes to water boundary nodes

```sql
-- Create land-to-land edges (similar to standard approach)
CREATE TABLE land_land_edges AS
SELECT
    t1.id AS source_id,
    t2.id AS target_id,
    ST_Length(ST_MakeLine(t1.geom, t2.geom)) AS length,
    ST_Length(ST_MakeLine(t1.geom, t2.geom)) / 5.0 AS cost, -- Normal speed on land (5 m/s)
    'land_land' AS edge_type,
    ST_MakeLine(t1.geom, t2.geom) AS geom
FROM
    terrain_grid_points t1
JOIN
    terrain_grid_points t2 ON ST_DWithin(t1.geom, t2.geom, :max_edge_length)
WHERE
    t1.id < t2.id
    AND t1.hex_type = 'land'
    AND t2.hex_type = 'land'
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Intersects(water_obstacles.geom, ST_MakeLine(t1.geom, t2.geom))
    );

-- Create land-to-boundary edges
CREATE TABLE land_boundary_edges AS
SELECT
    t.id AS source_id,
    b.node_id AS target_id,
    ST_Length(ST_MakeLine(t.geom, b.geom)) AS length,
    ST_Length(ST_MakeLine(t.geom, b.geom)) / 5.0 AS cost, -- Normal speed on land (5 m/s)
    'land_boundary' AS edge_type,
    ST_MakeLine(t.geom, b.geom) AS geom
FROM
    terrain_grid_points t
JOIN
    boundary_nodes b ON ST_DWithin(t.geom, b.geom, :max_edge_length)
WHERE
    t.hex_type = 'land'
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Intersects(water_obstacles.geom, ST_MakeLine(t.geom, b.geom))
    );

-- Create boundary-to-boundary edges
CREATE TABLE boundary_boundary_edges AS
SELECT
    b1.node_id AS source_id,
    b2.node_id AS target_id,
    ST_Length(ST_MakeLine(b1.geom, b2.geom)) AS length,
    ST_Length(ST_MakeLine(b1.geom, b2.geom)) / 5.0 AS cost, -- Normal speed on land (5 m/s)
    'boundary_boundary' AS edge_type,
    ST_MakeLine(b1.geom, b2.geom) AS geom
FROM
    boundary_nodes b1
JOIN
    boundary_nodes b2 ON ST_DWithin(b1.geom, b2.geom, :max_edge_length)
WHERE
    b1.node_id < b2.node_id
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Intersects(water_obstacles.geom, ST_MakeLine(b1.geom, b2.geom))
    );

-- Create boundary-to-water edges
CREATE TABLE boundary_water_edges AS
SELECT
    b.node_id AS source_id,
    w.node_id AS target_id,
    ST_Length(ST_MakeLine(b.geom, w.geom)) AS length,
    ST_Length(ST_MakeLine(b.geom, w.geom)) / (5.0 * :water_speed_factor) AS cost, -- Slower speed for water boundary (water_speed_factor)
    'boundary_water' AS edge_type,
    ST_MakeLine(b.geom, w.geom) AS geom
FROM
    boundary_nodes b
JOIN
    water_boundary_nodes w ON ST_DWithin(b.geom, w.geom, :max_edge_length)
WHERE
    NOT EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Contains(water_obstacles.geom, b.geom)
    );
```

### 5. Water Boundary Edge Creation

Create edges along the water boundaries to allow navigation along the perimeter of water obstacles:

```sql
-- Create water boundary edges
CREATE TABLE water_boundary_edges AS
WITH ordered_nodes AS (
    SELECT
        node_id,
        water_obstacle_id,
        geom,
        ST_Azimuth(geom, ST_Centroid(
            (SELECT geom FROM water_obstacles WHERE id = water_obstacle_id)
        )) AS azimuth
    FROM
        water_boundary_nodes
)
SELECT
    n1.node_id AS source_id,
    n2.node_id AS target_id,
    ST_Length(ST_MakeLine(n1.geom, n2.geom)) AS length,
    ST_Length(ST_MakeLine(n1.geom, n2.geom)) / (5.0 * :water_speed_factor) AS cost, -- Slower speed along water boundaries
    'water_boundary' AS edge_type,
    ST_MakeLine(n1.geom, n2.geom) AS geom
FROM
    ordered_nodes n1
JOIN
    ordered_nodes n2 ON n1.water_obstacle_id = n2.water_obstacle_id
    AND ST_DWithin(n1.geom, n2.geom, :boundary_edge_max_length)
WHERE
    n1.node_id < n2.node_id
    AND ABS(n1.azimuth - n2.azimuth) < 0.5; -- Only connect nodes with similar azimuth (nearby on the boundary)
```

### 6. Unified Graph Creation

Create a unified graph that combines all edge types:

```sql
-- Create a unified edges table
CREATE TABLE unified_boundary_edges AS
-- Land-to-land edges
SELECT
    source_id,
    target_id,
    length,
    cost,
    edge_type,
    1.0 AS speed_factor,
    FALSE AS is_water,
    geom
FROM
    land_land_edges
UNION ALL
-- Land-to-boundary edges
SELECT
    source_id,
    target_id,
    length,
    cost,
    edge_type,
    1.0 AS speed_factor,
    FALSE AS is_water,
    geom
FROM
    land_boundary_edges
UNION ALL
-- Boundary-to-boundary edges
SELECT
    source_id,
    target_id,
    length,
    cost,
    edge_type,
    1.0 AS speed_factor,
    FALSE AS is_water,
    geom
FROM
    boundary_boundary_edges
UNION ALL
-- Boundary-to-water edges
SELECT
    source_id,
    target_id,
    length,
    cost,
    edge_type,
    :water_speed_factor AS speed_factor,
    TRUE AS is_water,
    geom
FROM
    boundary_water_edges
UNION ALL
-- Water boundary edges
SELECT
    source_id,
    target_id,
    length,
    cost,
    edge_type,
    :water_speed_factor AS speed_factor,
    TRUE AS is_water,
    geom
FROM
    water_boundary_edges;
```

### 7. Graph Connectivity Verification

Verify that the unified graph is fully connected:

```sql
-- Check graph connectivity
WITH RECURSIVE
connected_nodes(node_id) AS (
    -- Start with the first node
    SELECT source_id FROM unified_boundary_edges LIMIT 1
    UNION
    -- Add all nodes reachable from already connected nodes
    SELECT e.target_id
    FROM connected_nodes c
    JOIN unified_boundary_edges e ON c.node_id = e.source_id
    WHERE e.target_id NOT IN (SELECT node_id FROM connected_nodes)
)
SELECT 
    (SELECT COUNT(DISTINCT source_id) FROM unified_boundary_edges) AS total_nodes,
    COUNT(*) AS connected_nodes,
    COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT source_id) FROM unified_boundary_edges) AS connectivity_percentage
FROM 
    connected_nodes;
```

## Implementation Steps

1. **Create SQL Scripts**:
   - `04_create_terrain_grid_boundary_3857.sql`: Create terrain grid with boundary preservation
   - `05_create_boundary_nodes_3857.sql`: Create boundary nodes and water boundary nodes
   - `06_create_boundary_edges_3857.sql`: Create edges between different node types
   - `07_create_unified_boundary_graph_3857.sql`: Create unified graph and verify connectivity

2. **Create Python Runner Script**:
   - `run_water_obstacle_pipeline_boundary_hexagon.py`: Run the pipeline with the boundary hexagon layer approach

3. **Update Configuration**:
   - Create a new configuration file `crs_standardized_config_boundary_hexagon.json` with parameters for the boundary hexagon layer approach

4. **Create Tests**:
   - `test_boundary_hexagon_layer.py`: Test the boundary hexagon layer approach

5. **Create Visualization Script**:
   - `visualize_boundary_hexagon_layer.py`: Visualize the boundary hexagon layer graph

## Configuration Parameters

The boundary hexagon layer approach requires the following configuration parameters:

```json
{
  "crs": {
    "storage": 3857,
    "export": 4326,
    "analysis": 3857
  },
  "terrain_grid": {
    "grid_spacing": 200,
    "max_edge_length": 500
  },
  "boundary_hexagon_layer": {
    "boundary_node_spacing": 100,
    "boundary_edge_max_length": 200,
    "water_speed_factor": 0.2,
    "boundary_extension_distance": 50,
    "max_bridge_distance": 300,
    "max_bridge_length": 150,
    "direction_count": 8,
    "max_connections_per_direction": 2
  }
}
```

## Expected Outcomes

1. **Improved Graph Connectivity**: The boundary hexagon layer approach should provide better connectivity between land and water boundaries.
2. **No "White Space" Issues**: The approach should eliminate the "white space" issues between terrain and water obstacles.
3. **More Natural Water Boundaries**: The water boundary edges should follow the natural contours of water obstacles
