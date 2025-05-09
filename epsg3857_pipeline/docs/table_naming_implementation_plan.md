# Table Naming Convention Implementation Plan

This document outlines the step-by-step plan for implementing the Pipeline Stage Prefixing naming convention for tables in the Boundary Hexagon Layer Pipeline.

## Overview

The implementation will follow these high-level steps:

1. Create a mapping document (completed: `table_naming_convention.md`)
2. Create a backward compatibility script (completed: `create_backward_compatibility_views.sql`)
3. Create a new pipeline script that runs the backward compatibility script (completed: `run_renamed_boundary_hexagon_layer_pipeline.py`)
4. Modify each SQL script to use the new table names
5. Test the modified pipeline
6. Update documentation and visualization scripts

## SQL Script Modifications

Each SQL script needs to be modified to use the new table names. Here's a detailed plan for each script:

### 1. 01_extract_water_features_3857.sql

- Rename `water_features_polygon` to `s01_water_features_polygon`
- Rename `water_features_line` to `s01_water_features_line`
- Rename `water_features` view to `s01_water_features_view`
- Update all DROP, CREATE, INSERT, and SELECT statements
- Update spatial index names

### 2. 02_create_water_buffers_3857.sql

- Rename `water_buffers` to `s02_water_buffers`
- Update references to `water_features_polygon` and `water_features_line` to use `s01_water_features_polygon` and `s01_water_features_line`
- Update all DROP, CREATE, INSERT, and SELECT statements
- Update spatial index names

### 3. 03_dissolve_water_buffers_3857.sql

- Rename `dissolved_water_buffers` to `s03_water_buffers_dissolved`
- Rename `water_obstacles` to `s03_water_obstacles`
- Update references to `water_buffers` to use `s02_water_buffers`
- Update all DROP, CREATE, INSERT, and SELECT statements
- Update spatial index names

### 4. 04_create_terrain_grid_boundary_hexagon.sql

- Rename `complete_hex_grid` to `s04_grid_hex_complete`
- Rename `classified_hex_grid` to `s04_grid_hex_classified`
- Rename `water_hexagons_with_land` to `s04_grid_water_with_land`
- Rename `water_hex_land_portions` to `s04_grid_water_land_portions`
- Rename `terrain_grid` to `s04_grid_terrain`
- Rename `terrain_grid_points` to `s04_grid_terrain_points`
- Update references to `dissolved_water_buffers` and `water_obstacles` to use `s03_water_buffers_dissolved` and `s03_water_obstacles`
- Update all DROP, CREATE, INSERT, and SELECT statements
- Update spatial index names

### 5. 04a_create_terrain_edges_hexagon.sql

- Rename `terrain_edges` to `s04a_edges_terrain`
- Update references to terrain grid tables to use the new names
- Update all DROP, CREATE, INSERT, and SELECT statements
- Update spatial index names

### 6. 05_create_boundary_nodes_hexagon.sql

- Rename `boundary_nodes` to `s05_nodes_boundary`
- Rename `water_boundary_nodes` to `s05_nodes_water_boundary`
- Rename `land_portion_nodes` to `s05_nodes_land_portion`
- Update references to terrain grid and water obstacle tables to use the new names
- Update all DROP, CREATE, INSERT, and SELECT statements
- Update spatial index names

### 7. 06_create_boundary_edges_hexagon_enhanced.sql

- Rename `boundary_boundary_edges` to `s06_edges_boundary_boundary`
- Rename `boundary_land_portion_edges` to `s06_edges_boundary_land_portion`
- Rename `land_portion_water_boundary_edges` to `s06_edges_land_portion_water_boundary`
- Rename `water_boundary_water_boundary_edges` to `s06_edges_water_boundary_water_boundary`
- Rename `boundary_water_boundary_edges` to `s06_edges_boundary_water_boundary`
- Rename `land_portion_land_edges` to `s06_edges_land_portion_land`
- Rename `all_boundary_edges` to `s06_edges_all_boundary`
- Update references to node tables to use the new names
- Update all DROP, CREATE, INSERT, and SELECT statements
- Update spatial index names

### 8. 07_create_unified_boundary_graph_hexagon.sql

- Rename `unified_boundary_nodes` to `s07_graph_unified_nodes`
- Rename `unified_boundary_edges` to `s07_graph_unified_edges`
- Rename `unified_boundary_graph` to `s07_graph_unified`
- Update references to node and edge tables to use the new names
- Update all DROP, CREATE, INSERT, and SELECT statements
- Update spatial index names

## Testing Strategy

1. **Unit Tests for Each Script**:
   - Test each modified script individually
   - Verify tables are created with correct structure
   - Verify data is correctly inserted

2. **Integration Tests for Pipeline**:
   - Test the entire pipeline end-to-end
   - Verify all tables are created correctly
   - Verify relationships between tables are maintained

3. **Backward Compatibility Tests**:
   - Test that the backward compatibility views work correctly
   - Verify that existing code that uses the old table names still works

4. **Visualization Tests**:
   - Test visualization scripts with new table names
   - Verify visualizations match previous results

## Implementation Timeline

1. **Day 1: Preparation**
   - Create mapping document (completed)
   - Create backward compatibility script (completed)
   - Create new pipeline script (completed)
   - Create implementation plan (this document)

2. **Day 2-3: SQL Script Modifications**
   - Modify SQL scripts one by one
   - Test each script individually
   - Document changes

3. **Day 4: Testing**
   - Run full integration tests
   - Test backward compatibility
   - Fix any issues

4. **Day 5: Documentation and Visualization**
   - Update documentation
   - Update visualization scripts
   - Final testing

## Rollback Plan

If issues are encountered during implementation, the following rollback plan will be used:

1. Revert to the original SQL scripts
2. Remove the backward compatibility views
3. Use the original pipeline script

## Conclusion

This implementation plan provides a comprehensive approach to adopting the Pipeline Stage Prefixing naming convention while maintaining backward compatibility and ensuring all components of the system continue to function correctly.