# Quick Start Guide: EPSG:3857 Terrain Graph Pipeline

This guide will walk you through the steps to set up the environment, load OSM data, and run the pipeline to generate the terrain graph with water obstacles as shown in the image.

## 1. Setup Environment

First, make sure you have Docker installed and running. The pipeline uses a PostgreSQL/PostGIS database in a Docker container.

```bash
# Start the Docker containers
docker-compose up -d
```

## 2. Database Management

The pipeline provides several scripts for managing the database:

### Reset Derived Tables

Use this script during development when you want to rerun the pipeline without reloading the OSM data:

```bash
python epsg3857_pipeline/scripts/reset_derived_tables.py
```

This script only drops the tables created by the pipeline, preserving the OSM data tables (planet_osm_*).

### Reset OSM Tables

Use this script when you want to change the OSM data source or reload the OSM data:

```bash
python epsg3857_pipeline/scripts/reset_osm_tables.py
```

This script only drops the OSM data tables (planet_osm_*), preserving any derived tables.

### Reset All Tables

Use this script when you want to start with a completely clean database:

```bash
python epsg3857_pipeline/scripts/reset_all_tables.py
```

WARNING: This will delete ALL data in the database, including both OSM data tables and derived tables. You will need to reload OSM data after running this script.

## 3. Import OSM Data

Use the import_osm_data.py script to load OpenStreetMap data into the PostGIS database:

```bash
# Import OSM data from a PBF file
python epsg3857_pipeline/scripts/import_osm_data.py --osm-file data/subsets/iowa-latest.osm_ia-central_r10.0km.osm.pbf
```

This script will:
- Check if the Docker container is running
- Install required PostgreSQL extensions (postgis, hstore, postgis_topology)
- Import OSM data using osm2pgsql

## 4. Run the Direct Water Obstacle Boundary Pipeline

This is the approach that generates the visualization you saw in the image:

```bash
# First, run the standard water obstacle pipeline to create water features and terrain grid
python epsg3857_pipeline/scripts/run_water_obstacle_pipeline_crs.py --config epsg3857_pipeline/config/crs_standardized_config.json --sql-dir epsg3857_pipeline/sql

# Then, run the direct water obstacle boundary conversion
python epsg3857_pipeline/scripts/run_obstacle_boundary_graph.py
```

The first command extracts water features from OSM data, creates water buffers, dissolves them, and creates a terrain grid. The second command converts water obstacle boundaries directly to graph elements.

## 5. Visualize the Results

To visualize the obstacle boundary graph as shown in the image:

```bash
python epsg3857_pipeline/scripts/visualize_obstacle_boundary_graph.py --show-unified
```

This will display the visualization showing:
- Terrain grid (hexagonal cells in gray)
- Water obstacles (white areas)
- Obstacle boundary nodes (blue dots)
- Boundary edges (blue lines)
- Terrain-to-boundary connections (red lines)

## Alternative Approaches

If you want to try other approaches:

### Standard Pipeline with Improved Water Edge Creation

```bash
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard
```

### Water Boundary Approach

```bash
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --water-boundary --config epsg3857_pipeline/config/crs_standardized_config_boundary.json
```

### Delaunay Triangulation Approach

```bash
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode delaunay --config epsg3857_pipeline/config/delaunay_config.json
```

## Typical Development Workflow

1. **Initial Setup**:
   ```bash
   docker-compose up -d
   python epsg3857_pipeline/scripts/reset_all_tables.py
   python epsg3857_pipeline/scripts/import_osm_data.py --osm-file data/subsets/iowa-latest.osm_ia-central_r10.0km.osm.pbf
   ```

2. **During Development** (when making changes to the pipeline):
   ```bash
   python epsg3857_pipeline/scripts/reset_derived_tables.py
   python epsg3857_pipeline/scripts/run_water_obstacle_pipeline_crs.py --config epsg3857_pipeline/config/crs_standardized_config.json --sql-dir epsg3857_pipeline/sql
   python epsg3857_pipeline/scripts/run_obstacle_boundary_graph.py
   ```

3. **When Changing OSM Data**:
   ```bash
   python epsg3857_pipeline/scripts/reset_osm_tables.py
   python epsg3857_pipeline/scripts/import_osm_data.py --osm-file [new-osm-file-path]
   ```

## Key Files and Directories

- `epsg3857_pipeline/scripts/`: Contains all Python scripts for running the pipeline
- `epsg3857_pipeline/sql/`: Contains SQL scripts for database operations
- `epsg3857_pipeline/config/`: Contains configuration files for different pipeline modes
- `epsg3857_pipeline/docs/`: Contains documentation for the pipeline
