/*
 * Water Features Data Model
 * 
 * This script implements a typed table approach with views for water features:
 * - water_features_polygon: Contains polygon water features (lakes, reservoirs)
 * - water_features_line: Contains line water features (rivers, streams)
 * - water_features: View that unifies both tables for backward compatibility
 *
 * This design provides type safety, performance benefits, and a clearer data model
 * while maintaining compatibility with existing code through the view.
 */

-- Extract water features from OSM data with EPSG:3857 coordinates
-- Parameters:
-- :storage_srid - SRID for storage (default: 3857)
-- :export_srid - SRID for export (default: 4326)
-- :analysis_srid - SRID for analysis (default: 3857)

-- Drop existing tables and views
DROP TABLE IF EXISTS water_features CASCADE;
DROP TABLE IF EXISTS water_features_polygon CASCADE;
DROP TABLE IF EXISTS water_features_line CASCADE;

-- Create water features polygon table
CREATE TABLE water_features_polygon (
    id SERIAL PRIMARY KEY,
    osm_id BIGINT,
    name TEXT,
    type TEXT,
    geom GEOMETRY(POLYGON, :storage_srid)
);

-- Create water features line table
CREATE TABLE water_features_line (
    id SERIAL PRIMARY KEY,
    osm_id BIGINT,
    name TEXT,
    type TEXT,
    geom GEOMETRY(LINESTRING, :storage_srid)
);

-- Extract water polygons
INSERT INTO water_features_polygon (osm_id, name, type, geom)
SELECT 
    osm_id,
    name,
    'water',
    ST_Transform(way, :storage_srid)::GEOMETRY(POLYGON, :storage_srid)
FROM 
    planet_osm_polygon
WHERE 
    ("natural" = 'water' OR
    "waterway" IN ('riverbank', 'dock') OR
    "landuse" = 'reservoir' OR
    "water" IS NOT NULL)
    AND ST_GeometryType(way) = 'ST_Polygon';

-- Extract water multipolygons
INSERT INTO water_features_polygon (osm_id, name, type, geom)
SELECT 
    osm_id,
    name,
    'water',
    ST_Transform(way, :storage_srid)::GEOMETRY(POLYGON, :storage_srid)
FROM 
    planet_osm_polygon
WHERE 
    ("natural" = 'water' OR
    "waterway" IN ('riverbank', 'dock') OR
    "landuse" = 'reservoir' OR
    "water" IS NOT NULL)
    AND ST_GeometryType(way) = 'ST_MultiPolygon';

-- Extract water lines
INSERT INTO water_features_line (osm_id, name, type, geom)
SELECT 
    osm_id,
    name,
    waterway,
    ST_Transform(way, :storage_srid)
FROM 
    planet_osm_line
WHERE 
    waterway IN ('river', 'stream', 'canal', 'drain', 'ditch')
    AND ST_GeometryType(way) IN ('ST_LineString', 'ST_MultiLineString');

-- Create spatial indexes
CREATE INDEX water_features_polygon_geom_idx ON water_features_polygon USING GIST (geom);
CREATE INDEX water_features_line_geom_idx ON water_features_line USING GIST (geom);

-- Create a unified view for backward compatibility
CREATE VIEW water_features AS
SELECT 
    id, 
    osm_id, 
    name, 
    type, 
    'polygon' AS geometry_type, 
    geom::GEOMETRY(GEOMETRY, :storage_srid) AS geom 
FROM 
    water_features_polygon
UNION ALL
SELECT 
    id, 
    osm_id, 
    name, 
    type, 
    'line' AS geometry_type, 
    geom::GEOMETRY(GEOMETRY, :storage_srid) AS geom 
FROM 
    water_features_line;

-- Log the results
SELECT 'Extracted ' || COUNT(*) || ' polygon water features' FROM water_features_polygon;
SELECT 'Extracted ' || COUNT(*) || ' line water features' FROM water_features_line;
SELECT 'Extracted ' || COUNT(*) || ' total water features' FROM water_features;
