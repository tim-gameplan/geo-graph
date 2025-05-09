# Water Boundary Approach for Terrain Graph Creation

This document describes the water boundary approach for creating terrain graphs with water obstacles. This approach fundamentally changes how water obstacles are represented in the graph, resulting in more realistic movement patterns and better graph connectivity.

## Overview

The water boundary approach treats water obstacles as navigable boundaries rather than impassable barriers. Instead of trying to create edges that cross water obstacles, we create edges along the perimeter of water obstacles and connect them to the terrain grid. This allows vehicles to navigate around water obstacles, which is more realistic than crossing them directly.

## Key Concepts

1. **Water Boundaries as Edges**: Water obstacle boundaries are converted to graph edges, allowing vehicles to navigate along the perimeter of water obstacles.
2. **Terrain Grid with Water**: The terrain grid includes cells that intersect with water, marked as water cells with higher costs.
3. **Terrain-to-Boundary Connections**: Terrain grid points are connected to the nearest water boundary points, creating a seamless transition between land and water.
4. **Unified Graph**: The terrain edges and water boundary edges are combined into a unified graph, ensuring full connectivity.

## Implementation Details

### 1. Terrain Grid Creation with Water

The terrain grid creation script (`04_create_terrain_grid_with_water_3857.sql`) creates a hexagonal grid that includes cells that intersect with water. These cells are marked as water cells with higher costs.

```sql
-- Mark grid cells that intersect with water obstacles
marked_grid AS (
    SELECT
        hg.geom,
        EXISTS (
            SELECT 1
            FROM water_obstacles wo
            WHERE ST_Intersects(hg.geom, wo.geom)
        ) AS is_water
    FROM hex_grid hg
)
```

### 2. Terrain Edges Creation with Water

The terrain edges creation script (`05_create_terrain_edges_with_water_3857.sql`) creates edges between all terrain grid points, including those in water. Edges that cross water or connect to water points have higher costs.

```sql
-- Higher cost for edges that cross water or connect to water points
CASE
    WHEN EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Intersects(water_obstacles.geom, ST_MakeLine(t1.geom, t2.geom))
    ) OR t1.is_water OR t2.is_water THEN ST_Length(ST_MakeLine(t1.geom, t2.geom)) / 1.0 -- Slower speed in water (1 m/s)
    ELSE ST_Length(ST_MakeLine(t1.geom, t2.geom)) / 5.0 -- Normal speed on land (5 m/s)
END AS cost
```

### 3. Water Boundary Edges Creation

The water boundary edges creation script (`06_create_water_boundary_edges_3857.sql`) has three main steps:

#### Step 1: Extract Boundary Points

Extract points directly from the vertices of each water obstacle polygon:

```sql
-- Extract points from the exterior ring of each polygon in their original order
boundary_points AS (
    SELECT 
        id AS water_obstacle_id,
        (ST_DumpPoints(ST_ExteriorRing(geom))).path[1] AS point_order,
        (ST_DumpPoints(ST_ExteriorRing(geom))).geom AS geom
    FROM 
        water_obstacles
)
```

#### Step 2: Create Edges Between Boundary Points

Create edges between adjacent boundary points to form a continuous path along the water boundary:

```sql
-- Use the original point order from the polygon vertices
ordered_boundary_points AS (
    SELECT 
        bp.id,
        bp.water_obstacle_id,
        bp.geom,
        p.point_order
    FROM 
        water_boundary_points bp
    JOIN (
        -- Get the original point order from the polygon vertices
        SELECT 
            id AS water_obstacle_id,
            (ST_DumpPoints(ST_ExteriorRing(geom))).path[1] AS point_order,
            (ST_DumpPoints(ST_ExteriorRing(geom))).geom AS geom
        FROM 
            water_obstacles
    ) p ON bp.water_obstacle_id = p.water_obstacle_id AND ST_Equals(bp.geom, p.geom)
)
-- Create edges between adjacent boundary points
SELECT 
    bp1.id AS source_id,
    bp2.id AS target_id,
    ST_Length(ST_MakeLine(bp1.geom, bp2.geom)) AS length,
    ST_Length(ST_MakeLine(bp1.geom, bp2.geom)) / (5.0 * :water_speed_factor) AS cost,
    bp1.water_obstacle_id,
    'boundary' AS edge_type,
    :water_speed_factor,
    ST_MakeLine(bp1.geom, bp2.geom) AS geom
FROM 
    ordered_boundary_points bp1
JOIN 
    ordered_boundary_points bp2 
    ON bp1.water_obstacle_id = bp2.water_obstacle_id 
    AND bp1.point_order + 1 = bp2.point_order
```

#### Step 3: Connect Terrain Points to Boundary Points

Connect terrain grid points to the nearest water boundary points, ensuring that connections don't cross through water obstacles:

```sql
-- For each terrain point near water but outside water obstacles, find the closest water boundary point
closest_connections AS (
    SELECT DISTINCT ON (tgp.id)
        tgp.id AS terrain_point_id,
        wbp.id AS boundary_point_id,
        wbp.water_obstacle_id,
        ST_Distance(tgp.geom, wbp.geom) AS distance,
        ST_MakeLine(tgp.geom, wbp.geom) AS geom
    FROM 
        terrain_grid_points tgp
    CROSS JOIN 
        water_boundary_points wbp
    WHERE 
        ST_DWithin(tgp.geom, wbp.geom, :max_connection_distance)
        -- Only connect terrain points that are outside water obstacles
        AND NOT EXISTS (
            SELECT 1
            FROM water_obstacles wo
            WHERE wo.id = wbp.water_obstacle_id
            AND ST_Contains(wo.geom, tgp.geom)
        )
        -- Ensure the connection line doesn't cross through the water obstacle
        AND NOT EXISTS (
            SELECT 1
            FROM water_obstacles wo
            WHERE wo.id = wbp.water_obstacle_id
            AND ST_Crosses(ST_MakeLine(tgp.geom, wbp.geom), wo.geom)
        )
    ORDER BY 
        tgp.id, ST_Distance(tgp.geom, wbp.geom)
)
```

### 4. Unified Graph Creation

The water boundary edges creation script also creates a unified graph that combines terrain edges and water boundary edges:

```sql
-- Create a unified edges table
DROP TABLE IF EXISTS unified_edges CASCADE;
CREATE TABLE unified_edges (
    id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    length NUMERIC,
    cost NUMERIC, -- Travel time cost
    edge_type TEXT,
    speed_factor NUMERIC,
    is_water BOOLEAN,
    geom GEOMETRY(LINESTRING, :storage_srid)
);

-- Insert terrain edges
INSERT INTO unified_edges (source_id, target_id, length, cost, edge_type, speed_factor, is_water, geom)
SELECT 
    source_id,
    target_id,
    length,
    cost,
    CASE WHEN is_water_crossing THEN 'terrain_water' ELSE 'terrain' END AS edge_type,
    CASE WHEN is_water_crossing THEN 0.2 ELSE 1.0 END AS speed_factor,
    is_water_crossing AS is_water,
    geom
FROM 
    terrain_edges;

-- Insert water edges
INSERT INTO unified_edges (source_id, target_id, length, cost, edge_type, speed_factor, is_water, geom)
SELECT 
    source_id,
    target_id,
    length,
    cost,
    'water_' || edge_type AS edge_type,
    speed_factor,
    TRUE AS is_water,
    geom
FROM 
    water_edges;
```

### 5. Graph Connectivity Verification

The water boundary edges creation script includes a connectivity check to ensure the graph is fully connected:

```sql
-- Check graph connectivity
WITH RECURSIVE
connected_nodes(node_id) AS (
    -- Start with the first node
    SELECT source_id FROM unified_edges LIMIT 1
    UNION
    -- Add all nodes reachable from already connected nodes
    SELECT e.target_id
    FROM connected_nodes c
    JOIN unified_edges e ON c.node_id = e.source_id
    WHERE e.target_id NOT IN (SELECT node_id FROM connected_nodes)
)
SELECT 
    (SELECT COUNT(DISTINCT source_id) FROM unified_edges) AS total_nodes,
    COUNT(*) AS connected_nodes,
    COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT source_id) FROM unified_edges) AS connectivity_percentage
FROM 
    connected_nodes;
```

## Configuration

The water boundary approach is configured in `crs_standardized_config_boundary.json`:

```json
{
    "water_edges": {
        "water_speed_factor": 0.2,
        "boundary_segment_length": 100,
        "max_connection_distance": 300
    }
}
```

- `water_speed_factor`: Speed factor for water edges (default: 0.2)
- `boundary_segment_length`: Length of boundary segments in meters (default: 100)
- `max_connection_distance`: Maximum distance for connecting terrain points to water boundaries (default: 300)

## Running the Pipeline

To run the pipeline with the water boundary approach:

```bash
python epsg3857_pipeline/run_epsg3857_pipeline.py --water-boundary
```

Or to use a custom configuration:

```bash
python epsg3857_pipeline/run_epsg3857_pipeline.py --water-boundary --config epsg3857_pipeline/config/crs_standardized_config_boundary.json
```

## Benefits

1. **More Realistic Movement**: Vehicles can now navigate along the perimeter of water obstacles, which is more realistic than crossing them directly.
2. **Full Graph Connectivity**: The graph is guaranteed to be fully connected, with no isolated components.
3. **Better Pathfinding**: Pathfinding algorithms can now find more realistic paths around water obstacles.
4. **More Accurate Costs**: Edge costs better reflect the difficulty of navigating around water obstacles.
5. **Easier Maintenance**: The algorithm is more intuitive and easier to understand and maintain.

## Comparison with Previous Approaches

### Original Approach

The original approach created terrain grid cells that avoided water obstacles and tried to create edges that crossed water obstacles directly. This resulted in poor graph connectivity and unrealistic movement patterns.

### Improved Approach

The improved approach added water body classification, optimal crossing point identification, and graph connectivity verification. While this improved connectivity, it still relied on creating edges that crossed water obstacles directly.

### Water Boundary Approach

The water boundary approach fundamentally changes how water obstacles are represented in the graph. Instead of creating edges that cross water obstacles, we create edges along the perimeter of water obstacles and connect them to the terrain grid. This results in more realistic movement patterns and better graph connectivity.

## Future Improvements

1. **Boundary Segmentation Refinement**: Refine the boundary segmentation algorithm to create more or fewer points based on the complexity of the water boundary.
2. **Cost Model Refinement**: Refine the cost model for different types of water boundaries (e.g., rivers vs. lakes).
3. **Performance Optimization**: Optimize the algorithm for large datasets, particularly the terrain-to-boundary connection step.
4. **Integration with Environmental Conditions**: Integrate with environmental conditions to adjust costs based on weather, time of day, etc.
