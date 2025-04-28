# Reversed Voronoi Connection Strategy

## Overview

The Reversed Voronoi Connection Strategy is an innovative approach for connecting terrain grid points to water obstacle boundaries. Unlike the standard Voronoi approach which creates Voronoi cells for boundary nodes, this "reversed" approach creates Voronoi cells for boundary terrain points, resulting in more natural connections and better distribution of connections across water boundaries.

## Problem Statement

In the original Voronoi Connection Strategy, we created Voronoi cells for boundary nodes along water obstacles. While this approach improved connection distribution compared to simple nearest-neighbor approaches, it still had some limitations:

1. **Uneven Distribution**: Some boundary nodes might receive too many connections while others receive none
2. **Suboptimal Terrain Coverage**: The Voronoi cells might not optimally cover the terrain points that need connections
3. **Geometry Errors**: The Voronoi diagram generation could encounter geometry errors with complex water boundaries
4. **Performance Issues**: Generating Voronoi diagrams for a large number of boundary nodes could be computationally expensive

## Solution: Reversed Voronoi Approach

The Reversed Voronoi Connection Strategy addresses these issues by:

1. Creating Voronoi cells for boundary terrain points instead of boundary nodes
2. Assigning boundary nodes to the Voronoi cell of the nearest boundary terrain point
3. Creating connections between each boundary terrain point and the boundary nodes within its Voronoi cell

This approach effectively "reverses" the assignment direction, letting terrain points "claim" boundary nodes rather than boundary nodes "claiming" terrain points.

## Implementation Details

### Key Components

1. **Boundary Terrain Point Identification**: Identify terrain grid points that are near water boundaries (classified as 'boundary' in the hexagonal grid)
2. **Voronoi Cell Generation**: Generate Voronoi cells for these boundary terrain points
3. **Boundary Node Assignment**: Assign boundary nodes to the Voronoi cell they fall within
4. **Connection Creation**: Create connections between each boundary terrain point and the boundary nodes assigned to its Voronoi cell

### SQL Implementation

```sql
-- Step 1: Identify boundary terrain points
DROP TABLE IF EXISTS boundary_terrain_points;
CREATE TABLE boundary_terrain_points AS
SELECT 
    id,
    geom
FROM 
    terrain_grid_points
WHERE 
    hex_type = 'boundary';

-- Step 2: Generate Voronoi diagram for boundary terrain points
DROP TABLE IF EXISTS voronoi_cells;
CREATE TABLE voronoi_cells (
    terrain_point_id INTEGER PRIMARY KEY,
    cell_geom GEOMETRY(POLYGON, :storage_srid)
);

-- Use ST_VoronoiPolygons to create Voronoi cells for boundary terrain points
INSERT INTO voronoi_cells (terrain_point_id, cell_geom)
WITH voronoi_polygons AS (
    SELECT ST_VoronoiPolygons(ST_Collect(geom)) AS geom
    FROM boundary_terrain_points
),
voronoi_dump AS (
    SELECT (ST_Dump(geom)).geom AS cell_geom
    FROM voronoi_polygons
)
SELECT 
    btp.id AS terrain_point_id,
    vd.cell_geom
FROM 
    voronoi_dump vd
JOIN 
    boundary_terrain_points btp
    ON ST_Contains(vd.cell_geom, btp.geom);

-- Step 3: Find boundary nodes that fall within each Voronoi cell
INSERT INTO obstacle_boundary_connection_edges (source_id, target_id, geom, cost)
SELECT 
    vc.terrain_point_id AS source_id,
    obn.node_id AS target_id,
    ST_MakeLine(
        (SELECT geom FROM boundary_terrain_points WHERE id = vc.terrain_point_id),
        obn.geom
    ) AS geom,
    ST_Distance(
        (SELECT geom FROM boundary_terrain_points WHERE id = vc.terrain_point_id),
        obn.geom
    ) AS cost
FROM 
    voronoi_cells vc
JOIN 
    obstacle_boundary_nodes obn ON ST_Intersects(vc.cell_geom, obn.geom)
WHERE 
    -- Ensure the connection doesn't cross through water obstacles
    NOT EXISTS (
        SELECT 1
        FROM water_obstacles wo
        WHERE ST_Crosses(
            ST_MakeLine(
                (SELECT geom FROM boundary_terrain_points WHERE id = vc.terrain_point_id),
                obn.geom
            ),
            wo.geom
        )
    )
    -- Limit the distance
    AND ST_Distance(
        (SELECT geom FROM boundary_terrain_points WHERE id = vc.terrain_point_id),
        obn.geom
    ) <= :voronoi_max_distance;
```

## Robust Implementation

The implementation includes several robustness features:

1. **Chunked Processing**: Process points in chunks to avoid memory issues with large datasets
2. **Fallback Mechanism**: If Voronoi diagram generation fails, fall back to a buffer-based approach
3. **Water Area Exclusion**: Exclude water areas from Voronoi cells to ensure connections don't cross water obstacles
4. **Distance Limiting**: Limit connections to a maximum distance to avoid unrealistic long connections
5. **Validation Checks**: Validate geometries and remove invalid ones to ensure robust processing

## Configuration Parameters

The Reversed Voronoi Connection Strategy uses the following configuration parameters:

- `voronoi_buffer_distance`: Buffer distance for the fallback approach (default: 200m)
- `voronoi_max_distance`: Maximum connection distance (default: 500m)
- `voronoi_connection_limit`: Maximum number of connections per terrain point (default: 1)
- `voronoi_tolerance`: Tolerance for geometry operations (default: 10m)

These parameters can be configured in the `voronoi_obstacle_boundary_config.json` file:

```json
"voronoi_connection": {
  "voronoi_buffer_distance": 200,
  "voronoi_max_distance": 500,
  "voronoi_connection_limit": 1,
  "voronoi_tolerance": 10
}
```

## Benefits

1. **More Natural Connections**: The reversed approach creates more natural connections between terrain and water boundaries.

2. **Better Distribution**: Connections are more evenly distributed across water boundaries, with each boundary terrain point getting a fair share of connections.

3. **Improved Robustness**: The chunked processing and fallback mechanisms make the approach more robust to complex geometries and large datasets.

4. **Better Performance**: Processing boundary terrain points (which are typically fewer than boundary nodes) can be more efficient.

5. **Reduced Geometry Errors**: The approach is less prone to geometry errors that can occur with complex water boundaries.

## Comparison with Standard Voronoi Approach

| Feature | Standard Voronoi Approach | Reversed Voronoi Approach |
|---------|---------------------------|---------------------------|
| **Voronoi Cells For** | Boundary Nodes | Boundary Terrain Points |
| **Assignment Direction** | Boundary Nodes → Terrain Points | Terrain Points → Boundary Nodes |
| **Connection Distribution** | Good | Better |
| **Robustness** | Good | Better |
| **Performance** | Good | Better for complex boundaries |
| **Natural Appearance** | Good | Better |

## Visualization

The existing visualization tools (`visualize_voronoi_obstacle_boundary.py`) can be used to visualize the results of the Reversed Voronoi Connection Strategy. The connections will appear as green lines between terrain points and boundary nodes, and the Voronoi cells can be displayed as transparent polygons if the `--show-voronoi` flag is used.

## Usage

To use the Reversed Voronoi Connection Strategy, run the reversed Voronoi obstacle boundary pipeline:

```bash
python epsg3857_pipeline/run_reversed_voronoi_obstacle_boundary_pipeline.py --verbose --visualize --show-voronoi
```

The pipeline will automatically use the Reversed Voronoi Connection Strategy for creating connections between terrain points and water obstacle boundaries.

## Future Improvements

1. **Adaptive Cell Sizing**: Adjust Voronoi cell sizes based on terrain complexity and boundary node density
2. **Multi-level Voronoi Diagrams**: Use hierarchical Voronoi diagrams for better coverage of complex boundaries
3. **Dynamic Connection Limits**: Adjust the number of connections per terrain point based on local geometry
4. **Integration with Environmental Conditions**: Consider environmental conditions when creating connections
5. **Parallel Processing**: Implement parallel processing for large datasets

## Conclusion

The Reversed Voronoi Connection Strategy represents a significant improvement over the standard Voronoi approach, providing more natural connections, better distribution, and improved robustness. By creating Voronoi cells for boundary terrain points instead of boundary nodes, it effectively "reverses" the assignment direction, resulting in a more intuitive and effective connection strategy.
