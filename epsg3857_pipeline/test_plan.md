# EPSG:3857 Pipeline Test Plan

This document outlines the testing strategy for the EPSG:3857 terrain graph pipeline, including test cases, methodologies, and expected outcomes.

## Testing Goals

1. Verify that the EPSG:3857 pipeline correctly handles coordinate reference systems
2. Ensure that the Delaunay triangulation produces valid and efficient terrain grids
3. Validate that water features are properly extracted, buffered, and dissolved
4. Confirm that the pipeline produces consistent and accurate results
5. Test performance and scalability with different dataset sizes

## Test Environment Setup

### Prerequisites

- PostgreSQL database with PostGIS extension
- Python 3.8+ with required dependencies
- OSM data subset for testing
- Configuration files for different test scenarios

### Database Setup

```bash
# Reset the database before each test
python scripts/reset_database.py --reset-derived

# Verify database connection
psql -h localhost -U gis -d gis -c "SELECT PostGIS_Version();"
```

## Test Categories

### 1. Unit Tests

Unit tests focus on individual components of the pipeline:

- **SQL Parameter Replacement**: Test that SQL parameters are correctly replaced in SQL files
- **Configuration Loading**: Test that configuration files are correctly loaded and parsed
- **Database Connection**: Test database connection and error handling
- **File Path Resolution**: Test that file paths are correctly resolved

### 2. Integration Tests

Integration tests verify that pipeline components work together correctly:

- **Water Feature Extraction**: Test that water features are correctly extracted from OSM data
- **Water Buffer Creation**: Test that water buffers are created with correct sizes
- **Water Buffer Dissolving**: Test that overlapping water buffers are correctly dissolved
- **Terrain Grid Creation**: Test that terrain grid is created with correct cell size and spacing
- **Terrain Edge Creation**: Test that terrain edges connect grid cells correctly
- **Water Edge Creation**: Test that water edges represent water obstacles correctly
- **Environmental Table Creation**: Test that environmental conditions are added correctly

### 3. End-to-End Tests

End-to-end tests verify that the complete pipeline works correctly:

- **Standard Pipeline**: Test the standard EPSG:3857 pipeline end-to-end
- **Delaunay Pipeline**: Test the Delaunay triangulation pipeline end-to-end
- **Unified Delaunay Pipeline**: Test the unified Delaunay pipeline for large datasets

### 4. Performance Tests

Performance tests measure the pipeline's efficiency and scalability:

- **Memory Usage**: Test memory usage with different dataset sizes
- **Execution Time**: Test execution time with different dataset sizes
- **Parallel Processing**: Test parallel processing with different thread counts
- **Spatial Partitioning**: Test spatial partitioning with different chunk sizes

## Test Cases

### Standard Pipeline Tests

| Test ID | Description | Input | Expected Output | Validation Method |
|---------|-------------|-------|----------------|-------------------|
| SP-01 | Run standard pipeline with default config | Default config | Complete terrain graph | Verify table counts and structure |
| SP-02 | Run standard pipeline with custom config | Custom config | Terrain graph with custom parameters | Verify parameter effects |
| SP-03 | Export graph slice | Coordinates, travel time | GraphML file | Verify file structure and content |
| SP-04 | Visualize graph | GraphML file | Visualization | Visual inspection |

### Delaunay Pipeline Tests

| Test ID | Description | Input | Expected Output | Validation Method |
|---------|-------------|-------|----------------|-------------------|
| DP-01 | Run Delaunay pipeline with default config | Default config | Triangulated terrain graph | Verify triangulation quality |
| DP-02 | Run Delaunay pipeline with custom config | Custom config | Custom triangulated graph | Verify parameter effects |
| DP-03 | Test triangulation with water boundaries | Water features | Triangulation respecting boundaries | Verify edge intersections |
| DP-04 | Test triangulation with different tolerances | Tolerance values | Different triangulation densities | Compare triangle counts |

### CRS Handling Tests

| Test ID | Description | Input | Expected Output | Validation Method |
|---------|-------------|-------|----------------|-------------------|
| CRS-01 | Verify coordinate transformations | Mixed CRS data | Consistent EPSG:3857 data | Check geometry SRID |
| CRS-02 | Test buffer sizes in meters | Buffer parameters | Correct buffer sizes | Measure buffer distances |
| CRS-03 | Test area calculations | Polygon features | Correct area values | Compare with reference |
| CRS-04 | Test distance calculations | Line features | Correct distance values | Compare with reference |

### Error Handling Tests

| Test ID | Description | Input | Expected Output | Validation Method |
|---------|-------------|-------|----------------|-------------------|
| EH-01 | Test with invalid config | Invalid config | Appropriate error message | Check error output |
| EH-02 | Test with missing SQL files | Missing files | Appropriate error message | Check error output |
| EH-03 | Test with database connection failure | Invalid connection | Appropriate error message | Check error output |
| EH-04 | Test with invalid parameters | Invalid parameters | Appropriate error message | Check error output |

## Test Execution

### Automated Tests

Automated tests are run using the `run_tests.sh` script:

```bash
# Run all tests
./epsg3857_pipeline/run_tests.sh

# Run only standard pipeline tests
./epsg3857_pipeline/run_tests.sh --standard-only

# Run only Delaunay triangulation tests
./epsg3857_pipeline/run_tests.sh --delaunay-only

# Run tests with verbose output
./epsg3857_pipeline/run_tests.sh --verbose
```

### Manual Tests

Some tests require manual verification:

1. **Visual Inspection**: Visualize the terrain graph and check for obvious issues
2. **Query Verification**: Run SQL queries to verify data integrity
3. **Performance Monitoring**: Monitor memory usage and execution time

## Test Reporting

Test results are logged to the following files:

- `test_epsg3857_pipeline.log`: Standard pipeline test results
- `test_delaunay_pipeline.log`: Delaunay pipeline test results

## Continuous Integration

For future implementation, consider setting up continuous integration:

1. Run tests automatically on each commit
2. Generate test reports and metrics
3. Notify developers of test failures
4. Track test coverage over time

## Test Maintenance

To keep tests relevant and effective:

1. Update tests when pipeline functionality changes
2. Add new tests for new features
3. Remove obsolete tests
4. Periodically review and optimize tests

## Known Test Limitations

1. Tests currently use a small OSM data subset, which may not catch issues with large datasets
2. Performance tests are not yet automated
3. Visual verification is still required for some aspects
4. Test coverage is not yet measured

## Future Test Improvements

1. Add more comprehensive unit tests
2. Implement property-based testing for edge cases
3. Add performance benchmarking
4. Implement test coverage measurement
5. Add tests for different geographic regions and feature distributions
