# EPSG:3857 Pipeline Development Worklog

This document tracks the development progress, issues encountered, and solutions implemented for the EPSG:3857 terrain graph pipeline.

## 2025-04-22: Parameter Handling Fix in SQL Files

### Issue
When running the Delaunay pipeline, we encountered an error in the SQL parameter replacement:

```
❌ Water obstacle pipeline (delaunay) failed: Command 'python epsg3857_pipeline/scripts/run_water_obstacle_pipeline_delaunay.py --config epsg3857_pipeline/config/delaunay_config.json --sql-dir epsg3857_pipeline/sql' returned non-zero exit status 1.
```

The specific error was:
```
ERROR - Error executing 05_create_terrain_edges_delaunay_3857.sql: trailing junk after numeric literal at or near "300_"
LINE 64: ...WHERE ST_DWithin(ST_StartPoint(ve.geom), tg.geom, 300_m) ORD...
```

### Root Cause Analysis
The parameter replacement in the SQL files was not working correctly when parameter names contained an underscore followed by a suffix (e.g., `_m`). Instead of replacing the parameter with just the numeric value, it was appending the suffix to the value, resulting in invalid SQL syntax like `300_m` instead of just `300`.

### Solution
1. Modified the parameter names in the SQL files to avoid using suffixes with underscores:
   - Changed `:connection_distance_m` to `:connection_dist` in `05_create_terrain_edges_delaunay_3857.sql`

2. Updated the Python script to include both parameter names for backward compatibility:
   - Added `params['connection_dist'] = terrain_grid.get('max_edge_length', 500)` in `run_water_obstacle_pipeline_delaunay.py`

### Testing
After implementing these changes, the Delaunay pipeline ran successfully:
```
✅ Water obstacle pipeline (delaunay) completed successfully
```

## 2025-04-22: Test Script Path Fix

### Issue
The test scripts were failing with errors like:
```
python: can't open file '/Users/tim/gameplan/dev/terrain-system/geo-graph/epsg3857_pipeline/epsg3857_pipeline/tests/test_epsg3857_pipeline.py': [Errno 2] No such file or directory
```

### Root Cause Analysis
The `run_tests.sh` script was using incorrect paths to the test files. It was looking for test files in `epsg3857_pipeline/epsg3857_pipeline/tests/` instead of `epsg3857_pipeline/tests/`.

### Solution
Modified the `run_tests.sh` script to use the correct paths:
- Changed `python epsg3857_pipeline/tests/test_epsg3857_pipeline.py $VERBOSE` to `python tests/test_epsg3857_pipeline.py $VERBOSE`
- Changed `python epsg3857_pipeline/tests/test_delaunay_pipeline.py $VERBOSE` to `python tests/test_delaunay_pipeline.py $VERBOSE`

## 2025-04-22: Test Script Path Fixes

### Issue
The test scripts were failing with errors like:
```
python: can't open file '/Users/tim/gameplan/dev/terrain-system/geo-graph/epsg3857_pipeline/scripts/reset_database.py': [Errno 2] No such file or directory
```

### Root Cause Analysis
The test scripts (test_epsg3857_pipeline.py and test_delaunay_pipeline.py) were using incorrect relative paths. When run from the epsg3857_pipeline directory via run_tests.sh, they were looking for files in epsg3857_pipeline/scripts/ and epsg3857_pipeline/epsg3857_pipeline/ instead of the correct locations.

### Solution
1. Modified the path to reset_database.py in both test scripts:
   - Changed `python scripts/reset_database.py` to `python ../scripts/reset_database.py`

2. Fixed paths to run_epsg3857_pipeline.py in both test scripts:
   - Changed `python epsg3857_pipeline/run_epsg3857_pipeline.py` to `python ../run_epsg3857_pipeline.py`

3. Fixed the path to the config file in test_delaunay_pipeline.py:
   - Changed `--config epsg3857_pipeline/config/delaunay_config.json` to `--config ../config/delaunay_config.json`

### Testing
After implementing these changes, the test scripts should be able to find the required files when executed from the epsg3857_pipeline directory.

## 2025-04-22: Self-Contained Directory Structure

### Issue
The EPSG:3857 pipeline had dependencies on scripts and utilities located outside the epsg3857_pipeline directory, making it difficult to use as a standalone module.

### Root Cause Analysis
The pipeline was originally developed with references to scripts in the parent directory, such as:
- `scripts/reset_database.py`
- `tools/export_slice_enhanced_fixed.py`
- `visualize_unified.py`

This created path reference issues when running the pipeline from different locations.

### Solution
1. Created a self-contained directory structure by copying necessary scripts into the epsg3857_pipeline directory:
   - Copied `scripts/reset_database.py` to `epsg3857_pipeline/scripts/reset_database.py`
   - Copied `tools/export_slice_enhanced_fixed.py` to `epsg3857_pipeline/scripts/export_slice.py`
   - Created a simplified version of `visualize_unified.py` as `epsg3857_pipeline/scripts/visualize.py`
   - Created a dedicated `epsg3857_pipeline/scripts/visualize_delaunay_triangulation.py`

2. Updated path references in `run_epsg3857_pipeline.py`:
   - Changed script paths to use relative paths within the epsg3857_pipeline directory
   - Updated config file paths to use relative paths
   - Updated SQL directory paths to use relative paths

3. Updated examples in the documentation to reflect the new self-contained structure

### Benefits
- The pipeline can now be run entirely from within the epsg3857_pipeline directory
- No dependencies on external scripts or utilities
- Easier to distribute and deploy
- More maintainable and less prone to path-related errors

## Ongoing Development Tasks

### Documentation
- README.md is up to date with current features and usage instructions
- Added this worklog to track development progress and issues

### Next Steps
1. Add more comprehensive tests for the Delaunay triangulation
2. Improve error handling in the pipeline scripts
3. Add more visualization options for the Delaunay triangulation
4. Optimize the SQL queries for better performance with large datasets

## Known Issues
1. Parameter replacement in SQL files can be problematic with certain parameter naming conventions
2. The unified Delaunay pipeline needs more testing with large datasets

## Performance Considerations
- The Delaunay triangulation can be memory-intensive for large datasets
- Consider implementing spatial partitioning for very large areas
- Optimize the SQL queries with proper indexing and parallel execution
