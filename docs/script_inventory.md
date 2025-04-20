# Script Inventory and Consolidation Plan

This document provides an inventory of all scripts in the project, their purposes, and identifies potential redundancies for consolidation.

## Database Management Scripts

| Script | Purpose | Redundancy Notes |
|--------|---------|------------------|
| `scripts/reset_database.py` | Resets the database, optionally reimports OSM data | Core utility, no redundancy |

## Pipeline Scripts

| Script | Purpose | Redundancy Notes |
|--------|---------|------------------|
| `scripts/run_pipeline.py` | Runs the standard terrain graph pipeline | Original pipeline script |
| `scripts/run_pipeline_enhanced.py` | Runs the enhanced terrain graph pipeline with improved cost calculation | Enhanced version of run_pipeline.py |
| `planning/scripts/run_water_obstacle_pipeline.py` | Runs the water obstacle modeling pipeline | New pipeline focused on water modeling |
| `planning/scripts/run_water_obstacle_pipeline_fixed.py` | Runs the improved water obstacle pipeline with better dissolve step | Fixed version of run_water_obstacle_pipeline.py |

**Consolidation Opportunity**: Consider creating a unified pipeline script that can run any of the pipelines based on command-line arguments.

## Export Scripts

| Script | Purpose | Redundancy Notes |
|--------|---------|------------------|
| `tools/export_slice_simple.py` | Exports a simple radius-based graph slice | Basic export functionality |
| `tools/export_slice_enhanced.py` | Exports an isochrone-based graph slice | Enhanced version of export_slice_simple.py |
| `tools/export_slice_enhanced_fixed.py` | Fixed version of export_slice_enhanced.py | Bug-fixed version of export_slice_enhanced.py |
| `scripts/export_slice_with_attributes.py` | Exports a graph slice with OSM attributes preserved | Attribute-focused version of export scripts |

**Consolidation Opportunity**: Consolidate all export scripts into a single script with different modes (simple, enhanced, with-attributes).

## Visualization Scripts

| Script | Purpose | Redundancy Notes |
|--------|---------|------------------|
| `visualize_graph.py` | Visualizes a GraphML file | General graph visualization |
| `planning/scripts/visualize_water_obstacles.py` | Visualizes water obstacles and terrain grid | Water-specific visualization |

**Consolidation Opportunity**: These serve different purposes but could potentially be unified with different visualization modes.

## Environmental Condition Scripts

| Script | Purpose | Redundancy Notes |
|--------|---------|------------------|
| `planning/scripts/update_environmental_conditions.py` | Updates environmental conditions in the database | Unique functionality, no redundancy |

## Testing Scripts

| Script | Purpose | Redundancy Notes |
|--------|---------|------------------|
| `planning/scripts/test_water_obstacle_pipeline.py` | Tests the water obstacle pipeline | Comprehensive test for water pipeline |
| `planning/tests/test_script_imports.py` | Tests that scripts can be imported without errors | Basic import tests |
| `planning/run_tests.sh` | Shell script to run all tests | Test runner |

**Consolidation Opportunity**: Create a unified testing framework that can test all pipelines.

## Analysis Scripts

| Script | Purpose | Redundancy Notes |
|--------|---------|------------------|
| `scripts/analyze_osm_attributes.py` | Analyzes OSM attributes in the database | Unique functionality, no redundancy |
| `scripts/run_sql_queries.py` | Runs SQL queries against the database | Utility script, no redundancy |

## SQL Scripts

| Script | Purpose | Redundancy Notes |
|--------|---------|------------------|
| `planning/sql/01_extract_water_features.sql` | Extracts water features from OSM data | Core water pipeline SQL |
| `planning/sql/02_create_water_buffers.sql` | Creates buffers around water features | Core water pipeline SQL |
| `planning/sql/03_dissolve_water_buffers.sql` | Dissolves overlapping water buffers | Original dissolve SQL |
| `planning/sql/03_dissolve_water_buffers_fixed.sql` | Fixed version of dissolve water buffers | Fixed version with better clustering |
| `planning/sql/03_dissolve_water_buffers_improved.sql` | Improved version of dissolve water buffers | Optimized for large datasets with proper coordinate transformation |
| `planning/sql/04_create_terrain_grid.sql` | Creates a terrain grid for the study area | Core water pipeline SQL |
| `planning/sql/05_create_terrain_edges.sql` | Creates terrain edges connecting grid cells | Core water pipeline SQL |
| `planning/sql/06_create_water_edges.sql` | Creates water edges representing water obstacles | Core water pipeline SQL |
| `planning/sql/07_create_environmental_tables.sql` | Adds environmental conditions to the water edges | Core water pipeline SQL |

**Consolidation Opportunity**: The three versions of the dissolve water buffers SQL could be consolidated into a single parameterized SQL file.

## Utility Scripts

| Script | Purpose | Redundancy Notes |
|--------|---------|------------------|
| `scripts/extract_osm_subset.py` | Extracts a subset of an OSM PBF file | Unique functionality, no redundancy |
| `scripts/setup_dev_environment.sh` | Sets up the development environment | Unique functionality, no redundancy |
| `planning/scripts/config_loader.py` | Loads configuration from JSON files | Utility for water pipeline, no redundancy |

## Consolidation Plan

Based on the analysis above, here's a plan for consolidating scripts:

### 1. Unified Pipeline Script

Create a new script `scripts/run_unified_pipeline.py` that can run any of the three pipelines:
- Standard terrain graph pipeline
- Enhanced terrain graph pipeline
- Water obstacle modeling pipeline

This script would take a `--mode` parameter to specify which pipeline to run, along with all the parameters needed for each pipeline.

### 2. Unified Export Script

Create a new script `tools/export_unified.py` that combines the functionality of all export scripts:
- Simple radius-based export
- Isochrone-based export
- Export with attributes
- Export with water obstacle information

This script would take a `--mode` parameter to specify which export method to use.

### 3. Unified Visualization Script

Create a new script `visualize_unified.py` that can visualize:
- GraphML files
- Water obstacles and terrain grid
- Combined visualizations

This script would take a `--mode` parameter to specify what to visualize.

### 4. Unified Testing Framework

Create a new directory `tests/` at the project root with:
- Unit tests for all components
- Integration tests for all pipelines
- A unified test runner script

### 5. Documentation Updates

Update all documentation to reflect the consolidated scripts, including:
- README.md
- docs/quick_start.md
- docs/project_notes.md
- docs/enhanced_pipeline.md
- planning/README.md

## Implementation Priority

1. Unified Pipeline Script (highest priority)
2. Unified Export Script
3. Unified Testing Framework
4. Unified Visualization Script (lowest priority)

## Migration Strategy

1. Create the new consolidated scripts
2. Update documentation to reference the new scripts
3. Deprecate but don't remove the old scripts (add deprecation warnings)
4. After a transition period, remove the deprecated scripts
