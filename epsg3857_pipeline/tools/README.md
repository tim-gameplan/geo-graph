# Support Tools

This directory contains support tools for the EPSG:3857 terrain graph pipeline.

## Overview

These tools are not part of the core pipeline but provide utilities for development, debugging, and maintenance.

## Components

### Database Tools

- `reset_derived_tables.py`: Reset only the derived tables, preserving OSM data
- `reset_osm_tables.py`: Reset only the OSM data tables, preserving derived tables
- `reset_all_tables.py`: Reset all tables in the database

### Diagnostic Tools

- `diagnostic_water_edges.sql`: SQL script for diagnosing water edge creation issues

## Usage

### Database Tools

```bash
# Reset derived tables
python tools/database/reset_derived_tables.py

# Reset OSM tables
python tools/database/reset_osm_tables.py

# Reset all tables
python tools/database/reset_all_tables.py
```

### Diagnostic Tools

```bash
# Run diagnostic queries for water edges
docker exec geo-graph-db-1 psql -U gis -d gis -f tools/diagnostics/diagnostic_water_edges.sql
```
