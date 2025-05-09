# Current vs. Proposed Table Names

This document compares the current table names in the database with the proposed table names using the Pipeline Stage Prefixing naming convention.

## Current Table Names

Based on the database screenshot, these are the current table names:

1. all_boundary_edges
2. boundary_boundary_edges
3. boundary_land_portion_edges
4. boundary_nodes
5. boundary_water_boundary_edges
6. classified_hex_grid
7. complete_hex_grid
8. dissolved_water_buffers
9. land_portion_land_edges
10. land_portion_nodes
11. land_portion_water_boundary_edges
12. planet_osm_line
13. planet_osm_point
14. planet_osm_polygon
15. planet_osm_roads
16. terrain_edges
17. terrain_grid
18. terrain_grid_points
19. unified_boundary_graph
20. unified_boundary_nodes
21. water_boundary_nodes
22. water_boundary_water_boundary_edges
23. water_features
24. water_buffers
25. water_features_line
26. water_features_polygon
27. water_hex_land_portions.land_portion
28. water_hexagons_with_land
29. water_obstacles

## Proposed Table Names

These are the proposed table names using the Pipeline Stage Prefixing naming convention:

1. s06_edges_all_boundary (from all_boundary_edges)
2. s06_edges_boundary_boundary (from boundary_boundary_edges)
3. s06_edges_boundary_land_portion (from boundary_land_portion_edges)
4. s05_nodes_boundary (from boundary_nodes)
5. s06_edges_boundary_water_boundary (from boundary_water_boundary_edges)
6. s04_grid_hex_classified (from classified_hex_grid)
7. s04_grid_hex_complete (from complete_hex_grid)
8. s03_water_buffers_dissolved (from dissolved_water_buffers)
9. s06_edges_land_portion_land (from land_portion_land_edges)
10. s05_nodes_land_portion (from land_portion_nodes)
11. s06_edges_land_portion_water_boundary (from land_portion_water_boundary_edges)
12. planet_osm_line (unchanged - OSM source table)
13. planet_osm_point (unchanged - OSM source table)
14. planet_osm_polygon (unchanged - OSM source table)
15. planet_osm_roads (unchanged - OSM source table)
16. s04a_edges_terrain (from terrain_edges)
17. s04_grid_terrain (from terrain_grid)
18. s04_grid_terrain_points (from terrain_grid_points)
19. s07_graph_unified (from unified_boundary_graph)
20. s07_graph_unified_nodes (from unified_boundary_nodes)
21. s05_nodes_water_boundary (from water_boundary_nodes)
22. s06_edges_water_boundary_water_boundary (from water_boundary_water_boundary_edges)
23. s01_water_features_view (from water_features)
24. s02_water_buffers (from water_buffers)
25. s01_water_features_line (from water_features_line)
26. s01_water_features_polygon (from water_features_polygon)
27. s04_grid_water_land_portions (from water_hex_land_portions.land_portion)
28. s04_grid_water_with_land (from water_hexagons_with_land)
29. s03_water_obstacles (from water_obstacles)

## Implementation Status

The implementation plan we've created is a proposal for future implementation. The tables shown in the screenshot are the current tables in the database, which would be renamed according to our proposed naming convention.

The implementation plan includes:

1. Creating modified SQL scripts that use the new table names
2. Creating backward compatibility views with the old table names
3. Updating the pipeline runner to use the modified scripts
4. Testing the implementation
5. Updating code references to use the new table names

## Next Steps

The next steps are to:

1. Create the directory structure for the modified scripts
2. Implement the modified SQL scripts starting with `03_dissolve_water_buffers_3857.sql`
3. Update the primary pipeline to support both old and new table names
4. Begin testing the implementation

This implementation will improve the organization and maintainability of the database schema, making it easier to understand and work with the pipeline.