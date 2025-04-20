-- Create unified_edges table without topology
BEGIN;
DROP TABLE IF EXISTS unified_edges CASCADE;
CREATE TABLE unified_edges AS
SELECT id, source, target, cost, geom FROM road_edges
UNION ALL
SELECT id, source, target, cost, geom FROM water_edges
UNION ALL
SELECT id, source, target, cost, geom FROM terrain_edges;

-- Create index on geometry
CREATE INDEX ON unified_edges USING GIST(geom);
COMMIT;
