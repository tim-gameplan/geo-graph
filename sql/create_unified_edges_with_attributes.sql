-- Create unified_edges table with preserved OSM attributes
BEGIN;
DROP TABLE IF EXISTS unified_edges CASCADE;
CREATE TABLE unified_edges AS
SELECT 
    id, 
    source, 
    target, 
    cost, 
    geom,
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
    'road' AS edge_type
FROM road_edges
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
    'terrain' AS edge_type
FROM terrain_edges;

-- Create index on geometry
CREATE INDEX ON unified_edges USING GIST(geom);
COMMIT;
