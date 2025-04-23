# Water Edge Creation Improvement Proposal

## Current Issues

The current water edge creation algorithm in the EPSG:3857 pipeline has several limitations that result in poor graph connectivity:

1. **Distance Threshold Issues**: The current approach uses a fixed distance threshold (recently increased from 500m to 1000m) to find pairs of terrain points that can form water crossing edges. This threshold may not be appropriate for all water bodies, especially large lakes or wide rivers.

2. **Restrictive Intersection Requirement**: The current algorithm requires that water edges must intersect with water obstacles. This is too restrictive and can prevent valid crossing edges from being created, especially for irregular-shaped water bodies.

3. **Boundary Point Selection**: The algorithm selects boundary points of water obstacles without considering the shape or size of the water body, which can lead to suboptimal crossing points.

4. **No Connectivity Verification**: There is no post-processing step to verify that the graph is fully connected and to add necessary edges where connectivity is missing.

## Proposed Solution

We propose a comprehensive solution to improve water edge creation and ensure graph connectivity:

### 1. Water Body Classification

First, we should classify water bodies based on their shape, size, and type to apply different edge creation strategies:

```sql
-- Create a water body classification table
CREATE TABLE water_body_classification (
    id SERIAL PRIMARY KEY,
    water_obstacle_id INTEGER REFERENCES water_obstacles(id),
    type TEXT, -- 'lake', 'river', 'stream', etc.
    area NUMERIC, -- Area in square meters
    perimeter NUMERIC, -- Perimeter in meters
    width_avg NUMERIC, -- Average width in meters
    width_max NUMERIC, -- Maximum width in meters
    length NUMERIC, -- Length in meters (for linear features)
    compactness NUMERIC, -- Perimeter^2 / (4 * PI * area)
    crossing_strategy TEXT -- 'bridge', 'ferry', 'none', etc.
);

-- Populate the classification table
INSERT INTO water_body_classification (
    water_obstacle_id, type, area, perimeter, 
    width_avg, width_max, length, compactness, crossing_strategy
)
SELECT 
    wo.id,
    CASE
        WHEN ST_Area(wo.geom) > 1000000 THEN 'lake'
        WHEN ST_Perimeter(wo.geom) / GREATEST(SQRT(ST_Area(wo.geom)), 1) > 10 THEN 'river'
        ELSE 'stream'
    END AS type,
    ST_Area(wo.geom) AS area,
    ST_Perimeter(wo.geom) AS perimeter,
    ST_Area(wo.geom) / GREATEST(ST_Perimeter(wo.geom), 1) AS width_avg,
    -- Calculate max width using ST_MaximumInscribedCircle
    (ST_MaximumInscribedCircle(wo.geom)).radius * 2 AS width_max,
    -- Approximate length for linear features
    CASE
        WHEN ST_Perimeter(wo.geom) / GREATEST(SQRT(ST_Area(wo.geom)), 1) > 10 
        THEN ST_Length(ST_ApproximateMedialAxis(wo.geom))
        ELSE NULL
    END AS length,
    ST_Perimeter(wo.geom)^2 / (4 * PI() * ST_Area(wo.geom)) AS compactness,
    CASE
        WHEN ST_Area(wo.geom) > 1000000 THEN 'ferry'
        WHEN ST_Area(wo.geom) > 10000 THEN 'bridge'
        ELSE 'ford'
    END AS crossing_strategy
FROM 
    water_obstacles wo;
```

### 2. Optimal Crossing Point Identification

For each water body, identify optimal crossing points based on its classification:

```sql
-- Create a table for optimal crossing points
CREATE TABLE optimal_crossing_points (
    id SERIAL PRIMARY KEY,
    water_obstacle_id INTEGER REFERENCES water_obstacles(id),
    crossing_type TEXT, -- 'bridge', 'ferry', 'ford'
    geom GEOMETRY(LINESTRING, :storage_srid)
);

-- For rivers: Find narrow points and create perpendicular crossings
INSERT INTO optimal_crossing_points (water_obstacle_id, crossing_type, geom)
SELECT 
    wbc.water_obstacle_id,
    wbc.crossing_strategy,
    ST_Intersection(
        ST_Buffer(ST_ClosestPoint(
            ST_Boundary(wo.geom), 
            ST_PointN(ST_ApproximateMedialAxis(wo.geom), generate_series(1, ST_NPoints(ST_ApproximateMedialAxis(wo.geom))))
        ), 50),
        wo.geom
    ) AS geom
FROM 
    water_body_classification wbc
JOIN 
    water_obstacles wo ON wbc.water_obstacle_id = wo.id
WHERE 
    wbc.type = 'river';

-- For lakes: Create crossings at narrow points or use ferry routes
INSERT INTO optimal_crossing_points (water_obstacle_id, crossing_type, geom)
SELECT 
    wbc.water_obstacle_id,
    wbc.crossing_strategy,
    ST_ShortestLine(
        ST_PointN(ST_Boundary(wo.geom), generate_series(1, ST_NPoints(ST_Boundary(wo.geom)), ST_NPoints(ST_Boundary(wo.geom))/10)),
        ST_PointN(ST_Boundary(wo.geom), generate_series(ST_NPoints(ST_Boundary(wo.geom))/2, ST_NPoints(ST_Boundary(wo.geom)), ST_NPoints(ST_Boundary(wo.geom))/10))
    ) AS geom
FROM 
    water_body_classification wbc
JOIN 
    water_obstacles wo ON wbc.water_obstacle_id = wo.id
WHERE 
    wbc.type = 'lake'
    AND ST_Length(
        ST_ShortestLine(
            ST_PointN(ST_Boundary(wo.geom), generate_series(1, ST_NPoints(ST_Boundary(wo.geom)), ST_NPoints(ST_Boundary(wo.geom))/10)),
            ST_PointN(ST_Boundary(wo.geom), generate_series(ST_NPoints(ST_Boundary(wo.geom))/2, ST_NPoints(ST_Boundary(wo.geom)), ST_NPoints(ST_Boundary(wo.geom))/10))
        )
    ) < wbc.width_max * 1.5;
```

### 3. Terrain Point Connection

Connect terrain points using the optimal crossing points:

```sql
-- Create water edges using optimal crossing points
INSERT INTO water_edges (source_id, target_id, length, cost, water_obstacle_id, speed_factor, geom)
WITH crossing_terrain_points AS (
    -- For each optimal crossing point, find the nearest terrain grid points
    SELECT 
        ocp.id AS crossing_id,
        ocp.water_obstacle_id,
        ocp.crossing_type,
        ocp.geom AS crossing_geom,
        (
            SELECT tgp.id
            FROM terrain_grid_points tgp
            ORDER BY ST_Distance(ST_StartPoint(ocp.geom), tgp.geom)
            LIMIT 1
        ) AS source_id,
        (
            SELECT tgp.id
            FROM terrain_grid_points tgp
            ORDER BY ST_Distance(ST_EndPoint(ocp.geom), tgp.geom)
            LIMIT 1
        ) AS target_id
    FROM 
        optimal_crossing_points ocp
)
SELECT 
    ctp.source_id,
    ctp.target_id,
    ST_Length(ST_MakeLine(
        (SELECT geom FROM terrain_grid_points WHERE id = ctp.source_id),
        (SELECT geom FROM terrain_grid_points WHERE id = ctp.target_id)
    )) AS length,
    CASE
        WHEN ctp.crossing_type = 'ferry' THEN ST_Length(ctp.crossing_geom) / (5.0 * 0.2) -- Slower for ferries
        WHEN ctp.crossing_type = 'bridge' THEN ST_Length(ctp.crossing_geom) / (5.0 * 0.8) -- Slightly slower for bridges
        ELSE ST_Length(ctp.crossing_geom) / (5.0 * 0.5) -- Medium speed for fords
    END AS cost,
    ctp.water_obstacle_id,
    CASE
        WHEN ctp.crossing_type = 'ferry' THEN 0.2
        WHEN ctp.crossing_type = 'bridge' THEN 0.8
        ELSE 0.5
    END AS speed_factor,
    ST_MakeLine(
        (SELECT geom FROM terrain_grid_points WHERE id = ctp.source_id),
        (SELECT geom FROM terrain_grid_points WHERE id = ctp.target_id)
    ) AS geom
FROM 
    crossing_terrain_points ctp;
```

### 4. Graph Connectivity Verification

Add a post-processing step to verify graph connectivity and add necessary edges:

```sql
-- Create a function to check graph connectivity
CREATE OR REPLACE FUNCTION check_graph_connectivity() RETURNS TABLE (
    component_id INTEGER,
    node_count INTEGER
) AS $$
BEGIN
    -- Create a temporary table for connected components
    CREATE TEMP TABLE connected_components (
        component_id SERIAL PRIMARY KEY,
        nodes INTEGER[]
    );
    
    -- Find connected components using a breadth-first search
    WITH RECURSIVE
    nodes AS (
        SELECT id FROM terrain_grid_points
    ),
    edges AS (
        SELECT source_id, target_id FROM unified_edges
    ),
    components(component_id, node_id, visited) AS (
        SELECT 1, MIN(id), ARRAY[MIN(id)] FROM nodes
        UNION ALL
        SELECT
            CASE
                WHEN NOT (n.id = ANY(c.visited)) AND EXISTS (
                    SELECT 1 FROM edges e 
                    WHERE (e.source_id = ANY(c.visited) AND e.target_id = n.id)
                    OR (e.target_id = ANY(c.visited) AND e.source_id = n.id)
                ) THEN c.component_id
                WHEN NOT EXISTS (
                    SELECT 1 FROM components c2 
                    WHERE n.id = ANY(c2.visited)
                ) THEN c.component_id + 1
                ELSE c.component_id
            END,
            n.id,
            CASE
                WHEN NOT (n.id = ANY(c.visited)) AND EXISTS (
                    SELECT 1 FROM edges e 
                    WHERE (e.source_id = ANY(c.visited) AND e.target_id = n.id)
                    OR (e.target_id = ANY(c.visited) AND e.source_id = n.id)
                ) THEN c.visited || n.id
                WHEN NOT EXISTS (
                    SELECT 1 FROM components c2 
                    WHERE n.id = ANY(c2.visited)
                ) THEN ARRAY[n.id]
                ELSE c.visited
            END
        FROM components c
        CROSS JOIN nodes n
        WHERE NOT EXISTS (
            SELECT 1 FROM components c2 
            WHERE c2.component_id = c.component_id AND n.id = ANY(c2.visited)
        )
    )
    INSERT INTO connected_components (component_id, nodes)
    SELECT component_id, array_agg(node_id)
    FROM components
    GROUP BY component_id;
    
    -- Return the component sizes
    RETURN QUERY
    SELECT cc.component_id, array_length(cc.nodes, 1) AS node_count
    FROM connected_components cc
    ORDER BY node_count DESC;
    
    -- Clean up
    DROP TABLE connected_components;
END;
$$ LANGUAGE plpgsql;

-- Create a function to add edges to connect disconnected components
CREATE OR REPLACE FUNCTION connect_graph_components() RETURNS INTEGER AS $$
DECLARE
    components_connected INTEGER := 0;
    source_component INTEGER;
    target_component INTEGER;
    source_node INTEGER;
    target_node INTEGER;
    min_distance NUMERIC;
    current_distance NUMERIC;
BEGIN
    -- Get the largest component (main graph)
    SELECT component_id INTO source_component
    FROM check_graph_connectivity()
    ORDER BY node_count DESC
    LIMIT 1;
    
    -- Connect each smaller component to the main graph
    FOR target_component, target_node IN
        WITH components AS (
            SELECT cc.component_id, unnest(cc.nodes) AS node_id
            FROM connected_components cc
            WHERE cc.component_id != source_component
        )
        SELECT c.component_id, c.node_id
        FROM components c
    LOOP
        -- Find the closest pair of nodes between the two components
        min_distance := 'Infinity'::NUMERIC;
        source_node := NULL;
        
        FOR source_node IN
            WITH main_component AS (
                SELECT unnest(nodes) AS node_id
                FROM connected_components
                WHERE component_id = source_component
            )
            SELECT mc.node_id
            FROM main_component mc
        LOOP
            -- Calculate distance between nodes
            SELECT ST_Distance(
                (SELECT geom FROM terrain_grid_points WHERE id = source_node),
                (SELECT geom FROM terrain_grid_points WHERE id = target_node)
            ) INTO current_distance;
            
            -- Update if this is the closest pair
            IF current_distance < min_distance THEN
                min_distance := current_distance;
                source_node := source_node;
            END IF;
        END LOOP;
        
        -- Add an edge between the closest pair of nodes
        IF source_node IS NOT NULL THEN
            INSERT INTO water_edges (
                source_id, target_id, length, cost, water_obstacle_id, speed_factor, geom
            )
            SELECT 
                source_node,
                target_node,
                min_distance AS length,
                min_distance / (5.0 * 0.2) AS cost, -- Slow crossing
                NULL AS water_obstacle_id, -- No specific water obstacle
                0.2 AS speed_factor, -- Slow speed factor
                ST_MakeLine(
                    (SELECT geom FROM terrain_grid_points WHERE id = source_node),
                    (SELECT geom FROM terrain_grid_points WHERE id = target_node)
                ) AS geom;
            
            components_connected := components_connected + 1;
        END IF;
    END LOOP;
    
    -- Update the unified edges table
    INSERT INTO unified_edges (source_id, target_id, length, cost, edge_type, speed_factor, geom)
    SELECT 
        source_id,
        target_id,
        length,
        cost,
        'water',
        speed_factor,
        geom
    FROM 
        water_edges
    WHERE 
        id > (SELECT MAX(id) FROM water_edges) - components_connected;
    
    RETURN components_connected;
END;
$$ LANGUAGE plpgsql;

-- Check graph connectivity and connect components if needed
SELECT 'Graph has ' || COUNT(*) || ' connected components' FROM check_graph_connectivity();
SELECT 'Connected ' || connect_graph_components() || ' components';
SELECT 'Graph now has ' || COUNT(*) || ' connected components' FROM check_graph_connectivity();
```

### 5. Edge Cost Refinement

Refine edge costs based on crossing type and environmental conditions:

```sql
-- Update water edge costs based on crossing type and environmental conditions
UPDATE water_edges
SET cost = 
    CASE
        WHEN crossing_type = 'ferry' THEN length / (5.0 * 0.2) -- Slower for ferries
        WHEN crossing_type = 'bridge' THEN length / (5.0 * 0.8) -- Slightly slower for bridges
        ELSE length / (5.0 * 0.5) -- Medium speed for fords
    END,
    speed_factor = 
    CASE
        WHEN crossing_type = 'ferry' THEN 0.2
        WHEN crossing_type = 'bridge' THEN 0.8
        ELSE 0.5
    END;

-- Update unified edges table with the new costs
UPDATE unified_edges ue
SET cost = we.cost,
    speed_factor = we.speed_factor
FROM water_edges we
WHERE ue.source_id = we.source_id
AND ue.target_id = we.target_id
AND ue.edge_type = 'water';
```

## Implementation Plan

To implement this improved water edge creation algorithm, we propose the following steps:

1. **Create a New SQL Script**: Create a new SQL script `06_create_water_edges_improved_3857.sql` that implements the water body classification, optimal crossing point identification, terrain point connection, graph connectivity verification, and edge cost refinement.

2. **Update the Pipeline Runner**: Modify the `run_water_obstacle_pipeline_crs.py` and `run_water_obstacle_pipeline_delaunay.py` scripts to use the new SQL script instead of the current `06_create_water_edges_3857.sql`.

3. **Add Configuration Parameters**: Add new configuration parameters to the `config_loader_3857.py` script to control the water edge creation algorithm, such as:
   - `water_crossing_strategies`: Configuration for different water crossing strategies
   - `connectivity_check_enabled`: Whether to enable graph connectivity verification
   - `max_crossing_distance`: Maximum distance for water crossings

4. **Update the Documentation**: Update the documentation to reflect the new water edge creation algorithm, including:
   - `README.md`: Add information about the improved water edge creation
   - `database_schema.md`: Add information about the new tables
   - `worklog.md`: Document the implementation of the improved algorithm

5. **Add Tests**: Add tests to verify that the improved algorithm creates water edges correctly and ensures graph connectivity.

## Expected Benefits

The proposed solution should provide the following benefits:

1. **Improved Graph Connectivity**: The graph will be fully connected, allowing for paths between any two points in the terrain.

2. **More Realistic Water Crossings**: The water crossings will be more realistic, with different crossing types (bridges, ferries, fords) based on the water body characteristics.

3. **Better Performance**: The algorithm will be more efficient, especially for large datasets, by focusing on optimal crossing points rather than trying all possible combinations of terrain points.

4. **More Accurate Edge Costs**: The edge costs will better reflect the difficulty of crossing different types of water bodies, leading to more realistic path planning.

5. **Easier Maintenance**: The algorithm will be more modular and easier to maintain, with clear separation of concerns between water body classification, crossing point identification, terrain point connection, and graph connectivity verification.

## Conclusion

The current water edge creation algorithm in the EPSG:3857 pipeline has several limitations that result in poor graph connectivity. By implementing the proposed solution, we can significantly improve the quality of the terrain graph, making it more realistic and useful for path planning applications.
