-- Enhanced version of derive_road_and_water_fixed.sql with additional attributes
-- and improved cost calculation for isochrone analysis

-- roads: keep all highway=* with additional attributes
DROP TABLE IF EXISTS road_edges;
CREATE TABLE road_edges AS
SELECT
    osm_id AS id,
    way AS geom,
    -- Enhanced cost calculation based on road attributes
    CASE
        -- Default speeds based on highway type
        WHEN highway = 'motorway' THEN ST_Length(ST_Transform(way, 4326)::geography) / 30 -- ~108 km/h
        WHEN highway = 'trunk' THEN ST_Length(ST_Transform(way, 4326)::geography) / 25 -- ~90 km/h
        WHEN highway = 'primary' THEN ST_Length(ST_Transform(way, 4326)::geography) / 20 -- ~72 km/h
        WHEN highway = 'secondary' THEN ST_Length(ST_Transform(way, 4326)::geography) / 15 -- ~54 km/h
        WHEN highway = 'tertiary' THEN ST_Length(ST_Transform(way, 4326)::geography) / 12 -- ~43 km/h
        WHEN highway = 'residential' THEN ST_Length(ST_Transform(way, 4326)::geography) / 10 -- ~36 km/h
        WHEN highway = 'service' THEN ST_Length(ST_Transform(way, 4326)::geography) / 8 -- ~29 km/h
        WHEN highway = 'track' THEN ST_Length(ST_Transform(way, 4326)::geography) / 5 -- ~18 km/h
        WHEN highway = 'path' THEN ST_Length(ST_Transform(way, 4326)::geography) / 3 -- ~11 km/h
        -- Adjust for surface type
        WHEN surface IN ('unpaved', 'gravel', 'dirt', 'ground') THEN ST_Length(ST_Transform(way, 4326)::geography) / 8 -- ~29 km/h
        -- Default fallback
        ELSE ST_Length(ST_Transform(way, 4326)::geography) / 18 -- ~65 km/h
    END AS cost,
    -- Original attributes
    name,
    highway,
    ref,
    oneway,
    surface,
    bridge,
    tunnel,
    layer,
    access,
    service,
    junction,
    -- Additional attributes
    width,
    bicycle,
    foot,
    horse,
    toll
FROM planet_osm_line
WHERE highway IS NOT NULL;

CREATE INDEX ON road_edges USING GIST(geom);

-- water features: rivers, lakes, etc. with additional attributes
DROP TABLE IF EXISTS water_polys;
CREATE TABLE water_polys AS
-- Polygon water features
SELECT
    osm_id AS id,
    way AS geom,
    'polygon' AS feature_type,
    name,
    water,
    "natural",
    waterway,
    landuse,
    -- Additional attributes
    width,
    intermittent,
    CASE
        WHEN water IS NOT NULL THEN 'water'
        WHEN "natural" = 'water' THEN 'natural'
        WHEN landuse = 'reservoir' THEN 'reservoir'
        ELSE NULL
    END AS water_type
FROM planet_osm_polygon
WHERE water IS NOT NULL
   OR "natural" = 'water'
   OR landuse = 'reservoir'

UNION ALL

-- Linear water features (rivers, streams, canals, etc.)
SELECT
    osm_id AS id,
    way AS geom,
    'line' AS feature_type,
    name,
    NULL AS water,
    NULL AS "natural",
    waterway,
    NULL AS landuse,
    -- Additional attributes
    width,
    intermittent,
    waterway AS water_type
FROM planet_osm_line
WHERE waterway IN ('river', 'stream', 'canal', 'drain', 'ditch');

CREATE INDEX ON water_polys USING GIST(geom);
