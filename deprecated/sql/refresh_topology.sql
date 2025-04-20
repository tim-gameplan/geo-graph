-- refresh_topology.sql
-- Rebuild unified topology after buffers & grid updated
BEGIN;
DROP TABLE IF EXISTS unified_edges CASCADE;
CREATE TABLE unified_edges AS
SELECT id, source, target, cost, geom FROM road_edges
UNION ALL
SELECT id, source, target, cost, geom FROM water_edges
UNION ALL
SELECT id, source, target, cost, geom FROM terrain_edges;
SELECT pgr_createTopology('unified_edges', 0.1, 'geom');
COMMIT;
