# Renamed Tables Pipeline

This document explains how to use the renamed tables pipeline, which implements the Pipeline Stage Prefixing naming convention for tables in the Boundary Hexagon Layer Pipeline.

## Overview

The renamed tables pipeline is a version of the Boundary Hexagon Layer Pipeline that uses a new table naming convention. The new naming convention follows this format:

```
s{stage_number}_{category}_{entity}
```

Where:
- `s{stage_number}` indicates the pipeline stage (e.g., s01, s02)
- `{category}` indicates the data category (e.g., water, grid, nodes, edges)
- `{entity}` describes the specific entity or processing state

For example, `water_features_polygon` becomes `s01_water_features_polygon`.

## Benefits

The new naming convention provides several benefits:

1. **Pipeline Order**: Tables automatically sort in pipeline order in database tools
2. **Context**: Stage number provides immediate context about where in the pipeline a table belongs
3. **Grouping**: Easy to identify which tables are created by the same script
4. **Visual Separation**: Clear visual separation between stages

## Running the Pipeline

To run the pipeline with the new table naming convention, use the following command:

```bash
python epsg3857_pipeline/run_renamed_tables_pipeline.py
```

### Command-line Options

The pipeline supports the following command-line options:

- `--config`: Path to the configuration file (default: `../config/crs_standardized_config_boundary_hexagon.json`)
- `--sql-dir`: Path to the directory containing SQL scripts (default: `../core/sql`)
- `--container`: Name of the Docker container (default: `db`)
- `--verbose`: Print verbose output
- `--no-compatibility-views`: Do not create backward compatibility views

Example:

```bash
python epsg3857_pipeline/run_renamed_tables_pipeline.py --verbose
```

## Backward Compatibility

By default, the pipeline creates backward compatibility views that allow existing code to continue working with the old table names. These views are created after all the tables have been created with the new naming convention.

If you don't want to create these views, you can use the `--no-compatibility-views` option:

```bash
python epsg3857_pipeline/run_renamed_tables_pipeline.py --no-compatibility-views
```

## Implementation Details

The implementation of the renamed tables pipeline consists of the following components:

1. **Renamed SQL Scripts**: Modified versions of the original SQL scripts that use the new table names
2. **Backward Compatibility Views**: A SQL script that creates views with the old table names that point to the new tables
3. **Pipeline Script**: A Python script that runs the renamed SQL scripts and the backward compatibility views script

The renamed SQL scripts are located in the `epsg3857_pipeline/core/sql/renamed` directory.

## Table Name Mapping

For a complete mapping of old table names to new table names, see the [Table Naming Convention](table_naming_convention.md) document.

## Migration Guide

If you have custom code that directly references the table names, you should update it to use the new table names. Alternatively, you can continue using the old table names, which will work through the backward compatibility views.

## Future Work

In the future, we plan to:

1. Update all visualization scripts to use the new table names
2. Update all documentation to use the new table names
3. Eventually remove the backward compatibility views once all code has been updated