# Core Pipeline

This directory contains the core components of the EPSG:3857 terrain graph pipeline.

## Overview

The core pipeline is the primary recommended approach for generating terrain graphs with water obstacles. It uses EPSG:3857 (Web Mercator) for all internal processing, ensuring accurate metric-based measurements and consistent buffer sizes.

## Components

### Scripts

- `config_loader_3857.py`: Configuration loader for the pipeline
- `run_epsg3857_pipeline.py`: Main pipeline runner script
- `run_water_obstacle_pipeline_improved.py`: Improved water obstacle pipeline with enhanced water edge creation
- `reset_database.py`: Script to reset the database
- `import_osm_data.py`: Script to import OSM data
- `export_slice.py`: Script to export graph slices
- `visualize.py`: Script to visualize the graph

### SQL

- `01_extract_water_features_3857.sql`: Extract water features from OSM data
- `02_create_water_buffers_3857.sql`: Create buffers around water features
- `03_dissolve_water_buffers_3857.sql`: Dissolve overlapping water buffers
- `04_create_terrain_grid_3857.sql`: Create a terrain grid
- `05_create_terrain_edges_3857.sql`: Create terrain edges
- `06_create_water_edges_improved_3857.sql`: Create water edges with improved algorithm
- `07_create_environmental_tables_3857.sql`: Create environmental tables

## Usage

See the main README.md file for usage instructions.
