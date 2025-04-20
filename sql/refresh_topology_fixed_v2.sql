-- refresh_topology_fixed_v2.sql
-- Rebuild unified topology after buffers & grid updated
-- Ensures all geometries have the same SRID (4326)
BEGIN;
DROP TABLE IF EXISTS unified_edges CASCADE;
CREATE TABLE unified_edges AS
SELECT 
    id, 
    source, 
    target, 
    cost, 
    CASE 
        WHEN ST_SRID(geom) = 3857 THEN ST_Transform(geom, 4326)
        ELSE geom
    END AS geom 
FROM road_edges
UNION ALL
SELECT 
    id, 
    source, 
    target, 
    cost, 
    CASE 
        WHEN ST_SRID(geom) = 3857 THEN ST_Transform(geom, 4326)
        ELSE geom
    END AS geom 
FROM water_edges
UNION ALL
SELECT 
    id, 
    source, 
    target, 
    cost, 
    CASE 
        WHEN ST_SRID(geom) = 3857 THEN ST_Transform(geom, 4326)
        ELSE geom
    END AS geom 
FROM terrain_edges;

-- Create topology (assign source and target node IDs)
SELECT pgr_createTopology('unified_edges', 0.1, 'geom');
COMMIT;
