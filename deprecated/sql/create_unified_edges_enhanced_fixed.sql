-- Enhanced version of create_unified_edges_with_attributes.sql
-- Includes additional attributes for improved isochrone analysis
-- Fixed to match the columns in derive_road_and_water_enhanced_fixed.sql

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
    width,
    bicycle,
    foot,
    horse,
    toll,
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
    width,
    NULL AS bicycle,
    NULL AS foot,
    NULL AS horse,
    NULL AS toll,
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
    NULL AS width,
    NULL AS bicycle,
    NULL AS foot,
    NULL AS horse,
    NULL AS toll,
    'terrain' AS edge_type
FROM terrain_edges;

-- Create index on geometry
CREATE INDEX ON unified_edges USING GIST(geom);
COMMIT;
