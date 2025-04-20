-- Enhanced version of create_unified_edges_with_attributes.sql
-- Includes additional attributes for improved isochrone analysis

BEGIN;
DROP TABLE IF EXISTS unified_edges CASCADE;
CREATE TABLE unified_edges AS
SELECT 
    id, 
    source, 
    target, 
    cost, 
    geom,
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
    horse,
    'road' AS edge_type
FROM road_edges
UNION ALL
SELECT 
    id, 
    source, 
    target, 
    cost, 
    geom,
    name,
    NULL AS highway,
    NULL AS ref,
    NULL AS oneway,
    NULL AS surface,
    NULL AS bridge,
    NULL AS tunnel,
    NULL AS layer,
    NULL AS access,
    NULL AS service,
    NULL AS junction,
    NULL AS maxspeed,
    width,
    NULL AS lanes,
    NULL AS toll,
    NULL AS smoothness,
    NULL AS lit,
    NULL AS foot,
    NULL AS bicycle,
    NULL AS horse,
    'water' AS edge_type
FROM water_edges
UNION ALL
SELECT 
    id, 
    source, 
    target, 
    cost, 
    geom,
    NULL AS name,
    NULL AS highway,
    NULL AS ref,
    NULL AS oneway,
    NULL AS surface,
    NULL AS bridge,
    NULL AS tunnel,
    NULL AS layer,
    NULL AS access,
    NULL AS service,
    NULL AS junction,
    NULL AS maxspeed,
    NULL AS width,
    NULL AS lanes,
    NULL AS toll,
    NULL AS smoothness,
    NULL AS lit,
    NULL AS foot,
    NULL AS bicycle,
    NULL AS horse,
    'terrain' AS edge_type
FROM terrain_edges;

-- Create index on geometry
CREATE INDEX ON unified_edges USING GIST(geom);
COMMIT;
