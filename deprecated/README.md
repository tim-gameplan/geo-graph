# Deprecated Files

This directory contains files that are no longer used in the main pipeline but are kept for reference.

## Overview

As the project has evolved, some files have been replaced with improved versions or are no longer needed. These files are moved to this directory to keep the main directories clean while preserving the history of the project.

## Deprecated Files

### Scripts

- **export_slice_with_attributes.py**: Replaced by `tools/export_slice_enhanced_fixed.py`, which provides improved isochrone-based slicing and better attribute handling.
- **run_pipeline.py**: Replaced by `scripts/run_pipeline_enhanced.py`, which provides improved OSM attribute preservation and better water feature modeling.

### SQL Files

- **build_terrain_grid.sql**: Replaced by `sql/build_terrain_grid_simple.sql`, which provides a simpler and more efficient terrain grid creation process.
- **build_water_buffers.sql**: Replaced by `sql/build_water_buffers_simple.sql`, which provides a simpler and more efficient water buffer creation process.
- **build_water_buffers_simple.sql**: Moved from `sql/` to `deprecated/sql/` and then back to `sql/` as it's still needed by the enhanced pipeline.
- **create_unified_edges_enhanced.sql**: Replaced by `sql/create_unified_edges_enhanced_fixed.sql`, which fixes issues with the original version.
- **create_unified_edges_enhanced_fixed.sql**: Replaced by `sql/create_unified_edges_enhanced_fixed_v2.sql`, which provides further improvements.
- **create_unified_edges_with_attributes.sql**: Replaced by `sql/create_unified_edges_enhanced_fixed_v2.sql`, which provides improved attribute handling.
- **create_unified_edges.sql**: Replaced by `sql/create_unified_edges_enhanced_fixed_v2.sql`, which provides improved OSM attribute preservation.
- **derive_road_and_water_enhanced.sql**: Replaced by `sql/derive_road_and_water_enhanced_fixed.sql`, which fixes issues with the original version.
- **derive_road_and_water_fixed.sql**: Replaced by `sql/derive_road_and_water_enhanced_fixed.sql`, which provides improved OSM attribute preservation.
- **derive_road_and_water.sql**: Replaced by `sql/derive_road_and_water_enhanced_fixed.sql`, which provides improved OSM attribute preservation.
- **refresh_topology_fixed.sql**: Replaced by `sql/refresh_topology_fixed_v2.sql`, which provides improved topology handling.
- **refresh_topology_simple.sql**: Replaced by `sql/refresh_topology_fixed_v2.sql`, which provides improved topology handling.
- **refresh_topology.sql**: Replaced by `sql/refresh_topology_fixed_v2.sql`, which provides improved topology handling.

### Tools

- **export_slice_enhanced.py**: Replaced by `tools/export_slice_enhanced_fixed.py`, which fixes issues with the original version.
- **export_slice_simple.py**: Replaced by `tools/export_slice_enhanced_fixed.py`, which provides improved isochrone-based slicing.
- **export_slice.py**: Replaced by `tools/export_slice_enhanced_fixed.py`, which provides improved isochrone-based slicing.

## When to Use Deprecated Files

In general, you should not use the deprecated files for new development. However, they may be useful for reference or for understanding the history of the project.

If you need to use a deprecated file, consider copying it to the appropriate directory and updating it to match the current project structure and naming conventions.

## Moving Files to Deprecated

When moving files to the deprecated directory, follow these guidelines:

1. Move the file to the corresponding subdirectory in `deprecated/` (e.g., `scripts/` to `deprecated/scripts/`).
2. Update the README.md file in the deprecated directory to document the file and why it was deprecated.
3. Update any documentation that references the file to point to the new version.
4. If the file is still referenced by other files, update those references to point to the new version.

## Restoring Files from Deprecated

If you need to restore a file from the deprecated directory, follow these guidelines:

1. Copy the file to the appropriate directory (e.g., `deprecated/scripts/` to `scripts/`).
2. Update the file to match the current project structure and naming conventions.
3. Update any references to the file in other files.
4. Update the documentation to reflect the restored file.
