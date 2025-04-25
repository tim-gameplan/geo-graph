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
| Delaunay Triangulation | **EXPERIMENTAL** | Uses Delaunay triangulation for terrain representation | For more natural terrain representation (still under development) |
| Boundary Hexagon Layer | **PLANNED** | Preserves hexagons at water boundaries for better connectivity | To address "white space" issues between terrain and water |

## Key Features

- **Consistent CRS Usage**: Uses EPSG:3857 (Web Mercator) for all internal processing, ensuring accurate metric-based measurements
- **Improved Water Feature Processing**: Enhanced water feature extraction, buffering, and dissolving with proper CRS handling
- **Hexagonal Terrain Grid**: Uses a hexagonal grid for more natural terrain representation and movement patterns
- **Multiple Water Handling Approaches**:
  - **Improved Water Edge Creation**: Advanced algorithms for creating water crossing edges with better graph connectivity
  - **Water Boundary Approach**: Treats water obstacles as navigable boundaries rather than impassable barriers
  - **Direct Water Boundary Conversion**: Directly converts water obstacle polygons to graph elements
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

# Run tests with verbose output
./epsg3857_pipeline/run_tests.sh --verbose
```

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

## Documentation

For more detailed documentation, see:

- [Database Schema](./docs/database_schema.md) - Detailed database schema documentation
- [Project Organization](./docs/project_organization.md) - Overview of project structure and components
- [Water Edge Creation Proposal](./docs/water_edge_creation_proposal.md) - Detailed proposal for improved water edge creation
- [Water Boundary Approach](./docs/water_boundary_approach.md) - Detailed documentation of the water boundary approach
- [Direct Water Boundary Conversion](./docs/direct_water_boundary_conversion.md) - Documentation of the direct water boundary conversion approach
- [Development Worklog](./worklog.md) - Track development progress, issues, and solutions
- [Test Plan](./test_plan.md) - Comprehensive testing strategy and test cases
