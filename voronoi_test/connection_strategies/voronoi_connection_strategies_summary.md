# Voronoi Connection Strategies Comparison

This document provides a comprehensive comparison of different strategies for connecting terrain grid points to water obstacle boundaries in the terrain graph pipeline.

## Introduction

The connection between terrain grid points and water obstacle boundaries is a critical component of the terrain graph pipeline. It determines how vehicles can navigate from the terrain grid to water boundaries and affects the quality of pathfinding around water obstacles.

Four different connection strategies have been implemented and tested:

1. **Nearest Neighbor**
2. **Buffer-Based Voronoi**
3. **True Voronoi**
4. **Reversed Voronoi**

## Strategy Descriptions

### 1. Nearest Neighbor

**Description**: Each terrain point connects to its nearest boundary node.

**Implementation**:
```sql
-- Find the nearest boundary node for each terrain point
SELECT 
    tgp.id AS terrain_point_id,
    (
        SELECT bn.id
        FROM test_boundary_nodes bn
        ORDER BY ST_Distance(tgp.geom, bn.geom)
        LIMIT 1
    ) AS boundary_node_id,
    ST_Distance(tgp.geom, (SELECT geom FROM test_boundary_nodes WHERE id = ...)) AS distance
FROM 
    test_terrain_points tgp
WHERE 
    tgp.hex_type = 'boundary'
    AND ST_Distance(...) <= :max_distance;
```

**Advantages**:
- Simple and intuitive
- Fast execution
- No complex geometry operations

**Disadvantages**:
- Uneven distribution of connections
- Some boundary nodes may receive many connections while others receive none
- May not create the most natural-looking connections

### 2. Buffer-Based Voronoi

**Description**: Creates a "Voronoi-like" partitioning using buffers around boundary nodes.

**Implementation**:
```sql
-- Create buffers around boundary nodes
WITH boundary_node_buffers AS (
    SELECT 
        id,
        geom,
        ST_Buffer(geom, :buffer_distance) AS buffer_geom
    FROM 
        test_boundary_nodes
)
-- Find terrain points that fall within each buffer
SELECT DISTINCT ON (tgp.id)
    tgp.id AS terrain_point_id,
    bnb.id AS boundary_node_id,
    ST_Distance(tgp.geom, bnb.geom) AS distance,
    bnb.buffer_geom AS voronoi_cell
FROM 
    test_terrain_points tgp
JOIN 
    boundary_node_buffers bnb
    ON ST_Intersects(tgp.geom, bnb.buffer_geom)
WHERE 
    tgp.hex_type = 'boundary'
    AND ST_Distance(tgp.geom, bnb.geom) <= :max_distance
ORDER BY
    tgp.id, ST_Distance(tgp.geom, bnb.geom);
```

**Advantages**:
- More even distribution of connections than nearest neighbor
- Robust and reliable
- No complex geometry operations
- Handles overlapping buffers by selecting the closest boundary node

**Disadvantages**:
- Not a true Voronoi diagram
- Buffer size parameter affects the results
- Overlapping buffers can create ambiguity

### 3. True Voronoi

**Description**: Uses PostGIS's `ST_VoronoiPolygons` to create true Voronoi cells for boundary nodes.

**Implementation**:
```sql
-- Create Voronoi diagram for boundary nodes
WITH voronoi_polygons AS (
    SELECT (ST_Dump(ST_VoronoiPolygons(ST_Collect(geom)))).geom AS cell_geom
    FROM test_boundary_nodes
),
-- Associate each Voronoi cell with its boundary node
voronoi_cells AS (
    SELECT 
        bn.id AS boundary_node_id,
        vp.cell_geom
    FROM 
        test_boundary_nodes bn
    JOIN 
        voronoi_polygons vp
        ON ST_Contains(vp.cell_geom, bn.geom)
)
-- Find terrain points that fall within each Voronoi cell
SELECT 
    tgp.id AS terrain_point_id,
    vc.boundary_node_id,
    ST_Distance(tgp.geom, (SELECT geom FROM test_boundary_nodes WHERE id = vc.boundary_node_id)) AS distance,
    vc.cell_geom AS voronoi_cell
FROM 
    test_terrain_points tgp
JOIN 
    voronoi_cells vc
    ON ST_Intersects(tgp.geom, vc.cell_geom)
WHERE 
    tgp.hex_type = 'boundary'
    AND ST_Distance(...) <= :max_distance;
```

**Advantages**:
- Mathematically optimal partitioning
- Even distribution of connections
- Creates natural-looking connections
- No buffer size parameter to tune

**Disadvantages**:
- Can encounter geometry errors with complex water boundaries
- More computationally expensive
- May create very large or small cells depending on boundary node distribution

### 4. Reversed Voronoi

**Description**: Creates Voronoi cells for boundary terrain points instead of boundary nodes.

**Implementation**:
```sql
-- Create Voronoi diagram for boundary terrain points
WITH boundary_terrain_points AS (
    SELECT id, geom
    FROM test_terrain_points
    WHERE hex_type = 'boundary'
),
voronoi_polygons AS (
    SELECT (ST_Dump(ST_VoronoiPolygons(ST_Collect(geom)))).geom AS cell_geom
    FROM boundary_terrain_points
),
-- Associate each Voronoi cell with its terrain point
voronoi_cells AS (
    SELECT 
        btp.id AS terrain_point_id,
        vp.cell_geom
    FROM 
        boundary_terrain_points btp
    JOIN 
        voronoi_polygons vp
        ON ST_Contains(vp.cell_geom, btp.geom)
)
-- Find boundary nodes that fall within each Voronoi cell
SELECT 
    vc.terrain_point_id,
    bn.id AS boundary_node_id,
    ST_Distance(
        (SELECT geom FROM test_terrain_points WHERE id = vc.terrain_point_id),
        bn.geom
    ) AS distance,
    vc.cell_geom AS voronoi_cell
FROM 
    voronoi_cells vc
JOIN 
    test_boundary_nodes bn
    ON ST_Intersects(vc.cell_geom, bn.geom)
WHERE 
    ST_Distance(...) <= :max_distance;
```

**Advantages**:
- Most natural-looking connections
- Better distribution than standard Voronoi approach
- Each terrain point gets a fair share of boundary nodes
- Reduced clustering of connections at boundary nodes

**Disadvantages**:
- Most complex implementation
- Can encounter geometry errors with complex terrain point distributions
- More computationally expensive
- May create multiple connections per terrain point

## Performance Comparison

| Strategy | Connection Count | Avg Connection Length | Execution Time (ms) | Evenness Score |
|----------|------------------|----------------------|---------------------|----------------|
| Nearest Neighbor | Baseline | Baseline | Fastest | Lowest |
| Buffer-Based Voronoi | Similar to Nearest Neighbor | Slightly higher | Fast | Medium |
| True Voronoi | May be lower | May be higher | Medium | High |
| Reversed Voronoi | Highest | May be highest | Slowest | Highest |

*Note: Actual values will depend on the specific dataset and parameters used.*

## Visual Comparison

The visual appearance of the connections differs significantly between strategies:

- **Nearest Neighbor**: Connections tend to cluster around certain boundary nodes, creating a "star" pattern.
- **Buffer-Based Voronoi**: Connections are more evenly distributed, but still show some clustering.
- **True Voronoi**: Connections are evenly distributed, with each boundary node receiving connections from terrain points in its Voronoi cell.
- **Reversed Voronoi**: Connections are most evenly distributed, with each terrain point connecting to boundary nodes in its Voronoi cell.

## Implementation Considerations

### Fallback Mechanisms

Both the True Voronoi and Reversed Voronoi strategies can encounter geometry errors with complex datasets. It's important to implement fallback mechanisms:

```sql
BEGIN
    -- Try the Voronoi approach
    -- ...
EXCEPTION
    WHEN OTHERS THEN
        -- Fall back to a simpler approach
        -- ...
END;
```

### Parameter Tuning

The Buffer-Based Voronoi strategy requires tuning the buffer size parameter:
- Too small: Some terrain points may not fall within any buffer
- Too large: Buffers overlap too much, reducing the "Voronoi-like" effect

### Distance Limiting

All strategies should limit the maximum connection distance to avoid unrealistic long connections:

```sql
WHERE ST_Distance(tgp.geom, bn.geom) <= :max_distance
```

## Recommendations

### For Small Datasets

- **Nearest Neighbor**: Simple and fast, suitable for small datasets with well-distributed boundary nodes.
- **Buffer-Based Voronoi**: Good balance of simplicity and connection distribution.

### For Medium Datasets

- **Buffer-Based Voronoi**: Robust and reliable, with good connection distribution.
- **True Voronoi**: Better connection distribution, but may encounter geometry errors.

### For Large Datasets

- **Buffer-Based Voronoi**: Most reliable for large datasets.
- **Reversed Voronoi**: Best connection distribution, but most complex and may be slower.

### For Production Use

The **Reversed Voronoi** strategy is recommended for production use, with a fallback to **Buffer-Based Voronoi** if geometry errors are encountered. This provides the best connection distribution while ensuring robustness.

## Conclusion

The choice of connection strategy depends on the specific requirements of the terrain graph pipeline:

- If simplicity and performance are priorities, use **Nearest Neighbor** or **Buffer-Based Voronoi**.
- If connection distribution is a priority, use **True Voronoi** or **Reversed Voronoi**.
- If robustness is a priority, use **Buffer-Based Voronoi** with a fallback mechanism.

The **Reversed Voronoi** strategy provides the best overall results, with the most natural-looking connections and the best distribution. However, it is also the most complex to implement and may be slower than other strategies.
