# Boundary Hexagon Layer Approach

## Overview

The Boundary Hexagon Layer approach is an enhanced method for connecting terrain and water obstacle boundaries in the EPSG:3857 Terrain Graph Pipeline. It addresses the "white space" issues between terrain and water obstacles by preserving hexagons at water boundaries and using land portions of water hexagons to create more natural connections.

## Key Concepts

### Hexagon Classification

Hexagons in the terrain grid are classified into three types:

1. **Land Hexagons**: Hexagons that don't intersect water obstacles
2. **Boundary Hexagons**: Hexagons that intersect water obstacles but their centerpoints are not in water
3. **Water with Land Hexagons**: Hexagons that intersect water obstacles AND their centerpoints are in water, but they have land portions

### Node Types

The approach creates three types of nodes:

1. **Boundary Nodes**: Nodes placed at the centers of boundary hexagons
2. **Land Portion Nodes**: Nodes placed on the land portions of water hexagons
3. **Water Boundary Nodes**: Nodes placed along water obstacle boundaries

### Connection Strategy

Connections are created in a specific direction - from land toward water:

1. **Boundary-to-Boundary Edges**: Connect boundary nodes to other boundary nodes
2. **Boundary-to-Land-Portion Edges**: Connect boundary nodes to land portion nodes
3. **Land-Portion-to-Water-Boundary Edges**: Connect land portion nodes to water boundary nodes

This ensures that pathfinding can navigate from land to water obstacles, but not into water.

## Advantages

1. **Eliminates White Space**: By using land portions of water hexagons, the approach eliminates the "white space" between terrain and water obstacles
2. **Natural Connections**: Creates more natural connections between terrain and water obstacles
3. **Directional Connections**: Ensures connections go from land toward water, not into water
4. **Better Pathfinding**: Improves pathfinding capabilities around water features

## Implementation

The approach is implemented in the following SQL scripts:

1. `04_create_terrain_grid_boundary_hexagon.sql`: Creates the terrain grid with proper hexagon classification
2. `05_create_boundary_nodes_hexagon.sql`: Creates boundary nodes, water boundary nodes, and land portion nodes
3. `06_create_boundary_edges_hexagon.sql`: Creates connections between nodes
4. `07_create_unified_boundary_graph_hexagon.sql`: Combines all nodes and edges into a unified graph

## Usage

To run the boundary hexagon layer pipeline:

```bash
python epsg3857_pipeline/run_boundary_hexagon_layer_pipeline.py --config epsg3857_pipeline/config/boundary_hexagon_layer_config.json --verbose
```

To visualize the results:

```bash
python epsg3857_pipeline/core/scripts/visualize_boundary_hexagon_layer.py --output-dir epsg3857_pipeline/visualizations
```

## Configuration

The boundary hexagon layer approach can be configured using the following parameters in the configuration file:

```json
{
  "boundary_hexagon_layer": {
    "boundary_node_spacing": 100,
    "boundary_edge_max_length": 200,
    "water_speed_factor": 0.2,
    "boundary_extension_distance": 50,
    "max_bridge_distance": 300,
    "max_bridge_length": 150,
    "direction_count": 8,
    "max_connections_per_direction": 2
  }
}
```

- `boundary_node_spacing`: Spacing between water boundary nodes (in meters)
- `boundary_edge_max_length`: Maximum length of edges between nodes (in meters)
- `water_speed_factor`: Factor to multiply edge costs for water edges
- `boundary_extension_distance`: Distance to extend boundary nodes into water (in meters)
- `max_bridge_distance`: Maximum distance for bridge connections (in meters)
- `max_bridge_length`: Maximum length of bridge connections (in meters)
- `direction_count`: Number of directions to consider for connections
- `max_connections_per_direction`: Maximum number of connections per direction

## Comparison with Other Approaches

The Boundary Hexagon Layer approach offers several advantages over other connection strategies:

1. **Nearest Neighbor**: Unlike the simple nearest neighbor approach, the boundary hexagon layer creates more natural connections and eliminates white space.
2. **Buffer-Based Voronoi**: The boundary hexagon layer approach is more efficient and creates more natural connections than the buffer-based Voronoi approach.
3. **True Voronoi**: While the true Voronoi approach creates natural connections, it doesn't address the white space issue as effectively as the boundary hexagon layer approach.
4. **Reversed Voronoi**: The boundary hexagon layer approach builds on the reversed Voronoi approach by adding land portions of water hexagons for better connectivity.

## Future Enhancements

Potential future enhancements to the boundary hexagon layer approach include:

1. **Dynamic Node Placement**: Adjust node placement based on terrain features
2. **Adaptive Connection Strategies**: Use different connection strategies based on the local terrain
3. **Performance Optimizations**: Improve performance for large datasets
4. **Integration with Other Approaches**: Combine with other approaches like reversed Voronoi for even better results
