# Hexagon Obstacle Boundary Pipeline

This document describes the Hexagon Obstacle Boundary Pipeline, which combines the benefits of a hexagonal terrain grid with the precise water boundary representation of the obstacle boundary approach.

## Overview

The Hexagon Obstacle Boundary Pipeline is a hybrid approach that:

1. Creates a hexagonal terrain grid that includes water boundaries
2. Uses the original obstacle boundary approach to create water boundary nodes and edges
3. Connects the terrain grid to the water boundary nodes
4. Creates a unified graph for navigation

This approach preserves the exact shape of water obstacles while using a hexagonal grid for better terrain representation.

## Key Features

- **Hexagonal Terrain Grid**: Uses a hexagonal grid for more natural terrain representation and movement patterns
- **Precise Water Boundaries**: Preserves the exact shape of water obstacles by extracting boundary nodes and edges
- **Optimal Connectivity**: Connects terrain grid points to water boundary nodes for seamless navigation
- **Unified Graph**: Creates a unified graph that combines terrain edges and water boundary edges
- **Configurable Parameters**: Extensive configuration options for grid spacing, boundary node spacing, and more
- **Visualization Tools**: Tools for visualizing the terrain grid, water obstacles, and boundary nodes

## Pipeline Stages

1. **Extract Water Features**: Extract water features from OSM data with EPSG:3857 coordinates
2. **Create Water Buffers**: Create buffers around water features using metric distances
3. **Dissolve Water Buffers**: Dissolve overlapping water buffers with proper simplification
4. **Create Hexagonal Terrain Grid**: Create a hexagonal terrain grid that includes water boundaries
5. **Create Obstacle Boundary Nodes**: Extract boundary nodes from water obstacles
6. **Create Obstacle Boundary Edges**: Create edges connecting adjacent boundary nodes
7. **Create Connection Edges**: Connect terrain grid points to boundary nodes
8. **Create Unified Graph**: Combine all edge tables into a unified graph

## Usage

### Running the Pipeline

```bash
# Run the pipeline with default settings
python epsg3857_pipeline/run_hexagon_obstacle_boundary_pipeline.py

# Run with verbose output
python epsg3857_pipeline/run_hexagon_obstacle_boundary_pipeline.py --verbose

# Skip database reset
python epsg3857_pipeline/run_hexagon_obstacle_boundary_pipeline.py --skip-reset

# Use a custom configuration file
python epsg3857_pipeline/run_hexagon_obstacle_boundary_pipeline.py --config path/to/config.json

# Visualize the results after running the pipeline
python epsg3857_pipeline/run_hexagon_obstacle_boundary_pipeline.py --visualize

# Save the visualization to a specific file
python epsg3857_pipeline/run_hexagon_obstacle_boundary_pipeline.py --visualize --output path/to/output.png
```

### Running Tests

```bash
# Run all tests
./epsg3857_pipeline/run_tests.sh

# Run only the hexagon obstacle boundary tests
./epsg3857_pipeline/run_tests.sh --hexagon-obstacle-only

# Run tests with verbose output
./epsg3857_pipeline/run_tests.sh --hexagon-obstacle-only --verbose
```

### Visualizing the Results

```bash
# Visualize the results
python epsg3857_pipeline/core/scripts/visualize_hexagon_obstacle_boundary.py

# Save the visualization to a specific file
python epsg3857_pipeline/core/scripts/visualize_hexagon_obstacle_boundary.py --output path/to/output.png

# Use verbose output
python epsg3857_pipeline/core/scripts/visualize_hexagon_obstacle_boundary.py --verbose
```

## Configuration

The pipeline is configured using a JSON file. Here's an example configuration:

```json
{
  "crs": {
    "storage": 3857,
    "export": 4326,
    "analysis": 3857
  },
  "terrain_grid": {
    "grid_spacing": 200,
    "max_edge_length": 500
  },
  "water_crossing": {
    "max_crossing_distance": 300
  },
  "environmental_conditions": {
    "water_speed_factor": 0.2
  },
  "obstacle_boundary": {
    "boundary_node_spacing": 100,
    "boundary_edge_max_length": 200,
    "connection_distance": 1000,
    "max_connections_per_boundary_node": 5,
    "max_connections_per_terrain_point": 2,
    "node_tolerance": 10
  },
  "simplify_tolerance": 5
}
```

### Configuration Parameters

- **crs.storage**: The SRID to use for storing geometries in the database (default: 3857)
- **crs.export**: The SRID to use for exporting geometries (default: 4326)
- **crs.analysis**: The SRID to use for analysis (default: 3857)
- **terrain_grid.grid_spacing**: The spacing between hexagonal grid cells in meters (default: 200)
- **terrain_grid.max_edge_length**: The maximum length of terrain edges in meters (default: 500)
- **water_crossing.max_crossing_distance**: The maximum distance for connecting terrain grid points to boundary nodes in meters (default: 300)
- **environmental_conditions.water_speed_factor**: The speed factor for water edges (default: 0.2)
- **simplify_tolerance**: The tolerance for simplifying geometries in meters (default: 5)
- **obstacle_boundary.node_tolerance**: The distance tolerance for finding existing nodes when using the Line-to-Point Connection Strategy (default: 10)

## Data Model

### Terrain Grid

The terrain grid uses a hexagonal grid approach:

- **terrain_grid**: Contains hexagonal grid cells with a `hex_type` column that can be 'land', 'water', or 'boundary'
- **terrain_grid_points**: Contains the centroids of the grid cells, used for connectivity

Benefits of the hexagonal grid:
- More natural-looking terrain representation
- Equal distances between adjacent cells
- Better adaptation to natural features
- More efficient movement patterns

### Obstacle Boundary

The obstacle boundary approach extracts the exact shape of water obstacles:

- **obstacle_boundary_nodes**: Contains points extracted from water obstacle boundaries
- **obstacle_boundary_edges**: Contains edges connecting adjacent boundary nodes
- **obstacle_boundary_connection_edges**: Contains edges connecting terrain grid points to boundary nodes

The pipeline now uses the Line-to-Point Connection Strategy, which connects terrain nodes to the closest point on water obstacle boundaries rather than to pre-existing boundary nodes. This approach creates more direct and natural connections, improving navigation around water obstacles. See [Line-to-Point Connection Strategy](./line_to_point_connection_strategy.md) for more details.

### Unified Graph

The unified graph combines all edge tables:

- **unified_obstacle_edges**: Contains all edges from terrain edges, boundary edges, and connection edges

## Benefits

- **Improved Accuracy**: Using EPSG:3857 for internal processing ensures accurate metric-based measurements
- **More Natural Terrain**: Hexagonal grid provides a more natural terrain representation
- **Precise Water Boundaries**: Obstacle boundary approach preserves the exact shape of water obstacles
- **Optimal Connectivity**: Connection edges ensure seamless navigation between terrain and water boundaries
- **Direct Water Connections**: Line-to-Point Connection Strategy creates more direct and natural connections to water boundaries
- **Better Distribution**: Connections are more evenly distributed along water boundaries, reducing redundancy
- **Better Performance**: Unified graph improves pathfinding performance

## Comparison with Other Approaches

| Feature | Standard Pipeline | Delaunay Pipeline | Obstacle Boundary Pipeline | Hexagon Obstacle Boundary Pipeline |
|---------|------------------|-------------------|----------------------------|-----------------------------------|
| Terrain Grid | Rectangular | Triangular | Rectangular | Hexagonal |
| Water Representation | Crossing Edges | Crossing Edges | Boundary Nodes and Edges | Boundary Nodes and Edges |
| Grid Adaptability | Low | High | Low | Medium |
| Water Boundary Precision | Low | Medium | High | High |
| Connectivity | Medium | High | High | High |
| Performance | Medium | Medium | High | High |

## Troubleshooting

### Common Issues

- **Memory errors during dissolve step**: Increase the `work_mem` parameter in the SQL script
- **Slow performance**: Enable parallel query execution and optimize the SQL queries
- **Simplification issues**: Adjust the simplification tolerance in the SQL script
- **Missing water features**: Check the water feature extraction parameters in the configuration
- **Path issues**: Ensure that paths in scripts are correctly specified relative to the current working directory
- **Docker connectivity**: Make sure the Docker containers are running before executing scripts that interact with the database

### Graph Connectivity

If you encounter graph connectivity issues:

1. Check if obstacle boundary nodes are being created (the obstacle_boundary_nodes table should not be empty)
2. Check if connection edges are being created (the obstacle_boundary_connection_edges table should not be empty)
3. Adjust the max_connection_distance parameter in the configuration file
4. Use the visualization tools to identify disconnected components in the graph

### Debugging

- Use the `--verbose` flag with the runner scripts to see more detailed output
- Check the SQL queries in the SQL scripts to ensure they are correctly extracting and processing the data
- Use the visualization script to visualize the results and check if they look correct
- Run tests with the `--verbose` flag to get more detailed output about what's happening during test execution

## Future Improvements

- **Adaptive Grid Spacing**: Adjust grid spacing based on terrain complexity
- **Multi-level Grid**: Use different grid resolutions for different areas
- **Parallel Processing**: Implement parallel processing for large datasets
- **Improved Visualization**: Add interactive visualization tools
- **Performance Optimization**: Optimize SQL queries for better performance
- **Integration with Routing Engines**: Integrate with routing engines like pgRouting or Valhalla
