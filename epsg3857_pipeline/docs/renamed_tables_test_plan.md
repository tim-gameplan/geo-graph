# Renamed Tables Test Plan

This document outlines the test plan for verifying that the renamed tables pipeline works correctly.

## Test Objectives

1. Verify that all tables are created with the correct structure and data
2. Verify that the backward compatibility views work correctly
3. Verify that existing code that uses the old table names still works
4. Verify that the pipeline produces the same results as the original pipeline

## Test Environment

- Docker container with PostGIS
- Sample OSM data
- Python 3.8+
- PostgreSQL client

## Test Cases

### 1. Unit Tests for Each Script

#### 1.1. Test 01_extract_water_features_3857.sql

- **Objective**: Verify that the script creates the correct tables with the correct structure and data
- **Steps**:
  1. Run the script
  2. Verify that `s01_water_features_polygon` and `s01_water_features_line` tables are created
  3. Verify that the tables have the correct structure
  4. Verify that the tables contain the expected data
  5. Verify that the spatial indexes are created
  6. Verify that the `s01_water_features_view` view is created and works correctly

#### 1.2. Test 02_create_water_buffers_3857.sql

- **Objective**: Verify that the script creates the correct table with the correct structure and data
- **Steps**:
  1. Run the script
  2. Verify that the `s02_water_buffers` table is created
  3. Verify that the table has the correct structure
  4. Verify that the table contains the expected data
  5. Verify that the spatial index is created

#### 1.3. Test 03_dissolve_water_buffers_3857.sql

- **Objective**: Verify that the script creates the correct tables with the correct structure and data
- **Steps**:
  1. Run the script
  2. Verify that the `s03_water_buffers_dissolved` and `s03_water_obstacles` tables are created
  3. Verify that the tables have the correct structure
  4. Verify that the tables contain the expected data
  5. Verify that the spatial indexes are created

#### 1.4. Test 04_create_terrain_grid_boundary_hexagon.sql

- **Objective**: Verify that the script creates the correct tables with the correct structure and data
- **Steps**:
  1. Run the script
  2. Verify that all grid tables are created with the correct structure
  3. Verify that the tables contain the expected data
  4. Verify that the spatial indexes are created

#### 1.5. Test 04a_create_terrain_edges_hexagon.sql

- **Objective**: Verify that the script creates the correct table with the correct structure and data
- **Steps**:
  1. Run the script
  2. Verify that the `s04a_edges_terrain` table is created
  3. Verify that the table has the correct structure
  4. Verify that the table contains the expected data
  5. Verify that the spatial index is created

#### 1.6. Test 05_create_boundary_nodes_hexagon.sql

- **Objective**: Verify that the script creates the correct tables with the correct structure and data
- **Steps**:
  1. Run the script
  2. Verify that all node tables are created with the correct structure
  3. Verify that the tables contain the expected data
  4. Verify that the spatial indexes are created

#### 1.7. Test 06_create_boundary_edges_hexagon_enhanced.sql

- **Objective**: Verify that the script creates the correct tables with the correct structure and data
- **Steps**:
  1. Run the script
  2. Verify that all edge tables are created with the correct structure
  3. Verify that the tables contain the expected data
  4. Verify that the spatial indexes are created

#### 1.8. Test 07_create_unified_boundary_graph_hexagon.sql

- **Objective**: Verify that the script creates the correct tables with the correct structure and data
- **Steps**:
  1. Run the script
  2. Verify that all graph tables are created with the correct structure
  3. Verify that the tables contain the expected data
  4. Verify that the spatial indexes are created

### 2. Integration Tests for Pipeline

#### 2.1. Test Full Pipeline

- **Objective**: Verify that the entire pipeline works correctly end-to-end
- **Steps**:
  1. Run the pipeline with the command `python epsg3857_pipeline/run_renamed_tables_pipeline.py`
  2. Verify that all tables are created with the correct structure and data
  3. Verify that the pipeline completes without errors
  4. Verify that the pipeline produces the same results as the original pipeline

#### 2.2. Test Backward Compatibility

- **Objective**: Verify that the backward compatibility views work correctly
- **Steps**:
  1. Run the pipeline with the command `python epsg3857_pipeline/run_renamed_tables_pipeline.py`
  2. Verify that all backward compatibility views are created
  3. Verify that the views return the same data as the new tables
  4. Run a query that uses the old table names and verify that it works correctly

#### 2.3. Test No Compatibility Views Option

- **Objective**: Verify that the `--no-compatibility-views` option works correctly
- **Steps**:
  1. Run the pipeline with the command `python epsg3857_pipeline/run_renamed_tables_pipeline.py --no-compatibility-views`
  2. Verify that the backward compatibility views are not created

### 3. Visualization Tests

#### 3.1. Test Visualization Scripts

- **Objective**: Verify that visualization scripts work correctly with the new table names
- **Steps**:
  1. Run the pipeline with the command `python epsg3857_pipeline/run_renamed_tables_pipeline.py`
  2. Run visualization scripts that use the new table names
  3. Verify that the visualizations match the expected results

#### 3.2. Test Backward Compatibility for Visualization

- **Objective**: Verify that visualization scripts that use the old table names still work correctly
- **Steps**:
  1. Run the pipeline with the command `python epsg3857_pipeline/run_renamed_tables_pipeline.py`
  2. Run visualization scripts that use the old table names
  3. Verify that the visualizations match the expected results

## Test Data

- Use a small sample of OSM data for testing
- Create test cases with known expected results

## Test Execution

1. Run unit tests for each script
2. Run integration tests for the pipeline
3. Run visualization tests
4. Document test results

## Test Reporting

- Document any issues found during testing
- Document any differences between the renamed tables pipeline and the original pipeline
- Document any performance differences

## Acceptance Criteria

- All tables are created with the correct structure and data
- The backward compatibility views work correctly
- Existing code that uses the old table names still works
- The pipeline produces the same results as the original pipeline
- Visualization scripts work correctly with both the new and old table names