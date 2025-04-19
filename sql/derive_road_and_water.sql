-- roads: keep all highway=*
DROP TABLE IF EXISTS road_edges;
CREATE TABLE road_edges AS
SELECT
    osm_id AS id,
    way   AS geom,
    ST_Length(way::geography) / 18 AS cost   -- rough 18 m/s ≈ 40 mph
FROM planet_osm_line
WHERE highway IS NOT NULL;

CREATE INDEX ON road_edges USING GIST(geom);

-- water polygons: rivers, lakes, etc.
DROP TABLE IF EXISTS water_polys;
CREATE TABLE water_polys AS
SELECT
    osm_id AS id,
    way    AS geom
FROM planet_osm_polygon
WHERE water IS NOT NULL
   OR "natural" = 'water'
   OR landuse   = 'reservoir';

CREATE INDEX ON water_polys USING GIST(geom);
