-- 01_extract_water_features.sql
-- Extract water features from OSM data, including both polygons and lines
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
    way AS geom,
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
    way AS geom,
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
WHERE waterway = ANY(ARRAY[:line_types]);

-- Filter out small water bodies if specified
DELETE FROM water_features 
WHERE feature_type = 'polygon' AND ST_Area(ST_Transform(geom, 4326)::geography) < :min_area_sqm;

-- Filter out intermittent water features if not included
DELETE FROM water_features 
WHERE intermittent = 'yes' AND :include_intermittent = false;

-- Create spatial index
CREATE INDEX ON water_features USING GIST(geom);

-- Log the results
SELECT feature_type, water_type, COUNT(*) 
FROM water_features 
GROUP BY feature_type, water_type 
ORDER BY feature_type, water_type;
