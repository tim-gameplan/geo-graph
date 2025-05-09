# How to Run the Pipeline with Renamed Tables

This document explains how to run the pipeline with the new table naming convention.

## Overview

After implementing the Pipeline Stage Prefixing naming convention, there are two ways to run the pipeline with the new table names:

1. Using the primary pipeline with the `--use-renamed-tables` flag
2. Using the wrapper script `run_renamed_tables_pipeline.py`

Both methods will run the pipeline using the modified SQL scripts that create tables with the new naming convention, and will also create backward compatibility views with the old table names.

## Prerequisites

Before running the pipeline with the new table names, ensure that:

1. The modified SQL scripts have been created in the `epsg3857_pipeline/core/sql/renamed/` directory
2. The backward compatibility views script has been created
3. The primary pipeline has been updated to support the `--use-renamed-tables` flag
4. The wrapper script `run_renamed_tables_pipeline.py` has been created

## Method 1: Using the Primary Pipeline with the `--use-renamed-tables` Flag

The primary pipeline (`run_boundary_hexagon_layer_enhanced_pipeline.py`) has been updated to support a new flag `--use-renamed-tables`. When this flag is set, the pipeline will use the modified SQL scripts that create tables with the new naming convention.

### Command

```bash
python epsg3857_pipeline/run_boundary_hexagon_layer_enhanced_pipeline.py --use-renamed-tables
```

### Options

The primary pipeline supports the following options:

- `--config`: Path to the configuration file (default: `epsg3857_pipeline/config/crs_standardized_config_boundary_hexagon.json`)
- `--sql-dir`: Path to the directory containing SQL scripts (default: `epsg3857_pipeline/core/sql`)
- `--container-name`: Name of the Docker container (default: `db`)
- `--verbose`: Print verbose output
- `--use-renamed-tables`: Use the renamed tables

### Example

```bash
python epsg3857_pipeline/run_boundary_hexagon_layer_enhanced_pipeline.py --config epsg3857_pipeline/config/crs_standardized_config_boundary_hexagon.json --sql-dir epsg3857_pipeline/core/sql --container-name db --verbose --use-renamed-tables
```

## Method 2: Using the Wrapper Script

A wrapper script `run_renamed_tables_pipeline.py` has been created that runs the primary pipeline with the `--use-renamed-tables` flag set. This provides a simpler way to run the pipeline with the new table naming convention.

### Command

```bash
python epsg3857_pipeline/run_renamed_tables_pipeline.py
```

### Options

The wrapper script supports the same options as the primary pipeline, except for the `--use-renamed-tables` flag which is always set:

- `--config`: Path to the configuration file (default: `epsg3857_pipeline/config/crs_standardized_config_boundary_hexagon.json`)
- `--sql-dir`: Path to the directory containing SQL scripts (default: `epsg3857_pipeline/core/sql`)
- `--container-name`: Name of the Docker container (default: `db`)
- `--verbose`: Print verbose output

### Example

```bash
python epsg3857_pipeline/run_renamed_tables_pipeline.py --config epsg3857_pipeline/config/crs_standardized_config_boundary_hexagon.json --sql-dir epsg3857_pipeline/core/sql --container-name db --verbose
```

## Verifying the Results

After running the pipeline with the new table naming convention, you can verify that the tables have been created with the new names:

```bash
docker compose exec db psql -U gis -d gis -c "\dt s*"
```

This will list all tables that start with `s`, which should include all the tables with the new naming convention.

You can also verify that the backward compatibility views have been created:

```bash
docker compose exec db psql -U gis -d gis -c "\dv"
```

This will list all views, which should include the backward compatibility views with the old table names.

## Troubleshooting

If you encounter issues when running the pipeline with the new table naming convention, check the following:

1. Ensure that the modified SQL scripts exist in the `epsg3857_pipeline/core/sql/renamed/` directory
2. Ensure that the backward compatibility views script exists
3. Ensure that the primary pipeline has been updated to support the `--use-renamed-tables` flag
4. Check the logs for any error messages

## Conclusion

Running the pipeline with the new table naming convention is straightforward using either the primary pipeline with the `--use-renamed-tables` flag or the wrapper script `run_renamed_tables_pipeline.py`. Both methods will create tables with the new naming convention and backward compatibility views with the old table names, ensuring a smooth transition to the new naming convention.