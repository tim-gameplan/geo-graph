# File Organization and Workflow Guide

## Overview

This document outlines the file organization strategy for the terrain graph pipeline project and provides recommendations for the optimal workflow. The goal is to provide a clear understanding of the project structure and how to use the various scripts effectively.

## Directory Structure

The project is organized into the following directories:

```
geo-graph/
├── data/                    # Input data files
│   └── subsets/             # Subsets of OSM data
├── deprecated/              # Deprecated files (kept for reference)
│   ├── scripts/             # Deprecated script files
│   ├── sql/                 # Deprecated SQL files
│   └── tools/               # Deprecated tool files
├── docs/                    # Documentation
├── output/                  # Output files
│   ├── exports/             # Exported GraphML files
│   ├── logs/                # Log files
│   └── visualizations/      # Visualization outputs
│       ├── combined/        # Combined visualizations
│       ├── graphml/         # GraphML visualizations
│       ├── terrain/         # Terrain grid visualizations
│       └── water/           # Water obstacle visualizations
├── planning/                # Planning and development files
│   ├── config/              # Configuration files
│   ├── scripts/             # Planning scripts
│   ├── sql/                 # Planning SQL files
│   └── tests/               # Test files
├── scripts/                 # Core scripts
├── sql/                     # Core SQL files
├── tools/                   # Tool scripts
└── utils/                   # Utility modules
```

## Core Files

The following files form the core of the terrain graph pipeline:

### Pipeline Scripts

- `scripts/run_pipeline_enhanced.py` - Enhanced pipeline with OSM attributes
- `scripts/run_unified_pipeline.py` - Unified interface for all pipelines
- `planning/scripts/run_water_obstacle_pipeline.py` - Water obstacle pipeline

### Export Scripts

- `tools/export_slice_enhanced_fixed.py` - Enhanced export with isochrone-based slicing
- `tools/export_unified.py` - Unified interface for all export operations

### Visualization Scripts

- `visualize_graph.py` - Visualize GraphML files
- `visualize_unified.py` - Unified interface for all visualization operations
- `planning/scripts/visualize_water_obstacles.py` - Visualize water obstacles

### SQL Scripts

- `sql/derive_road_and_water_enhanced_fixed.sql` - Extract road and water features with OSM attributes
- `sql/create_edge_tables_enhanced.sql` - Create edge tables with OSM attributes
- `sql/create_unified_edges_enhanced_fixed_v2.sql` - Create unified edges with OSM attributes
- `sql/refresh_topology_fixed_v2.sql` - Refresh topology with fixed SRID handling

### Utility Scripts

- `scripts/reset_database.py` - Reset the database
- `scripts/extract_osm_subset.py` - Extract OSM subsets
- `planning/scripts/config_loader.py` - Load configuration files
- `utils/file_management.py` - File management utilities

## Recommended Workflow

For the most complete and feature-rich pipeline, we recommend the following workflow:

### 1. Reset the Database

```bash
python scripts/reset_database.py --reset-all
```

### 2. Run the Enhanced Pipeline

```bash
python scripts/run_pipeline_enhanced.py
```

### 3. Export a Slice

```bash
python tools/export_slice_enhanced_fixed.py --lon -93.63 --lat 41.99 --minutes 60 --outfile enhanced_test.graphml
```

### 4. Visualize the Exported Graph

```bash
python visualize_unified.py --mode graphml --input enhanced_test.graphml
```

## Alternative Workflows

### Using the Unified Pipeline Script

The unified pipeline script provides a single interface for running any of the three pipelines:

```bash
# Run the enhanced pipeline
python scripts/run_unified_pipeline.py --mode enhanced

# Run the water obstacle pipeline
python scripts/run_unified_pipeline.py --mode water --config planning/config/default_config.json

# Run the test pipeline
python scripts/run_unified_pipeline.py --mode test
```

### Using the Unified Export Script

The unified export script provides a single interface for all export operations:

```bash
# Export a simple radius-based slice
python tools/export_unified.py --mode simple --lon -93.63 --lat 41.99 --radius 5

# Export an isochrone-based slice
python tools/export_unified.py --mode enhanced --lon -93.63 --lat 41.99 --minutes 60

# Export a slice with OSM attributes
python tools/export_unified.py --mode attributes --lon -93.63 --lat 41.99 --radius 5
```

### Using the Unified Visualization Script

The unified visualization script provides a single interface for all visualization operations:

```bash
# Visualize a GraphML file
python visualize_unified.py --mode graphml --input enhanced_test.graphml

# Visualize water obstacles
python visualize_unified.py --mode water

# Create a combined visualization
python visualize_unified.py --mode combined --input enhanced_test.graphml
```

## File Management

All visualization outputs are stored in a structured directory hierarchy with timestamp-based naming. See [File Management Guide](file_management.md) for details.

## Deprecated Files

Files that have been deprecated in favor of newer, more comprehensive versions are moved to the `deprecated/` directory. These files are kept for reference but should not be used in production. See [Deprecated Files README](../deprecated/README.md) for details.

## Conclusion

By following this file organization strategy and recommended workflow, we can maintain a clean, organized project that is easy to understand and use. The unified scripts provide a consistent interface for all operations, making it easier to run the pipeline, export slices, and visualize the results.
