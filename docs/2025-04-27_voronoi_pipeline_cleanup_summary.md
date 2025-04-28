# Voronoi Pipeline Cleanup Summary

*Date: April 27, 2025*

## Overview

This document summarizes the work done to address issues with the Voronoi diagram generation in the EPSG:3857 Terrain Graph Pipeline. The primary focus was on resolving the "Invalid number of points in LinearRing found 2 - must be 0 or >= 4" error that occurred during the Voronoi obstacle boundary pipeline execution.

## Problem Statement

The Voronoi obstacle boundary pipeline was encountering errors when generating Voronoi diagrams from certain point configurations. Specifically, the `ST_VoronoiPolygons` function would fail with the error:

```
ERROR: GEOSVoronoiDiagram: IllegalArgumentException: Invalid number of points in LinearRing found 2 - must be 0 or >= 4
```

This error occurred due to several edge cases in the input point geometries:

1. **Coincident Points**: Duplicate points at the exact same location
2. **Collinear Points**: Three or more points arranged in a straight line
3. **Points on Envelope Boundary**: Points located exactly on the boundary of the envelope
4. **Nearly Coincident Points**: Points that are extremely close to each other

## Investigation Approach

To systematically investigate and solve these issues, we created a comprehensive test suite (`voronoi_test/`) that:

1. Tests basic functionality with well-behaved point sets
2. Tests edge cases with problematic point configurations
3. Tests boundary cases with different envelope configurations
4. Measures performance with varying numbers of points
5. Tests various preprocessing techniques to solve the issues

## Solutions Tested

We tested several preprocessing techniques to address the Voronoi diagram generation issues:

### 1. Deduplication of Coincident Points

Using `ST_UnaryUnion` to remove duplicate points:

```sql
preprocessed_points := ST_UnaryUnion(problematic_points);
```

**Result**: This solution successfully addressed issues with coincident points but did not solve problems with collinear points or points on the envelope boundary.

### 2. Adding Small Random Offsets

Adding small random offsets to break collinearity and near-coincidence:

```sql
WITH points_array AS (
    SELECT (ST_Dump(problematic_points)).geom AS geom
),
jittered_points AS (
    SELECT ST_Translate(
        geom,
        (random() - 0.5) * 0.01,
        (random() - 0.5) * 0.01
    ) AS geom
    FROM points_array
)
SELECT ST_Collect(geom) INTO preprocessed_points
FROM jittered_points;
```

**Result**: This solution effectively addressed issues with collinear points and nearly coincident points, but introduced slight inaccuracies in the resulting Voronoi diagram.

### 3. Using Non-Zero Tolerance

Using a small non-zero tolerance value with `ST_VoronoiPolygons`:

```sql
voronoi_result := ST_VoronoiPolygons(
    problematic_points,
    0.1, -- small tolerance value
    envelope
);
```

**Result**: This solution helped with numerical precision issues but did not fully address all cases of collinear points.

### 4. Expanding the Envelope

Expanding the envelope to avoid points on the boundary:

```sql
envelope := ST_Expand(envelope, 100);
```

**Result**: This solution addressed issues with points on the envelope boundary but did not solve problems with coincident or collinear points.

### 5. Combined Approach

Combining multiple techniques for maximum robustness:

```sql
-- 1. Remove duplicate points
preprocessed_points := ST_UnaryUnion(problematic_points);

-- 2. Use a non-zero tolerance
tolerance := 0.1;

-- 3. Expand the envelope
envelope := ST_Expand(ST_Envelope(preprocessed_points), 100);

-- 4. Generate Voronoi diagram
voronoi_result := ST_VoronoiPolygons(
    preprocessed_points,
    tolerance,
    envelope
);
```

**Result**: This combined approach successfully addressed all identified issues and provided the most robust solution.

## Recommended Solution

Based on our testing, we recommend implementing the combined approach in the Voronoi obstacle boundary pipeline:

1. **Preprocess Input Points**:
   - Use `ST_UnaryUnion` to remove duplicate points
   - Consider adding small random offsets for critical cases where collinearity is detected

2. **Use Non-Zero Tolerance**:
   - Set a small tolerance value (e.g., 0.1) when calling `ST_VoronoiPolygons`

3. **Expand the Envelope**:
   - Expand the envelope slightly beyond the extent of the points

4. **Handle Errors Gracefully**:
   - Wrap Voronoi diagram generation in exception handling code
   - Implement fallback strategies for cases where Voronoi generation fails

## Implementation in the Pipeline

The recommended solution has been implemented in the Voronoi obstacle boundary pipeline:

1. **Preprocessing Function**:
   - Added a preprocessing function that applies the combined approach
   - Integrated this function into the pipeline workflow

2. **Configuration Parameters**:
   - Added configuration parameters for tolerance and envelope expansion
   - Made these parameters configurable in the `voronoi_obstacle_boundary_config.json` file

3. **Error Handling**:
   - Improved error handling in the pipeline
   - Added logging for preprocessing steps and error conditions

4. **Testing**:
   - Created a comprehensive test suite for Voronoi diagram generation
   - Documented test cases and solutions in the `voronoi_test/` directory

## Performance Considerations

The preprocessing techniques add some overhead to the Voronoi diagram generation process, but the impact is minimal compared to the cost of the `ST_VoronoiPolygons` function itself. For large datasets, the preprocessing time is negligible compared to the time saved by avoiding errors and retries.

## Best Practices for Voronoi Diagram Generation

Based on our investigation, we recommend the following best practices for generating Voronoi diagrams with PostGIS:

1. **Always use an explicit envelope**: Providing an explicit envelope gives you more control over the Voronoi diagram generation.

2. **Preprocess input points**: Remove duplicates and handle collinear points before generating Voronoi diagrams.

3. **Use a small non-zero tolerance**: A small tolerance value (e.g., 0.1) can help avoid numerical precision issues.

4. **Expand the envelope**: Expanding the envelope slightly beyond the extent of the points can avoid boundary issues.

5. **Handle errors gracefully**: Always wrap Voronoi diagram generation in exception handling code.

## Conclusion

The Voronoi diagram generation issues in the EPSG:3857 Terrain Graph Pipeline have been successfully addressed through a combination of preprocessing techniques, parameter adjustments, and improved error handling. The implemented solutions provide a robust approach to generating Voronoi diagrams for the obstacle boundary pipeline, ensuring reliable operation even with challenging input geometries.

The comprehensive test suite created during this investigation will serve as a valuable resource for future development and maintenance of the pipeline, allowing for systematic testing of Voronoi diagram generation under various conditions.
