-- 06_create_water_edges_comparison.sql
-- Create water edges from both original and dissolved buffers without simplification
-- No parameters required

-- Create water_edges_original from high-resolution buffers
DROP TABLE IF EXISTS water_edges_original CASCADE;
CREATE TABLE water_edges_original AS
SELECT 
    ROW_NUMBER() OVER () AS id,
    NULL::bigint AS source,
    NULL::bigint AS target,
    CASE
        WHEN crossability = 0 THEN 9999.0
        ELSE (100.0 / crossability) * 10.0
    END AS cost,
    crossability,
    buffer_rule_applied AS buffer_rules_applied,
    crossability_rule_applied AS crossability_rules_applied,
    buffer_size_m AS avg_buffer_size_m,
    'water_edge_original' AS edge_type,
    ST_Length(boundary::geography) AS length_m,
    boundary AS geom
FROM (
    SELECT 
        id,
        crossability,
        buffer_rule_applied,
        crossability_rule_applied,
        buffer_size_m,
        (ST_Dump(ST_Boundary(geom))).geom AS boundary
    FROM water_buf
) AS boundaries
WHERE ST_Length(boundary) > 0;

-- Create spatial index
CREATE INDEX ON water_edges_original USING GIST(geom);

-- Create water_edges_dissolved from dissolved buffers
DROP TABLE IF EXISTS water_edges_dissolved CASCADE;
CREATE TABLE water_edges_dissolved AS
SELECT 
    ROW_NUMBER() OVER () AS id,
    NULL::bigint AS source,
    NULL::bigint AS target,
    CASE
        WHEN crossability = 0 THEN 9999.0
        ELSE (100.0 / crossability) * 10.0
    END AS cost,
    crossability,
    buffer_rules_applied,
    crossability_rules_applied,
    avg_buffer_size_m,
    'water_edge_dissolved' AS edge_type,
    ST_Length(boundary::geography) AS length_m,
    boundary AS geom
FROM (
    SELECT 
        id,
        crossability,
        crossability_group,
        buffer_rules_applied,
        crossability_rules_applied,
        avg_buffer_size_m,
        (ST_Dump(ST_Boundary(geom))).geom AS boundary
    FROM water_buf_dissolved
) AS boundaries
WHERE ST_Length(boundary) > 0;

-- Create spatial index
CREATE INDEX ON water_edges_dissolved USING GIST(geom);

-- Log the results for original edges
SELECT 
    'original' AS source,
    COUNT(*) as edge_count,
    MIN(crossability) as min_crossability,
    MAX(crossability) as max_crossability,
    MIN(cost) as min_cost,
    MAX(cost) as max_cost,
    AVG(cost) as avg_cost,
    MIN(length_m) as min_edge_length_m,
    MAX(length_m) as max_edge_length_m,
    AVG(length_m) as avg_edge_length_m,
    SUM(length_m) / 1000 as total_length_km
FROM water_edges_original;

-- Log the results for dissolved edges
SELECT 
    'dissolved' AS source,
    COUNT(*) as edge_count,
    MIN(crossability) as min_crossability,
    MAX(crossability) as max_crossability,
    MIN(cost) as min_cost,
    MAX(cost) as max_cost,
    AVG(cost) as avg_cost,
    MIN(length_m) as min_edge_length_m,
    MAX(length_m) as max_edge_length_m,
    AVG(length_m) as avg_edge_length_m,
    SUM(length_m) / 1000 as total_length_km
FROM water_edges_dissolved;

-- Compare edge counts
SELECT 
    'water_edges_original' AS source,
    COUNT(*) as edge_count,
    SUM(length_m) / 1000 as total_length_km,
    AVG(cost) as avg_cost
FROM water_edges_original
UNION ALL
SELECT 
    'water_edges_dissolved' AS source,
    COUNT(*) as edge_count,
    SUM(length_m) / 1000 as total_length_km,
    AVG(cost) as avg_cost
FROM water_edges_dissolved;
