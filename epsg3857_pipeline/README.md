# EPSG:3857 Terrain Graph Pipeline

A standardized pipeline for terrain graph generation using EPSG:3857 (Web Mercator) for consistent and accurate spatial operations.

## Overview

This pipeline addresses the coordinate reference system (CRS) inconsistency issues in the original terrain graph pipeline by standardizing on EPSG:3857 (Web Mercator) for all internal processing. It also includes an enhanced Delaunay triangulation approach for more natural terrain representation.

## Key Features

- **Consistent CRS Usage**: Uses EPSG:3857 (Web Mercator) for all internal processing, ensuring accurate metric-based measurements
- **Delaunay Triangulation**: Optional terrain grid generation using Delaunay triangulation for more natural terrain representation
- **Improved Water Feature Processing**: Enhanced water feature extraction, buffering, and dissolving with proper CRS handling
- **Configurable Parameters**: Extensive configuration options for water features, terrain grid, and environmental conditions
- **Comprehensive Testing**: Automated tests to verify CRS consistency and triangulation quality
- **Visualization Tools**: Tools for visualizing the terrain graph, water obstacles, and Delaunay triangulation

## Directory Structure

```
epsg3857_pipeline/
├── config/                 # Configuration files
│   ├── crs_standardized_config.json  # Standard EPSG:3857 config
│   └── delaunay_config.json          # Delaunay triangulation config
├── tests/                  # Test scripts
│   ├── test_epsg3857_pipeline.py     # Tests for standard pipeline
│   └── test_delaunay_pipeline.py     # Tests for Delaunay pipeline
├── run_epsg3857_pipeline.py  # Main pipeline script
└── run_tests.sh              # Test runner script
```

## Usage

### Running the Standard Pipeline

```bash
# Reset the database (if needed)
python scripts/reset_database.py --reset-derived

# Run the standard EPSG:3857 pipeline
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --config epsg3857_pipeline/config/crs_standardized_config.json
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
  "terrain_grid_delaunay": {
    "grid_spacing": 200,
    "boundary_point_spacing": 100,
    "simplify_tolerance": 5
  }
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
- [Development Worklog](./worklog.md) - Track development progress, issues, and solutions
- [Test Plan](./test_plan.md) - Comprehensive testing strategy and test cases

## License

This project is licensed under the MIT License - see the LICENSE file for details.
