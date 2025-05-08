# EPSG:3857 Terrain Graph Pipeline

A standardized pipeline for terrain graph generation using EPSG:3857 (Web Mercator) for consistent and accurate spatial operations.

## Overview

This pipeline addresses the coordinate reference system (CRS) inconsistency issues in the original terrain graph pipeline by standardizing on EPSG:3857 (Web Mercator) for all internal processing. It also includes enhanced approaches for terrain representation and water feature handling.

## Pipeline Status

The project includes several pipeline approaches with different status levels:

| Pipeline Approach | Status | Description | When to Use |
|-------------------|--------|-------------|------------|
| Standard Pipeline | **STABLE** | Basic pipeline with hexagonal grid and improved water edge creation | General purpose terrain graph generation |
| Water Boundary Approach | **STABLE** | Treats water obstacles as navigable boundaries | When precise water boundary navigation is needed |
| Obstacle Boundary Approach | **STABLE** | Directly converts water obstacle polygons to graph elements | For clean boundary representation with optimal connectivity |
| Hexagon Obstacle Boundary | **STABLE** | Combines hexagonal grid with precise water obstacle boundaries | For better terrain representation with accurate water boundaries |
| Voronoi Obstacle Boundary | **STABLE** | Uses Voronoi diagrams for natural connections between terrain and water | For optimal and evenly distributed connections to water boundaries |
| Delaunay Triangulation | **EXPERIMENTAL** | Uses Delaunay triangulation for terrain representation | For more natural terrain representation (still under development) |
| Boundary Hexagon Layer | **STABLE** | Preserves hexagons at water boundaries for better connectivity with enhanced land portion connectivity | For optimal connectivity between land portions and the rest of the terrain |

## Key Features

- **Consistent CRS Usage**: Uses EPSG:3857 (Web Mercator) for all internal processing, ensuring accurate metric-based measurements
- **Improved Water Feature Processing**: Enhanced water feature extraction, buffering, and dissolving with proper CRS handling
- **Hexagonal Terrain Grid**: Uses a hexagonal grid for more natural terrain representation and movement patterns
- **Multiple Water Handling Approaches**:
  - **Improved Water Edge Creation**: Advanced algorithms for creating water crossing edges with better graph connectivity
  - **Water Boundary Approach**: Treats water obstacles as navigable boundaries rather than impassable barriers
  - **Direct Water Boundary Conversion**: Directly converts water obstacle polygons to graph elements
  - **Line-to-Point Connection Strategy**: Connects terrain nodes to the closest point on water boundaries for more direct and natural connections
  - **Voronoi Connection Strategy**: Uses Voronoi diagrams to create more natural and evenly distributed connections between terrain and water obstacles
- **Configurable Parameters**: Extensive configuration options for water features, terrain grid, and environmental conditions
- **Comprehensive Testing**: Automated tests to verify CRS consistency and quality
- **Visualization Tools**: Tools for visualizing the terrain graph, water obstacles, and different approaches

## Directory Structure

The project is organized into the following directories:

```
epsg3857_pipeline/
├── core/                  # Core production pipeline components
│   ├── scripts/           # Main pipeline scripts
│   ├── sql/               # SQL scripts for the core pipeline
│   ├── tests/             # Test scripts for the core pipeline
│   ├── utils/             # Utility modules
│   └── obstacle_boundary/ # Obstacle boundary implementation
├── tools/                 # Support tools for development and maintenance
│   ├── database/          # Database management tools
│   └── diagnostics/       # Diagnostic tools
├── alternatives/          # Alternative approaches (stable but not primary)
│   ├── standard/          # Original standard approach
│   ├── fixed/             # Fixed water edge creation approach
│   ├── water_boundary/    # Water boundary approach
│   └── obstacle_boundary/ # Obstacle boundary approach
├── experimental/          # Experimental features (under development)
│   └── delaunay/          # Delaunay triangulation approach
├── config/                # Configuration files
├── docs/                  # Documentation
├── tests/                 # Integration tests
└── visualizations/        # Visualization outputs
```

## Quick Start Guide

### Prerequisites

- Docker with PostgreSQL/PostGIS container running
- Python 3.8+ with required dependencies
- OSM data for the area of interest

### 1. Import OSM Data

Before running the pipeline, import OpenStreetMap (OSM) data into the PostGIS database:

```bash
# Import OSM data from a PBF file
python epsg3857_pipeline/core/scripts/import_osm_data.py --osm-file data/subsets/iowa-latest.osm.pbf

# Specify a different container name
python epsg3857_pipeline/core/scripts/import_osm_data.py --osm-file data/subsets/iowa-latest.osm.pbf --container geo-graph-db-1

# Enable verbose logging
python epsg3857_pipeline/core/scripts/import_osm_data.py --osm-file data/subsets/iowa-latest.osm.pbf --verbose
```

### 2. Run the Pipeline

Choose the appropriate pipeline approach based on your needs:

#### Standard Pipeline (Recommended for most cases)

```bash
# Run the standard pipeline with improved water edge creation (default)
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard

# Run with verbose output
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --verbose
```

#### Water Boundary Approach

```bash
# Run the water boundary approach
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --water-boundary
```

#### Obstacle Boundary Approach

```bash
# Run the obstacle boundary pipeline
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py

# Run with custom parameters
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py --storage-srid 3857 --max-connection-distance 300 --water-speed-factor 0.2
```

#### Hexagon Obstacle Boundary

```bash
# Run the hexagon obstacle boundary pipeline
python epsg3857_pipeline/run_hexagon_obstacle_boundary_pipeline.py

# Run with visualization
python epsg3857_pipeline/run_hexagon_obstacle_boundary_pipeline.py --visualize

# Run with custom parameters
python epsg3857_pipeline/run_hexagon_obstacle_boundary_pipeline.py --config epsg3857_pipeline/config/hexagon_obstacle_boundary_config.json --verbose
```

#### Voronoi Obstacle Boundary

```bash
# Run the Voronoi obstacle boundary pipeline
python epsg3857_pipeline/run_voronoi_obstacle_boundary_pipeline.py

# Run with visualization and show Voronoi cells
python epsg3857_pipeline/run_voronoi_obstacle_boundary_pipeline.py --visualize --show-voronoi

# Run with custom parameters
python epsg3857_pipeline/run_voronoi_obstacle_boundary_pipeline.py --config epsg3857_pipeline/config/voronoi_obstacle_boundary_config.json --verbose
```

#### Delaunay Triangulation (Experimental)

```bash
# Run the Delaunay triangulation pipeline
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode delaunay
```

### 3. Export a Graph Slice

```bash
# Export a graph slice around a specific coordinate
python epsg3857_pipeline/core/scripts/export_slice.py --lon -93.63 --lat 41.99 --minutes 60 --outfile iowa_central_3857.graphml
```

### 4. Visualize the Results

```bash
# Visualize the graph
python epsg3857_pipeline/core/scripts/visualize.py --mode graphml --input iowa_central_3857.graphml

# Visualize water obstacles
python epsg3857_pipeline/core/scripts/visualize.py --mode water

# Visualize the obstacle boundary graph
python epsg3857_pipeline/core/obstacle_boundary/visualize.py --output obstacle_boundary_graph.png

# Visualize the hexagon obstacle boundary graph
python epsg3857_pipeline/core/scripts/visualize_hexagon_obstacle_boundary.py --output hexagon_obstacle_boundary.png

# Visualize the hexagon obstacle boundary components
python epsg3857_pipeline/core/scripts/visualize_hexagon_obstacle_boundary_components.py --output hexagon_components.png

# Visualize the Voronoi obstacle boundary graph
python epsg3857_pipeline/core/scripts/visualize_voronoi_obstacle_boundary.py --output voronoi_obstacle_boundary.png

# Visualize the Voronoi obstacle boundary with Voronoi cells
python epsg3857_pipeline/core/scripts/visualize_voronoi_obstacle_boundary.py --show-voronoi --output voronoi_cells.png

# Visualize the boundary hexagon layer
python epsg3857_pipeline/core/scripts/visualize_boundary_hexagon_layer.py --output boundary_hexagon_layer.png

# Visualize the unified boundary graph
python epsg3857_pipeline/core/scripts/visualize_unified_boundary_graph.py --output unified_boundary_graph.png
```

## Pipeline Approaches in Detail

### Standard Pipeline

The standard pipeline creates a hexagonal terrain grid that avoids water obstacles and connects grid points with edges. It uses an improved water edge creation algorithm that ensures better graph connectivity.

Key features:
- Hexagonal grid for more natural terrain representation
- Improved water edge creation for better connectivity
- Environmental conditions for realistic travel costs

```bash
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard
```

### Water Boundary Approach

The water boundary approach treats water obstacles as navigable boundaries rather than impassable barriers. It creates edges along the perimeter of water obstacles and connects terrain grid points to water boundary points.

Key features:
- Edges along water boundaries for navigation
- Connections between terrain and water boundaries
- Full graph connectivity

```bash
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --water-boundary
```

### Obstacle Boundary Approach

The obstacle boundary approach directly converts water obstacle polygons to graph elements, creating a more precise representation of water boundaries.

Key features:
- Precise water boundary representation
- Optimal connectivity between terrain and water boundaries
- Clean boundary representation

```bash
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py
```

### Hexagon Obstacle Boundary

The hexagon obstacle boundary approach combines a hexagonal terrain grid with precise water obstacle boundaries. It classifies hexagons as 'land', 'boundary', or 'water' to create a more natural representation of the terrain and water boundaries.

Key features:
- Hexagonal grid for more natural terrain representation
- Classification of hexagons for better boundary representation
- Precise water boundary representation with optimal connectivity
- Natural connections between terrain and water boundaries

```bash
python epsg3857_pipeline/run_hexagon_obstacle_boundary_pipeline.py
```

### Voronoi Obstacle Boundary

The Voronoi obstacle boundary approach uses Voronoi diagrams to create more natural and evenly distributed connections between terrain and water obstacles. It partitions the space around water boundary nodes into Voronoi cells, which are used to determine which terrain nodes connect to which boundary nodes.

Key features:
- Voronoi partitioning for optimal connection assignment
- Even distribution of connections to water boundaries
- Prevents connection clustering and ensures good coverage
- More natural and intuitive navigation around water obstacles

```bash
python epsg3857_pipeline/run_voronoi_obstacle_boundary_pipeline.py
```

### Boundary Hexagon Layer

The boundary hexagon layer approach preserves hexagons at water boundaries for better connectivity and uses land portions of water hexagons to connect boundary nodes to water boundary nodes. It includes enhanced connectivity between land portion nodes and land/boundary nodes.

Key features:
- Preserves hexagons at water boundaries
- Identifies land portions within water hexagons
- Creates connections between boundary nodes, water boundary nodes, and land portion nodes
- Enhanced connectivity between land portion nodes and land/boundary nodes
- Unified boundary graph with terrain edges

```bash
# Run the boundary hexagon layer pipeline
python epsg3857_pipeline/run_boundary_hexagon_layer_pipeline.py

# Run the enhanced boundary hexagon layer pipeline with improved land portion connectivity
python epsg3857_pipeline/run_boundary_hexagon_layer_enhanced_pipeline.py

# Run with visualization
python epsg3857_pipeline/run_boundary_hexagon_layer_pipeline.py --visualize

# Run with custom parameters
python epsg3857_pipeline/run_boundary_hexagon_layer_pipeline.py --config epsg3857_pipeline/config/boundary_hexagon_layer_config.json --verbose
```

### Delaunay Triangulation (Experimental)

The Delaunay triangulation approach uses Delaunay triangulation for terrain grid generation, which provides a more natural terrain representation.

Key features:
- More natural terrain representation
- Better adaptation to water boundaries
- Optimal connectivity

```bash
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode delaunay
```

## Configuration

The pipeline is configured using JSON files in the `epsg3857_pipeline/config/` directory:

- `crs_standardized_config.json`: Configuration for the standard pipeline
- `crs_standardized_config_improved.json`: Configuration with improved water edge creation parameters
- `crs_standardized_config_boundary.json`: Configuration for the water boundary approach
- `hexagon_obstacle_boundary_config.json`: Configuration for the hexagon obstacle boundary approach
- `voronoi_obstacle_boundary_config.json`: Configuration for the Voronoi obstacle boundary approach
- `delaunay_config.json`: Configuration for the Delaunay triangulation pipeline

### Example Configuration

```json
{
  "crs": {
    "storage": 3857,
    "export": 4326,
    "analysis": 3857
  },
  "water_features": {
    "polygon_types": ["water", "natural", "reservoir"],
    "line_types": ["river", "stream", "canal", "drain", "ditch"]
  },
  "water_buffers": {
    "default": 50,
    "lake": 100,
    "river": 75,
    "stream": 30
  },
  "terrain_grid": {
    "grid_spacing": 200,
    "max_edge_length": 500
  },
  "water_crossing": {
    "connectivity_check_enabled": true,
    "max_crossing_distance": 2000,
    "crossing_strategies": {
      "lake": "ferry",
      "river": "bridge",
      "stream": "ford"
    },
    "speed_factors": {
      "ferry": 0.2,
      "bridge": 0.8,
      "ford": 0.5,
      "connectivity": 0.2
    }
  },
  "environmental_conditions": {
    "default_speed": 5.0,
    "water_speed_factor": 0.2,
    "uphill_speed_factor": 0.8,
    "downhill_speed_factor": 1.2
  }
}
```

## Database Management

The pipeline includes several scripts for managing the database:

```bash
# Reset only the derived tables (preserves OSM data)
python epsg3857_pipeline/tools/database/reset_derived_tables.py

# Dynamically identify and reset all non-OSM tables (preserves OSM data)
python epsg3857_pipeline/tools/database/reset_non_osm_tables.py

# Reset all tables (including OSM data)
python epsg3857_pipeline/tools/database/reset_all_tables.py
```

## Running Tests

```bash
# Run all tests
./epsg3857_pipeline/run_tests.sh

# Run only standard pipeline tests
./epsg3857_pipeline/run_tests.sh --standard-only

# Run only Delaunay triangulation tests
./epsg3857_pipeline/run_tests.sh --delaunay-only

# Run only hexagon obstacle boundary tests
./epsg3857_pipeline/run_tests.sh --hexagon-obstacle-only

# Run only Voronoi obstacle boundary tests
./epsg3857_pipeline/run_tests.sh --voronoi-obstacle-only

# Run tests with verbose output
./epsg3857_pipeline/run_tests.sh --verbose
```

### Voronoi Connection Strategies Test Suite

The project includes a dedicated test suite for comparing different connection strategies for connecting terrain grid points to water obstacle boundaries:

```bash
# Run the Voronoi connection strategies test
./run_voronoi_test.sh

# Show Voronoi cells in the visualization
./run_voronoi_test.sh --show-cells

# Skip running the SQL script (if you've already run it)
./run_voronoi_test.sh --skip-sql

# For more options
./run_voronoi_test.sh --help
```

This test suite compares four different connection strategies:
1. **Simple Nearest Neighbor**: Basic approach connecting to the closest boundary node
2. **Line-to-Point Connection**: Creates direct connections to the boundary
3. **Standard Voronoi Connection**: Uses Voronoi cells for boundary nodes
4. **Reversed Voronoi Connection**: Creates Voronoi cells for terrain points

The test generates visualizations in the `visualizations` directory showing the different strategies side by side and analyzing the distribution of connections.

## Troubleshooting

### Common Issues

- **Memory errors during dissolve step**: Increase the `work_mem` parameter in the SQL script
- **Slow performance**: Enable parallel query execution and optimize the SQL queries
- **Simplification issues**: Adjust the simplification tolerance in the SQL script
- **Missing water features**: Check the water feature extraction parameters in the configuration
- **Path issues**: Ensure that paths in scripts are correctly specified relative to the current working directory
- **Docker connectivity**: Make sure the Docker containers are running before executing scripts that interact with the database
- **Graph connectivity issues**: If you encounter graph connectivity issues, use the improved water edge creation algorithm (default) or consider the water boundary or obstacle boundary approaches.

### Graph Connectivity

If you encounter issues with graph connectivity (e.g., paths cannot be found between certain points), consider:

1. Using the water boundary approach with the `--water-boundary` flag
2. Using the direct water obstacle boundary conversion approach with the `run_obstacle_boundary_pipeline.py` script
3. Checking if water edges are being created (the water_edges table should not be empty)
4. Adjusting the relevant parameters in the configuration file
5. Using the visualization tools to identify disconnected components in the graph

## Comparing Pipelines

To easily compare different pipeline approaches, you can use the provided comparison script:

```bash
# Run both standard and obstacle boundary pipelines
./epsg3857_pipeline/compare_pipelines.sh

# Run with visualization
./epsg3857_pipeline/compare_pipelines.sh --visualize

# Run with graph slice export
./epsg3857_pipeline/compare_pipelines.sh --export-slice

# Run with custom coordinates and travel time
./epsg3857_pipeline/compare_pipelines.sh --coordinates "-93.63 41.99" --travel-time 60

# Run with all options
./epsg3857_pipeline/compare_pipelines.sh --verbose --visualize --export-slice
```

This script will run both pipelines in sequence and provide outputs for comparison.

## Documentation

For more detailed documentation, see:

- [Database Schema](./docs/database_schema.md) - Detailed database schema documentation
- [Project Organization](./docs/project_organization.md) - Overview of project structure and components
- [Water Edge Creation Proposal](./docs/water_edge_creation_proposal.md) - Detailed proposal for improved water edge creation
- [Pipeline Approaches Guide](./docs/pipeline_approaches_guide.md) - Comprehensive guide to all pipeline approaches (Standard, Water Boundary, Obstacle Boundary, etc.)
- [Connection Strategies Guide](./docs/connection_strategies_guide.md) - Comprehensive guide to all connection strategies (Line-to-Point, Voronoi, Reversed Voronoi)
- [Obstacle Boundary Implementation](./docs/obstacle_boundary_implementation.md) - Implementation details of the obstacle boundary approach
- [Boundary Hexagon Layer Approach](./docs/boundary_hexagon_layer_approach.md) - Comprehensive documentation of the boundary hexagon layer approach
- [Enhanced Land Portion Connectivity](./docs/enhanced_land_portion_connectivity_summary.md) - Documentation of enhanced land portion connectivity implementation
- [Voronoi Connection Strategies Summary](./voronoi_connection_strategies_summary.md) - Comprehensive overview of different connection strategies
- [Pipeline Comparison Scripts](./docs/pipeline_comparison_scripts.md) - Comprehensive reference for running different pipelines
- [Development Worklog](./worklog.md) - Track development progress, issues, and solutions
- [Test Plan](./test_plan.md) - Comprehensive testing strategy and test cases
