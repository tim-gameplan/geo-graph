# Land Portion Land Connections Enhancement Summary

**Date:** May 1, 2025  
**Author:** Cline  
**Status:** Completed  

## Overview

This document summarizes the enhancements made to the Boundary Hexagon Layer approach to improve connectivity between land portions across water obstacles. The primary enhancement is the addition of direct connections between land portion nodes, creating a more robust network for pathfinding across water obstacles.

## Problem Statement

In the previous implementation, land portion nodes (nodes placed on the land portions of water hexagons) were only connected to:
1. Boundary nodes (nodes at the centers of boundary hexagons)
2. Water boundary nodes (nodes along water obstacle boundaries)
3. Land nodes (nodes at the centers of land hexagons)

This created a dependency where land portion nodes could only communicate with each other through boundary nodes or water boundary nodes, which could lead to suboptimal paths when navigating across water obstacles with multiple land portions.

## Solution

We enhanced the Boundary Hexagon Layer approach by adding direct connections between land portion nodes, allowing for more efficient pathfinding across water obstacles. The key components of this enhancement include:

1. **Land Portion to Land Portion Connections**: Direct connections between land portion nodes within a configurable distance
2. **Selective Connection Strategy**: Using a modulo-based approach to limit the number of connections and prevent excessive edge creation
3. **Water Obstacle Avoidance**: Ensuring connections don't cross through water obstacles
4. **Visualization Support**: Updated visualization scripts to display the new connections

## Implementation Details

### 1. Configuration Parameters

Added new configuration parameters to control land portion to land portion connections:

```json
"boundary_hexagon_layer": {
  "max_land_portion_connection_distance": 300,
  "land_portion_connection_modulo": 3,
  "land_speed_factor": 1.0
}
```

- **max_land_portion_connection_distance**: Maximum distance between land portion nodes to create a connection
- **land_portion_connection_modulo**: Modulo value to limit the number of connections (only nodes where id % modulo = 0 initiate connections)
- **land_speed_factor**: Speed factor for land portion to land portion connections

### 2. SQL Implementation

Enhanced the `06_create_boundary_edges_hexagon.sql` script to create land portion to land portion connections:

```sql
-- Create land-portion-to-land-portion edges
INSERT INTO land_portion_land_edges (start_node_id, end_node_id, geom, length, cost)
SELECT
    lp1.id AS start_node_id,
    lp2.id AS end_node_id,
    ST_MakeLine(lp1.geom, lp2.geom) AS geom,
    ST_Length(ST_MakeLine(lp1.geom, lp2.geom)) AS length,
    ST_Length(ST_MakeLine(lp1.geom, lp2.geom)) / (5.0 * :land_speed_factor) AS cost
FROM
    land_portion_nodes lp1
JOIN
    land_portion_nodes lp2 ON ST_DWithin(lp1.geom, lp2.geom, :max_land_portion_connection_distance)
WHERE
    lp1.id < lp2.id
    AND (lp1.id % :land_portion_connection_modulo) = 0
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles wo
        WHERE ST_Intersects(ST_MakeLine(lp1.geom, lp2.geom), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(lp1.geom, 1), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(lp2.geom, 1), wo.geom)
    );
```

Also updated the all_boundary_edges table to include the land portion to land portion edges:

```sql
-- Land-portion-to-land-portion edges
SELECT
    e.start_node_id,
    e.end_node_id,
    'land_portion' AS start_node_type,
    'land_portion' AS end_node_type,
    e.geom,
    e.length,
    e.cost
FROM
    land_portion_land_edges e
WHERE
    EXISTS (
        SELECT 1
        FROM land_portion_nodes lp
        WHERE lp.id = e.end_node_id
    );
```

### 3. Visualization Updates

Enhanced the `visualize_unified_boundary_graph.py` script to visualize land portion to land portion connections:

```python
# Land-portion-to-land-portion edges
land_portion_land_portion_edges = unified_edges_gdf[(unified_edges_gdf['start_node_type'] == 'land_portion') &
                                                   (unified_edges_gdf['end_node_type'] == 'land_portion')]
land_portion_land_portion_edges.plot(ax=ax, color='purple', linewidth=2.0, linestyle='--')
```

Added a new legend entry for land portion to land portion edges:

```python
plt.Line2D([0], [0], color='purple', linewidth=2.0, linestyle='--', label='Land-Portion-to-Land-Portion Edges')
```

## Benefits

The land portion land connections enhancement provides several key benefits:

1. **Improved Pathfinding**: More direct routes across water obstacles with multiple land portions
2. **Reduced Dependency**: Land portion nodes are no longer dependent on boundary nodes or water boundary nodes for communication
3. **More Natural Paths**: Paths that better reflect real-world navigation options across water obstacles
4. **Configurable Connectivity**: The modulo-based approach allows for fine-tuning the connectivity based on the specific use case

## Example Scenario

Consider a lake with several islands (represented as land portions). In the previous implementation, navigating from one island to another would require:
1. Going from the first island (land portion) to a boundary node
2. From the boundary node to another boundary node
3. From that boundary node to the second island (land portion)

With the new enhancement, there can be a direct connection from the first island to the second island, resulting in a more efficient path.

## Future Work

Potential future enhancements to the land portion land connections include:

1. **Dynamic Connection Strategy**: Adjust the connection strategy based on the size and shape of the land portions
2. **Hierarchical Connections**: Create a hierarchy of land portion nodes to further optimize pathfinding
3. **Environmental Factors**: Consider environmental factors (e.g., weather, terrain) when creating connections
4. **Multi-Modal Connections**: Support different modes of transportation (e.g., boat, bridge) between land portions

## Conclusion

The land portion land connections enhancement significantly improves the Boundary Hexagon Layer approach by creating a more robust network for pathfinding across water obstacles. The modulo-based approach ensures that the number of connections remains manageable while still providing efficient paths.
