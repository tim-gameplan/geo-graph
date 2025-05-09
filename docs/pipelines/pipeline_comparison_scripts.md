# Pipeline Comparison Scripts

This document provides a comprehensive reference for running both the standard EPSG:3857 pipeline and the new obstacle boundary pipeline, along with visualization and testing commands.

## Prerequisites

Before running any pipeline, ensure you have:

1. Docker running with the PostgreSQL/PostGIS container
2. OSM data imported into the database

```bash
# Import OSM data (if not already done)
python epsg3857_pipeline/core/scripts/import_osm_data.py --osm-file data/subsets/iowa-latest.osm_ia-central_r10.0km.osm.pbf
```

## Database Management

```bash
# Reset only derived tables (preserves OSM data)
python epsg3857_pipeline/tools/database/reset_derived_tables.py

# Reset only OSM tables (preserves derived tables)
python epsg3857_pipeline/tools/database/reset_osm_tables.py

# Reset all tables (including OSM data)
python epsg3857_pipeline/tools/database/reset_all_tables.py --confirm

# Reset non-OSM tables (dynamically identifies and resets derived tables)
python epsg3857_pipeline/tools/database/reset_non_osm_tables.py
```

## 1. Standard EPSG:3857 Pipeline

The standard pipeline creates a terrain graph with water obstacles represented as areas to avoid, with some edges crossing water obstacles where appropriate.

### Basic Usage

```bash
# Reset the database (if needed)
python epsg3857_pipeline/core/scripts/reset_database.py --reset-derived

# Run the standard pipeline with improved water edge creation (default)
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard
```

### Advanced Options

```bash
# Run with verbose output
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --verbose

# Skip database reset (if you've already reset it)
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --skip-reset

# Run with standard water edge creation (not recommended)
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --standard-water-edges --config epsg3857_pipeline/config/crs_standardized_config.json

# Run with water boundary approach
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --water-boundary --config epsg3857_pipeline/config/crs_standardized_config_boundary.json
```

## 2. Obstacle Boundary Pipeline

The obstacle boundary pipeline treats water obstacles as navigable boundaries rather than impassable barriers, creating a more realistic representation of how vehicles navigate around water obstacles.

### Basic Usage

```bash
# First run the standard pipeline to prepare water features
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --skip-reset

# Then run the obstacle boundary pipeline
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py
```

### Advanced Options

```bash
# Run with verbose output
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py --verbose

# Run with custom parameters
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py --storage-srid 3857 --max-connection-distance 300 --water-speed-factor 0.2
```

## 3. Delaunay Triangulation Pipeline (Experimental)

The Delaunay triangulation pipeline uses Delaunay triangulation for more natural terrain representation.

```bash
# Reset the database (if needed)
python epsg3857_pipeline/core/scripts/reset_database.py --reset-derived

# Run the Delaunay triangulation pipeline
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode delaunay --config epsg3857_pipeline/config/delaunay_config.json
```

## 4. Exporting Graph Slices

```bash
# Export a graph slice around a specific coordinate
python epsg3857_pipeline/core/scripts/export_slice.py --lon -93.63 --lat 41.99 --minutes 60 --outfile iowa_central_3857.graphml
```

## 5. Visualizing Results

### Standard Visualization

```bash
# Visualize the graph
python epsg3857_pipeline/core/scripts/visualize.py --mode graphml --input iowa_central_3857.graphml

# Visualize water obstacles
python epsg3857_pipeline/core/scripts/visualize.py --mode water
```

### Obstacle Boundary Visualization

```bash
# Visualize the obstacle boundary graph
python epsg3857_pipeline/core/obstacle_boundary/visualize.py --output epsg3857_pipeline/visualizations/obstacle_boundary_graph.png
```

## 6. Running Tests

```bash
# Run all tests
./epsg3857_pipeline/run_tests.sh

# Run only standard pipeline tests
./epsg3857_pipeline/run_tests.sh --standard-only

# Run only Delaunay triangulation tests
./epsg3857_pipeline/run_tests.sh --delaunay-only

# Run only water boundary approach tests
./epsg3857_pipeline/run_tests.sh --water-boundary-only

# Run only obstacle boundary tests
./epsg3857_pipeline/run_tests.sh --obstacle-boundary-only

# Run tests with verbose output
./epsg3857_pipeline/run_tests.sh --verbose
```

## 7. Pipeline Comparison

### Key Differences

1. **Standard Pipeline**:
   - Creates water crossing edges that directly cross water obstacles
   - Uses a fixed distance threshold for water crossing edges
   - May result in unrealistic movement patterns around water obstacles

2. **Obstacle Boundary Pipeline**:
   - Creates edges along the perimeter of water obstacles
   - Preserves the original shape and detail of water obstacles
   - Results in more realistic movement patterns around water obstacles
   - Ensures full graph connectivity with no isolated components

### When to Use Each Pipeline

- **Standard Pipeline**: Use when you need a simple terrain graph with basic water obstacle handling.
- **Obstacle Boundary Pipeline**: Use when you need more realistic movement patterns around water obstacles and better graph connectivity.
- **Delaunay Triangulation Pipeline**: Use when you need a more natural terrain representation with triangulation that follows the contours of water features.

## 8. Complete End-to-End Example

```bash
# Reset the database
python epsg3857_pipeline/tools/database/reset_non_osm_tables.py

# Import OSM data (if needed)
python epsg3857_pipeline/core/scripts/import_osm_data.py --osm-file data/subsets/iowa-latest.osm_ia-central_r10.0km.osm.pbf

# Run the standard pipeline to prepare water features
python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard --skip-reset

# Run the obstacle boundary pipeline
python epsg3857_pipeline/run_obstacle_boundary_pipeline.py --verbose

# Visualize the obstacle boundary graph
python epsg3857_pipeline/core/obstacle_boundary/visualize.py --output epsg3857_pipeline/visualizations/obstacle_boundary_graph.png

# Export a graph slice
python epsg3857_pipeline/core/scripts/export_slice.py --lon -93.63 --lat 41.99 --minutes 60 --outfile iowa_central_obstacle_boundary.graphml

# Run tests to verify the pipeline
./epsg3857_pipeline/run_tests.sh --obstacle-boundary-only
