-- 01_extract_water_features_3857.sql
-- Extract water features from OSM data, including both polygons and lines
-- Uses EPSG:3857 (Web Mercator) for all geometries
-- Parameters:
-- :polygon_types - Array of polygon water feature types to extract
-- :line_types - Array of line water feature types to extract
-- :min_area_sqm - Minimum area for polygon water features
-- :include_intermittent - Whether to include intermittent water features

-- Create water_features table
DROP TABLE IF EXISTS water_features;
CREATE TABLE water_features AS
-- Water polygons
SELECT
    osm_id AS id,
    ST_Transform(way, 3857) AS geom,  -- Transform to Web Mercator
    'polygon' AS feature_type,
    name,
    water,
    "natural",
    waterway,
    landuse,
    width,
    intermittent,
    CASE
        WHEN water IS NOT NULL THEN 'water'
        WHEN "natural" = 'water' THEN 'natural'
        WHEN landuse = 'reservoir' THEN 'reservoir'
        ELSE NULL
    END AS water_type
FROM planet_osm_polygon
WHERE (water IS NOT NULL)
   OR ("natural" = 'water')
   OR (landuse = 'reservoir')

UNION ALL

-- Waterway lines (rivers, streams, canals, etc.)
SELECT
    osm_id AS id,
    ST_Transform(way, 3857) AS geom,  -- Transform to Web Mercator
    'line' AS feature_type,
    name,
    NULL AS water,
    NULL AS "natural",
    waterway,
    NULL AS landuse,
    width,
    intermittent,
    waterway AS water_type
FROM planet_osm_line
WHERE 
    -- Match explicit waterway types from config
    waterway = ANY(ARRAY[:line_types])
    -- Also include any named waterways even if not explicitly typed
    OR (waterway IS NOT NULL AND name IS NOT NULL)
    -- Include features with river or stream in their name
    OR (name IS NOT NULL AND (
        name ILIKE '%river%' OR 
        name ILIKE '%stream%' OR 
        name ILIKE '%creek%' OR 
        name ILIKE '%brook%' OR
        name ILIKE '%canal%'
    ));

-- Filter out small water bodies if specified
-- Note: Using ST_Area directly on EPSG:3857 geometries (in square meters)
DELETE FROM water_features 
WHERE feature_type = 'polygon' AND ST_Area(geom) < :min_area_sqm;

-- Filter out intermittent water features if not included
DELETE FROM water_features 
WHERE intermittent = 'yes' AND :include_intermittent = false;

-- Create spatial index
CREATE INDEX ON water_features USING GIST(geom);

-- Add SRID metadata to the geometry column
ALTER TABLE water_features 
ALTER COLUMN geom TYPE geometry(Geometry, 3857) 
USING ST_SetSRID(geom, 3857);

-- Log the results
SELECT feature_type, water_type, COUNT(*) 
FROM water_features 
GROUP BY feature_type, water_type 
ORDER BY feature_type, water_type;

-- Log area statistics for polygons (in square meters)
SELECT 
    water_type,
    COUNT(*) as count,
    MIN(ST_Area(geom)) as min_area_sqm,
    MAX(ST_Area(geom)) as max_area_sqm,
    AVG(ST_Area(geom)) as avg_area_sqm
FROM water_features
WHERE feature_type = 'polygon'
GROUP BY water_type
ORDER BY water_type;

-- Log length statistics for lines (in meters)
SELECT 
    water_type,
    COUNT(*) as count,
    MIN(ST_Length(geom)) as min_length_m,
    MAX(ST_Length(geom)) as max_length_m,
    AVG(ST_Length(geom)) as avg_length_m
FROM water_features
WHERE feature_type = 'line'
GROUP BY water_type
ORDER BY water_type;
