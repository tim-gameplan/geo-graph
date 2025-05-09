# Table Naming Implementation Plan: Detailed SQL Script Modifications

This document provides a detailed implementation plan for modifying the SQL scripts to use the Pipeline Stage Prefixing naming convention.

## Overview

The implementation will follow these high-level steps:

1. Create a `renamed` directory in `epsg3857_pipeline/core/sql/` to store the modified scripts
2. Modify each SQL script to use the new table naming convention
3. Create a backward compatibility script to maintain compatibility with existing code
4. Update the pipeline runner to use the modified scripts
5. Test the implementation to ensure it works correctly

## SQL Script Modification Approach

For each SQL script, we'll apply the following changes:

1. Add a header comment explaining the purpose of the script
2. Rename tables according to the naming convention
3. Update references to other tables to use their new names
4. Update spatial index names to match the new table names
5. Update log messages to use the new table names

## Script-by-Script Implementation Plan

### 1. 01_extract_water_features_3857.sql

**Status**: ✅ Completed

**Changes**:
- Renamed tables:
  - `water_features_polygon` → `s01_water_features_polygon`
  - `water_features_line` → `s01_water_features_line`
  - `water_features` (view) → `s01_water_features_view`
- Updated spatial index names
- Added header comment

### 2. 02_create_water_buffers_3857.sql

**Status**: ✅ Completed

**Changes**:
- Renamed table:
  - `water_buffers` → `s02_water_buffers`
- Updated references to `water_features_polygon` and `water_features_line`
- Updated spatial index name
- Added header comment

### 3. 03_dissolve_water_buffers_3857.sql

**Status**: 🔄 In Progress

**Changes**:
- Rename tables:
  - `dissolved_water_buffers` → `s03_water_buffers_dissolved`
  - `water_obstacles` → `s03_water_obstacles`
- Update references to `water_buffers` to use `s02_water_buffers`
- Update spatial index names
- Add header comment

**Implementation Details**:
- See [03_dissolve_water_buffers_3857_modified.md](03_dissolve_water_buffers_3857_modified.md) for the modified script
- See [sql_script_modification_approach.md](sql_script_modification_approach.md) for the detailed approach

### 4. 04_create_terrain_grid_boundary_hexagon.sql

**Status**: 📝 Planned

**Changes**:
- Rename tables:
  - `complete_hex_grid` → `s04_grid_hex_complete`
  - `classified_hex_grid` → `s04_grid_hex_classified`
  - `water_hexagons_with_land` → `s04_grid_water_with_land`
  - `water_hex_land_portions` → `s04_grid_water_land_portions`
  - `terrain_grid` → `s04_grid_terrain`
  - `terrain_grid_points` → `s04_grid_terrain_points`
- Update references to `water_obstacles`
- Update spatial index names
- Add header comment

### 5. 04a_create_terrain_edges_hexagon.sql

**Status**: 📝 Planned

**Changes**:
- Rename table:
  - `terrain_edges` → `s04a_edges_terrain`
- Update references to `terrain_grid` and `terrain_grid_points`
- Update spatial index name
- Add header comment

### 6. 05_create_boundary_nodes_hexagon.sql

**Status**: 📝 Planned

**Changes**:
- Rename tables:
  - `boundary_nodes` → `s05_nodes_boundary`
  - `water_boundary_nodes` → `s05_nodes_water_boundary`
  - `land_portion_nodes` → `s05_nodes_land_portion`
- Update references to `terrain_grid`, `water_hexagons_with_land`, and `water_hex_land_portions`
- Update spatial index names
- Add header comment

### 7. 06_create_boundary_edges_hexagon_enhanced.sql

**Status**: 📝 Planned

**Changes**:
- Rename tables:
  - `boundary_boundary_edges` → `s06_edges_boundary_boundary`
  - `boundary_land_portion_edges` → `s06_edges_boundary_land_portion`
  - `land_portion_water_boundary_edges` → `s06_edges_land_portion_water_boundary`
  - `water_boundary_water_boundary_edges` → `s06_edges_water_boundary_water_boundary`
  - `boundary_water_boundary_edges` → `s06_edges_boundary_water_boundary`
  - `land_portion_land_edges` → `s06_edges_land_portion_land`
  - `all_boundary_edges` → `s06_edges_all_boundary`
- Update references to `boundary_nodes`, `water_boundary_nodes`, and `land_portion_nodes`
- Update spatial index names
- Add header comment

### 8. 07_create_unified_boundary_graph_hexagon.sql

**Status**: 📝 Planned

**Changes**:
- Rename tables:
  - `unified_boundary_nodes` → `s07_graph_unified_nodes`
  - `unified_boundary_edges` → `s07_graph_unified_edges`
  - `unified_boundary_graph` → `s07_graph_unified`
- Update references to `boundary_nodes`, `water_boundary_nodes`, `land_portion_nodes`, and all edge tables
- Update spatial index names
- Add header comment

### 9. create_backward_compatibility_views.sql

**Status**: ✅ Completed

**Changes**:
- Created views with the old table names that point to the new tables
- Added header comment

## Implementation Challenges and Solutions

### Challenge 1: Maintaining Backward Compatibility

**Solution**: Create views with the old table names that point to the new tables. This ensures that existing code continues to work with the new naming convention.

### Challenge 2: Ensuring Consistent Naming

**Solution**: Follow the naming convention strictly and use a consistent approach for all scripts. Document the naming convention and the mapping between old and new table names.

### Challenge 3: Testing the Implementation

**Solution**: Create a test plan that verifies the functionality of each script and the entire pipeline. Test both the new table names and the backward compatibility views.

## Testing Strategy

1. **Unit Testing**: Test each script individually to ensure it works correctly with the new table names.
2. **Integration Testing**: Test the entire pipeline to ensure all scripts work together correctly.
3. **Backward Compatibility Testing**: Test the backward compatibility views to ensure existing code continues to work.
4. **Performance Testing**: Compare the performance of the original and modified scripts to ensure there's no degradation.

## Implementation Timeline

1. **Phase 1**: Modify scripts 01-03 (Completed)
2. **Phase 2**: Modify scripts 04-05 (In Progress)
3. **Phase 3**: Modify scripts 06-07
4. **Phase 4**: Test the implementation
5. **Phase 5**: Deploy the implementation

## Next Steps

1. Complete the modification of `03_dissolve_water_buffers_3857.sql`
2. Begin the modification of `04_create_terrain_grid_boundary_hexagon.sql`
3. Update the test plan to include the modified scripts
4. Create a deployment plan for the implementation

## Conclusion

This implementation plan provides a detailed approach for modifying the SQL scripts to use the Pipeline Stage Prefixing naming convention. By following this plan, we can ensure a smooth transition to the new naming convention while maintaining backward compatibility with existing code.