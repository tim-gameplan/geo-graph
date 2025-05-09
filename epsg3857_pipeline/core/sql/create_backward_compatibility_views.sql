/*
 * create_backward_compatibility_views.sql
 *
 * This script creates views with the old table names that point to the new tables,
 * ensuring that existing code continues to work with the new naming convention.
 */

-- Drop existing views if they exist
DROP VIEW IF EXISTS water_features CASCADE;
DROP VIEW IF EXISTS water_features_polygon CASCADE;
DROP VIEW IF EXISTS water_features_line CASCADE;
DROP VIEW IF EXISTS water_buffers CASCADE;
DROP VIEW IF EXISTS dissolved_water_buffers CASCADE;
DROP VIEW IF EXISTS water_obstacles CASCADE;
DROP VIEW IF EXISTS complete_hex_grid CASCADE;
DROP VIEW IF EXISTS classified_hex_grid CASCADE;
DROP VIEW IF EXISTS water_hexagons_with_land CASCADE;
DROP VIEW IF EXISTS water_hex_land_portions CASCADE;
DROP VIEW IF EXISTS terrain_grid CASCADE;
DROP VIEW IF EXISTS terrain_grid_points CASCADE;
DROP VIEW IF EXISTS terrain_edges CASCADE;
DROP VIEW IF EXISTS boundary_nodes CASCADE;
DROP VIEW IF EXISTS water_boundary_nodes CASCADE;
DROP VIEW IF EXISTS land_portion_nodes CASCADE;
DROP VIEW IF EXISTS boundary_boundary_edges CASCADE;
DROP VIEW IF EXISTS boundary_land_portion_edges CASCADE;
DROP VIEW IF EXISTS land_portion_water_boundary_edges CASCADE;
DROP VIEW IF EXISTS water_boundary_water_boundary_edges CASCADE;
DROP VIEW IF EXISTS boundary_water_boundary_edges CASCADE;
DROP VIEW IF EXISTS land_portion_land_edges CASCADE;
DROP VIEW IF EXISTS all_boundary_edges CASCADE;
DROP VIEW IF EXISTS unified_boundary_nodes CASCADE;
DROP VIEW IF EXISTS unified_boundary_edges CASCADE;
DROP VIEW IF EXISTS unified_boundary_graph CASCADE;

-- Create views for backward compatibility
-- Stage 1: Water Features
CREATE VIEW water_features_polygon AS SELECT * FROM s01_water_features_polygon;
CREATE VIEW water_features_line AS SELECT * FROM s01_water_features_line;
CREATE VIEW water_features AS SELECT * FROM s01_water_features_view;

-- Stage 2: Water Buffers
CREATE VIEW water_buffers AS SELECT * FROM s02_water_buffers;

-- Stage 3: Dissolved Water Buffers and Obstacles
CREATE VIEW dissolved_water_buffers AS SELECT * FROM s03_water_buffers_dissolved;
CREATE VIEW water_obstacles AS SELECT * FROM s03_water_obstacles;

-- Stage 4: Terrain Grid
CREATE VIEW complete_hex_grid AS SELECT * FROM s04_grid_hex_complete;
CREATE VIEW classified_hex_grid AS SELECT * FROM s04_grid_hex_classified;
CREATE VIEW water_hexagons_with_land AS SELECT * FROM s04_grid_water_with_land;
CREATE VIEW water_hex_land_portions AS SELECT * FROM s04_grid_water_land_portions;
CREATE VIEW terrain_grid AS SELECT * FROM s04_grid_terrain;
CREATE VIEW terrain_grid_points AS SELECT * FROM s04_grid_terrain_points;

-- Stage 4a: Terrain Edges
CREATE VIEW terrain_edges AS SELECT * FROM s04a_edges_terrain;

-- Stage 5: Boundary Nodes
CREATE VIEW boundary_nodes AS SELECT * FROM s05_nodes_boundary;
CREATE VIEW water_boundary_nodes AS SELECT * FROM s05_nodes_water_boundary;
CREATE VIEW land_portion_nodes AS SELECT * FROM s05_nodes_land_portion;

-- Stage 6: Boundary Edges
CREATE VIEW boundary_boundary_edges AS SELECT * FROM s06_edges_boundary_boundary;
CREATE VIEW boundary_land_portion_edges AS SELECT * FROM s06_edges_boundary_land_portion;
CREATE VIEW land_portion_water_boundary_edges AS SELECT * FROM s06_edges_land_portion_water_boundary;
CREATE VIEW water_boundary_water_boundary_edges AS SELECT * FROM s06_edges_water_boundary_water_boundary;
CREATE VIEW boundary_water_boundary_edges AS SELECT * FROM s06_edges_boundary_water_boundary;
CREATE VIEW land_portion_land_edges AS SELECT * FROM s06_edges_land_portion_land;
CREATE VIEW all_boundary_edges AS SELECT * FROM s06_edges_all_boundary;

-- Stage 7: Unified Boundary Graph
CREATE VIEW unified_boundary_nodes AS SELECT * FROM s07_graph_unified_nodes;
CREATE VIEW unified_boundary_edges AS SELECT * FROM s07_graph_unified_edges;
CREATE VIEW unified_boundary_graph AS SELECT * FROM s07_graph_unified;

-- Log the results
SELECT 'Created backward compatibility views for all tables';