# Obstacle Boundary Pipeline

The Obstacle Boundary Pipeline is an approach that directly converts water obstacle polygons to graph elements, creating a more precise representation of water boundaries for navigation.

## Overview

Unlike the standard pipeline which creates edges that cross water obstacles, the obstacle boundary pipeline treats water obstacles as navigable boundaries. It extracts the vertices from water obstacle polygons and creates edges along the perimeter of water obstacles, allowing for more realistic navigation around water features.

## Pipeline Stages

1. **Extract Boundary Nodes**: Extract vertices from water obstacles as graph nodes
2. **Create Boundary Edges**: Create edges between adjacent vertices along water boundaries
3. **Connect Terrain to Boundary**: Connect terrain grid points to the nearest boundary nodes
4. **Create Unified Graph**: Combine terrain edges, boundary edges, and connection edges into a unified graph

## Database Tables

The obstacle boundary pipeline creates the following tables:

### obstacle_boundary_nodes

Contains vertices extracted from water obstacles:

```sql
CREATE TABLE obstacle_boundary_nodes (
    node_id SERIAL PRIMARY KEY,
    water_obstacle_id INTEGER,
    point_order INTEGER,
    geom geometry(POINT)
);
```

- `node_id`: Unique identifier for the node
- `water_obstacle_id`: Reference to the water obstacle this node belongs to
- `point_order`: Order of the point in the water obstacle boundary
- `geom`: Geometry of the node (point)

### obstacle_boundary_edges

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

- `edge_id`: Unique identifier for the edge
- `source_node_id`: Reference to the source node
- `target_node_id`: Reference to the target node
- `water_obstacle_id`: Reference to the water obstacle this edge belongs to
- `length`: Length of the edge in meters
- `geom`: Geometry of the edge (linestring)

### obstacle_boundary_connection_edges

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

- `edge_id`: Unique identifier for the edge
- `terrain_node_id`: Reference to the terrain node
- `boundary_node_id`: Reference to the boundary node
- `water_obstacle_id`: Reference to the water obstacle this edge belongs to
- `length`: Length of the edge in meters
- `geom`: Geometry of the edge (linestring)

### unified_obstacle_edges

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

- `edge_id`: Unique identifier for the edge
- `source_id`: Reference to the source node
- `target_id`: Reference to the target node
- `length`: Length of the edge in meters
- `cost`: Travel time cost (length / (speed * speed_factor))
- `edge_type`: Type of edge ('terrain', 'boundary', or 'connection')
- `speed_factor`: Speed factor for the edge (1.0 for terrain, 0.2 for water)
- `is_water`: Whether the edge is a water edge
- `geom`: Geometry of the edge (linestring)

## Running the Pipeline

To run the obstacle boundary pipeline:

```bash
# Run the obstacle boundary pipeline
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py

# Run the obstacle boundary pipeline with verbose output
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py --verbose

# Run the obstacle boundary pipeline with custom parameters
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py --storage-srid 3857 --max-connection-distance 300 --water-speed-factor 0.2
```

## Parameters

The obstacle boundary pipeline accepts the following parameters:

- `--storage-srid`: SRID for storage (default: 3857)
- `--max-connection-distance`: Maximum distance for connecting terrain points to boundary nodes (default: 300)
- `--water-speed-factor`: Speed factor for water edges (default: 0.2)
- `--verbose`: Enable verbose logging

## Visualization

To visualize the obstacle boundary graph:

```bash
# Visualize the obstacle boundary graph
python epsg3857_pipeline/core/obstacle_boundary/visualize.py
```

This will create a visualization of the obstacle boundary graph, showing:
- Water obstacles (blue)
- Terrain grid points (green)
- Obstacle boundary nodes (red)
- Obstacle boundary edges (blue)
- Obstacle boundary connection edges (orange)

The visualization is saved to `obstacle_boundary_graph.png`.

## Benefits

The obstacle boundary pipeline offers several benefits over the standard pipeline:

1. **More Realistic Navigation**: By treating water obstacles as navigable boundaries, the pipeline creates a more realistic representation of how vehicles navigate around water features.

2. **Precise Boundary Representation**: The pipeline preserves the exact shape of water obstacles, creating a clean representation of water boundaries.

3. **Improved Graph Connectivity**: The pipeline ensures full graph connectivity by connecting terrain grid points to the nearest boundary nodes.

4. **Optimal Pathfinding**: The unified graph allows for optimal pathfinding around water obstacles, with appropriate costs for different edge types.

5. **Configurable Parameters**: The pipeline offers configurable parameters for storage SRID, connection distance, and water speed factor.

## Example Results

In our test dataset, the obstacle boundary pipeline created:
- 18,981 obstacle boundary nodes
- 18,981 obstacle boundary edges
- 1,058 obstacle boundary connection edges
- 142,785 unified obstacle edges (18,981 boundary + 1,058 connection + 122,746 terrain)

The largest water obstacle (ID 2) had 14,943 nodes and edges, representing a complex water feature.

## Conclusion

The obstacle boundary pipeline provides a more precise and realistic representation of water boundaries for navigation. By directly converting water obstacle polygons to graph elements, it creates a clean representation of water boundaries that can be used for optimal pathfinding around water obstacles.
