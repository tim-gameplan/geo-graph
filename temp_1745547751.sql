/*
 * Improved Water Edges Creation
 * 
 * This script creates edges that cross water obstacles using an improved algorithm
 * that classifies water bodies, identifies optimal crossing points, connects terrain points,
 * verifies graph connectivity, and refines edge costs.
 */

-- Create water edges with EPSG:3857 coordinates
-- Parameters:
-- 3857 - SRID for storage (default: 3857)
-- 0.2 - Speed factor for water edges (default: 0.2)
-- True - Whether to enable graph connectivity verification (default: true)
-- 2000 - Maximum distance for water crossings (default: 2000)

-- Set work_mem to a higher value for better performance
SET work_mem = '256MB';

-- Create water edges table
DROP TABLE IF EXISTS water_edges CASCADE;
CREATE TABLE water_edges (
    id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    length NUMERIC,
    cost NUMERIC, -- Travel time cost
    water_obstacle_id INTEGER,
    crossing_type TEXT, -- 'bridge', 'ferry', 'ford'
    speed_factor NUMERIC,
    geom GEOMETRY(LINESTRING, 3857)
);

-- Step 1: Water Body Classification
-- Create a water body classification table
DROP TABLE IF EXISTS water_body_classification CASCADE;
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
    crossing_strategy TEXT -- 'bridge', 'ferry', 'ford'
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
    -- Calculate max width using ST_MaximumInscribedCircle if available, otherwise approximate
    CASE 
        WHEN ST_Area(wo.geom) > 0 THEN 
            COALESCE(
                (SELECT radius * 2 FROM ST_MaximumInscribedCircle(wo.geom) LIMIT 1),
                SQRT(ST_Area(wo.geom) / PI())
            )
        ELSE 0
    END AS width_max,
    -- Approximate length for linear features
    CASE
        WHEN ST_Perimeter(wo.geom) / GREATEST(SQRT(ST_Area(wo.geom)), 1) > 10 
        THEN ST_Length(ST_Simplify(wo.geom, 10))
        ELSE NULL
    END AS length,
    CASE 
        WHEN ST_Area(wo.geom) > 0 THEN 
            ST_Perimeter(wo.geom)^2 / (4 * PI() * ST_Area(wo.geom))
        ELSE 1
    END AS compactness,
    CASE
        WHEN ST_Area(wo.geom) > 1000000 THEN 'ferry'
        WHEN ST_Area(wo.geom) > 10000 THEN 'bridge'
        ELSE 'ford'
    END AS crossing_strategy
FROM 
    water_obstacles wo;

-- Create spatial index
CREATE INDEX water_body_classification_water_obstacle_id_idx ON water_body_classification (water_obstacle_id);

-- Log the results
SELECT 'Classified ' || COUNT(*) || ' water bodies' FROM water_body_classification;
SELECT type, crossing_strategy, COUNT(*) FROM water_body_classification GROUP BY type, crossing_strategy ORDER BY type, crossing_strategy;

-- Step 2: Optimal Crossing Point Identification
-- Create a table for optimal crossing points
DROP TABLE IF EXISTS optimal_crossing_points CASCADE;
CREATE TABLE optimal_crossing_points (
    id SERIAL PRIMARY KEY,
    water_obstacle_id INTEGER REFERENCES water_obstacles(id),
    crossing_type TEXT, -- 'bridge', 'ferry', 'ford'
    geom GEOMETRY(LINESTRING, 3857)
);

-- For rivers: Find narrow points and create perpendicular crossings
-- This is a simplified approach that creates crossings at regular intervals along the river
INSERT INTO optimal_crossing_points (water_obstacle_id, crossing_type, geom)
WITH river_boundaries AS (
    SELECT 
        wbc.water_obstacle_id,
        wbc.crossing_strategy,
        ST_Boundary(wo.geom) AS boundary,
        ST_Centroid(wo.geom) AS centroid,
        wbc.length
    FROM 
        water_body_classification wbc
    JOIN 
        water_obstacles wo ON wbc.water_obstacle_id = wo.id
    WHERE 
        wbc.type = 'river'
),
river_points AS (
    SELECT 
        rb.water_obstacle_id,
        rb.crossing_strategy,
        ST_PointN(rb.boundary, generate_series(1, ST_NPoints(rb.boundary), 
            GREATEST(ST_NPoints(rb.boundary) / 10, 1))) AS point,
        rb.centroid
    FROM 
        river_boundaries rb
)
SELECT 
    rp1.water_obstacle_id,
    rp1.crossing_strategy,
    ST_MakeLine(rp1.point, 
        (SELECT rp2.point 
         FROM river_points rp2 
         WHERE rp2.water_obstacle_id = rp1.water_obstacle_id 
         ORDER BY ST_Distance(rp1.point, rp2.point) DESC 
         LIMIT 1)) AS geom
FROM 
    river_points rp1
WHERE 
    ST_Distance(rp1.point, rp1.centroid) < 2000 / 2;

-- For lakes: Create crossings at narrow points or use ferry routes
-- This is a simplified approach that creates crossings across the lake
INSERT INTO optimal_crossing_points (water_obstacle_id, crossing_type, geom)
WITH lake_boundaries AS (
    SELECT 
        wbc.water_obstacle_id,
        wbc.crossing_strategy,
        ST_Boundary(wo.geom) AS boundary,
        ST_Centroid(wo.geom) AS centroid,
        wbc.width_max
    FROM 
        water_body_classification wbc
    JOIN 
        water_obstacles wo ON wbc.water_obstacle_id = wo.id
    WHERE 
        wbc.type = 'lake'
),
lake_points AS (
    SELECT 
        lb.water_obstacle_id,
        lb.crossing_strategy,
        ST_PointN(lb.boundary, generate_series(1, ST_NPoints(lb.boundary), 
            GREATEST(ST_NPoints(lb.boundary) / 8, 1))) AS point,
        lb.centroid,
        lb.width_max
    FROM 
        lake_boundaries lb
)
SELECT 
    lp1.water_obstacle_id,
    lp1.crossing_strategy,
    ST_MakeLine(lp1.point, lp1.centroid) AS geom
FROM 
    lake_points lp1
WHERE 
    ST_Distance(lp1.point, lp1.centroid) < 2000;

-- For streams: Create simple crossings
INSERT INTO optimal_crossing_points (water_obstacle_id, crossing_type, geom)
WITH stream_boundaries AS (
    SELECT 
        wbc.water_obstacle_id,
        wbc.crossing_strategy,
        ST_Boundary(wo.geom) AS boundary,
        ST_Centroid(wo.geom) AS centroid
    FROM 
        water_body_classification wbc
    JOIN 
        water_obstacles wo ON wbc.water_obstacle_id = wo.id
    WHERE 
        wbc.type = 'stream'
),
stream_points AS (
    SELECT 
        sb.water_obstacle_id,
        sb.crossing_strategy,
        ST_PointN(sb.boundary, generate_series(1, ST_NPoints(sb.boundary), 
            GREATEST(ST_NPoints(sb.boundary) / 4, 1))) AS point,
        sb.centroid
    FROM 
        stream_boundaries sb
)
SELECT 
    sp1.water_obstacle_id,
    sp1.crossing_strategy,
    ST_MakeLine(sp1.point, 
        (SELECT sp2.point 
         FROM stream_points sp2 
         WHERE sp2.water_obstacle_id = sp1.water_obstacle_id 
         ORDER BY ST_Distance(sp1.point, sp2.point) DESC 
         LIMIT 1)) AS geom
FROM 
    stream_points sp1;

-- Create spatial index
CREATE INDEX optimal_crossing_points_geom_idx ON optimal_crossing_points USING GIST (geom);
CREATE INDEX optimal_crossing_points_water_obstacle_id_idx ON optimal_crossing_points (water_obstacle_id);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' optimal crossing points' FROM optimal_crossing_points;
SELECT crossing_type, COUNT(*) FROM optimal_crossing_points GROUP BY crossing_type ORDER BY crossing_type;

-- Step 3: Terrain Point Connection
-- Create water edges using optimal crossing points
INSERT INTO water_edges (source_id, target_id, length, cost, water_obstacle_id, crossing_type, speed_factor, geom)
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
    ctp.crossing_type,
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
    crossing_terrain_points ctp
WHERE
    ctp.source_id IS NOT NULL AND
    ctp.target_id IS NOT NULL AND
    ctp.source_id != ctp.target_id;

-- Create spatial index
CREATE INDEX water_edges_geom_idx ON water_edges USING GIST (geom);
CREATE INDEX water_edges_source_id_idx ON water_edges (source_id);
CREATE INDEX water_edges_target_id_idx ON water_edges (target_id);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' water edges' FROM water_edges;
SELECT crossing_type, COUNT(*) FROM water_edges GROUP BY crossing_type ORDER BY crossing_type;

-- Step 4: Graph Connectivity Verification
-- Create a unified edges table for connectivity checking
DROP TABLE IF EXISTS unified_edges CASCADE;
CREATE TABLE unified_edges (
    id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    length NUMERIC,
    cost NUMERIC, -- Travel time cost
    edge_type TEXT,
    speed_factor NUMERIC,
    geom GEOMETRY(LINESTRING, 3857)
);

-- Insert terrain edges
INSERT INTO unified_edges (source_id, target_id, length, cost, edge_type, speed_factor, geom)
SELECT 
    source_id,
    target_id,
    length,
    cost,
    'terrain',
    1.0,
    geom
FROM 
    terrain_edges;

-- Insert water edges
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
    water_edges;

-- Create spatial index
CREATE INDEX unified_edges_geom_idx ON unified_edges USING GIST (geom);
CREATE INDEX unified_edges_source_id_idx ON unified_edges (source_id);
CREATE INDEX unified_edges_target_id_idx ON unified_edges (target_id);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' unified edges' FROM unified_edges;
SELECT edge_type, COUNT(*) FROM unified_edges GROUP BY edge_type ORDER BY edge_type;

-- Check graph connectivity if enabled
DO $$
DECLARE
    component_count INTEGER;
    largest_component_size INTEGER;
    total_nodes INTEGER;
    disconnected_nodes INTEGER;
    source_node INTEGER;
    target_node INTEGER;
    min_distance NUMERIC;
    current_distance NUMERIC;
    components_connected INTEGER := 0;
BEGIN
    -- Only run if connectivity check is enabled
    IF True THEN
        -- Create a temporary table for connected components
        CREATE TEMP TABLE connected_components (
            component_id INTEGER,
            node_id INTEGER
        );
        
        -- Find connected components using a recursive CTE
        WITH RECURSIVE
        nodes AS (
            SELECT id FROM terrain_grid_points
        ),
        edges AS (
            SELECT source_id, target_id FROM unified_edges
        ),
        component(node_id, component_id) AS (
            SELECT id, id FROM nodes
            UNION ALL
            SELECT e.target_id, c.component_id
            FROM component c
            JOIN edges e ON c.node_id = e.source_id
            WHERE NOT EXISTS (
                SELECT 1 FROM component c2
                WHERE c2.node_id = e.target_id
            )
            UNION ALL
            SELECT e.source_id, c.component_id
            FROM component c
            JOIN edges e ON c.node_id = e.target_id
            WHERE NOT EXISTS (
                SELECT 1 FROM component c2
                WHERE c2.node_id = e.source_id
            )
        )
        INSERT INTO connected_components
        SELECT MIN(component_id), node_id
        FROM component
        GROUP BY node_id;
        
        -- Count the number of connected components
        SELECT COUNT(DISTINCT component_id) INTO component_count
        FROM connected_components;
        
        -- Get the size of the largest component
        SELECT COUNT(*) INTO largest_component_size
        FROM connected_components
        WHERE component_id = (
            SELECT component_id
            FROM connected_components
            GROUP BY component_id
            ORDER BY COUNT(*) DESC
            LIMIT 1
        );
        
        -- Get the total number of nodes
        SELECT COUNT(*) INTO total_nodes
        FROM terrain_grid_points;
        
        -- Calculate the number of disconnected nodes
        disconnected_nodes := total_nodes - largest_component_size;
        
        -- Log the connectivity information
        RAISE NOTICE 'Graph has % connected components', component_count;
        RAISE NOTICE 'Largest component has % nodes (%.2f%% of total)', 
            largest_component_size, 
            (largest_component_size::FLOAT / total_nodes::FLOAT) * 100;
        RAISE NOTICE '% nodes (%.2f%%) are disconnected from the main component', 
            disconnected_nodes, 
            (disconnected_nodes::FLOAT / total_nodes::FLOAT) * 100;
        
        -- If there are multiple components, connect them
        IF component_count > 1 THEN
            RAISE NOTICE 'Connecting disconnected components...';
            
            -- Get the largest component ID
            WITH component_sizes AS (
                SELECT component_id, COUNT(*) AS size
                FROM connected_components
                GROUP BY component_id
                ORDER BY COUNT(*) DESC
            )
            SELECT component_id INTO source_node
            FROM component_sizes
            LIMIT 1;
            
            -- For each smaller component, connect it to the main component
            FOR target_node IN
                SELECT DISTINCT component_id
                FROM connected_components
                WHERE component_id != source_node
            LOOP
                -- Find the closest pair of nodes between the two components
                min_distance := 'Infinity'::NUMERIC;
                source_node := NULL;
                target_node := NULL;
                
                -- Find the closest pair of nodes
                SELECT 
                    cc1.node_id, 
                    cc2.node_id, 
                    ST_Distance(tgp1.geom, tgp2.geom)
                INTO source_node, target_node, min_distance
                FROM connected_components cc1
                CROSS JOIN connected_components cc2
                JOIN terrain_grid_points tgp1 ON cc1.node_id = tgp1.id
                JOIN terrain_grid_points tgp2 ON cc2.node_id = tgp2.id
                WHERE cc1.component_id = (
                    SELECT component_id
                    FROM connected_components
                    GROUP BY component_id
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                )
                AND cc2.component_id = target_node
                ORDER BY ST_Distance(tgp1.geom, tgp2.geom)
                LIMIT 1;
                
                -- Add an edge between the closest pair of nodes
                IF source_node IS NOT NULL AND target_node IS NOT NULL THEN
                    INSERT INTO water_edges (
                        source_id, target_id, length, cost, water_obstacle_id, crossing_type, speed_factor, geom
                    )
                    SELECT 
                        source_node,
                        target_node,
                        min_distance AS length,
                        min_distance / (5.0 * 0.2) AS cost, -- Slow crossing
                        NULL AS water_obstacle_id, -- No specific water obstacle
                        'connectivity' AS crossing_type, -- Special type for connectivity edges
                        0.2 AS speed_factor, -- Slow speed factor
                        ST_MakeLine(
                            (SELECT geom FROM terrain_grid_points WHERE id = source_node),
                            (SELECT geom FROM terrain_grid_points WHERE id = target_node)
                        ) AS geom;
                    
                    components_connected := components_connected + 1;
                END IF;
            END LOOP;
            
            -- Update the unified edges table with the new connectivity edges
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
                crossing_type = 'connectivity';
            
            RAISE NOTICE 'Connected % components', components_connected;
        END IF;
        
        -- Clean up
        DROP TABLE connected_components;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Step 5: Edge Cost Refinement
-- Update water edge costs based on crossing type and environmental conditions
UPDATE water_edges
SET cost = 
    CASE
        WHEN crossing_type = 'ferry' THEN length / (5.0 * 0.2) -- Slower for ferries
        WHEN crossing_type = 'bridge' THEN length / (5.0 * 0.8) -- Slightly slower for bridges
        WHEN crossing_type = 'connectivity' THEN length / (5.0 * 0.2) -- Slow for connectivity edges
        ELSE length / (5.0 * 0.5) -- Medium speed for fords
    END,
    speed_factor = 
    CASE
        WHEN crossing_type = 'ferry' THEN 0.2
        WHEN crossing_type = 'bridge' THEN 0.8
        WHEN crossing_type = 'connectivity' THEN 0.2
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

-- Log the final results
SELECT 'Final water edges count: ' || COUNT(*) FROM water_edges;
SELECT 'Final unified edges count: ' || COUNT(*) FROM unified_edges;
SELECT 'Water edges by crossing type:';
SELECT crossing_type, COUNT(*), AVG(cost) AS avg_cost, AVG(speed_factor) AS avg_speed_factor
FROM water_edges
GROUP BY crossing_type
ORDER BY crossing_type;

-- Reset work_mem to default value
RESET work_mem;
