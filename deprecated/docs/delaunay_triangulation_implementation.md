# Delaunay Triangulation Implementation for Terrain Grid

**Date:** April 21, 2025  
**Author:** Cline  
**Project:** Terrain System - Geo-Graph  

## Overview

This document describes the implementation of Delaunay triangulation for terrain grid generation in the geo-graph terrain system. This approach represents a significant improvement over the regular grid-based approach previously used, providing more natural terrain representation and better adaptation to irregular water boundaries.

## What is Delaunay Triangulation?

Delaunay triangulation is a geometric algorithm that creates a triangulation (a mesh of triangles) from a set of points such that no point is inside the circumcircle of any triangle in the triangulation. This property ensures that the triangulation maximizes the minimum angle of all triangles, avoiding skinny triangles.

In our terrain system context, Delaunay triangulation provides several advantages:

1. **Adaptive mesh density**: The triangulation naturally adapts to the density of input points
2. **Better representation of irregular boundaries**: The triangulation follows the contours of water features more naturally
3. **Optimal connectivity**: The triangulation creates an optimal set of connections between points
4. **Reduced edge count**: While maintaining good connectivity, the triangulation often requires fewer edges than a regular grid

## Implementation Details

### 1. Point Generation

The implementation starts by generating a set of points that will form the vertices of the triangulation:

- A regular grid of points covering the extent of the data (similar to the previous approach)
- Additional points along water buffer boundaries to ensure better edge representation around water features
- Filtering out points that intersect with water buffers

```sql
-- First, create a temporary table with a regular grid of points
CREATE TEMP TABLE temp_grid_points AS
WITH 
-- Create a regular grid of points covering the extent of the data
-- Using EPSG:3857 for consistent meter-based operations
grid_extent AS (
    SELECT ST_Extent(geom) AS extent
    FROM water_buf_dissolved
),
grid_points AS (
    SELECT 
        ST_SetSRID(
            ST_MakePoint(
                ST_XMin(extent) + (x * 200),
                ST_YMin(extent) + (y * 200)
            ),
            3857
        ) AS geom
    FROM grid_extent,
         generate_series(0, ceil((ST_XMax(extent) - ST_XMin(extent)) / 200)::integer) AS x,
         generate_series(0, ceil((ST_YMax(extent) - ST_YMin(extent)) / 200)::integer) AS y
)
-- Filter out points that intersect with water buffers
SELECT gp.geom
FROM grid_points gp
WHERE NOT EXISTS (
    SELECT 1 
    FROM water_buf_dissolved wb
    WHERE ST_Intersects(gp.geom, wb.geom)
);

-- Add points along water buffer boundaries for better edge representation
INSERT INTO temp_grid_points
WITH boundary_points AS (
    SELECT 
        geom,
        ST_Boundary(geom) AS boundary,
        ST_NPoints(ST_Boundary(geom)) AS num_points,
        ST_Length(ST_Boundary(geom)) AS boundary_length,
        -- Calculate step size (approximately every 100 meters)
        GREATEST(1, ST_NPoints(ST_Boundary(geom)) / GREATEST(1, ST_Length(ST_Boundary(geom)) / 100)) AS step
    FROM water_buf_dissolved
)
SELECT 
    ST_PointN(boundary, n) AS geom
FROM boundary_points,
     generate_series(1, num_points, step::integer) AS n;
```

### 2. Triangulation

Once the points are generated, we create the Delaunay triangulation using PostGIS's `ST_DelaunayTriangles` function:

```sql
-- Create the Delaunay triangulation
CREATE TABLE terrain_triangulation AS
SELECT 
    (ST_Dump(ST_DelaunayTriangles(ST_Collect(geom), 0.001, 0))).geom AS geom
FROM unique_grid_points;
```

The `ST_DelaunayTriangles` function takes three parameters:
- The collection of points to triangulate
- A tolerance value (0.001) for removing duplicate points
- A flag (0) indicating that we want to return triangles rather than a TIN

### 3. Terrain Grid Generation

From the triangulation, we create the terrain grid by taking the centroids of the triangles:

```sql
-- Create terrain grid from triangulation centroids
CREATE TABLE terrain_grid AS
SELECT 
    ROW_NUMBER() OVER () AS id,
    ST_Centroid(geom) AS geom,
    1.0 AS cost -- Placeholder for slope-based cost
FROM terrain_triangulation
WHERE NOT EXISTS (
    SELECT 1 
    FROM water_buf_dissolved wb
    WHERE ST_Intersects(ST_Centroid(terrain_triangulation.geom), wb.geom)
);
```

### 4. Edge Extraction

The edges of the triangulation form the basis for the terrain edges:

```sql
-- Extract edges from the Delaunay triangulation
CREATE TABLE terrain_edges AS
WITH 
-- Extract the boundary of each triangle
triangle_boundaries AS (
    SELECT 
        id,
        ST_ExteriorRing(geom) AS boundary
    FROM (
        SELECT 
            ROW_NUMBER() OVER () AS id,
            geom
        FROM terrain_triangulation
    ) AS triangles
),
-- Extract individual edges from triangle boundaries
triangle_edges AS (
    SELECT 
        id,
        ST_MakeLine(
            ST_PointN(boundary, n),
            ST_PointN(boundary, CASE WHEN n = ST_NPoints(boundary) - 1 THEN 1 ELSE n + 1 END)
        ) AS geom
    FROM triangle_boundaries,
         generate_series(1, 3) AS n
),
-- Deduplicate edges (each edge appears in two triangles)
unique_edges AS (
    SELECT DISTINCT ON (
        LEAST(ST_X(ST_StartPoint(geom)), ST_X(ST_EndPoint(geom))),
        LEAST(ST_Y(ST_StartPoint(geom)), ST_Y(ST_EndPoint(geom))),
        GREATEST(ST_X(ST_StartPoint(geom)), ST_X(ST_EndPoint(geom))),
        GREATEST(ST_Y(ST_StartPoint(geom)), ST_Y(ST_EndPoint(geom)))
    )
        geom
    FROM triangle_edges
),
-- Filter out edges that cross water buffers
valid_edges AS (
    SELECT 
        geom,
        ST_Length(geom) AS length_m
    FROM unique_edges
    WHERE NOT EXISTS (
        SELECT 1 
        FROM water_buf_dissolved wb
        WHERE ST_Intersects(unique_edges.geom, wb.geom)
    )
),
-- Find the nearest terrain grid points to the start and end of each edge
edge_endpoints AS (
    SELECT 
        ve.geom,
        ve.length_m,
        (SELECT tg.id FROM terrain_grid tg ORDER BY ST_StartPoint(ve.geom) <-> tg.geom LIMIT 1) AS source_id,
        (SELECT tg.id FROM terrain_grid tg ORDER BY ST_EndPoint(ve.geom) <-> tg.geom LIMIT 1) AS target_id
    FROM valid_edges ve
)
-- Create the final terrain edges table
SELECT 
    ROW_NUMBER() OVER () AS id,
    source_id,
    target_id,
    NULL::bigint AS source, -- Will be populated by pgr_createTopology
    NULL::bigint AS target, -- Will be populated by pgr_createTopology
    -- Calculate cost based on length
    CASE 
        WHEN length_m <= 0 THEN 0.1 -- Avoid zero costs
        ELSE length_m / 100.0 -- Scale down for reasonable costs
    END AS cost,
    length_m,
    geom
FROM edge_endpoints
-- Ensure source_id and target_id are valid and different
WHERE 
    source_id IS NOT NULL AND 
    target_id IS NOT NULL AND 
    source_id != target_id;
```

## Benefits of the Delaunay Approach

### 1. More Natural Terrain Representation

The Delaunay triangulation creates a more natural representation of the terrain compared to a regular grid. The triangulation adapts to the density of input points, creating smaller triangles in areas with more detail and larger triangles in areas with less detail.

### 2. Better Adaptation to Irregular Water Boundaries

By adding points along water buffer boundaries, the triangulation follows the contours of water features more naturally. This results in a more accurate representation of the terrain around water features, which is critical for routing applications.

### 3. Optimal Connectivity

The Delaunay triangulation creates an optimal set of connections between points, ensuring good connectivity while minimizing the number of edges. This results in more efficient routing and better performance.

### 4. Improved Edge Quality

The edges extracted from the triangulation have several desirable properties:
- They connect points that are naturally related (part of the same triangle)
- They avoid crossing water features
- They provide good coverage of the terrain

### 5. Consistent CRS Usage

The implementation uses EPSG:3857 (Web Mercator) for all operations, ensuring consistent metric-based measurements. This is particularly important for calculating edge lengths and costs.

## Performance Considerations

The Delaunay triangulation approach can be more computationally expensive than a regular grid approach, especially for large datasets. However, the benefits in terms of terrain representation and routing quality generally outweigh the performance cost.

To optimize performance:
- The implementation filters out points that intersect with water buffers before triangulation
- The triangulation uses a tolerance value to remove duplicate points
- The edge extraction process deduplicates edges that appear in multiple triangles

## Future Improvements

Several potential improvements could be made to the Delaunay triangulation implementation:

1. **Triangulation Quality Metrics**: Add quality metrics for the triangulation, such as minimum angle statistics
2. **Spatial Partitioning**: For large datasets, implement spatial partitioning to process the triangulation in chunks
3. **Edge Cost Refinement**: Incorporate terrain slope or other environmental factors into edge cost calculation
4. **Visualization**: Create specific visualization tools for the Delaunay triangulation
5. **Parameter Tuning**: Experiment with different point densities and triangulation parameters

## Conclusion

The Delaunay triangulation approach represents a significant improvement over the regular grid-based approach for terrain grid generation. It provides more natural terrain representation, better adaptation to irregular water boundaries, and optimal connectivity, resulting in more accurate and efficient routing.

By combining the Delaunay triangulation with consistent CRS usage (EPSG:3857), the implementation ensures accurate and consistent spatial operations throughout the terrain system pipeline.
