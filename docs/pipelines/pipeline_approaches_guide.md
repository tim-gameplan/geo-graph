# Comprehensive Pipeline Approaches Guide

This document provides a comprehensive overview of the different pipeline approaches available in the EPSG:3857 Terrain Graph Pipeline. It consolidates information from multiple approach-specific documents into a single reference guide.

## Introduction

The EPSG:3857 Terrain Graph Pipeline offers several approaches for creating terrain graphs with water obstacles. Each approach has its own strengths and is suitable for different use cases. This guide will help you understand the differences between these approaches and choose the one that best fits your needs.

## Available Pipeline Approaches

1. **Standard Pipeline**: Basic pipeline with hexagonal grid and improved water edge creation
2. **Water Boundary Approach**: Treats water obstacles as navigable boundaries
3. **Obstacle Boundary Approach**: Directly converts water obstacle polygons to graph elements
4. **Hexagon Obstacle Boundary**: Combines hexagonal grid with precise water obstacle boundaries
5. **Voronoi Obstacle Boundary**: Uses Voronoi diagrams for natural connections between terrain and water
6. **Reversed Voronoi Obstacle Boundary**: Uses reversed Voronoi approach for more natural connections
7. **Boundary Hexagon Layer**: Preserves hexagons at water boundaries for better connectivity and uses land portions of water hexagons

## 1. Standard Pipeline

### Overview

The standard pipeline creates a hexagonal terrain grid that avoids water obstacles and connects grid points with edges. It uses an improved water edge creation algorithm that ensures better graph connectivity.

### Key Features

- **Hexagonal Grid**: Uses a hexagonal grid for more natural terrain representation
- **Improved Water Edge Creation**: Advanced algorithms for creating water crossing edges with better graph connectivity
- **Environmental Conditions**: Adjusts edge costs based on environmental conditions

### Usage

```bash
# Run the standard pipeline with improved water edge creation (default)
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard

# Run with verbose output
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --verbose
```

### When to Use

Use the standard pipeline when you need a general-purpose terrain graph with good connectivity and don't need precise water boundary representation.

## 2. Water Boundary Approach

### Overview

The water boundary approach treats water obstacles as navigable boundaries rather than impassable barriers. It creates edges along the perimeter of water obstacles and connects terrain grid points to water boundary points.

### Key Concepts

1. **Water Boundaries as Edges**: Water obstacle boundaries are converted to graph edges, allowing vehicles to navigate along the perimeter of water obstacles.
2. **Terrain Grid with Water**: The terrain grid includes cells that intersect with water, marked as water cells with higher costs.
3. **Terrain-to-Boundary Connections**: Terrain grid points are connected to the nearest water boundary points, creating a seamless transition between land and water.
4. **Unified Graph**: The terrain edges and water boundary edges are combined into a unified graph, ensuring full connectivity.

### Implementation Details

#### 1. Terrain Grid Creation with Water

The terrain grid creation script creates a hexagonal grid that includes cells that intersect with water. These cells are marked as water cells with higher costs.

#### 2. Terrain Edges Creation with Water

The terrain edges creation script creates edges between all terrain grid points, including those in water. Edges that cross water or connect to water points have higher costs.

#### 3. Water Boundary Edges Creation

The water boundary edges creation script has three main steps:

1. **Extract Boundary Points**: Extract points directly from the vertices of each water obstacle polygon
2. **Create Edges Between Boundary Points**: Create edges between adjacent boundary points to form a continuous path along the water boundary
3. **Connect Terrain Points to Boundary Points**: Connect terrain grid points to the nearest water boundary points

#### 4. Unified Graph Creation

The water boundary edges creation script also creates a unified graph that combines terrain edges and water boundary edges.

### Usage

```bash
# Run the water boundary approach
python epsg3857_pipeline/run_epsg3857_pipeline.py --water-boundary

# Run with custom configuration
python epsg3857_pipeline/run_epsg3857_pipeline.py --water-boundary --config epsg3857_pipeline/config/crs_standardized_config_boundary.json
```

### Configuration

The water boundary approach is configured in `crs_standardized_config_boundary.json`:

```json
{
    "water_edges": {
        "water_speed_factor": 0.2,
        "boundary_segment_length": 100,
        "max_connection_distance": 300
    }
}
```

### Benefits

1. **More Realistic Movement**: Vehicles can now navigate along the perimeter of water obstacles, which is more realistic than crossing them directly.
2. **Full Graph Connectivity**: The graph is guaranteed to be fully connected, with no isolated components.
3. **Better Pathfinding**: Pathfinding algorithms can now find more realistic paths around water obstacles.
4. **More Accurate Costs**: Edge costs better reflect the difficulty of navigating around water obstacles.
5. **Easier Maintenance**: The algorithm is more intuitive and easier to understand and maintain.

### When to Use

Use the water boundary approach when you need more realistic movement patterns around water obstacles and better graph connectivity.

## 3. Obstacle Boundary Approach

### Overview

The Obstacle Boundary Pipeline is an approach that directly converts water obstacle polygons to graph elements, creating a more precise representation of water boundaries for navigation.

### Pipeline Stages

1. **Extract Boundary Nodes**: Extract vertices from water obstacles as graph nodes
2. **Create Boundary Edges**: Create edges between adjacent vertices along water boundaries
3. **Connect Terrain to Boundary**: Connect terrain grid points to the nearest boundary nodes
4. **Create Unified Graph**: Combine terrain edges, boundary edges, and connection edges into a unified graph

### Database Tables

The obstacle boundary pipeline creates the following tables:

#### obstacle_boundary_nodes

Contains vertices extracted from water obstacles:

```sql
CREATE TABLE obstacle_boundary_nodes (
    node_id SERIAL PRIMARY KEY,
    water_obstacle_id INTEGER,
    point_order INTEGER,
    geom geometry(POINT)
);
```

#### obstacle_boundary_edges

Contains edges connecting adjacent vertices along water boundaries:

```sql
CREATE TABLE obstacle_boundary_edges (
    edge_id SERIAL PRIMARY KEY,
    source_node_id INTEGER,
    target_node_id INTEGER,
    water_obstacle_id INTEGER,
    length NUMERIC,
    geom geometry(LINESTRING)
);
```

#### obstacle_boundary_connection_edges

Contains edges connecting terrain grid points to boundary nodes:

```sql
CREATE TABLE obstacle_boundary_connection_edges (
    edge_id SERIAL PRIMARY KEY,
    terrain_node_id INTEGER,
    boundary_node_id INTEGER,
    water_obstacle_id INTEGER,
    length NUMERIC,
    geom geometry(LINESTRING)
);
```

#### unified_obstacle_edges

Contains a unified graph combining terrain edges, boundary edges, and connection edges:

```sql
CREATE TABLE unified_obstacle_edges (
    edge_id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    length NUMERIC,
    cost NUMERIC,
    edge_type TEXT,
    speed_factor NUMERIC,
    is_water BOOLEAN,
    geom geometry(LINESTRING)
);
```

### Usage

```bash
# Run the obstacle boundary pipeline
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py

# Run the obstacle boundary pipeline with verbose output
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py --verbose

# Run the obstacle boundary pipeline with custom parameters
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py --storage-srid 3857 --max-connection-distance 300 --water-speed-factor 0.2
```

### Parameters

The obstacle boundary pipeline accepts the following parameters:

- `--storage-srid`: SRID for storage (default: 3857)
- `--max-connection-distance`: Maximum distance for connecting terrain points to boundary nodes (default: 300)
- `--water-speed-factor`: Speed factor for water edges (default: 0.2)
- `--verbose`: Enable verbose logging

### Visualization

```bash
# Visualize the obstacle boundary graph
python epsg3857_pipeline/core/obstacle_boundary/visualize.py
```

### Benefits

1. **More Realistic Navigation**: By treating water obstacles as navigable boundaries, the pipeline creates a more realistic representation of how vehicles navigate around water features.
2. **Precise Boundary Representation**: The pipeline preserves the exact shape of water obstacles, creating a clean representation of water boundaries.
3. **Improved Graph Connectivity**: The pipeline ensures full graph connectivity by connecting terrain grid points to the nearest boundary nodes.
4. **Optimal Pathfinding**: The unified graph allows for optimal pathfinding around water obstacles, with appropriate costs for different edge types.
5. **Configurable Parameters**: The pipeline offers configurable parameters for storage SRID, connection distance, and water speed factor.

### When to Use

Use the obstacle boundary approach when you need a precise representation of water boundaries and optimal pathfinding around water obstacles.

## 4. Hexagon Obstacle Boundary

### Overview

The Hexagon Obstacle Boundary Pipeline is a hybrid approach that:

1. Creates a hexagonal terrain grid that includes water boundaries
2. Uses the original obstacle boundary approach to create water boundary nodes and edges
3. Connects the terrain grid to the water boundary nodes
4. Creates a unified graph for navigation

This approach preserves the exact shape of water obstacles while using a hexagonal grid for better terrain representation.

### Key Features

- **Hexagonal Terrain Grid**: Uses a hexagonal grid for more natural terrain representation and movement patterns
- **Precise Water Boundaries**: Preserves the exact shape of water obstacles by extracting boundary nodes and edges
- **Optimal Connectivity**: Connects terrain grid points to water boundary nodes for seamless navigation
- **Unified Graph**: Creates a unified graph that combines terrain edges and water boundary edges
- **Configurable Parameters**: Extensive configuration options for grid spacing, boundary node spacing, and more
- **Visualization Tools**: Tools for visualizing the terrain grid, water obstacles, and boundary nodes

### Pipeline Stages

1. **Extract Water Features**: Extract water features from OSM data with EPSG:3857 coordinates
2. **Create Water Buffers**: Create buffers around water features using metric distances
3. **Dissolve Water Buffers**: Dissolve overlapping water buffers with proper simplification
4. **Create Hexagonal Terrain Grid**: Create a hexagonal terrain grid that includes water boundaries
5. **Create Obstacle Boundary Nodes**: Extract boundary nodes from water obstacles
6. **Create Obstacle Boundary Edges**: Create edges connecting adjacent boundary nodes
7. **Create Connection Edges**: Connect terrain grid points to boundary nodes
8. **Create Unified Graph**: Combine all edge tables into a unified graph

### Usage

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

### Configuration

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

### Data Model

#### Terrain Grid

The terrain grid uses a hexagonal grid approach:

- **terrain_grid**: Contains hexagonal grid cells with a `hex_type` column that can be 'land', 'water', or 'boundary'
- **terrain_grid_points**: Contains the centroids of the grid cells, used for connectivity

Benefits of the hexagonal grid:
- More natural-looking terrain representation
- Equal distances between adjacent cells
- Better adaptation to natural features
- More efficient movement patterns

#### Obstacle Boundary

The obstacle boundary approach extracts the exact shape of water obstacles:

- **obstacle_boundary_nodes**: Contains points extracted from water obstacle boundaries
- **obstacle_boundary_edges**: Contains edges connecting adjacent boundary nodes
- **obstacle_boundary_connection_edges**: Contains edges connecting terrain grid points to boundary nodes

The pipeline now uses the Line-to-Point Connection Strategy, which connects terrain nodes to the closest point on water obstacle boundaries rather than to pre-existing boundary nodes. This approach creates more direct and natural connections, improving navigation around water obstacles.

#### Unified Graph

The unified graph combines all edge tables:

- **unified_obstacle_edges**: Contains all edges from terrain edges, boundary edges, and connection edges

### Benefits

- **Improved Accuracy**: Using EPSG:3857 for internal processing ensures accurate metric-based measurements
- **More Natural Terrain**: Hexagonal grid provides a more natural terrain representation
- **Precise Water Boundaries**: Obstacle boundary approach preserves the exact shape of water obstacles
- **Optimal Connectivity**: Connection edges ensure seamless navigation between terrain and water boundaries
- **Direct Water Connections**: Line-to-Point Connection Strategy creates more direct and natural connections to water boundaries
- **Better Distribution**: Connections are more evenly distributed along water boundaries, reducing redundancy
- **Better Performance**: Unified graph improves pathfinding performance

### When to Use

Use the hexagon obstacle boundary approach when you need a more natural terrain representation with precise water boundaries and optimal connectivity.

## 5. Voronoi Obstacle Boundary

### Overview

The Voronoi Obstacle Boundary approach uses Voronoi diagrams to create more natural and evenly distributed connections between terrain and water obstacles. It partitions the space around water boundary nodes into Voronoi cells, which are used to determine which terrain nodes connect to which boundary nodes.

### Key Features

- **Voronoi Partitioning**: Uses Voronoi diagrams to partition the space around water boundary nodes
- **Even Distribution**: Creates an even distribution of connections to water boundaries
- **Prevents Clustering**: Prevents connection clustering and ensures good coverage
- **Natural Navigation**: Creates more natural and intuitive navigation around water obstacles

### Usage

```bash
# Run the Voronoi obstacle boundary pipeline
python epsg3857_pipeline/run_voronoi_obstacle_boundary_pipeline.py

# Run with visualization and show Voronoi cells
python epsg3857_pipeline/run_voronoi_obstacle_boundary_pipeline.py --visualize --show-voronoi

# Run with custom parameters
python epsg3857_pipeline/run_voronoi_obstacle_boundary_pipeline.py --config epsg3857_pipeline/config/voronoi_obstacle_boundary_config.json --verbose
```

### When to Use

Use the Voronoi obstacle boundary approach when you need an even distribution of connections to water boundaries and more natural navigation around water obstacles.

## 6. Reversed Voronoi Obstacle Boundary

### Overview

The Reversed Voronoi Obstacle Boundary approach uses a reversed Voronoi approach for more natural connections. Instead of creating Voronoi cells for boundary nodes, it creates Voronoi cells for terrain points, which are then used to determine which boundary nodes connect to which terrain points.

### Key Features

- **Reversed Voronoi Partitioning**: Creates Voronoi cells for terrain points instead of boundary nodes
- **More Natural Connections**: Creates more natural-looking connections between terrain and water boundaries
- **Better Distribution**: Each terrain point gets a fair share of boundary nodes
- **Reduced Clustering**: Reduces clustering of connections at boundary nodes

### Usage

```bash
# Run the reversed Voronoi obstacle boundary pipeline
python epsg3857_pipeline/run_reversed_voronoi_obstacle_boundary_pipeline.py

# Run with visualization and show Voronoi cells
python epsg3857_pipeline/run_reversed_voronoi_obstacle_boundary_pipeline.py --visualize --show-voronoi

# Run with custom parameters
python epsg3857_pipeline/run_reversed_voronoi_obstacle_boundary_pipeline.py --config epsg3857_pipeline/config/voronoi_obstacle_boundary_config.json --verbose
```

### When to Use

Use the reversed Voronoi obstacle boundary approach when you need the most natural-looking connections between terrain and water boundaries and the best distribution of connections.

## 7. Boundary Hexagon Layer

### Overview

The Boundary Hexagon Layer approach is an enhanced method for connecting terrain and water obstacle boundaries. It addresses the "white space" issues between terrain and water obstacles by preserving hexagons at water boundaries and using land portions of water hexagons to create more natural connections.

### Key Concepts

#### Hexagon Classification

Hexagons in the terrain grid are classified into three types:

1. **Land Hexagons**: Hexagons that don't intersect water obstacles
2. **Boundary Hexagons**: Hexagons that intersect water obstacles but their centerpoints are not in water
3. **Water with Land Hexagons**: Hexagons that intersect water obstacles AND their centerpoints are in water, but they have land portions

#### Node Types

The approach creates three types of nodes:

1. **Boundary Nodes**: Nodes placed at the centers of boundary hexagons
2. **Land Portion Nodes**: Nodes placed on the land portions of water hexagons
3. **Water Boundary Nodes**: Nodes placed along water obstacle boundaries

#### Connection Strategy

Connections are created in a specific direction - from land toward water:

1. **Boundary-to-Boundary Edges**: Connect boundary nodes to other boundary nodes
2. **Boundary-to-Land-Portion Edges**: Connect boundary nodes to land portion nodes
3. **Land-Portion-to-Water-Boundary Edges**: Connect land portion nodes to water boundary nodes

This ensures that pathfinding can navigate from land to water obstacles, but not into water.

### Usage

```bash
# Run the boundary hexagon layer pipeline
python epsg3857_pipeline/run_boundary_hexagon_layer_pipeline.py --config epsg3857_pipeline/config/boundary_hexagon_layer_config.json --verbose

# Run the enhanced boundary hexagon layer pipeline with improved land portion connectivity
python epsg3857_pipeline/run_boundary_hexagon_layer_enhanced_pipeline.py

# Visualize the results
python epsg3857_pipeline/core/scripts/visualize_boundary_hexagon_layer.py --output-dir epsg3857_pipeline/visualizations
```

### Configuration

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

### Advantages

1. **Eliminates White Space**: By using land portions of water hexagons, the approach eliminates the "white space" between terrain and water obstacles
2. **Natural Connections**: Creates more natural connections between terrain and water obstacles
3. **Directional Connections**: Ensures connections go from land toward water, not into water
4. **Better Pathfinding**: Improves pathfinding capabilities around water features

### When to Use

Use the boundary hexagon layer approach when you need to eliminate the "white space" between terrain and water obstacles and create more natural connections with directional control.

## Comparison of Pipeline Approaches

| Feature | Standard Pipeline | Water Boundary | Obstacle Boundary | Hexagon Obstacle Boundary | Voronoi Obstacle Boundary | Reversed Voronoi | Boundary Hexagon Layer |
|---------|------------------|----------------|-------------------|---------------------------|---------------------------|------------------|------------------------|
| Terrain Grid | Hexagonal | Hexagonal with Water | Rectangular | Hexagonal | Hexagonal | Hexagonal | Hexagonal with Classification |
| Water Representation | Crossing Edges | Boundary Edges | Boundary Nodes and Edges | Boundary Nodes and Edges | Boundary Nodes and Edges | Boundary Nodes and Edges | Boundary Nodes, Edges, and Land Portions |
| Grid Adaptability | Low | Medium | Low | Medium | Medium | Medium | High |
| Water Boundary Precision | Low | Medium | High | High | High | High | High |
| Connectivity | Medium | High | High | High | High | High | Very High |
| Connection Distribution | Uneven | Uneven | Uneven | Even | Very Even | Most Even | Very Even |
| White Space Elimination | No | Partial | No | No | No | No | Yes |
| Directional Control | No | No | No | No | No | No | Yes |
| Performance | Medium | Medium | High | High | Medium | Medium | High |
| Complexity | Low | Medium | Medium | Medium | High | Very High | High |

## Recommendations

### For Small Datasets

- **Standard Pipeline**: Simple and fast, suitable for small datasets with simple water features
- **Water Boundary Approach**: Good balance of simplicity and water boundary representation

### For Medium Datasets

- **Obstacle Boundary Approach**: Good balance of precision and performance
- **Hexagon Obstacle Boundary**: Better terrain representation with precise water boundaries

### For Large Datasets

- **Hexagon Obstacle Boundary**: Best balance of precision, performance, and natural representation
- **Boundary Hexagon Layer**: Best for eliminating white space and creating natural connections

### For Production Use

The **Boundary Hexagon Layer** approach is recommended for production use, with a fallback to **Hexagon Obstacle Boundary** if performance is a concern. This provides the best balance of precision, natural representation, and connectivity.

## Future Improvements

Potential future improvements to the pipeline approaches include:

1. **Adaptive Grid Spacing**: Adjust grid spacing based on terrain complexity
2. **Multi-level Grid**: Use different grid resolutions for different areas
3. **Parallel Processing**: Implement parallel processing for large datasets
4. **Improved Visualization**: Add interactive visualization tools
5. **Performance Optimization**: Optimize SQL queries for better performance
6. **Integration with Routing Engines**: Integrate with routing engines like pgRouting or Valhalla
7. **Machine Learning**: Use machine learning to optimize parameters based on terrain characteristics

## Conclusion

The EPSG:3857 Terrain Graph Pipeline offers a variety of approaches for creating terrain graphs with water obstacles. Each approach has its own strengths and is suitable for different use cases. By understanding the differences between these approaches, you can choose the one that best fits your needs.

The evolution of these approaches shows a clear progression toward more natural terrain representation, more precise water boundary representation, and better connectivity between terrain and water obstacles. The latest approaches, such as the Boundary Hexagon Layer, represent the state of the art in terrain graph creation with water obstacles.
