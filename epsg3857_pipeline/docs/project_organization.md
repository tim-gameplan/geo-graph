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
│   ├── component_status.md                  # Status of each component
│   ├── database_schema.md                   # Database schema documentation
│   ├── direct_water_boundary_conversion.md  # Direct water boundary conversion documentation
│   ├── getting_started.md                   # Getting started guide
│   ├── obstacle_boundary_pipeline.md        # Obstacle boundary pipeline documentation
│   ├── pipeline_comparison.md               # Comparison of pipeline approaches
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

## Documentation Structure

The documentation is organized to help new engineers quickly understand the project and get started:

1. **README.md**: Main project documentation with an overview, key features, and usage examples
2. **Getting Started Guide** (`docs/getting_started.md`): Step-by-step guide for new engineers
3. **Component Status** (`docs/component_status.md`): Status of each component (stable, experimental, deprecated)
4. **Pipeline Comparison** (`docs/pipeline_comparison.md`): Detailed comparison of different pipeline approaches
5. **Project Organization** (`docs/project_organization.md`): This document, explaining the project structure
6. **Database Schema** (`docs/database_schema.md`): Detailed database schema documentation
7. **Approach-Specific Documentation**:
   - `docs/water_edge_creation_proposal.md`: Proposal for improved water edge creation
   - `docs/water_boundary_approach.md`: Documentation of the water boundary approach
   - `docs/direct_water_boundary_conversion.md`: Documentation of the direct water boundary conversion
   - `docs/obstacle_boundary_pipeline.md`: Documentation of the obstacle boundary pipeline
8. **Development Logs**:
   - `worklog.md`: Track of development progress, issues, and solutions
   - `epsg3857_pipeline_repair_log.md`: Log of repairs and fixes
9. **Test Documentation**:
   - `test_plan.md`: Comprehensive testing strategy and test cases

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

6. **Create Water Edges** (`06_create_water_edges_improved_3857.sql`):
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
- `import_osm_data.py`: Imports OSM data into the database

### 6. Database Management Tools

The pipeline includes several scripts for managing the database:

- `reset_derived_tables.py`: Resets only the derived tables (preserves OSM data)
- `reset_non_osm_tables.py`: Dynamically identifies and resets all non-OSM tables
- `reset_all_tables.py`: Resets all tables (including OSM data)
- `reset_osm_tables.py`: Resets only the OSM tables

### 7. Obstacle Boundary Pipeline

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

### 8. Pipeline Approaches

The project includes several approaches for generating terrain graphs:

1. **Standard Pipeline**: Basic pipeline with hexagonal grid and improved water edge creation
2. **Water Boundary Approach**: Treats water obstacles as navigable boundaries
3. **Obstacle Boundary Approach**: Directly converts water obstacle polygons to graph elements
4. **Delaunay Triangulation** (Experimental): Uses Delaunay triangulation for terrain representation
5. **Boundary Hexagon Layer** (Planned): Preserves hexagons at water boundaries for better connectivity

See `docs/pipeline_comparison.md` for a detailed comparison of these approaches.

### 9. Testing

- `test_epsg3857_pipeline.py`: Tests for the standard pipeline
- `test_delaunay_pipeline.py`: Tests for the Delaunay triangulation pipeline
- `test_water_boundary_approach.py`: Tests for the water boundary approach
- `test_obstacle_boundary_graph.py`: Tests for the obstacle boundary pipeline
- `test_crs_standardization.py`: Tests for CRS standardization
- `test_delaunay_triangulation.py`: Tests for triangulation quality

## Recent Improvements

1. **Documentation Improvements**:
   - Created a consolidated README.md with clear status indicators for different components
   - Added a component status document for quick reference
   - Created a getting started guide for new engineers
   - Added a pipeline comparison document to help choose the right approach
   - Updated the project organization document to reflect the current structure

2. **Hexagonal Terrain Grid Implementation**:
   - Replaced the rectangular grid with a hexagonal grid using ST_HexagonGrid()
   - Created a two-table structure with terrain_grid (polygons) and terrain_grid_points (centroids)
   - Added proper spatial indexing for improved query performance
   - Implemented comprehensive logging for better diagnostics

3. **Water Edge Creation Improvements**:
   - Increased the distance threshold from 500m to 1000m to accommodate the actual distances between terrain points
   - Documented the need for a more robust water edge creation algorithm in future updates

4. **Obstacle Boundary Pipeline Implementation**:
   - Developed a new approach that directly converts water obstacle polygons to graph elements
   - Created a more precise representation of water boundaries for navigation
   - Implemented a unified graph that combines terrain edges, boundary edges, and connection edges
   - Added visualization tools for the obstacle boundary graph
   - Created comprehensive documentation for the obstacle boundary pipeline

5. **Database Management Improvements**:
   - Created new scripts for managing the database (reset_derived_tables.py, reset_non_osm_tables.py, etc.)
   - Implemented a dynamic approach to identify and reset non-OSM tables
   - Added safety features like confirmation prompts for potentially destructive operations
   - Improved error handling and logging in database management scripts

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

### 4. Boundary Hexagon Layer Implementation

The boundary hexagon layer approach is planned but not yet implemented. This approach would:

- Preserve hexagons that intersect with water obstacles
- Create nodes on the land portion of boundary hexagons
- Connect boundary nodes to both terrain and obstacle nodes
- Fill the "white space" between terrain and water obstacles

## Recommendations for Future Development

### 1. Standardize Parameter Naming

Implement a consistent parameter naming convention across all SQL files and Python scripts. This will help avoid the parameter naming mismatch issues that have been encountered.

### 2. Implement Graph Connectivity Verification

Add a post-processing step to verify graph connectivity and add necessary edges where connectivity is missing. This will ensure that the graph is fully connected and can be used for pathfinding.

### 3. Optimize for Large Datasets

Implement spatial partitioning and parallel processing for large datasets. This will improve performance and allow the pipeline to handle larger areas.

### 4. Implement the Boundary Hexagon Layer Approach

Develop the planned boundary hexagon layer approach to address the "white space" issues between terrain and water obstacles. This will provide a more natural representation of water boundaries.

### 5. Improve Documentation

Continue to improve the documentation with more examples, diagrams, and explanations. This will help new engineers understand the project more quickly.

### 6. Expand Test Coverage

Add more comprehensive tests, particularly for edge cases and large datasets. This will help ensure the pipeline works correctly in all scenarios.

### 7. Refactor SQL Scripts

Refactor the SQL scripts to improve readability, performance, and maintainability. This may include breaking down complex queries, adding more comments, and optimizing for performance.

## Conclusion

The EPSG:3857 Terrain Graph Pipeline is a comprehensive solution for generating terrain graphs with accurate spatial operations. It addresses the coordinate reference system inconsistency issues in the original terrain graph pipeline and provides several approaches for different use cases.

The project is well-organized with clear separation of concerns and a modular design. The documentation has been improved to help new engineers understand the project and get started quickly.

While there are still some issues to address, particularly with graph connectivity and performance optimization, the pipeline is stable and ready for use in production environments.
