# Line-to-Point Connection Strategy

## Overview

The Line-to-Point Connection Strategy is an enhancement to the Hexagon Obstacle Boundary approach that improves how terrain nodes connect to water obstacle boundaries. Instead of connecting terrain nodes to pre-existing boundary nodes, this approach connects each terrain node to the closest point on the water obstacle boundary line itself.

## Problem Statement

In the original implementation, connections were made between terrain nodes and pre-existing boundary nodes based solely on point-to-point distance. This approach had several limitations:

1. **Suboptimal Connections**: Terrain nodes might not connect to the most relevant part of the water boundary
2. **Redundant Connections**: Multiple terrain nodes might connect to the same boundary node, creating redundant paths
3. **Uneven Distribution**: Connections were not evenly distributed along the water boundary
4. **White Space Issues**: Large gaps could exist between the terrain grid and water obstacles

## Solution

The Line-to-Point Connection Strategy addresses these issues by:

1. Finding the closest point on each water obstacle boundary for each boundary terrain node
2. Either connecting to an existing boundary node near that point or creating a new node
3. Creating more direct and meaningful connections to the actual boundary

## Implementation Details

### Key Components

1. **Closest Point Calculation**: For each boundary terrain node, we find the closest point on each nearby water obstacle using `ST_ClosestPoint`
2. **Node Reuse or Creation**: We either reuse an existing boundary node (if one exists within a tolerance) or create a new one
3. **Connection Creation**: We create a direct connection from the terrain node to the closest point on the boundary

### SQL Implementation

```sql
-- Connect terrain grid points to the closest point on water obstacles
-- Only connect boundary hexagons to water obstacles
-- This uses the line-to-point approach for more direct connections
INSERT INTO obstacle_boundary_connection_edges (terrain_node_id, boundary_node_id, water_obstacle_id, length, geom)
WITH closest_boundary_points AS (
    -- For each boundary terrain point, find the closest point on each water obstacle
    SELECT 
        tgp.id AS terrain_node_id,
        wo.id AS water_obstacle_id,
        ST_ClosestPoint(wo.geom, tgp.geom) AS closest_point,
        ST_Distance(tgp.geom, wo.geom) AS distance,
        -- Rank connections by distance for each terrain point
        ROW_NUMBER() OVER (PARTITION BY tgp.id ORDER BY ST_Distance(tgp.geom, wo.geom)) AS terrain_rank
    FROM 
        terrain_grid_points tgp
    CROSS JOIN 
        water_obstacles wo
    WHERE 
        -- Only connect boundary hexagons
        tgp.hex_type = 'boundary'
        -- Only consider water obstacles within the maximum connection distance
        AND ST_DWithin(tgp.geom, wo.geom, :max_connection_distance)
        -- Ensure the connection line doesn't cross through the water obstacle
        AND NOT EXISTS (
            SELECT 1
            FROM water_obstacles wo2
            WHERE wo2.id = wo.id
            AND ST_Crosses(ST_MakeLine(tgp.geom, ST_ClosestPoint(wo.geom, tgp.geom)), wo2.geom)
        )
),
-- Find the nearest existing boundary node to each closest point or prepare to create new ones
boundary_node_mapping AS (
    SELECT 
        cbp.terrain_node_id,
        cbp.water_obstacle_id,
        cbp.closest_point,
        cbp.distance,
        -- Find the nearest existing boundary node within a tolerance
        (
            SELECT node_id 
            FROM obstacle_boundary_nodes 
            WHERE water_obstacle_id = cbp.water_obstacle_id 
            AND ST_DWithin(geom, cbp.closest_point, :node_tolerance)
            ORDER BY ST_Distance(geom, cbp.closest_point) 
            LIMIT 1
        ) AS nearest_node_id,
        -- Generate a new node ID if we'll need to create a new node
        CASE 
            WHEN NOT EXISTS (
                SELECT 1 
                FROM obstacle_boundary_nodes 
                WHERE water_obstacle_id = cbp.water_obstacle_id 
                AND ST_DWithin(geom, cbp.closest_point, :node_tolerance)
            ) 
            THEN nextval('obstacle_boundary_nodes_node_id_seq')
            ELSE NULL
        END AS new_node_id
    FROM 
        closest_boundary_points cbp
    WHERE 
        -- Limit the number of connections per terrain point
        terrain_rank <= :max_connections_per_terrain_point
)
-- Create the connection edges
SELECT 
    bnm.terrain_node_id,
    COALESCE(bnm.nearest_node_id, bnm.new_node_id) AS boundary_node_id,
    bnm.water_obstacle_id,
    bnm.distance AS length,
    ST_MakeLine(
        (SELECT geom FROM terrain_grid_points WHERE id = bnm.terrain_node_id),
        bnm.closest_point
    ) AS geom
FROM 
    boundary_node_mapping bnm;

-- Insert new boundary nodes for the closest points that don't have nearby existing nodes
INSERT INTO obstacle_boundary_nodes (node_id, water_obstacle_id, point_order, geom)
SELECT 
    bnm.new_node_id,
    bnm.water_obstacle_id,
    (SELECT COALESCE(MAX(point_order), 0) + 1 FROM obstacle_boundary_nodes WHERE water_obstacle_id = bnm.water_obstacle_id),
    bnm.closest_point
FROM 
    boundary_node_mapping bnm
WHERE 
    bnm.nearest_node_id IS NULL
    AND bnm.new_node_id IS NOT NULL;
```

## Configuration Parameters

The Line-to-Point Connection Strategy introduces a new configuration parameter:

- `node_tolerance`: The distance tolerance (in meters) for finding existing boundary nodes. If a boundary node exists within this distance of the closest point, it will be reused instead of creating a new node.

This parameter can be configured in the `hexagon_obstacle_boundary_config.json` file:

```json
"obstacle_boundary": {
  "boundary_node_spacing": 100,
  "boundary_edge_max_length": 200,
  "connection_distance": 1000,
  "max_connections_per_boundary_node": 5,
  "max_connections_per_terrain_point": 2,
  "node_tolerance": 10
}
```

## Benefits

1. **More Direct Connections**: Each boundary terrain node connects to the closest point on the water obstacle boundary, not just to the closest pre-existing boundary node.

2. **Better Distribution**: Connections are more evenly distributed along the water boundary.

3. **Reduced Redundancy**: Fewer redundant connections, as each terrain node connects to the most relevant part of the boundary.

4. **Improved Navigation**: More natural paths for navigation between terrain and water boundaries.

5. **Reduced White Space**: Better connectivity across the "white space" between terrain grid and water obstacles.

## Visualization

The existing visualization tools (`visualize_hexagon_obstacle_boundary.py` and `visualize_hexagon_obstacle_boundary_components.py`) can be used to visualize the results of the Line-to-Point Connection Strategy. The connections will appear as green dotted lines between terrain nodes and boundary nodes.

## Usage

To use the Line-to-Point Connection Strategy, simply run the hexagon obstacle boundary pipeline as usual:

```bash
python epsg3857_pipeline/run_hexagon_obstacle_boundary_pipeline.py --verbose --visualize
```

The pipeline will automatically use the Line-to-Point Connection Strategy for creating connections between terrain nodes and water obstacle boundaries.
