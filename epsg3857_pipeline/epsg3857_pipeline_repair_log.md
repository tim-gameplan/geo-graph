# EPSG:3857 Pipeline Repair Log

## Issue Analysis

After reviewing the EPSG:3857 pipeline, we've identified several issues that are preventing the pipeline from working correctly:

1. **Parameter Naming Mismatch**: The SQL files are looking for parameters like `:lake_buffer`, `:river_buffer`, etc., but the config_loader_3857.py script is providing parameters with names like `buffer_lake`, `buffer_river`, etc.

2. **Empty Tables**: Most of the tables in the pipeline are empty, even though the pipeline appears to run successfully. Only the water_features table has data (1126 rows), and the dissolved_water_buffers table has 1 row but with NULL geometry.

3. **Path Issues**: There were path issues in the log files, with the pipeline looking for files in incorrect locations like `/Users/tim/gameplan/dev/terrain-system/geo-graph/epsg3857_pipeline/epsg3857_pipeline/scripts/run_water_obstacle_pipeline_crs.py`.

4. **Parameter Substitution Issues**: There were issues with parameter substitution in the SQL files, particularly with parameters that had suffixes like `_m` (e.g., `5_m`), which caused syntax errors.

## Repair Plan

To fix these issues, we need to:

1. **Fix Parameter Naming**: Update either the SQL files or the config_loader_3857.py script to ensure that parameter names match. For example, if the SQL files use `:lake_buffer`, the config_loader_3857.py script should provide a parameter named `lake_buffer`.

2. **Fix Parameter Substitution**: Ensure that parameters with suffixes like `_m` are handled correctly. This might involve modifying the SQL files to use a different syntax or updating the parameter substitution logic in the run_water_obstacle_pipeline_crs.py script.

3. **Fix Path Issues**: Ensure that all paths in the pipeline scripts are correct and consistent.

4. **Debug Empty Tables**: Investigate why the tables are empty even though the pipeline appears to run successfully. This might involve adding more logging to the SQL files or checking the SQL output directly.

## Implementation

### 1. Fix Parameter Naming

The mismatch in parameter naming is likely the root cause of the empty tables. The SQL files are looking for parameters like `:lake_buffer`, but the config_loader_3857.py script is providing parameters with names like `buffer_lake`.

We need to update the config_loader_3857.py script to provide parameters with the correct names:

```python
# Add water buffer sizes
for feature_type, buffer_size in water_buffers.items():
    params[f'{feature_type}_buffer'] = buffer_size
```

Alternatively, we could update the SQL files to use the parameter names provided by the config_loader_3857.py script:

```sql
-- Create buffers for water polygons
INSERT INTO water_buffers (water_feature_id, buffer_size, geom)
SELECT 
    id,
    CASE
        WHEN type = 'water' THEN :buffer_lake
        ELSE :buffer_default
    END AS buffer_size,
    ST_Buffer(
        geom,
        CASE
            WHEN type = 'water' THEN :buffer_lake
            ELSE :buffer_default
        END
    ) AS geom
FROM 
    water_features
WHERE 
    ST_GeometryType(geom) IN ('ST_Polygon', 'ST_MultiPolygon');
```

### 2. Fix Parameter Substitution

The parameter substitution issues with suffixes like `_m` can be fixed by modifying the SQL files to use a different syntax or by updating the parameter substitution logic in the run_water_obstacle_pipeline_crs.py script.

For example, we could update the SQL files to use a different syntax:

```sql
-- Instead of
ST_SimplifyPreserveTopology(geom, 5_m)

-- Use
ST_SimplifyPreserveTopology(geom, :simplify_tolerance)
```

### 3. Fix Path Issues

The path issues can be fixed by ensuring that all paths in the pipeline scripts are correct and consistent. This might involve updating the paths in the run_epsg3857_pipeline.py script or other scripts that call the pipeline scripts.

### 4. Debug Empty Tables

To debug the empty tables, we can add more logging to the SQL files or check the SQL output directly. For example, we could add a SELECT statement at the end of each SQL file to check the row count:

```sql
-- Log the results
SELECT 'Created ' || COUNT(*) || ' water buffers' FROM water_buffers;
```

## Testing

After implementing these fixes, we should test the pipeline to ensure that it works correctly:

1. Run the pipeline with the standard configuration
2. Check that all tables have data
3. Verify that the geometry in the dissolved_water_buffers table is valid
4. Run the pipeline with the Delaunay configuration
5. Check that all tables have data
6. Verify that the geometry in the dissolved_water_buffers table is valid

## Data Model Improvements

### Typed Water Features Tables

We've improved the water features data model by implementing typed tables:

- Created separate tables for polygon and line geometries
- Added a unifying view for backward compatibility
- Updated documentation to reflect the new model

This change improves type safety, query performance, and makes the data model more explicit.

### Hexagonal Terrain Grid

We've improved the terrain grid model by implementing a hexagonal grid approach:

- Replaced the rectangular grid with a hexagonal grid using ST_HexagonGrid()
- Created a two-table structure with terrain_grid (polygons) and terrain_grid_points (centroids)
- Updated edge creation to work with the new structure
- Added cost calculations based on edge length and speed factors

Benefits of this approach:
- More natural-looking terrain representation
- Equal distances between adjacent cells
- Better adaptation to natural features
- More efficient movement patterns
- More accurate cost modeling

## Conclusion

The EPSG:3857 pipeline has several issues that are preventing it from working correctly. By fixing the parameter naming, parameter substitution, path issues, debugging the empty tables, and improving the data model, we should be able to get the pipeline working correctly.
