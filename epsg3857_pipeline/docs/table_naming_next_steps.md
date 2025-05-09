# Table Naming Implementation: Next Steps

This document outlines the immediate next steps for implementing the Pipeline Stage Prefixing naming convention.

## Immediate Tasks (Next 3 Days)

### Day 1: Complete SQL Script Modifications for Stage 3

1. **Finalize `03_dissolve_water_buffers_3857.sql` Modification**
   - Use the template in [03_dissolve_water_buffers_3857_modified.md](03_dissolve_water_buffers_3857_modified.md)
   - Create the directory if it doesn't exist: `mkdir -p epsg3857_pipeline/core/sql/renamed`
   - Save the modified script to `epsg3857_pipeline/core/sql/renamed/03_dissolve_water_buffers_3857.sql`
   - Test the script to ensure it works correctly

2. **Prepare for Stage 4 Script Modifications**
   - Review `04_create_terrain_grid_boundary_hexagon.sql` to understand its structure
   - Identify all tables that need to be renamed
   - Create a detailed modification plan similar to [sql_script_modification_approach.md](sql_script_modification_approach.md)

### Day 2: Modify SQL Scripts for Stage 4

1. **Modify `04_create_terrain_grid_boundary_hexagon.sql`**
   - Rename tables:
     - `complete_hex_grid` → `s04_grid_hex_complete`
     - `classified_hex_grid` → `s04_grid_hex_classified`
     - `water_hexagons_with_land` → `s04_grid_water_with_land`
     - `water_hex_land_portions` → `s04_grid_water_land_portions`
     - `terrain_grid` → `s04_grid_terrain`
     - `terrain_grid_points` → `s04_grid_terrain_points`
   - Update references to `water_obstacles` to use `s03_water_obstacles`
   - Update spatial index names
   - Add header comment
   - Save to `epsg3857_pipeline/core/sql/renamed/04_create_terrain_grid_boundary_hexagon.sql`
   - Test the script

2. **Modify `04a_create_terrain_edges_hexagon.sql`**
   - Rename table: `terrain_edges` → `s04a_edges_terrain`
   - Update references to `terrain_grid` and `terrain_grid_points` to use `s04_grid_terrain` and `s04_grid_terrain_points`
   - Update spatial index name
   - Add header comment
   - Save to `epsg3857_pipeline/core/sql/renamed/04a_create_terrain_edges_hexagon.sql`
   - Test the script

### Day 3: Update Primary Pipeline and Begin Testing

1. **Update Primary Pipeline**
   - Follow the plan in [primary_pipeline_update_plan.md](primary_pipeline_update_plan.md)
   - Create a backup of the existing pipeline
   - Modify the pipeline script to support both the old and new table naming conventions
   - Create a wrapper script for the renamed tables pipeline
   - Test the updated pipeline

2. **Begin Unit Testing**
   - Create unit tests for the modified scripts
   - Test each script individually to ensure it works correctly
   - Document the results
   - Fix any issues that arise

## Required Resources

1. **Development Environment**
   - Docker environment with PostgreSQL and PostGIS
   - Python environment with required packages

2. **Test Data**
   - Sample OSM data for testing
   - Existing database with the old table structure for comparison

3. **Documentation**
   - Table naming convention documentation
   - SQL script modification approach
   - Implementation plan

## Expected Outcomes

1. **Modified SQL Scripts**
   - `03_dissolve_water_buffers_3857.sql`
   - `04_create_terrain_grid_boundary_hexagon.sql`
   - `04a_create_terrain_edges_hexagon.sql`

2. **Updated Primary Pipeline**
   - Modified `run_boundary_hexagon_layer_enhanced_pipeline.py` with `--use-renamed-tables` flag
   - New wrapper script `run_renamed_tables_pipeline.py`

3. **Unit Tests**
   - Tests for each modified script
   - Documentation of test results

## Success Criteria

1. All modified scripts work correctly with the new table naming convention
2. The primary pipeline successfully runs with both the old and new table naming conventions
3. Unit tests pass for all modified scripts
4. The implementation follows the table naming convention consistently

## Potential Challenges and Mitigations

1. **Complex SQL Scripts**
   - **Challenge**: Some SQL scripts may be complex and difficult to modify
   - **Mitigation**: Break down the modification into smaller steps, test each step

2. **Dependencies Between Scripts**
   - **Challenge**: Changes in one script may affect other scripts
   - **Mitigation**: Test the entire pipeline after modifying each script

3. **Performance Issues**
   - **Challenge**: The new naming convention may introduce performance issues
   - **Mitigation**: Monitor performance during testing, optimize as needed

## Communication Plan

1. **Daily Updates**
   - Provide daily updates on progress
   - Document any issues or challenges encountered
   - Update the implementation plan as needed

2. **Code Reviews**
   - Request code reviews for modified scripts
   - Address feedback promptly

3. **Documentation Updates**
   - Update documentation to reflect changes
   - Ensure all team members are aware of the changes

## Conclusion

By following these next steps, we can make significant progress on implementing the Pipeline Stage Prefixing naming convention. The focus on completing the SQL script modifications for Stages 3 and 4, updating the primary pipeline, and beginning testing will set a solid foundation for the rest of the implementation.