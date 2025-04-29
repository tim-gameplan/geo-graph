# Voronoi Connection Strategies

This directory contains tools for testing and comparing different strategies for connecting terrain grid points to water obstacle boundaries in the terrain graph pipeline.

## Overview

The connection between terrain grid points and water obstacle boundaries is a critical component of the terrain graph pipeline. It determines how vehicles can navigate from the terrain grid to water boundaries and affects the quality of pathfinding around water obstacles.

This test suite implements and compares four different connection strategies:

1. **Nearest Neighbor**: Each terrain point connects to its nearest boundary node
2. **Buffer-Based Voronoi**: Creates a "Voronoi-like" partitioning using buffers around boundary nodes
3. **True Voronoi**: Uses PostGIS's `ST_VoronoiPolygons` to create true Voronoi cells for boundary nodes
4. **Reversed Voronoi**: Creates Voronoi cells for boundary terrain points instead of boundary nodes

## Files

- `voronoi_connection_strategies_summary.md`: Comprehensive comparison of different connection strategies
- `voronoi_connection_test.sql`: SQL script that implements and tests the different strategies
- `run_voronoi_connection_test.py`: Python script that runs the SQL test and visualizes the results
- `run_voronoi_test.sh`: Shell script to run the test with various options
- `README.md`: This file

## Requirements

- PostgreSQL with PostGIS extension
- Python 3.8+ with the following packages:
  - psycopg2
  - pandas
  - numpy
  - matplotlib

## Usage

### Running the Test

```bash
# Run with default settings
./run_voronoi_test.sh

# Run with verbose output
./run_voronoi_test.sh --verbose

# Run with a custom output file
./run_voronoi_test.sh --output custom_results.png

# Run without visualization
./run_voronoi_test.sh --no-visualization

# Show help
./run_voronoi_test.sh --help
```

### Python Script Options

```bash
python3 run_voronoi_connection_test.py --help
```

Options:
- `--container`: Docker container name (default: geo-graph-db-1)
- `--output`: Output file name (default: voronoi_connection_test_results.png)
- `--verbose`: Enable verbose output
- `--no-visualization`: Skip visualization and only run the SQL test

## Test Methodology

The test creates a synthetic dataset with:
- Water obstacles (circular polygons)
- Terrain grid points (hexagonal grid)
- Boundary nodes (points along water obstacle boundaries)

For each connection strategy, it:
1. Creates connections between terrain points and boundary nodes
2. Measures the execution time
3. Calculates metrics (connection count, average length, evenness score)
4. Visualizes the results

## Metrics

The test calculates the following metrics for each strategy:

- **Connection Count**: Total number of connections created
- **Average Connection Length**: Average distance of connections
- **Execution Time**: Time taken to execute the strategy (in milliseconds)
- **Evenness Score**: Measure of how evenly connections are distributed (1.0 is perfectly even)

## Visualization

The test generates a visualization with:
- Four subplots, one for each strategy
- Water obstacles shown in blue
- Terrain points colored by type (green for boundary, yellow for land, blue for water)
- Boundary nodes shown in red
- Connections shown as green lines
- Voronoi cells shown as purple outlines (where applicable)
- A table of metrics at the bottom

## Extending the Test

To add a new connection strategy:
1. Add the strategy implementation to `voronoi_connection_test.sql`
2. Add the strategy to the data fetching in `run_voronoi_connection_test.py`
3. Add the strategy to the visualization in `run_voronoi_connection_test.py`
4. Update the summary document `voronoi_connection_strategies_summary.md`

## Related Documentation

For more information on the connection strategies and their implementation in the terrain graph pipeline, see:
- `epsg3857_pipeline/docs/voronoi_connection_strategy.md`
- `epsg3857_pipeline/docs/reversed_voronoi_connection_strategy.md`
- `epsg3857_pipeline/docs/line_to_point_connection_strategy.md`
