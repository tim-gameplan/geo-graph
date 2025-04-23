-- Extract water features from OSM data with EPSG:3857 coordinates
-- Parameters:
-- :storage_srid - SRID for storage (default: 3857)
-- :export_srid - SRID for export (default: 4326)
-- :analysis_srid - SRID for analysis (default: 3857)

-- Create water features table
DROP TABLE IF EXISTS water_features CASCADE;
CREATE TABLE water_features (
    id SERIAL PRIMARY KEY,
    osm_id BIGINT,
    name TEXT,
    type TEXT,
    geom GEOMETRY(GEOMETRY, :storage_srid)
);

-- Extract water polygons
INSERT INTO water_features (osm_id, name, type, geom)
SELECT 
    osm_id,
    name,
    'water',
    ST_Transform(way, :storage_srid)
FROM 
    planet_osm_polygon
WHERE 
    "natural" = 'water' OR
    "waterway" IN ('riverbank', 'dock') OR
    "landuse" = 'reservoir' OR
    "water" IS NOT NULL;

-- Extract water lines
INSERT INTO water_features (osm_id, name, type, geom)
SELECT 
    osm_id,
    name,
    waterway,
    ST_Transform(way, :storage_srid)
FROM 
    planet_osm_line
WHERE 
    waterway IN ('river', 'stream', 'canal', 'drain', 'ditch');

-- Create spatial index
CREATE INDEX water_features_geom_idx ON water_features USING GIST (geom);

-- Log the results
SELECT 'Extracted ' || COUNT(*) || ' water features' FROM water_features;
