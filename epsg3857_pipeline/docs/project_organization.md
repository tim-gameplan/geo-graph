# EPSG:3857 Pipeline Project Organization

This document provides an overview of the EPSG:3857 pipeline project organization, including file structure, key components, and recommendations for future development.

## Project Structure

The EPSG:3857 pipeline is organized into the following directories:

```
epsg3857_pipeline/
├── config/                 # Configuration files
│   ├── crs_standardized_config.json         # Standard EPSG:3857 config
│   ├── crs_standardized_config_improved.json # Config with improved water edge creation
│   ├── crs_standardized_config_boundary.json # Config with water boundary approach
│   └── delaunay_config.json                 # Delaunay triangulation config
├── core/                   # Core implementation
│   ├── scripts/            # Python scripts
│   │   ├── config_loader_3857.py            # Configuration loader
│   │   ├── export_slice.py                  # Graph slice export utility
│   │   ├── import_osm_data.py               # OSM data import utility
│   │   ├── reset_database.py                # Database reset utility
│   │   ├── run_epsg3857_pipeline.py         # Main pipeline script
│   │   ├── run_water_obstacle_pipeline_improved.py # Improved pipeline runner
│   │   └── visualize.py                     # Visualization utility
│   ├── sql/                # SQL scripts
│   │   ├── 01_extract_water_features_3857.sql   # Extract water features
│   │   ├── 02_create_water_buffers_3857.sql     # Create water buffers
│   │   ├── 03_dissolve_water_buffers_3857.sql   # Dissolve water buffers
│   │   ├── 04_create_terrain_grid_3857.sql      # Create terrain grid
│   │   ├── 05_create_terrain_edges_3857.sql     # Create terrain edges
│   │   ├── 06_create_water_edges_improved_3857.sql # Improved water edges
│   │   └── 07_create_environmental_tables_3857.sql # Create environmental tables
│   ├── tests/              # Test scripts
│   │   ├── test_epsg3857_pipeline.py            # Tests for standard pipeline
│   │   ├── test_delaunay_pipeline.py            # Tests for Delaunay pipeline
│   │   ├── test_water_boundary_approach.py      # Tests for water boundary approach
│   │   └── test_obstacle_boundary_graph.py      # Tests for obstacle boundary graph
│   ├── utils/              # Utility modules
│   │   ├── __init__.py                          # Package initialization
│   │   └── logging_utils.py                     # Logging utilities
│   └── obstacle_boundary/  # Obstacle boundary pipeline
│       ├── __init__.py                          # Package initialization
│       ├── create_obstacle_boundary_graph.sql   # SQL script for obstacle boundary graph
│       ├── run_obstacle_boundary_pipeline.py    # Pipeline runner
│       ├── visualize.py                         # Visualization utility
│       └── test.py                              # Test script
├── docs/                   # Documentation
│   ├── database_schema.md                   # Database schema documentation
│   ├── direct_water_boundary_conversion.md  # Direct water boundary conversion documentation
│   ├── obstacle_boundary_pipeline.md        # Obstacle boundary pipeline documentation
│   ├── project_organization.md              # This document
│   ├── water_boundary_approach.md           # Water boundary approach documentation
│   └── water_edge_creation_proposal.md      # Water edge creation proposal
├── tools/                  # Support tools
│   ├── database/           # Database management tools
│   │   ├── reset_all_tables.py              # Reset all tables
│   │   ├── reset_derived_tables.py          # Reset only derived tables
│   │   ├── reset_non_osm_tables.py          # Reset non-OSM tables
│   │   └── reset_osm_tables.py              # Reset only OSM tables
│   └── diagnostics/        # Diagnostic tools
│       └── diagnostic_water_edges.sql       # Diagnostic queries for water edges
├── alternatives/           # Alternative approaches
│   ├── standard/           # Original standard approach
│   ├── fixed/              # Fixed water edge creation approach
│   ├── water_boundary/     # Water boundary approach
│   └── obstacle_boundary/  # Obstacle boundary approach
├── experimental/           # Experimental features
│   └── delaunay/           # Delaunay triangulation approach
├── visualizations/         # Visualization outputs
├── epsg3857_pipeline_repair_log.md          # Repair log
├── README.md               # Project README
├── run_epsg3857_pipeline.py                 # Main pipeline script wrapper
├── run_obstacle_boundary_pipeline.py        # Obstacle boundary pipeline wrapper
├── run_tests.sh                             # Test runner script
├── test_plan.md                             # Comprehensive test plan
└── worklog.md                               # Development worklog
```

## Key Components

### 1. Pipeline Runner (`run_epsg3857_pipeline.py`)

The main entry point for the pipeline, which orchestrates the execution of the various pipeline stages. It supports different modes:
- Standard mode: Uses a regular hexagonal grid
- Delaunay mode: Uses Delaunay triangulation
- Unified Delaunay mode: Uses parallel processing for large datasets

### 2. Configuration System

- `config_loader_3857.py`: Loads and validates configuration files
- Configuration files in JSON format with parameters for:
  - Coordinate reference systems
  - Water feature types
  - Buffer sizes
  - Grid spacing
  - Environmental conditions

### 3. SQL Pipeline Stages

The pipeline consists of several SQL scripts that are executed in sequence:

1. **Extract Water Features** (`01_extract_water_features_3857.sql`):
   - Extracts water features from OSM data
   - Creates typed tables for polygon and line geometries
   - Creates a unified view for backward compatibility

2. **Create Water Buffers** (`02_create_water_buffers_3857.sql`):
   - Creates buffers around water features
   - Uses different buffer sizes for different water feature types

3. **Dissolve Water Buffers** (`03_dissolve_water_buffers_3857.sql`):
   - Dissolves overlapping water buffers
   - Simplifies the resulting geometry
   - Creates a table of water obstacles

4. **Create Terrain Grid** (`04_create_terrain_grid_3857.sql` or `04_create_terrain_grid_delaunay_3857.sql`):
   - Creates a terrain grid using either a hexagonal grid or Delaunay triangulation
   - Filters out grid cells that intersect with water obstacles
   - Creates centroids for connectivity

5. **Create Terrain Edges** (`05_create_terrain_edges_3857.sql` or `05_create_terrain_edges_delaunay_3857.sql`):
   - Creates edges between terrain grid points
   - Calculates edge lengths and costs
   - Excludes edges that intersect with water obstacles

6. **Create Water Edges** (`06_create_water_edges_3857.sql`):
   - Creates edges that cross water obstacles
   - Calculates edge lengths and costs with water speed factors
   - Creates a unified edges table combining terrain and water edges

7. **Create Environmental Tables** (`07_create_environmental_tables_3857.sql`):
   - Adds environmental conditions to edges
   - Calculates speed factors based on conditions

### 4. Data Model

The pipeline uses a typed table approach for better performance and type safety:

- **Water Features**:
  - `water_features_polygon`: Contains polygon water features (lakes, reservoirs)
  - `water_features_line`: Contains line water features (rivers, streams)
  - `water_features`: View that unifies both tables for backward compatibility

- **Terrain Grid**:
  - `terrain_grid`: Contains hexagonal grid cells that avoid water obstacles
  - `terrain_grid_points`: Contains the centroids of the grid cells, used for connectivity

- **Edges**:
  - `terrain_edges`: Contains edges between terrain grid points
  - `water_edges`: Contains edges that cross water obstacles
  - `unified_edges`: Combines terrain and water edges

### 5. Utilities

- `reset_database.py`: Resets the database tables
- `export_slice.py`: Exports a graph slice around a specific coordinate
- `visualize.py`: Visualizes the graph
- `visualize_delaunay_triangulation.py`: Visualizes Delaunay triangulation

### 6. Obstacle Boundary Pipeline

The obstacle boundary pipeline is a new approach that directly converts water obstacle polygons to graph elements:

1. **Extract Boundary Nodes** (`create_obstacle_boundary_graph.sql`):
   - Extracts vertices from water obstacles as graph nodes
   - Creates a table of obstacle boundary nodes with references to water obstacles

2. **Create Boundary Edges** (`create_obstacle_boundary_graph.sql`):
   - Creates edges between adjacent vertices along water boundaries
   - Calculates edge lengths and creates a table of obstacle boundary edges

3. **Connect Terrain to Boundary** (`create_obstacle_boundary_graph.sql`):
   - Connects terrain grid points to the nearest boundary nodes
   - Creates a table of obstacle boundary connection edges

4. **Create Unified Graph** (`create_obstacle_boundary_graph.sql`):
   - Combines terrain edges, boundary edges, and connection edges into a unified graph
   - Calculates edge costs based on edge type and speed factors

The obstacle boundary pipeline creates the following tables:
- `obstacle_boundary_nodes`: Vertices extracted from water obstacles
- `obstacle_boundary_edges`: Edges connecting adjacent vertices along water boundaries
- `obstacle_boundary_connection_edges`: Edges connecting terrain grid points to boundary nodes
- `unified_obstacle_edges`: A unified graph combining terrain edges, boundary edges, and connection edges

### 7. Testing

- `test_epsg3857_pipeline.py`: Tests for the standard pipeline
- `test_delaunay_pipeline.py`: Tests for the Delaunay triangulation pipeline
- `test_water_boundary_approach.py`: Tests for the water boundary approach
- `test_obstacle_boundary_graph.py`: Tests for the obstacle boundary pipeline
- `test_crs_standardization.py`: Tests for CRS standardization
- `test_delaunay_triangulation.py`: Tests for triangulation quality

## Recent Improvements

1. **Hexagonal Terrain Grid Implementation**:
   - Replaced the rectangular grid with a hexagonal grid using ST_HexagonGrid()
   - Created a two-table structure with terrain_grid (polygons) and terrain_grid_points (centroids)
   - Added proper spatial indexing for improved query performance
   - Implemented comprehensive logging for better diagnostics

2. **Water Edge Creation Improvements**:
   - Increased the distance threshold from 500m to 1000m to accommodate the actual distances between terrain points
   - Documented the need for a more robust water edge creation algorithm in future updates

3. **Obstacle Boundary Pipeline Implementation**:
   - Developed a new approach that directly converts water obstacle polygons to graph elements
   - Created a more precise representation of water boundaries for navigation
   - Implemented a unified graph that combines terrain edges, boundary edges, and connection edges
   - Added visualization tools for the obstacle boundary graph
   - Created comprehensive documentation for the obstacle boundary pipeline

4. **Database Management Improvements**:
   - Created new scripts for managing the database (reset_derived_tables.py, reset_non_osm_tables.py, etc.)
   - Implemented a dynamic approach to identify and reset non-OSM tables
   - Added safety features like confirmation prompts for potentially destructive operations
   - Improved error handling and logging in database management scripts

5. **Documentation Updates**:
   - Updated the worklog.md with details about the water edge creation issues and proposed solutions
   - Added a new section to the epsg3857_pipeline_repair_log.md about graph connectivity issues
   - Updated the database_schema.md to reflect the new terrain grid structure and obstacle boundary tables
   - Created a new obstacle_boundary_pipeline.md document with detailed information about the obstacle boundary pipeline
   - Updated the project_organization.md to reflect the new project structure and components

## Current Issues and Future Work

### 1. Graph Connectivity

The most critical issue is the graph connectivity problem, particularly with water edges not being created properly. Proposed solutions include:

- Develop a more robust algorithm for creating water crossing edges
- Consider different approaches for different types of water bodies (rivers vs lakes)
- Implement a graph connectivity check to ensure the final graph is fully connected
- Add a post-processing step to add necessary edges where connectivity is missing

### 2. Parameter Handling

There were issues with parameter naming and substitution in the SQL files:

- Parameter naming mismatch between SQL files and the config loader
- Issues with parameter substitution for parameters with suffixes like `_m`

These issues have been partially addressed, but a more comprehensive solution may be needed.

### 3. Performance Optimization

The pipeline can be slow for large datasets, particularly during the dissolve step. Proposed improvements include:

- Optimize the SQL queries with proper indexing and parallel execution
- Implement spatial partitioning for very large areas
- Increase the work_mem parameter for better performance during the dissolve step

## Recommendations for Future Development

### 1. Improve Water Edge Creation

The current approach for creating water edges has limitations:

- The distance threshold may not be appropriate for all datasets
- The requirement that edges must intersect water obstacles is too restrictive
- Large water bodies may not have terrain points that can form valid crossing edges

Recommendations:
- Develop a more sophisticated algorithm that considers the shape and size of water bodies
- Use different approaches for different types of water bodies (e.g., rivers vs lakes)
- Implement a post-processing step to ensure graph connectivity

### 2. Enhance Testing

The current tests focus on basic functionality, but more comprehensive tests are needed:

- Add tests for graph connectivity
- Add tests for edge costs and speed factors
- Add tests for different environmental conditions
- Add tests for different water body types and sizes

### 3. Improve Documentation

The documentation is good, but could be enhanced:

- Add more detailed explanations of the algorithms used
- Add more examples of how to use the pipeline for different scenarios
- Add more troubleshooting information
- Add more visualizations to illustrate the pipeline stages

### 4. Enhance Visualization

The current visualization tools are basic, but could be enhanced:

- Add more interactive visualizations
- Add the ability to visualize the graph with different edge costs
- Add the ability to visualize paths through the graph
- Add the ability to visualize the impact of different environmental conditions

### 5. Implement Graph Analysis Tools

The current pipeline focuses on graph creation, but tools for analyzing the graph would be useful:

- Add tools for finding shortest paths
- Add tools for analyzing graph connectivity
- Add tools for analyzing the impact of different environmental conditions
- Add tools for comparing different graph generation approaches

## Conclusion

The EPSG:3857 pipeline is a well-organized and comprehensive solution for terrain graph generation. The recent improvements, particularly the hexagonal grid implementation, have significantly enhanced the pipeline's capabilities. However, there are still issues to be addressed, particularly with graph connectivity. The recommendations outlined above should help guide future development efforts to make the pipeline even more robust and useful.
