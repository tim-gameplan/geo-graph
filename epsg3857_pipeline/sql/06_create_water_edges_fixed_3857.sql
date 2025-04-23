/*
 * Water Edges Creation (Fixed Version)
 * 
 * This script creates edges that cross water obstacles with an increased distance threshold
 * and a relaxed intersection requirement to ensure water edges are created properly.
 */

-- Create water edges with EPSG:3857 coordinates
-- Parameters:
-- :storage_srid - SRID for storage (default: 3857)
-- :water_speed_factor - Speed factor for water edges (default: 0.2)
-- :max_edge_distance - Maximum distance for water edges (default: 2000)

-- Create water edges table
DROP TABLE IF EXISTS water_edges CASCADE;
CREATE TABLE water_edges (
    id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    length NUMERIC,
    cost NUMERIC, -- Travel time cost
    water_obstacle_id INTEGER,
    speed_factor NUMERIC,
    geom GEOMETRY(LINESTRING, :storage_srid)
);

-- Find terrain grid points near water obstacles
WITH water_boundary_points AS (
    -- Get points along the boundary of water obstacles
    SELECT 
        wo.id AS water_obstacle_id,
        (ST_DumpPoints(ST_Boundary(wo.geom))).geom AS geom
    FROM 
        water_obstacles wo
),
nearest_terrain_points AS (
    -- For each water boundary point, find the nearest terrain grid point
    SELECT DISTINCT ON (wbp.geom)
        wbp.water_obstacle_id,
        wbp.geom AS water_point,
        tg.id AS terrain_point_id,
        tg.geom AS terrain_point,
        ST_Distance(wbp.geom, tg.geom) AS distance
    FROM 
        water_boundary_points wbp
    CROSS JOIN 
        terrain_grid_points tg
    ORDER BY 
        wbp.geom, ST_Distance(wbp.geom, tg.geom)
)
-- Create water edges between terrain grid points that are near water obstacles
INSERT INTO water_edges (source_id, target_id, length, cost, water_obstacle_id, speed_factor, geom)
SELECT 
    ntp1.terrain_point_id AS source_id,
    ntp2.terrain_point_id AS target_id,
    ST_Length(ST_MakeLine(ntp1.terrain_point, ntp2.terrain_point)) AS length,
    ST_Length(ST_MakeLine(ntp1.terrain_point, ntp2.terrain_point)) / (5.0 * :water_speed_factor) AS cost, -- Slower speed in water
    ntp1.water_obstacle_id,
    :water_speed_factor,
    ST_MakeLine(ntp1.terrain_point, ntp2.terrain_point) AS geom
FROM 
    nearest_terrain_points ntp1
JOIN 
    nearest_terrain_points ntp2 ON ntp1.water_obstacle_id = ntp2.water_obstacle_id
WHERE 
    ntp1.terrain_point_id < ntp2.terrain_point_id AND
    ST_DWithin(ntp1.terrain_point, ntp2.terrain_point, :max_edge_distance) AND
    -- Ensure the edge is near the water obstacle (relaxed from strict intersection)
    ST_DWithin(
        ST_MakeLine(ntp1.terrain_point, ntp2.terrain_point),
        (SELECT geom FROM water_obstacles WHERE id = ntp1.water_obstacle_id),
        100 -- Allow edges that are within 100 meters of the water obstacle
    );

-- Create spatial index
CREATE INDEX water_edges_geom_idx ON water_edges USING GIST (geom);
CREATE INDEX water_edges_source_id_idx ON water_edges (source_id);
CREATE INDEX water_edges_target_id_idx ON water_edges (target_id);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' water edges' FROM water_edges;

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
    geom GEOMETRY(LINESTRING, :storage_srid)
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
