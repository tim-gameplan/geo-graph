/*
 * Water Boundary Edges Creation
 * 
 * This script creates edges along water obstacle boundaries and connects them to the terrain grid.
 * It allows vehicles to navigate along the perimeter of water obstacles.
 */

-- Create water edges with EPSG:3857 coordinates
-- Parameters:
-- :storage_srid - SRID for storage (default: 3857)
-- :water_speed_factor - Speed factor for water edges (default: 0.2)
-- :boundary_segment_length - Length of boundary segments in meters (default: 100)
-- :max_connection_distance - Maximum distance for connecting terrain points to water boundaries (default: 300)

-- Create water edges table
DROP TABLE IF EXISTS water_edges CASCADE;
CREATE TABLE water_edges (
    id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    length NUMERIC,
    cost NUMERIC, -- Travel time cost
    water_obstacle_id INTEGER,
    edge_type TEXT, -- 'boundary' or 'connection'
    speed_factor NUMERIC,
    geom GEOMETRY(LINESTRING, :storage_srid)
);

-- Create water boundary points table to store points along water boundaries
DROP TABLE IF EXISTS water_boundary_points CASCADE;
CREATE TABLE water_boundary_points (
    id SERIAL PRIMARY KEY,
    water_obstacle_id INTEGER,
    geom GEOMETRY(POINT, :storage_srid)
);

-- Step 1: Extract boundary points directly from water obstacle polygons
-- This preserves the original structure and ordering of the polygon vertices
WITH 
boundary_points AS (
    -- Extract points from the exterior ring of each polygon in their original order
    SELECT 
        id AS water_obstacle_id,
        (ST_DumpPoints(ST_ExteriorRing(geom))).path[1] AS point_order,
        (ST_DumpPoints(ST_ExteriorRing(geom))).geom AS geom
    FROM 
        water_obstacles
)
INSERT INTO water_boundary_points (water_obstacle_id, geom)
SELECT 
    water_obstacle_id,
    geom
FROM 
    boundary_points;

-- Create spatial index on boundary points
CREATE INDEX water_boundary_points_geom_idx ON water_boundary_points USING GIST (geom);
CREATE INDEX water_boundary_points_water_obstacle_id_idx ON water_boundary_points (water_obstacle_id);

-- Step 2: Create edges between adjacent boundary points
INSERT INTO water_edges (source_id, target_id, length, cost, water_obstacle_id, edge_type, speed_factor, geom)
WITH ordered_boundary_points AS (
    -- Use the original point order from the polygon vertices
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
SELECT 
    bp1.id AS source_id,
    bp2.id AS target_id,
    ST_Length(ST_MakeLine(bp1.geom, bp2.geom)) AS length,
    ST_Length(ST_MakeLine(bp1.geom, bp2.geom)) / (5.0 * :water_speed_factor) AS cost, -- Slower speed along water boundaries
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
UNION ALL
-- Connect the last point back to the first point to close the loop
SELECT 
    bp_last.id AS source_id,
    bp_first.id AS target_id,
    ST_Length(ST_MakeLine(bp_last.geom, bp_first.geom)) AS length,
    ST_Length(ST_MakeLine(bp_last.geom, bp_first.geom)) / (5.0 * :water_speed_factor) AS cost,
    bp_last.water_obstacle_id,
    'boundary' AS edge_type,
    :water_speed_factor,
    ST_MakeLine(bp_last.geom, bp_first.geom) AS geom
FROM 
    (
        SELECT 
            id, water_obstacle_id, geom, point_order,
            MAX(point_order) OVER (PARTITION BY water_obstacle_id) AS max_order
        FROM 
            ordered_boundary_points
    ) bp_last
JOIN 
    ordered_boundary_points bp_first 
    ON bp_last.water_obstacle_id = bp_first.water_obstacle_id 
    AND bp_first.point_order = 1
WHERE 
    bp_last.point_order = bp_last.max_order;

-- Step 3: Connect terrain grid points to water boundary points
INSERT INTO water_edges (source_id, target_id, length, cost, water_obstacle_id, edge_type, speed_factor, geom)
WITH closest_connections AS (
    -- For each terrain point near water but outside water obstacles, find the closest water boundary point
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
SELECT 
    terrain_point_id AS source_id,
    boundary_point_id AS target_id,
    distance AS length,
    distance / 5.0 AS cost, -- Normal speed for connections
    water_obstacle_id,
    'connection' AS edge_type,
    1.0 AS speed_factor, -- Normal speed factor for connections
    geom
FROM 
    closest_connections;

-- Create spatial index
CREATE INDEX water_edges_geom_idx ON water_edges USING GIST (geom);
CREATE INDEX water_edges_source_id_idx ON water_edges (source_id);
CREATE INDEX water_edges_target_id_idx ON water_edges (target_id);
CREATE INDEX water_edges_edge_type_idx ON water_edges (edge_type);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' water boundary points' FROM water_boundary_points;
SELECT 'Created ' || COUNT(*) || ' water edges' FROM water_edges;
SELECT edge_type, COUNT(*) FROM water_edges GROUP BY edge_type ORDER BY edge_type;

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

-- Create spatial index
CREATE INDEX unified_edges_geom_idx ON unified_edges USING GIST (geom);
CREATE INDEX unified_edges_source_id_idx ON unified_edges (source_id);
CREATE INDEX unified_edges_target_id_idx ON unified_edges (target_id);
CREATE INDEX unified_edges_edge_type_idx ON unified_edges (edge_type);
CREATE INDEX unified_edges_is_water_idx ON unified_edges (is_water);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' unified edges' FROM unified_edges;
SELECT edge_type, COUNT(*) FROM unified_edges GROUP BY edge_type ORDER BY edge_type;

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
