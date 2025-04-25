# Direct Water Obstacle Boundary Conversion

This module implements a direct water obstacle boundary conversion approach for terrain graph generation. It directly converts water obstacle polygons to graph elements, creating a clean representation of water boundaries for navigation.

## Key Features

- **Exact Boundary Representation**: Preserves the exact shape of water obstacles by extracting vertices from water obstacle polygons as graph nodes
- **Boundary Navigation**: Creates edges between adjacent boundary nodes, allowing for navigation along the perimeter of water obstacles
- **Terrain-to-Boundary Connections**: Connects terrain grid points to the nearest boundary nodes, creating a seamless transition between land and water
- **Unified Graph**: Creates a unified graph that combines terrain edges and water boundary edges, ensuring full connectivity
- **Configurable Parameters**: Provides parameters for controlling the connection distance, water speed factor, and other aspects of the graph generation

## Usage

```bash
# Run the obstacle boundary pipeline
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py

# Run with custom parameters
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py --max-connection-distance 500 --water-speed-factor 0.3

# Enable verbose logging
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py --verbose
```

## Implementation Details

The implementation consists of the following components:

1. **SQL Script**: `create_obstacle_boundary_graph.sql` - Implements the core algorithm for converting water obstacles to graph elements
2. **Python Script**: `run_obstacle_boundary_pipeline.py` - Provides a command-line interface for running the SQL script with parameters

### Algorithm Overview

1. **Extract Boundary Nodes**: Extract vertices from water obstacle polygons as graph nodes
2. **Create Boundary Edges**: Create edges between adjacent boundary nodes, forming a closed loop around each water obstacle
3. **Connect Terrain to Boundary**: Connect terrain grid points to the nearest boundary nodes, creating a seamless transition between land and water
4. **Create Unified Graph**: Combine terrain edges and water boundary edges into a unified graph for navigation

### Data Model

The implementation creates the following tables:

- **obstacle_boundary_nodes**: Contains nodes extracted from water obstacle boundaries
- **obstacle_boundary_edges**: Contains edges connecting adjacent boundary nodes
- **obstacle_boundary_connection_edges**: Contains edges connecting terrain grid points to boundary nodes
- **unified_obstacle_edges**: Contains all edges (terrain, boundary, and connection) in a unified graph

## Benefits

- **More Realistic Movement**: Vehicles can navigate along the perimeter of water obstacles, which is more realistic than crossing them directly
- **Full Graph Connectivity**: The graph is guaranteed to be fully connected, with no isolated components
- **Better Pathfinding**: Pathfinding algorithms can find more realistic paths around water obstacles
- **More Accurate Costs**: Edge costs better reflect the difficulty of navigating around water obstacles
- **Easier Maintenance**: The algorithm is more intuitive and easier to understand and maintain
