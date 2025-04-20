-- 03_dissolve_water_buffers_fixed.sql
-- Merge overlapping water buffers to simplify analysis with improved handling for large datasets
-- No parameters required

-- Create water_buf_dissolved table
DROP TABLE IF EXISTS water_buf_dissolved;
CREATE TABLE water_buf_dissolved AS
WITH 
-- First, identify clusters of spatially connected water buffers
connected_clusters AS (
    SELECT
        CASE
            WHEN crossability < 20 THEN 'low'
            WHEN crossability < 50 THEN 'medium'
            ELSE 'high'
        END AS crossability_group,
        -- Use ST_ClusterDBSCAN to identify connected clusters
        -- The eps parameter (2nd arg) is the max distance between features to be considered connected
        -- Setting it to 0 means features must touch or overlap
        -- The minpoints parameter (3rd arg) is the min number of points to form a cluster
        -- Setting it to 1 means even a single feature can form its own cluster
        ST_ClusterDBSCAN(geom, 0, 1) OVER (
            PARTITION BY 
                CASE
                    WHEN crossability < 20 THEN 'low'
                    WHEN crossability < 50 THEN 'medium'
                    ELSE 'high'
                END
        ) AS cluster_id,
        id,
        crossability,
        buffer_rule_applied,
        crossability_rule_applied,
        buffer_size_m,
        geom
    FROM water_buf
),
-- Group by both crossability range AND cluster ID to ensure only connected features are merged
crossability_groups AS (
    SELECT
        crossability_group,
        cluster_id,
        MIN(crossability) AS min_crossability,
        MAX(crossability) AS max_crossability,
        -- Aggregate decision tracking attributes
        string_agg(DISTINCT buffer_rule_applied, ', ' ORDER BY buffer_rule_applied) AS buffer_rules_applied,
        string_agg(DISTINCT crossability_rule_applied, ', ' ORDER BY crossability_rule_applied) AS crossability_rules_applied,
        -- Calculate average buffer size
        AVG(buffer_size_m) AS avg_buffer_size_m,
        -- Union only the geometries that are in the same cluster
        ST_Union(geom) AS geom
    FROM connected_clusters
    GROUP BY crossability_group, cluster_id
)
SELECT
    ROW_NUMBER() OVER () AS id,
    crossability_group,
    -- Use the minimum crossability value for the group
    -- This is conservative - assumes the worst case for crossing
    min_crossability AS crossability,
    buffer_rules_applied,
    crossability_rules_applied,
    avg_buffer_size_m,
    -- Simplify with a small tolerance to preserve the overall shape
    ST_SimplifyPreserveTopology(geom, 0.1) AS geom
FROM crossability_groups;

-- Create spatial index
CREATE INDEX ON water_buf_dissolved USING GIST(geom);

-- Log the results
SELECT 
    crossability_group, 
    COUNT(*) as count,
    MIN(crossability) as min_crossability,
    MAX(crossability) as max_crossability,
    buffer_rules_applied,
    crossability_rules_applied,
    avg_buffer_size_m,
    SUM(ST_Area(geom::geography)) / 1000000 as total_area_sq_km
FROM water_buf_dissolved 
GROUP BY crossability_group, buffer_rules_applied, crossability_rules_applied, avg_buffer_size_m
ORDER BY crossability_group;

-- Log cluster statistics
SELECT 
    crossability_group,
    COUNT(*) as cluster_count,
    MIN(ST_Area(geom::geography)) / 10000 as min_cluster_area_hectares,
    MAX(ST_Area(geom::geography)) / 10000 as max_cluster_area_hectares,
    AVG(ST_Area(geom::geography)) / 10000 as avg_cluster_area_hectares
FROM water_buf_dissolved
GROUP BY crossability_group
ORDER BY crossability_group;

-- Compare with original water buffers
SELECT 
    'original' AS source,
    COUNT(*) as count,
    MIN(crossability) as min_crossability,
    MAX(crossability) as max_crossability,
    SUM(ST_Area(geom::geography)) / 1000000 as total_area_sq_km
FROM water_buf
UNION ALL
SELECT 
    'dissolved' AS source,
    COUNT(*) as count,
    MIN(crossability) as min_crossability,
    MAX(crossability) as max_crossability,
    SUM(ST_Area(geom::geography)) / 1000000 as total_area_sq_km
FROM water_buf_dissolved;
