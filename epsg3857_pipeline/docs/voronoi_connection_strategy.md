# Voronoi Connection Strategy

## Overview

The Voronoi Connection Strategy is an advanced approach for connecting terrain grid points to water obstacle boundaries. It uses Voronoi diagrams to create more natural and evenly distributed connections between terrain and water obstacles, ensuring better coverage and more intuitive navigation.

## Key Concepts

### Voronoi Diagrams

A Voronoi diagram partitions a plane into regions based on distance to a specified set of points. For each point, there is a corresponding region consisting of all points closer to that point than to any other. In our context:

- The points are the water boundary nodes
- The regions (Voronoi cells) determine which terrain grid points connect to which boundary nodes

### Benefits Over Other Connection Strategies

1. **Even Distribution**: Prevents clustering of connections to certain boundary nodes
2. **Natural Partitioning**: Creates a more intuitive division of space around water obstacles
3. **Optimal Coverage**: Ensures all parts of the water boundary are accessible
4. **Reduced Redundancy**: Minimizes unnecessary connections while maintaining connectivity

## Implementation Details

### 1. Boundary Node Creation

First, boundary nodes are created along the perimeter of water obstacles at regular intervals:

```sql
-- Create boundary nodes along water obstacle boundaries
INSERT INTO obstacle_boundary_nodes (node_id, geom)
SELECT 
    ROW_NUMBER() OVER () AS node_id,
    ST_PointN(ST_Boundary(geom), generate_series(1, ST_NPoints(ST_Boundary(geom))))
FROM 
    water_obstacles;
```

### 2. Voronoi Cell Generation

Voronoi cells are generated for each boundary node:

```sql
-- Generate Voronoi cells for boundary nodes
CREATE TABLE voronoi_cells AS
SELECT 
    obn.node_id,
    ST_VoronoiPolygon(ST_Collect(obn.geom), :voronoi_buffer_distance) AS cell_geom
FROM 
    obstacle_boundary_nodes obn
GROUP BY 
    obn.node_id;
```

### 3. Cell Clipping

The Voronoi cells are clipped to exclude water areas and limited to a maximum distance from the boundary node:

```sql
-- Clip Voronoi cells to exclude water areas and limit distance
UPDATE voronoi_cells
SET cell_geom = ST_Difference(
    ST_Intersection(
        cell_geom,
        ST_Buffer(
            (SELECT geom FROM obstacle_boundary_nodes WHERE node_id = voronoi_cells.node_id),
            :voronoi_max_distance
        )
    ),
    (SELECT ST_Union(geom) FROM water_obstacles)
);
```

### 4. Connection Assignment

Terrain grid points are assigned to boundary nodes based on which Voronoi cell they fall within:

```sql
-- Create connections between terrain grid points and boundary nodes
INSERT INTO obstacle_boundary_connection_edges (edge_id, source_id, target_id, geom, cost)
SELECT 
    ROW_NUMBER() OVER () AS edge_id,
    tgp.point_id AS source_id,
    vc.node_id AS target_id,
    ST_MakeLine(tgp.geom, obn.geom) AS geom,
    ST_Length(ST_MakeLine(tgp.geom, obn.geom)) AS cost
FROM 
    terrain_grid_points tgp
JOIN 
    voronoi_cells vc ON ST_Contains(vc.cell_geom, tgp.geom)
JOIN 
    obstacle_boundary_nodes obn ON vc.node_id = obn.node_id
WHERE 
    tgp.hex_type = 'land' OR tgp.hex_type = 'boundary'
LIMIT 
    :voronoi_connection_limit PER (tgp.point_id);
```

## Configuration Parameters

The Voronoi connection strategy can be configured with the following parameters:

| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `voronoi_buffer_distance` | Distance to buffer the Voronoi diagram | 500 meters |
| `voronoi_max_distance` | Maximum distance for connections | 1000 meters |
| `voronoi_connection_limit` | Maximum connections per terrain point | 2 |
| `voronoi_tolerance` | Tolerance for geometric operations | 10 meters |

These parameters can be adjusted in the `voronoi_obstacle_boundary_config.json` configuration file.

## Visualization

The Voronoi connection strategy can be visualized using the `visualize_voronoi_obstacle_boundary.py` script:

```bash
python epsg3857_pipeline/core/scripts/visualize_voronoi_obstacle_boundary.py --show-voronoi
```

This will display:
- Terrain grid points (classified as land, boundary, or water)
- Water obstacles
- Boundary nodes
- Boundary edges
- Connection edges
- Voronoi cells (when `--show-voronoi` is specified)

## Integration with the Pipeline

The Voronoi connection strategy is integrated into the Voronoi Obstacle Boundary Pipeline, which can be run with:

```bash
python epsg3857_pipeline/run_voronoi_obstacle_boundary_pipeline.py
```

This pipeline:
1. Creates a hexagonal terrain grid
2. Extracts water obstacles
3. Creates boundary nodes along water obstacles
4. Generates Voronoi cells for boundary nodes
5. Connects terrain grid points to boundary nodes using Voronoi partitioning
6. Creates a unified graph for navigation

## Comparison with Other Strategies

| Strategy | Pros | Cons |
|----------|------|------|
| **Line-to-Point** | Simple implementation, direct connections | Can cluster connections to certain boundary nodes |
| **Hexagon Boundary** | Good for regular grid representation | Less precise for irregular water boundaries |
| **Voronoi** | Even distribution, natural partitioning | More complex implementation, higher computational cost |

## Future Improvements

1. **Dynamic Cell Sizing**: Adjust Voronoi cell size based on boundary curvature
2. **Weighted Voronoi Diagrams**: Use weighted Voronoi diagrams to account for terrain features
3. **Multi-level Voronoi**: Implement hierarchical Voronoi diagrams for different scales
4. **Adaptive Connection Limits**: Vary connection limits based on terrain characteristics

## References

1. Aurenhammer, F. (1991). "Voronoi diagrams—a survey of a fundamental geometric data structure". ACM Computing Surveys, 23(3), 345–405.
2. PostGIS Documentation: [ST_VoronoiPolygon](https://postgis.net/docs/ST_VoronoiPolygon.html)
3. de Berg, M., Cheong, O., van Kreveld, M., & Overmars, M. (2008). "Computational Geometry: Algorithms and Applications". Springer-Verlag.
