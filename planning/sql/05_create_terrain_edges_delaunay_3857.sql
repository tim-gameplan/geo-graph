-- 05_create_terrain_edges_delaunay_3857.sql
-- Create terrain edges from Delaunay triangulation
-- Uses EPSG:3857 (Web Mercator) for all operations
-- Parameters:
-- Maximum distance in meters between connected grid cells is 300 meters

-- Create terrain_edges table
DROP TABLE IF EXISTS terrain_edges CASCADE;

-- Extract edges from the Delaunay triangulation
CREATE TABLE terrain_edges AS
WITH 
-- Extract the boundary of each triangle
triangle_boundaries AS (
    SELECT 
        id,
        ST_ExteriorRing(geom) AS boundary
    FROM (
        SELECT 
            ROW_NUMBER() OVER () AS id,
            geom
        FROM terrain_triangulation
    ) AS triangles
),
-- Extract individual edges from triangle boundaries
triangle_edges AS (
    SELECT 
        id,
        ST_MakeLine(
            ST_PointN(boundary, n),
            ST_PointN(boundary, CASE WHEN n = ST_NPoints(boundary) - 1 THEN 1 ELSE n + 1 END)
        ) AS geom
    FROM triangle_boundaries,
         generate_series(1, 3) AS n
),
-- Deduplicate edges (each edge appears in two triangles)
unique_edges AS (
    SELECT DISTINCT ON (
        LEAST(ST_X(ST_StartPoint(geom)), ST_X(ST_EndPoint(geom))),
        LEAST(ST_Y(ST_StartPoint(geom)), ST_Y(ST_EndPoint(geom))),
        GREATEST(ST_X(ST_StartPoint(geom)), ST_X(ST_EndPoint(geom))),
        GREATEST(ST_Y(ST_StartPoint(geom)), ST_Y(ST_EndPoint(geom)))
    )
        geom
    FROM triangle_edges
),
-- Filter out edges that cross water buffers
valid_edges AS (
    SELECT 
        geom,
        ST_Length(geom) AS length_m
    FROM unique_edges
    WHERE NOT EXISTS (
        SELECT 1 
        FROM water_buf_dissolved wb
        WHERE ST_Intersects(unique_edges.geom, wb.geom)
    )
),
-- Find the nearest terrain grid points to the start and end of each edge
edge_endpoints AS (
    SELECT 
        ve.geom,
        ve.length_m,
        (SELECT tg.id FROM terrain_grid tg ORDER BY ST_StartPoint(ve.geom) <-> tg.geom LIMIT 1) AS source_id,
        (SELECT tg.id FROM terrain_grid tg ORDER BY ST_EndPoint(ve.geom) <-> tg.geom LIMIT 1) AS target_id
    FROM valid_edges ve
)
-- Create the final terrain edges table
SELECT 
    ROW_NUMBER() OVER () AS id,
    source_id,
    target_id,
    NULL::bigint AS source, -- Will be populated by pgr_createTopology
    NULL::bigint AS target, -- Will be populated by pgr_createTopology
    -- Calculate cost based on length
    CASE 
        WHEN length_m <= 0 THEN 0.1 -- Avoid zero costs
        ELSE length_m / 100.0 -- Scale down for reasonable costs
    END AS cost,
    length_m,
    geom
FROM edge_endpoints
-- Ensure source_id and target_id are valid and different
WHERE 
    source_id IS NOT NULL AND 
    target_id IS NOT NULL AND 
    source_id != target_id;

-- Create spatial index
CREATE INDEX ON terrain_edges USING GIST(geom);

-- Add SRID metadata to the geometry column
ALTER TABLE terrain_edges 
ALTER COLUMN geom TYPE geometry(LineString, 3857) 
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
