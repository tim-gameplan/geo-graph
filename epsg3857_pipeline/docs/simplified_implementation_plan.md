# Simplified Table Naming Implementation Plan

Based on the clarification that legacy apps do not need to be supported, this document outlines a simplified implementation plan for the Pipeline Stage Prefixing naming convention.

## Overview

Since backward compatibility is not required, we can directly update the SQL scripts and code to use the new table names. This simplifies the implementation significantly, as we don't need to create backward compatibility views or support both old and new table names in the pipeline.

## Implementation Steps

### 1. Update SQL Scripts

Update all SQL scripts to use the new table naming convention:

1. **01_extract_water_features_3857.sql**:
   - Rename `water_features_polygon` to `s01_water_features_polygon`
   - Rename `water_features_line` to `s01_water_features_line`
   - Rename `water_features` to `s01_water_features_view`

2. **02_create_water_buffers_3857.sql**:
   - Rename `water_buffers` to `s02_water_buffers`

3. **03_dissolve_water_buffers_3857.sql**:
   - Rename `dissolved_water_buffers` to `s03_water_buffers_dissolved`
   - Rename `water_obstacles` to `s03_water_obstacles`

4. **04_create_terrain_grid_boundary_hexagon.sql**:
   - Rename `complete_hex_grid` to `s04_grid_hex_complete`
   - Rename `classified_hex_grid` to `s04_grid_hex_classified`
   - Rename `water_hexagons_with_land` to `s04_grid_water_with_land`
   - Rename `water_hex_land_portions` to `s04_grid_water_land_portions`
   - Rename `terrain_grid` to `s04_grid_terrain`
   - Rename `terrain_grid_points` to `s04_grid_terrain_points`

5. **04a_create_terrain_edges_hexagon.sql**:
   - Rename `terrain_edges` to `s04a_edges_terrain`

6. **05_create_boundary_nodes_hexagon.sql**:
   - Rename `boundary_nodes` to `s05_nodes_boundary`
   - Rename `water_boundary_nodes` to `s05_nodes_water_boundary`
   - Rename `land_portion_nodes` to `s05_nodes_land_portion`

7. **06_create_boundary_edges_hexagon_enhanced.sql**:
   - Rename `boundary_boundary_edges` to `s06_edges_boundary_boundary`
   - Rename `boundary_land_portion_edges` to `s06_edges_boundary_land_portion`
   - Rename `land_portion_water_boundary_edges` to `s06_edges_land_portion_water_boundary`
   - Rename `water_boundary_water_boundary_edges` to `s06_edges_water_boundary_water_boundary`
   - Rename `boundary_water_boundary_edges` to `s06_edges_boundary_water_boundary`
   - Rename `land_portion_land_edges` to `s06_edges_land_portion_land`
   - Rename `all_boundary_edges` to `s06_edges_all_boundary`

8. **07_create_unified_boundary_graph_hexagon.sql**:
   - Rename `unified_boundary_nodes` to `s07_graph_unified_nodes`
   - Rename `unified_boundary_edges` to `s07_graph_unified_edges`
   - Rename `unified_boundary_graph` to `s07_graph_unified`

### 2. Update Code References

Update all code that references the old table names to use the new table names:

1. **Pipeline Runner Scripts**:
   - Update `run_boundary_hexagon_layer_enhanced_pipeline.py`
   - Update any other scripts that reference the old table names

2. **Visualization Scripts**:
   - Update any visualization scripts that reference the old table names

3. **Tests**:
   - Update any tests that reference the old table names

### 3. Testing

Test the updated pipeline to ensure it works correctly:

1. **Run the Pipeline**:
   - Run the pipeline with the updated SQL scripts
   - Verify that all tables are created with the new names
   - Verify that the pipeline completes successfully

2. **Run Tests**:
   - Run any existing tests to verify that they work with the new table names
   - Fix any issues that arise

## Implementation Timeline

The implementation can be completed in a shorter timeframe since we don't need to create backward compatibility views or support both old and new table names:

1. **Day 1**: Update SQL scripts
2. **Day 2**: Update code references
3. **Day 3**: Testing and fixes

## Conclusion

This simplified implementation plan provides a straightforward approach for implementing the Pipeline Stage Prefixing naming convention without the need for backward compatibility. By directly updating the SQL scripts and code to use the new table names, we can implement the naming convention quickly and efficiently.