# Pipeline Scripts

This directory contains the active pipeline scripts for the terrain system.

## Current Production Pipeline

- `run_boundary_hexagon_layer_enhanced_pipeline.py`: Enhanced Boundary Hexagon Layer Pipeline

This is the current production pipeline that creates derived tables in PostGIS from loaded OSM data. It uses the hexagon boundary layer approach with enhanced connectivity between land_portion nodes and land/boundary nodes.

## Usage

```bash
python epsg3857_pipeline/pipelines/run_boundary_hexagon_layer_enhanced_pipeline.py
```

For more options:

```bash
python epsg3857_pipeline/pipelines/run_boundary_hexagon_layer_enhanced_pipeline.py --help