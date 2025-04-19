# Terrain Graph Development Scripts

This directory contains utility scripts to help with development, testing, and analysis of the terrain graph pipeline. These scripts are designed to be succinct but versatile, allowing you to work with smaller subsets of OSM data while maintaining all the data attributes.

## Script Overview

| Script | Purpose |
|--------|---------|
| `extract_osm_subset.py` | Extract a smaller geographic area from a larger OSM file |
| `reset_database.py` | Reset the PostGIS database and reimport OSM data |
| `run_pipeline.py` | Run the complete terrain graph pipeline with options to preserve OSM attributes |
| `analyze_osm_attributes.py` | Analyze OSM data attributes and recommend which ones to include in the graph |
| `export_slice_with_attributes.py` | Export a graph slice with all OSM attributes preserved |
| `query_osm_attributes.sql` | SQL queries to explore OSM attributes in the database |
| `setup_dev_environment.sh` | All-in-one script to set up a development environment |

## Prerequisites

These scripts require:

- Python 3.9+
- Docker and Docker Compose (for database operations)
- osmium-tool (for OSM data extraction)
- Additional Python packages:
  ```
  pandas
  matplotlib
  sqlalchemy
  psycopg2-binary
  tabulate
  ```

You can install the required Python packages with:

```bash
# Install from the scripts/requirements.txt file
pip install -r scripts/requirements.txt
```

## Usage Examples

### 1. Extract a Subset of OSM Data

Extract a 10km radius area around one of the benchmark locations:

```bash
# Extract area around Iowa State (IA-Central benchmark)
python scripts/extract_osm_subset.py --input data/iowa-latest.osm.pbf --benchmark ia-central --radius 10

# Extract area around custom coordinates
python scripts/extract_osm_subset.py --input data/iowa-latest.osm.pbf --coordinates -93.6 41.6 --radius 5 --name des_moines
```

### 2. Reset the Database

Reset the database and import a subset of OSM data:

```bash
# Reset the entire database
python scripts/reset_database.py --reset-all

# Reset only the derived tables (keeping the original OSM import)
python scripts/reset_database.py --reset-derived

# Reset and import OSM data
python scripts/reset_database.py --reset-all --import data/subsets/iowa-latest_ia-central_r10km.osm.pbf
```

### 3. Run the Pipeline

Run the complete pipeline with preserved OSM attributes:

```bash
# Run the pipeline with default settings
python scripts/run_pipeline.py

# Run the pipeline with preserved OSM attributes
python scripts/run_pipeline.py --preserve-attributes

# Run the pipeline and export a slice
python scripts/run_pipeline.py --preserve-attributes --export --lon -93.63 --lat 41.99 --radius 5 --output slice.graphml
```

### 4. Analyze OSM Attributes

Analyze the OSM data attributes in the database:

```bash
# Basic analysis
python scripts/analyze_osm_attributes.py

# Show examples of values for each attribute
python scripts/analyze_osm_attributes.py --show-examples

# Save plots to a directory
python scripts/analyze_osm_attributes.py --output-dir analysis
```

### 5. Export Graph Slice with Attributes

Export a graph slice with all OSM attributes preserved:

```bash
# Basic export with attributes
python scripts/export_slice_with_attributes.py --lon -93.63 --lat 41.99 --radius 5

# Export with attributes and include geometry
python scripts/export_slice_with_attributes.py --lon -93.63 --lat 41.99 --radius 5 --include-geometry

# Export from a specific edge table
python scripts/export_slice_with_attributes.py --lon -93.63 --lat 41.99 --edge-table road_edges
```

### 6. Query OSM Attributes

The `query_osm_attributes.sql` file contains a collection of SQL queries to explore OSM attributes in the database. You can run these queries using the `run_sql_queries.py` script:

```bash
# Run all queries in the file
python scripts/run_sql_queries.py --file scripts/query_osm_attributes.sql

# Run a specific query by number (e.g., query #4 to count highway types)
python scripts/run_sql_queries.py --query-number 4

# Run a custom query
python scripts/run_sql_queries.py --query "SELECT highway, COUNT(*) as count FROM planet_osm_line WHERE highway IS NOT NULL GROUP BY highway ORDER BY count DESC;"
```

The SQL file includes queries for:
- Listing tables and columns
- Counting different types of roads and water features
- Finding roads with specific attributes (surface, speed limit, etc.)
- Comparing the original OSM tables with the derived tables

You can also run these queries in pgAdmin, which is available at http://localhost:5050 (user: admin@example.com, password: admin).

## Complete Development Workflow

### Option 1: All-in-One Setup Script

The easiest way to set up a development environment is to use the provided setup script:

```bash
# Run with default settings
./scripts/setup_dev_environment.sh

# Run with custom settings
./scripts/setup_dev_environment.sh --input data/iowa-latest.osm.pbf --benchmark ia-central --radius 10 --show-examples
```

The setup script combines all the steps below into a single command and provides sensible defaults.

### Option 2: Step-by-Step Workflow

If you prefer more control, you can run each step manually:

```bash
# 1. Start the Docker containers
docker compose up -d

# 2. Extract a subset of OSM data
python scripts/extract_osm_subset.py --input data/iowa-latest.osm.pbf --benchmark ia-central --radius 10

# 3. Reset the database and import the subset
python scripts/reset_database.py --reset-all --import data/subsets/iowa-latest_ia-central_r10km.osm.pbf

# 4. Analyze the OSM attributes
python scripts/analyze_osm_attributes.py --show-examples

# 5. Run the pipeline with preserved attributes
python scripts/run_pipeline.py --preserve-attributes

# 6. Export a slice for testing
python scripts/export_slice_with_attributes.py --lon -93.63 --lat 41.99 --radius 5 --output slice_with_attributes.graphml
```

## Making Scripts Executable

You can make the scripts executable with:

```bash
chmod +x scripts/*.py
```

Then you can run them directly:

```bash
./scripts/extract_osm_subset.py --help
```

## Notes

- The scripts use the Docker container name to interact with the database. If you have multiple containers running, you may need to specify the container name manually.
- The `extract_osm_subset.py` script requires osmium-tool to be installed. You can install it with `apt-get install osmium-tool` on Ubuntu or `brew install osmium-tool` on macOS.
- The `analyze_osm_attributes.py` script requires matplotlib for plotting. If you don't need plots, you can remove the matplotlib import and related code.
