-- 03_dissolve_water_buffers_improved.sql
-- Merge overlapping water buffers to simplify analysis with improved handling for large datasets
-- Uses proper coordinate transformations and appropriate simplification tolerances
-- No parameters required

-- Set work memory higher for complex spatial operations
SET work_mem = '256MB';

-- Enable parallel query execution
SET max_parallel_workers_per_gather = 4;

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
),
-- Apply different simplification strategies based on water feature characteristics
simplified_groups AS (
    SELECT
        crossability_group,
        min_crossability,
        max_crossability,
        buffer_rules_applied,
        crossability_rules_applied,
        avg_buffer_size_m,
        -- Transform to Web Mercator (EPSG:3857) for meter-based simplification
        -- Then simplify with appropriate tolerance and transform back to WGS84
        ST_Transform(
            ST_SimplifyPreserveTopology(
                ST_Transform(geom, 3857),
                -- Use 5 meters tolerance for simplification in Web Mercator
                5
            ),
            4326
        ) AS geom
    FROM crossability_groups
),
-- Add area constraint to filter out extremely large polygons
area_constrained AS (
    SELECT
        crossability_group,
        min_crossability,
        max_crossability,
        buffer_rules_applied,
        crossability_rules_applied,
        avg_buffer_size_m,
        geom,
        ST_Area(geom::geography) AS area_sqm
    FROM simplified_groups
),
-- Create Iowa bounding box for clipping
iowa_bounds AS (
    SELECT ST_Envelope(ST_Union(geom)) AS bbox
    FROM water_buf
),
-- Apply area constraint and clip to Iowa bounds
filtered_groups AS (
    SELECT
        a.crossability_group,
        a.min_crossability,
        a.max_crossability,
        a.buffer_rules_applied,
        a.crossability_rules_applied,
        a.avg_buffer_size_m,
        -- Clip to Iowa bounds to prevent features extending beyond state boundaries
        ST_Intersection(a.geom, b.bbox) AS geom
    FROM area_constrained a, iowa_bounds b
    -- Filter out extremely large polygons (> 5000 sq km)
    WHERE a.area_sqm < 5000000000
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
    geom
FROM filtered_groups;

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
