# File Organization and Pipeline Documentation

This document provides an overview of the file organization and pipeline process for the terrain system project.

## Directory Structure

The project is organized into the following directories:

- **data/**: Contains input data files and subsets
- **deprecated/**: Contains deprecated scripts and SQL files that are no longer used
- **docker/**: Contains Docker configuration files
- **docs/**: Contains project documentation
- **output/**: Contains output files, organized into subdirectories
  - **exports/**: Contains exported graph files (GraphML)
  - **logs/**: Contains log files
  - **visualizations/**: Contains visualization images, organized by type
    - **graphml/**: Graph visualizations
    - **water/**: Water obstacle visualizations
    - **terrain/**: Terrain visualizations
    - **combined/**: Combined visualizations
- **planning/**: Contains planning-related files
  - **config/**: Configuration files for different environments
  - **scripts/**: Planning-specific scripts
  - **sql/**: SQL files for planning-specific operations
  - **tests/**: Test files for planning-specific scripts
- **scripts/**: Contains main pipeline scripts
- **sql/**: Contains SQL files for the main pipeline
- **tools/**: Contains utility tools and scripts
- **utils/**: Contains utility modules

## Pipeline Process

The terrain system pipeline consists of several steps:

1. **Database Reset**: Reset the database to prepare for a new pipeline run
2. **Enhanced Pipeline**: Run the enhanced pipeline to create the unified edges
3. **Water Obstacle Pipeline**: Run the water obstacle pipeline to model water features
4. **Export**: Export a slice of the graph for visualization
5. **Visualization**: Visualize the graph slice and water obstacles

### Database Reset

The database reset is performed using the `scripts/reset_database.py` script:

```bash
python scripts/reset_database.py --reset-derived
```

This script resets all derived tables while preserving the base OSM data.

### Enhanced Pipeline

The enhanced pipeline is run using the `scripts/run_pipeline_enhanced.py` script:

```bash
python scripts/run_pipeline_enhanced.py
```

This script executes the following SQL files in sequence:

1. `derive_road_and_water_enhanced_fixed.sql`: Extract road and water features from OSM data
2. `build_water_buffers_simple.sql`: Create water buffers around water features
3. `create_grid_profile.sql`: Create a grid profile for terrain modeling
4. `build_terrain_grid_simple.sql`: Create a terrain grid based on the grid profile
5. `create_edge_tables_enhanced.sql`: Create edge tables for the graph
6. `add_source_target_columns.sql`: Add source and target columns to the edge tables
7. `create_unified_edges_enhanced_fixed_v2.sql`: Create the unified edges table
8. `refresh_topology_fixed_v2.sql`: Refresh the graph topology

### Water Obstacle Pipeline

The water obstacle pipeline is run using the `scripts/run_unified_pipeline.py` script:

```bash
python scripts/run_unified_pipeline.py --mode water --config planning/config/default_config.json
```

This script executes the following SQL files in sequence:

1. `01_extract_water_features.sql`: Extract water features from OSM data
2. `02_create_water_buffers.sql`: Create water buffers around water features
3. `03_dissolve_water_buffers.sql`: Dissolve overlapping water buffers
4. `04_create_terrain_grid.sql`: Create a terrain grid
5. `05_create_terrain_edges.sql`: Create terrain edges
6. `06_create_water_edges.sql`: Create water edges
7. `07_create_environmental_tables.sql`: Create environmental tables

### Export

The graph slice is exported using the `tools/export_slice_enhanced_fixed.py` script:

```bash
python tools/export_slice_enhanced_fixed.py --lon -93.63 --lat 41.99 --minutes 60 --outfile enhanced_test.graphml
```

This script creates an isochrone-based slice of the graph centered at the specified coordinates.

### Visualization

The graph slice and water obstacles are visualized using the `visualize_unified.py` script:

```bash
# Visualize the graph slice
python visualize_unified.py --mode graphml --input enhanced_test.graphml

# Visualize the water obstacles
python visualize_unified.py --mode water
```

## Database Schema

The database schema consists of the following tables:

### Unified Edges Table

The `unified_edges` table contains the unified graph edges:

- `id`: Edge ID
- `source`: Source vertex ID
- `target`: Target vertex ID
- `cost`: Edge cost
- `geom`: Edge geometry

### Water Edges Table

The `water_edges` table contains the water obstacle edges:

- `id`: Edge ID
- `source`: Source vertex ID
- `target`: Target vertex ID
- `cost`: Edge cost
- `crossability`: Crossability value
- `avg_buffer_size_m`: Average buffer size in meters
- `length_m`: Edge length in meters
- `geom`: Edge geometry
- `edge_type`: Edge type
- `crossability_group`: Crossability group
- `buffer_rules_applied`: Buffer rules applied
- `crossability_rules_applied`: Crossability rules applied

### Water Buffers Table

The `water_buf_dissolved` table contains the dissolved water buffers:

- `id`: Buffer ID
- `crossability`: Crossability value
- `avg_buffer_size_m`: Average buffer size in meters
- `geom`: Buffer geometry
- `buffer_rules_applied`: Buffer rules applied
- `crossability_group`: Crossability group
- `crossability_rules_applied`: Crossability rules applied

### Environmental Conditions Table

The `environmental_conditions` table contains the environmental conditions:

- `condition_name`: Condition name
- `value`: Condition value
- `last_updated`: Last updated timestamp

## File Naming Conventions

The project uses the following file naming conventions:

- **SQL Files**: Snake case with descriptive names (e.g., `create_unified_edges.sql`)
- **Python Scripts**: Snake case with descriptive names (e.g., `run_pipeline_enhanced.py`)
- **Configuration Files**: Snake case with descriptive names (e.g., `default_config.json`)
- **Documentation Files**: Snake case with descriptive names (e.g., `file_organization.md`)
- **Output Files**: Timestamp-based naming with descriptive suffixes (e.g., `2025-04-20_14-19-56_enhanced_test_dpi-300.png`)

## Visualization Output

All visualizations are stored in the `output/visualizations/` directory, organized by type:

- **GraphML Visualizations**: `output/visualizations/graphml/`
- **Water Obstacle Visualizations**: `output/visualizations/water/`
- **Terrain Visualizations**: `output/visualizations/terrain/`
- **Combined Visualizations**: `output/visualizations/combined/`

Each visualization file is named with a timestamp, description, and parameters:

```
YYYY-MM-DD_HH-MM-SS_description_param1-value1_param2-value2.png
```

For example:

```
2025-04-20_14-19-56_enhanced_test_dpi-300.png
```

## Logging

All logs are stored in the `output/logs/` directory. Each log file is named with a date and description:

```
YYYY-MM-DD_description.log
```

For example:

```
2025-04-20_visualization.log
```

The logs use a consistent format:

```
YYYY-MM-DD HH:MM:SS,ms - logger_name - log_level - message
```

For example:

```
2025-04-20 14:19:56,113 - unified_visualization - INFO - Visualizing GraphML file: enhanced_test.graphml
```

## Recommended Workflow

For future development, we recommend the following workflow:

1. **Reset the Database**:

```bash
python scripts/reset_database.py --reset-derived
```

2. **Run the Enhanced Pipeline**:

```bash
python scripts/run_pipeline_enhanced.py
```

3. **Run the Water Obstacle Pipeline**:

```bash
python scripts/run_unified_pipeline.py --mode water --config planning/config/default_config.json
```

4. **Export a Graph Slice**:

```bash
python tools/export_slice_enhanced_fixed.py --lon -93.63 --lat 41.99 --minutes 60 --outfile enhanced_test.graphml
```

5. **Visualize the Results**:

```bash
# Visualize the graph slice
python visualize_unified.py --mode graphml --input enhanced_test.graphml

# Visualize the water obstacles
python visualize_unified.py --mode water
```

This workflow provides the most comprehensive solution with OSM attribute preservation and isochrone-based graph slicing.
