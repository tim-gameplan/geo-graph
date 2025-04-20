-- Enhanced version of derive_road_and_water_fixed.sql with additional attributes
-- and improved cost calculation for isochrone analysis

-- roads: keep all highway=* with additional attributes including maxspeed
DROP TABLE IF EXISTS road_edges;
CREATE TABLE road_edges AS
SELECT
    osm_id AS id,
    way AS geom,
    -- Enhanced cost calculation based on road attributes
    CASE
        -- Use maxspeed when available (convert km/h to m/s by multiplying by 0.277)
        WHEN maxspeed ~ '^[0-9]+$' THEN ST_Length(ST_Transform(way, 4326)::geography) / (maxspeed::numeric * 0.277)
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
    maxspeed,
    width,
    lanes,
    toll,
    smoothness,
    lit,
    foot,
    bicycle,
    horse
FROM planet_osm_line
WHERE highway IS NOT NULL;

CREATE INDEX ON road_edges USING GIST(geom);

-- water polygons: rivers, lakes, etc. with additional attributes
DROP TABLE IF EXISTS water_polys;
CREATE TABLE water_polys AS
SELECT
    osm_id AS id,
    way AS geom,
    name,
    water,
    "natural",
    waterway,
    landuse,
    -- Additional attributes
    width,
    depth,
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
   OR landuse = 'reservoir';

CREATE INDEX ON water_polys USING GIST(geom);
