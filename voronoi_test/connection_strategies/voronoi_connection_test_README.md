# Voronoi Connection Strategies Test

This package provides tools to test and visualize different connection strategies for connecting terrain grid points to water obstacle boundaries in the EPSG:3857 Terrain Graph Pipeline.

## Overview

The package includes:

1. **SQL Test Script** (`voronoi_connection_test.sql`): Creates test data and implements four different connection strategies:
   - Simple Nearest Neighbor
   - Line-to-Point Connection
   - Standard Voronoi Connection
   - Reversed Voronoi Connection

2. **Python Visualization Tool** (`run_voronoi_connection_test.py`): Runs the SQL script and visualizes the results using matplotlib.

3. **Documentation** (`voronoi_connection_strategies_summary.md`): Provides a comprehensive overview of the different connection strategies.

## Requirements

- PostgreSQL with PostGIS extension
- Docker (for running PostgreSQL in a container)
- Python 3.8+ with the following packages:
  - psycopg2
  - matplotlib
  - numpy

## Installation

1. Install the required Python packages:

```bash
pip install psycopg2-binary matplotlib numpy
```

2. Ensure you have a PostgreSQL container running with PostGIS:

```bash
docker-compose up -d
```

## Usage

### Running the SQL Script Directly

You can run the SQL script directly in your PostgreSQL database:

```bash
psql -U postgres -d postgres -f voronoi_connection_test.sql
```

This will:
1. Create test tables for water obstacles, terrain points, and boundary nodes
2. Implement four different connection strategies
3. Create a view for visualization
4. Run analysis queries to compare the strategies

### Using the Python Visualization Tool

The Python script provides a more user-friendly way to run the test and visualize the results:

```bash
python run_voronoi_connection_test.py
```

Optional arguments:
- `--host`: PostgreSQL host (default: localhost)
- `--port`: PostgreSQL port (default: 5432)
- `--dbname`: PostgreSQL database name (default: postgres)
- `--user`: PostgreSQL user (default: postgres)
- `--password`: PostgreSQL password (default: postgres)
- `--container`: Docker container name (default: geo-graph-db-1)
- `--sql-file`: SQL test file (default: voronoi_connection_test.sql)
- `--output-dir`: Output directory for visualizations (default: visualizations)
- `--skip-sql`: Skip running SQL script (use existing data)
- `--show-cells`: Show Voronoi cells in visualizations

Example:

```bash
python run_voronoi_connection_test.py --container my-postgres-container --show-cells
```

## Visualizations

The Python script generates two visualizations:

1. **Connection Strategies Comparison** (`connection_strategies_comparison.png`):
   - Shows the four connection strategies side by side
   - Displays water obstacles, terrain points, boundary nodes, and connections
   - Includes connection counts and average distances

2. **Node Distribution** (`node_distribution.png`):
   - Shows the distribution of connections per boundary node for each strategy
   - Includes statistics like min, max, mean, and standard deviation

## Understanding the Results

### Nearest Neighbor Strategy

The Nearest Neighbor strategy connects each terrain point to the nearest boundary node. This is the simplest approach but can lead to uneven distribution of connections, with some boundary nodes receiving many connections while others receive none.

### Line-to-Point Connection Strategy

The Line-to-Point Connection strategy connects each terrain point to the closest point on the water obstacle boundary, not to pre-existing boundary nodes. This creates more direct and meaningful connections to the actual boundary.

### Standard Voronoi Connection Strategy

The Standard Voronoi Connection strategy uses Voronoi diagrams to partition space around boundary nodes. Each terrain point is connected to the boundary node whose Voronoi cell contains it. This creates a more even distribution of connections.

### Reversed Voronoi Connection Strategy

The Reversed Voronoi Connection strategy flips the traditional approach by creating Voronoi cells for boundary terrain points instead of boundary nodes. This "reversed" approach results in more natural connections and better distribution of connections across water boundaries.

## Extending the Test

You can modify the SQL script to test different parameters or add new connection strategies:

1. Adjust the water obstacle shape or size
2. Change the terrain grid spacing
3. Modify the boundary node spacing
4. Implement new connection strategies
5. Add more analysis queries

## Integration with EPSG:3857 Terrain Graph Pipeline

To integrate these connection strategies into the EPSG:3857 Terrain Graph Pipeline:

1. Choose the appropriate connection strategy based on your requirements
2. Implement the strategy in your pipeline SQL scripts
3. Configure the parameters in your configuration files
4. Run the pipeline with the new connection strategy

## References

For more information on the different connection strategies, see:

- `voronoi_connection_strategies_summary.md`: Comprehensive overview of the connection strategies
- `epsg3857_pipeline/docs/voronoi_connection_strategy.md`: Documentation of the Standard Voronoi Connection Strategy
- `epsg3857_pipeline/docs/reversed_voronoi_connection_strategy.md`: Documentation of the Reversed Voronoi Connection Strategy
- `epsg3857_pipeline/docs/line_to_point_connection_strategy.md`: Documentation of the Line-to-Point Connection Strategy
