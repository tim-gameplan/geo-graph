# Getting Started with EPSG:3857 Terrain Graph Pipeline

This guide will help you get up and running with the EPSG:3857 Terrain Graph Pipeline. It covers environment setup, data preparation, running the pipeline, and troubleshooting common issues.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker**: The pipeline uses a PostgreSQL/PostGIS database running in a Docker container
- **Python 3.8+**: The pipeline scripts are written in Python
- **Required Python packages**: Install them using `pip install -r requirements.txt`
- **OSM data**: You'll need OpenStreetMap data for the area you want to process

## Environment Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-organization/geo-graph.git
cd geo-graph
```

### 2. Start the Docker Container

The pipeline uses a PostgreSQL/PostGIS database running in a Docker container. Start it using:

```bash
docker-compose up -d
```

This will start the PostgreSQL/PostGIS container with the name `geo-graph-db-1`.

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Data Preparation

### 1. Obtain OSM Data

You can download OpenStreetMap data from various sources:

- [Geofabrik](https://download.geofabrik.de/): Provides extracts for countries and regions
- [BBBike](https://extract.bbbike.org/): Allows you to extract custom regions
- [Overpass API](https://overpass-turbo.eu/): For smaller areas

For testing, you can use the provided sample data in the `data/subsets/` directory.

### 2. Import OSM Data

Before running the pipeline, you need to import the OSM data into the PostgreSQL/PostGIS database:

```bash
# Import OSM data from a PBF file
python epsg3857_pipeline/core/scripts/import_osm_data.py --osm-file data/subsets/iowa-latest.osm.pbf

# If your Docker container has a different name, specify it
python epsg3857_pipeline/core/scripts/import_osm_data.py --osm-file data/subsets/iowa-latest.osm.pbf --container geo-graph-db-1

# Enable verbose logging for more details
python epsg3857_pipeline/core/scripts/import_osm_data.py --osm-file data/subsets/iowa-latest.osm.pbf --verbose
```

## Running the Pipeline

The EPSG:3857 pipeline has several approaches. Choose the one that best fits your needs:

### Standard Pipeline (Recommended for Most Cases)

```bash
# Reset the database (if needed)
python epsg3857_pipeline/tools/database/reset_derived_tables.py

# Run the standard pipeline with improved water edge creation (default)
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard

# Run with verbose output
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --verbose
```

### Water Boundary Approach

Use this approach when you need precise water boundary navigation:

```bash
# Reset the database (if needed)
python epsg3857_pipeline/tools/database/reset_derived_tables.py

# Run the water boundary approach
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --water-boundary
```

### Obstacle Boundary Approach

Use this approach for clean boundary representation with optimal connectivity:

```bash
# Reset the database (if needed)
python epsg3857_pipeline/tools/database/reset_derived_tables.py

# Run the obstacle boundary pipeline
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py

# Run with custom parameters
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py --storage-srid 3857 --max-connection-distance 300 --water-speed-factor 0.2
```

### Delaunay Triangulation (Experimental)

Use this approach for more natural terrain representation (still under development):

```bash
# Reset the database (if needed)
python epsg3857_pipeline/tools/database/reset_derived_tables.py

# Run the Delaunay triangulation pipeline
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode delaunay
```

## Exporting Results

After running the pipeline, you can export a graph slice around a specific coordinate:

```bash
# Export a graph slice around a specific coordinate
python epsg3857_pipeline/core/scripts/export_slice.py --lon -93.63 --lat 41.99 --minutes 60 --outfile iowa_central_3857.graphml
```

## Visualizing Results

You can visualize the results using the provided visualization tools:

```bash
# Visualize the graph
python epsg3857_pipeline/core/scripts/visualize.py --mode graphml --input iowa_central_3857.graphml

# Visualize water obstacles
python epsg3857_pipeline/core/scripts/visualize.py --mode water

# Visualize the obstacle boundary graph
python epsg3857_pipeline/core/obstacle_boundary/visualize.py --output obstacle_boundary_graph.png
```

## Running Tests

The pipeline includes comprehensive tests to verify its functionality:

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

## Troubleshooting

### Common Issues

#### Docker Container Not Running

If you see an error like:

```
Error: Could not connect to Docker container
```

Ensure the Docker container is running:

```bash
docker ps
```

If it's not running, start it:

```bash
docker-compose up -d
```

#### Path Issues

If you see errors like:

```
python: can't open file '/path/to/file.py': [Errno 2] No such file or directory
```

Ensure you're running the commands from the correct directory (usually the root of the repository) and that the paths in the commands are correct.

#### Memory Errors During Dissolve Step

If you see memory errors during the dissolve step:

```
ERROR: out of memory
```

Increase the `work_mem` parameter in the SQL script:

```sql
SET work_mem = '1GB';
```

#### Missing Water Features

If the water features table is empty:

```
Created 0 water features
```

Check the water feature extraction parameters in the configuration file and ensure the OSM data contains water features.

#### Graph Connectivity Issues

If you encounter graph connectivity issues (e.g., paths cannot be found between certain points):

1. Use the improved water edge creation algorithm (default)
2. Try the water boundary approach with the `--water-boundary` flag
3. Try the direct water obstacle boundary conversion approach with the `run_obstacle_boundary_pipeline.py` script
4. Check if water edges are being created (the water_edges table should not be empty)
5. Adjust the relevant parameters in the configuration file
6. Use the visualization tools to identify disconnected components in the graph

## Next Steps

Once you've successfully run the pipeline, you can:

1. Explore the different pipeline approaches to find the one that best fits your needs
2. Customize the configuration files to adjust parameters
3. Integrate the pipeline into your own workflow
4. Contribute to the project by improving the code or documentation

## Additional Resources

- [README.md](../README.md): Main project documentation
- [Component Status](./component_status.md): Status of each component in the project
- [Database Schema](./database_schema.md): Detailed database schema documentation
- [Project Organization](./project_organization.md): Overview of project structure and components
