# EPSG:3857 Terrain Graph Pipeline

A standardized pipeline for terrain graph generation using EPSG:3857 (Web Mercator) for consistent and accurate spatial operations.

## Overview

This pipeline addresses the coordinate reference system (CRS) inconsistency issues in the original terrain graph pipeline by standardizing on EPSG:3857 (Web Mercator) for all internal processing. It also includes an enhanced Delaunay triangulation approach for more natural terrain representation.

## Key Features

- **Consistent CRS Usage**: Uses EPSG:3857 (Web Mercator) for all internal processing, ensuring accurate metric-based measurements
- **Delaunay Triangulation**: Optional terrain grid generation using Delaunay triangulation for more natural terrain representation
- **Improved Water Feature Processing**: Enhanced water feature extraction, buffering, and dissolving with proper CRS handling
- **Hexagonal Terrain Grid**: Uses a hexagonal grid for more natural terrain representation and movement patterns
- **Improved Water Edge Creation**: Advanced algorithms for creating water crossing edges with better graph connectivity
- **Water Boundary Approach**: Innovative approach that treats water obstacles as navigable boundaries rather than impassable barriers
- **Direct Water Boundary Conversion**: Approach that directly converts water obstacle polygons to graph elements for clean boundary representation
- **Configurable Parameters**: Extensive configuration options for water features, terrain grid, and environmental conditions
- **Comprehensive Testing**: Automated tests to verify CRS consistency and triangulation quality
- **Visualization Tools**: Tools for visualizing the terrain graph, water obstacles, and Delaunay triangulation

## Directory Structure

```
epsg3857_pipeline/
├── config/                 # Configuration files
│   ├── crs_standardized_config.json         # Standard EPSG:3857 config
│   ├── crs_standardized_config_improved.json # Config with improved water edge creation
│   ├── crs_standardized_config_boundary.json # Config with water boundary approach
│   └── delaunay_config.json                 # Delaunay triangulation config
├── docs/                   # Documentation
│   ├── database_schema.md                   # Database schema documentation
│   ├── project_organization.md              # Project structure overview
│   ├── water_edge_creation_proposal.md      # Water edge creation proposal
│   ├── water_boundary_approach.md           # Water boundary approach documentation
│   └── direct_water_boundary_conversion.md  # Direct water boundary conversion documentation
├── scripts/                # Python scripts
│   ├── config_loader_3857.py                # Configuration loader
│   ├── reset_database.py                    # Database reset utility
│   ├── run_water_obstacle_pipeline_crs.py   # Standard pipeline runner
│   ├── run_water_obstacle_pipeline_improved.py # Improved pipeline runner
│   ├── run_water_obstacle_pipeline_boundary.py # Water boundary approach runner
│   └── run_water_obstacle_pipeline_delaunay.py # Delaunay pipeline runner
├── sql/                    # SQL scripts
│   ├── 01_extract_water_features_3857.sql   # Extract water features
│   ├── 02_create_water_buffers_3857.sql     # Create water buffers
│   ├── 03_dissolve_water_buffers_3857.sql   # Dissolve water buffers
│   ├── 04_create_terrain_grid_3857.sql      # Create terrain grid
│   ├── 04_create_terrain_grid_with_water_3857.sql # Terrain grid with water
│   ├── 05_create_terrain_edges_3857.sql     # Create terrain edges
│   ├── 05_create_terrain_edges_with_water_3857.sql # Terrain edges with water
│   ├── 06_create_water_edges_3857.sql       # Create water edges
│   ├── 06_create_water_edges_improved_3857.sql # Improved water edges
│   ├── 06_create_water_boundary_edges_3857.sql # Water boundary edges
│   └── 07_create_environmental_tables_3857.sql # Create environmental tables
├── tests/                  # Test scripts
│   ├── test_epsg3857_pipeline.py            # Tests for standard pipeline
│   └── test_delaunay_pipeline.py            # Tests for Delaunay pipeline
├── epsg3857_pipeline_repair_log.md          # Repair log
├── run_epsg3857_pipeline.py                 # Main pipeline script
├── run_tests.sh                             # Test runner script
└── worklog.md                               # Development worklog
```

## Usage

### Running the Standard Pipeline

```bash
# Reset the database (if needed)
python scripts/reset_database.py --reset-derived

# Run the standard EPSG:3857 pipeline
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --config epsg3857_pipeline/config/crs_standardized_config.json

# Run the standard pipeline with improved water edge creation
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --improved-water-edges --config epsg3857_pipeline/config/crs_standardized_config_improved.json

# Run the standard pipeline with water boundary approach
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --water-boundary --config epsg3857_pipeline/config/crs_standardized_config_boundary.json

# Run the direct water obstacle boundary conversion
python epsg3857_pipeline/scripts/run_obstacle_boundary_graph.py

# Visualize the obstacle boundary graph
python epsg3857_pipeline/scripts/visualize_obstacle_boundary_graph.py --output obstacle_boundary_graph.png
```

### Running the Delaunay Triangulation Pipeline

```bash
# Reset the database (if needed)
python scripts/reset_database.py --reset-derived

# Run the Delaunay triangulation pipeline
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode delaunay --config epsg3857_pipeline/config/delaunay_config.json
```

### Running the Unified Delaunay Pipeline for Large Datasets

```bash
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode unified-delaunay --threads 8 --chunk-size 5000
```

### Exporting a Graph Slice

```bash
# Export a graph slice around a specific coordinate
python epsg3857_pipeline/run_epsg3857_pipeline.py --export --lon -93.63 --lat 41.99 --minutes 60 --outfile iowa_central_3857.graphml
```

### Visualizing the Results

```bash
# Visualize the graph
python epsg3857_pipeline/run_epsg3857_pipeline.py --visualize --viz-mode graphml --input iowa_central_3857.graphml

# Visualize water obstacles
python epsg3857_pipeline/run_epsg3857_pipeline.py --visualize --viz-mode water

# Visualize Delaunay triangulation
python epsg3857_pipeline/run_epsg3857_pipeline.py --visualize --viz-mode delaunay
```

### Running Tests

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

## Configuration

The pipeline is configured using JSON files in the `epsg3857_pipeline/config/` directory:

- `crs_standardized_config.json`: Configuration for the standard EPSG:3857 pipeline
- `crs_standardized_config_improved.json`: Configuration with improved water edge creation parameters
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
  "terrain_grid_delaunay": {
    "grid_spacing": 200,
    "boundary_point_spacing": 100,
    "simplify_tolerance": 5,
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
  },
  "simplify_tolerance": 5
}
```

## Data Model

### Water Features

The water features are stored using a typed table approach:

- **water_features_polygon**: Contains polygon water features (lakes, reservoirs)
- **water_features_line**: Contains line water features (rivers, streams)
- **water_features**: View that unifies both tables for backward compatibility

This design provides type safety, performance benefits, and a clearer data model
while maintaining compatibility with existing code through the view.

When querying:
- Use `water_features_polygon` or `water_features_line` directly when you only need one geometry type
- Use the `water_features` view when you need both types or for backward compatibility

### Terrain Grid

The terrain grid uses a hexagonal grid approach:

- **terrain_grid**: Contains hexagonal grid cells that avoid water obstacles
- **terrain_grid_points**: Contains the centroids of the grid cells, used for connectivity

Benefits of the hexagonal grid:
- More natural-looking terrain representation
- Equal distances between adjacent cells
- Better adaptation to natural features
- More efficient movement patterns

The terrain grid is created by:
1. Generating a hexagonal grid covering the extent of the data
2. Filtering out cells that intersect with water obstacles
3. Creating centroids for each cell for connectivity

## Pipeline Stages

1. **Extract Water Features**: Extract water features from OSM data with EPSG:3857 coordinates into typed tables
2. **Create Water Buffers**: Create buffers around water features using metric distances
3. **Dissolve Water Buffers**: Dissolve overlapping water buffers with proper simplification
4. **Create Terrain Grid**: Create a terrain grid using either a regular grid or Delaunay triangulation
5. **Create Terrain Edges**: Create terrain edges connecting grid cells
6. **Create Water Edges**: Create water edges representing water obstacles
7. **Create Environmental Tables**: Add environmental conditions to the water edges
8. **Create Unified Edges**: Combine all edge tables into a unified graph
9. **Create Topology**: Create topology for the unified graph
10. **Export Graph Slice**: Export a slice of the graph around a specific coordinate

## Benefits

- **Improved Accuracy**: Using EPSG:3857 for internal processing ensures accurate metric-based measurements
- **Consistent Buffer Sizes**: Buffer sizes are specified in meters, which is more intuitive and consistent
- **Better Performance**: Using a single CRS throughout the pipeline reduces coordinate transformations
- **More Natural Terrain**: Delaunay triangulation provides a more natural terrain representation
- **Better Adaptation to Water Boundaries**: The triangulation follows the contours of water features more naturally
- **Optimal Connectivity**: The triangulation creates an optimal set of connections between points

## Advanced Options

### Unified Delaunay Pipeline

The unified Delaunay pipeline is designed for processing large geographic areas efficiently by:

1. Partitioning the data into manageable spatial chunks
2. Processing each chunk in parallel
3. Merging the results into a unified dataset
4. Optimizing memory usage and performance

To run the unified Delaunay pipeline with custom settings:

```bash
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode unified-delaunay --threads 8 --chunk-size 10000
```

## Troubleshooting

### Common Issues

- **Memory errors during dissolve step**: Increase the `work_mem` parameter in the SQL script
- **Slow performance**: Enable parallel query execution and optimize the SQL queries
- **Simplification issues**: Adjust the simplification tolerance in the SQL script
- **Missing water features**: Check the water feature extraction parameters in the configuration
- **Path issues**: Ensure that paths in scripts are correctly specified relative to the current working directory
- **Docker connectivity**: Make sure the Docker containers are running before executing scripts that interact with the database
- **Graph connectivity issues**: If you encounter graph connectivity issues, use the improved water edge creation algorithm with the `--improved-water-edges` flag, which includes automatic connectivity verification and edge addition.

### Graph Connectivity

If you encounter issues with graph connectivity (e.g., paths cannot be found between certain points), consider:

1. Using the water boundary approach with the `--water-boundary` flag, which:
   - Treats water obstacles as navigable boundaries rather than impassable barriers
   - Creates edges along the perimeter of water obstacles
   - Connects terrain grid points to water boundary points
   - Ensures full graph connectivity with a connectivity verification step

2. Alternatively, using the improved water edge creation algorithm with the `--improved-water-edges` flag, which includes:
   - Water body classification based on shape, size, and type
   - Optimal crossing point identification for different water body types
   - Graph connectivity verification and automatic edge addition

3. Checking if water edges are being created (the water_edges table should not be empty)
4. Adjusting the relevant parameters in the configuration file
5. Using the visualization tools to identify disconnected components in the graph

### Debugging

- Use the `--verbose` flag with the runner scripts to see more detailed output
- Check the SQL queries in the SQL scripts to ensure they are correctly extracting and processing the data
- Use the visualization script to visualize the results and check if they look correct
- Check the log files (`epsg3857_pipeline.log`, `test_epsg3857_pipeline.log`, `test_delaunay_pipeline.log`) for detailed error messages
- Run tests with the `--verbose` flag to get more detailed output about what's happening during test execution

## Documentation

For more detailed documentation, see:

- [CRS Standardization Plan](../docs/crs_standardization_plan.md)
- [Delaunay Triangulation Implementation](../docs/delaunay_triangulation_implementation.md)
- [Unified Delaunay Pipeline](../docs/unified_delaunay_pipeline.md)
- [EPSG Consistency Summary](../docs/epsg_consistency_summary.md)
- [Database Schema](./docs/database_schema.md) - Detailed database schema documentation
- [Project Organization](./docs/project_organization.md) - Overview of project structure and components
- [Water Edge Creation Proposal](./docs/water_edge_creation_proposal.md) - Detailed proposal for improved water edge creation
- [Water Boundary Approach](./docs/water_boundary_approach.md) - Detailed documentation of the water boundary approach
- [Direct Water Boundary Conversion](./docs/direct_water_boundary_conversion.md) - Documentation of the direct water boundary conversion approach
- [Development Worklog](./worklog.md) - Track development progress, issues, and solutions
- [Test Plan](./test_plan.md) - Comprehensive testing strategy and test cases

## License

This project is licensed under the MIT License - see the LICENSE file for details.
