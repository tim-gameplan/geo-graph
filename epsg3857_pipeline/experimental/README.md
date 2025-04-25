# Experimental Features

This directory contains experimental features for the EPSG:3857 terrain graph pipeline.

## Overview

These features are under development or experimental and may not be fully functional. They are provided for research and development purposes.

## Components

### Delaunay

An experimental approach using Delaunay triangulation for terrain grid generation:

- `run_water_obstacle_pipeline_delaunay.py`: Delaunay pipeline runner
- `run_unified_delaunay_pipeline.py`: Unified Delaunay pipeline for large datasets
- `visualize_delaunay_triangulation.py`: Delaunay triangulation visualizer
- `04_create_terrain_grid_delaunay_3857.sql`: Delaunay terrain grid
- `05_create_terrain_edges_delaunay_3857.sql`: Delaunay terrain edges

## Status

The Delaunay triangulation approach is still under development. The unified Delaunay pipeline is incomplete and missing several required SQL files:

- `01_extract_water_features_chunk.sql`
- `02_create_water_buffers_chunk.sql`
- `03_dissolve_water_buffers_chunk.sql`
- `04_create_terrain_grid_delaunay_chunk.sql`
- `05_create_terrain_edges_delaunay_chunk.sql`
- `06_create_water_edges_chunk.sql`
- `07_create_environmental_tables_chunk.sql`

These files need to be created to implement spatial chunking for large datasets.

## Usage

These experimental features are not recommended for production use. They are provided for research and development purposes only.
