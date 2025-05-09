# Complete Implementation Plan: Pipeline Stage Prefixing Table Naming Convention

This document provides a comprehensive implementation plan for adopting the Pipeline Stage Prefixing naming convention for tables in the Boundary Hexagon Layer Pipeline. This plan is designed to be handed off to another engineer to help complete the implementation.

## Project Overview

We are implementing a new table naming convention for the Boundary Hexagon Layer Pipeline that follows this format:
```
s{stage_number}_{category}_{entity}
```

For example, `water_features_polygon` becomes `s01_water_features_polygon`.

## Current Status

The following components have already been implemented:

1. **Documentation**:
   - Created a mapping document (`table_naming_convention.md`) that lists all current table names and their new names
   - Created an implementation plan (`table_naming_implementation_plan.md`) that outlines the steps needed to modify each SQL script
   - Created a README file (`renamed_tables_pipeline.md`) that explains how to use the renamed tables pipeline
   - Created a test plan (`renamed_tables_test_plan.md`) that outlines how to test the implementation

2. **Backward Compatibility**:
   - Created a SQL script (`create_backward_compatibility_views.sql`) that creates views with the old table names that point to the new tables

3. **Pipeline Scripts**:
   - Created a new pipeline script (`run_renamed_tables_pipeline.py`) that runs the renamed SQL scripts and the backward compatibility views script
   - Created a wrapper script (`run_renamed_tables_pipeline.py`) that redirects to the pipeline script
   - Created a script (`run_latest_pipeline.py`) that runs the most recent pipeline

4. **SQL Scripts**:
   - Modified `01_extract_water_features_3857.sql` to use the new table names
   - Modified `02_create_water_buffers_3857.sql` to use the new table names

## Remaining Tasks

The following tasks still need to be completed:

### 1. Modify Remaining SQL Scripts

Six SQL scripts still need to be modified to use the new table names:

#### 1.1. Modify `03_dissolve_water_buffers_3857.sql`

- **Current Location**: `epsg3857_pipeline/core/sql/03_dissolve_water_buffers_3857.sql`
- **Target Location**: `epsg3857_pipeline/core/sql/renamed/03_dissolve_water_buffers_3857.sql`
- **Changes Needed**:
  - Rename `dissolved_water_buffers` to `s03_water_buffers_dissolved`
  - Rename `water_obstacles` to `s03_water_obstacles`
  - Update references to `water_buffers` to use `s02_water_buffers`
  - Update all DROP, CREATE, INSERT, and SELECT statements
  - Update spatial index names

#### 1.2. Modify `04_create_terrain_grid_boundary_hexagon.sql`

- **Current Location**: `epsg3857_pipeline/core/sql/04_create_terrain_grid_boundary_hexagon.sql`
- **Target Location**: `epsg3857_pipeline/core/sql/renamed/04_create_terrain_grid_boundary_hexagon.sql`
- **Changes Needed**:
  - Rename `complete_hex_grid` to `s04_grid_hex_complete`
  - Rename `classified_hex_grid` to `s04_grid_hex_classified`
  - Rename `water_hexagons_with_land` to `s04_grid_water_with_land`
  - Rename `water_hex_land_portions` to `s04_grid_water_land_portions`
  - Rename `terrain_grid` to `s04_grid_terrain`
  - Rename `terrain_grid_points` to `s04_grid_terrain_points`
  - Update references to `dissolved_water_buffers` and `water_obstacles` to use `s03_water_buffers_dissolved` and `s03_water_obstacles`
  - Update all DROP, CREATE, INSERT, and SELECT statements
  - Update spatial index names

#### 1.3. Modify `04a_create_terrain_edges_hexagon.sql`

- **Current Location**: `epsg3857_pipeline/core/sql/04a_create_terrain_edges_hexagon.sql`
- **Target Location**: `epsg3857_pipeline/core/sql/renamed/04a_create_terrain_edges_hexagon.sql`
- **Changes Needed**:
  - Rename `terrain_edges` to `s04a_edges_terrain`
  - Update references to terrain grid tables to use the new names
  - Update all DROP, CREATE, INSERT, and SELECT statements
  - Update spatial index names

#### 1.4. Modify `05_create_boundary_nodes_hexagon.sql`

- **Current Location**: `epsg3857_pipeline/core/sql/05_create_boundary_nodes_hexagon.sql`
- **Target Location**: `epsg3857_pipeline/core/sql/renamed/05_create_boundary_nodes_hexagon.sql`
- **Changes Needed**:
  - Rename `boundary_nodes` to `s05_nodes_boundary`
  - Rename `water_boundary_nodes` to `s05_nodes_water_boundary`
  - Rename `land_portion_nodes` to `s05_nodes_land_portion`
  - Update references to terrain grid and water obstacle tables to use the new names
  - Update all DROP, CREATE, INSERT, and SELECT statements
  - Update spatial index names

#### 1.5. Modify `06_create_boundary_edges_hexagon_enhanced.sql`

- **Current Location**: `epsg3857_pipeline/core/sql/06_create_boundary_edges_hexagon_enhanced.sql`
- **Target Location**: `epsg3857_pipeline/core/sql/renamed/06_create_boundary_edges_hexagon_enhanced.sql`
- **Changes Needed**:
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

#### 1.6. Modify `07_create_unified_boundary_graph_hexagon.sql`

- **Current Location**: `epsg3857_pipeline/core/sql/07_create_unified_boundary_graph_hexagon.sql`
- **Target Location**: `epsg3857_pipeline/core/sql/renamed/07_create_unified_boundary_graph_hexagon.sql`
- **Changes Needed**:
  - Rename `unified_boundary_nodes` to `s07_graph_unified_nodes`
  - Rename `unified_boundary_edges` to `s07_graph_unified_edges`
  - Rename `unified_boundary_graph` to `s07_graph_unified`
  - Update references to node and edge tables to use the new names
  - Update all DROP, CREATE, INSERT, and SELECT statements
  - Update spatial index names

### 2. Testing

#### 2.1. Unit Testing

Test each modified script individually:

1. Reset the database using `epsg3857_pipeline/tools/database/reset_non_osm_tables.py`
2. Run the previous scripts in sequence
3. Run the script being tested
4. Verify that the tables are created with the correct structure and data
5. Verify that the spatial indexes are created

#### 2.2. Integration Testing

Test the entire pipeline end-to-end:

1. Reset the database using `epsg3857_pipeline/tools/database/reset_non_osm_tables.py`
2. Run the pipeline with the command `python epsg3857_pipeline/run_renamed_tables_pipeline.py`
3. Verify that all tables are created with the correct structure and data
4. Verify that the pipeline completes without errors

#### 2.3. Backward Compatibility Testing

Test that the backward compatibility views work correctly:

1. Run the pipeline with the command `python epsg3857_pipeline/run_renamed_tables_pipeline.py`
2. Verify that all backward compatibility views are created
3. Verify that the views return the same data as the new tables
4. Run a query that uses the old table names and verify that it works correctly

#### 2.4. Visualization Testing

Test that visualization scripts work correctly:

1. Run the pipeline with the command `python epsg3857_pipeline/run_renamed_tables_pipeline.py`
2. Run visualization scripts that use the old table names
3. Verify that the visualizations match the expected results

### 3. Documentation Updates

#### 3.1. Update Visualization Scripts

Update visualization scripts to use the new table names:

1. Identify all visualization scripts that directly reference table names
2. Update the scripts to use the new table names
3. Test the updated scripts to verify that they work correctly

#### 3.2. Update Documentation

Update documentation to use the new table names:

1. Identify all documentation that directly references table names
2. Update the documentation to use the new table names
3. Review the updated documentation to verify that it is accurate

## Implementation Approach

### Step-by-Step Guide

1. **Create a New Branch**:
   ```bash
   git checkout -b table-naming-convention
   ```

2. **Modify SQL Scripts**:
   - For each SQL script, create a modified version in the `renamed` directory
   - Test each script individually after modification

3. **Run Integration Tests**:
   - Run the pipeline with the command `python epsg3857_pipeline/run_renamed_tables_pipeline.py`
   - Verify that all tables are created with the correct structure and data

4. **Update Visualization Scripts**:
   - Update visualization scripts to use the new table names
   - Test the updated scripts to verify that they work correctly

5. **Update Documentation**:
   - Update documentation to use the new table names
   - Review the updated documentation to verify that it is accurate

6. **Commit Changes**:
   ```bash
   git add .
   git commit -m "Implement Pipeline Stage Prefixing naming convention"
   git push origin table-naming-convention
   ```

7. **Create Pull Request**:
   - Create a pull request to merge the changes into the main branch
   - Include a description of the changes and the benefits of the new naming convention

### Tips for Implementation

1. **Use Search and Replace Carefully**:
   - Be careful when using search and replace to avoid replacing parts of words
   - Use word boundaries in search patterns to avoid partial matches

2. **Test Each Script Individually**:
   - Test each script individually after modification to catch issues early
   - Verify that the tables are created with the correct structure and data

3. **Check for Edge Cases**:
   - Check for edge cases where table names might be used in unexpected ways
   - Look for table names in comments, string literals, and other contexts

4. **Document Changes**:
   - Document all changes made to the SQL scripts
   - Include a summary of the changes in the commit message

## Timeline

- **Day 1**: Modify the remaining SQL scripts (3-4 scripts)
- **Day 2**: Modify the remaining SQL scripts (2-3 scripts)
- **Day 3**: Run integration tests and fix any issues
- **Day 4**: Update visualization scripts and documentation
- **Day 5**: Final testing and review

## Resources

- **Table Naming Convention**: `epsg3857_pipeline/docs/table_naming_convention.md`
- **Implementation Plan**: `epsg3857_pipeline/docs/table_naming_implementation_plan.md`
- **Test Plan**: `epsg3857_pipeline/docs/renamed_tables_test_plan.md`
- **Pipeline Script**: `epsg3857_pipeline/pipelines/run_renamed_tables_pipeline.py`
- **Backward Compatibility Script**: `epsg3857_pipeline/core/sql/create_backward_compatibility_views.sql`

## Conclusion

This implementation plan provides a comprehensive approach to adopting the Pipeline Stage Prefixing naming convention while maintaining backward compatibility and ensuring all components of the system continue to function correctly.

By following this plan, you should be able to complete the implementation of the new table naming convention and ensure that all components of the system work correctly with the new table names.