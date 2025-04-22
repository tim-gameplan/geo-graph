-- 05_create_terrain_edges_3857.sql
-- Create terrain edges that don't cross water features
-- Uses EPSG:3857 (Web Mercator) for all operations
-- Parameters:
-- :connection_distance_m - Maximum distance in meters between connected grid cells

-- Create terrain_edges table
DROP TABLE IF EXISTS terrain_edges CASCADE;
CREATE TABLE terrain_edges AS
WITH 
-- Create points at the centroids of the terrain grid cells
points AS (
    SELECT 
        id,
        ST_Centroid(geom) AS geom,
        cost
    FROM terrain_grid
),
-- Create candidate edges between nearby points
-- Using ST_DWithin with EPSG:3857 geometries (distance in meters)
candidate_edges AS (
    SELECT 
        a.id AS source_id,
        b.id AS target_id,
        (a.cost + b.cost) / 2 AS cost,
        ST_MakeLine(a.geom, b.geom) AS geom
    FROM points a
    JOIN points b ON ST_DWithin(a.geom, b.geom, 300) 
    WHERE a.id < b.id -- Avoid duplicate edges
),
-- Filter out edges that cross water buffers
valid_edges AS (
    SELECT 
        source_id,
        target_id,
        cost,
        geom
    FROM candidate_edges ce
    WHERE NOT EXISTS (
        SELECT 1 
        FROM water_buf_dissolved wb
        WHERE ST_Intersects(ce.geom, wb.geom)
    )
)
SELECT 
    ROW_NUMBER() OVER () AS id,
    source_id,
    target_id,
    NULL::bigint AS source, -- Will be populated by pgr_createTopology
    NULL::bigint AS target, -- Will be populated by pgr_createTopology
    cost,
    ST_Length(geom) AS length_m, -- Direct length in meters (EPSG:3857)
    geom
FROM valid_edges;

-- Create spatial index
CREATE INDEX ON terrain_edges USING GIST(geom);

-- Add SRID metadata to the geometry column
ALTER TABLE terrain_edges 
ALTER COLUMN geom TYPE geometry(Geometry, 3857) 
USING ST_SetSRID(geom, 3857);

-- Log the results
SELECT 
    COUNT(*) as edge_count,
    MIN(length_m) as min_edge_length_m,
    MAX(length_m) as max_edge_length_m,
    AVG(length_m) as avg_edge_length_m,
    SUM(length_m) / 1000 as total_length_km
FROM terrain_edges;

-- Calculate connectivity statistics
WITH 
node_connections AS (
    SELECT 
        source_id AS node_id,
        COUNT(*) AS connection_count
    FROM terrain_edges
    GROUP BY source_id
    UNION ALL
    SELECT 
        target_id AS node_id,
        COUNT(*) AS connection_count
    FROM terrain_edges
    GROUP BY target_id
),
node_stats AS (
    SELECT 
        node_id,
        SUM(connection_count) AS total_connections
    FROM node_connections
    GROUP BY node_id
)
SELECT 
    MIN(total_connections) AS min_connections,
    MAX(total_connections) AS max_connections,
    AVG(total_connections) AS avg_connections,
    COUNT(*) AS total_nodes,
    COUNT(*) FILTER (WHERE total_connections = 1) AS nodes_with_1_connection,
    COUNT(*) FILTER (WHERE total_connections = 2) AS nodes_with_2_connections,
    COUNT(*) FILTER (WHERE total_connections = 3) AS nodes_with_3_connections,
    COUNT(*) FILTER (WHERE total_connections = 4) AS nodes_with_4_connections,
    COUNT(*) FILTER (WHERE total_connections = 5) AS nodes_with_5_connections,
    COUNT(*) FILTER (WHERE total_connections = 6) AS nodes_with_6_connections,
    COUNT(*) FILTER (WHERE total_connections > 6) AS nodes_with_more_than_6_connections
FROM node_stats;
