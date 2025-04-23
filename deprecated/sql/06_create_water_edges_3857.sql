-- 06_create_water_edges_3857.sql
-- Create water edges with crossability-based costs
-- Uses EPSG:3857 (Web Mercator) for all operations
-- Parameters:
-- :simplify_tolerance_m - Simplification tolerance for boundaries
-- :boundary_point_spacing - Spacing for segmentizing boundaries

-- Create water_edges table
DROP TABLE IF EXISTS water_edges CASCADE;
CREATE TABLE water_edges AS
WITH 
-- Extract the boundaries of water buffers
water_boundaries AS (
    SELECT 
        id,
        crossability,
        crossability_group,
        buffer_rules_applied,
        crossability_rules_applied,
        avg_buffer_size_m,
        -- Convert MultiPolygon boundaries to LineString
        (ST_Dump(ST_Boundary(geom))).geom AS geom
    FROM water_buf_dissolved
),
-- Simplify the boundaries to reduce the number of vertices
-- Using a tolerance in meters (EPSG:3857)
simplified_boundaries AS (
    SELECT 
        id,
        crossability,
        crossability_group,
        buffer_rules_applied,
        crossability_rules_applied,
        avg_buffer_size_m,
        -- Simplify with a tolerance that preserves the overall shape
        ST_SimplifyPreserveTopology(geom, :simplify_tolerance_m) AS geom
    FROM water_boundaries
),
-- Split long boundaries into smaller segments
segmented_boundaries AS (
    SELECT 
        id,
        crossability,
        crossability_group,
        buffer_rules_applied,
        crossability_rules_applied,
        avg_buffer_size_m,
        -- Generate points along the boundary at regular intervals
        (ST_Dump(ST_Segmentize(geom, :boundary_point_spacing))).geom AS geom
    FROM simplified_boundaries
)
SELECT 
    ROW_NUMBER() OVER () AS id,
    NULL::bigint AS source, -- Will be populated by pgr_createTopology
    NULL::bigint AS target, -- Will be populated by pgr_createTopology
    -- Convert crossability (0-100) to cost (higher = harder to cross)
    -- Use a non-linear scale to emphasize the difference between low and high crossability
    CASE
        WHEN crossability = 0 THEN 9999.0 -- Effectively impassable
        ELSE (100.0 / crossability) * 10.0 -- Inverse relationship
    END AS cost,
    crossability,
    crossability_group,
    buffer_rules_applied,
    crossability_rules_applied,
    avg_buffer_size_m,
    'water_edge' AS edge_type,
    ST_Length(geom) AS length_m, -- Direct length in meters (EPSG:3857)
    geom
FROM segmented_boundaries
WHERE ST_Length(geom) > 0; -- Filter out empty geometries

-- Create spatial index
CREATE INDEX ON water_edges USING GIST(geom);

-- Add SRID metadata to the geometry column
ALTER TABLE water_edges 
ALTER COLUMN geom TYPE geometry(Geometry, 3857) 
USING ST_SetSRID(geom, 3857);

-- Log the results
SELECT 
    crossability_group,
    COUNT(*) as edge_count,
    MIN(crossability) as min_crossability,
    MAX(crossability) as max_crossability,
    AVG(crossability) as avg_crossability,
    MIN(cost) as min_cost,
    MAX(cost) as max_cost,
    AVG(cost) as avg_cost,
    buffer_rules_applied,
    crossability_rules_applied,
    MIN(length_m) as min_edge_length_m,
    MAX(length_m) as max_edge_length_m,
    AVG(length_m) as avg_edge_length_m,
    SUM(length_m) / 1000 as total_length_km
FROM water_edges
GROUP BY crossability_group, buffer_rules_applied, crossability_rules_applied
ORDER BY crossability_group;

-- Compare with terrain edges
SELECT 
    'water_edges' AS source,
    COUNT(*) as edge_count,
    SUM(length_m) / 1000 as total_length_km,
    AVG(cost) as avg_cost
FROM water_edges
UNION ALL
SELECT 
    'terrain_edges' AS source,
    COUNT(*) as edge_count,
    SUM(length_m) / 1000 as total_length_km,
    AVG(cost) as avg_cost
FROM terrain_edges;
