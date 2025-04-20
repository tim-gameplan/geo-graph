# Terrain Graph Pipeline

A scalable, maintainable pipeline for producing terrain-aware routing graphs from OpenStreetMap data, water features, and digital elevation models.

## Overview

This project creates a complete pipeline for:

1. **Master PostGIS + pgRouting graph** (roads + water-buffer + terrain) for continental extents
2. **On-demand AOI slices** (GraphML and Valhalla tiles) sized for up to a 24-hour drive
3. **Automation tooling** (Typer CLI + Makefile + cron) for scheduled and ad-hoc builds

## Pipeline Architecture

```
                 ┌───────────────────────────────┐
                 │  Geofabrik PBF (continent)    │
                 └──────────────┬────────────────┘
                                ▼
                    (1) osm2pgsql --flex
                                ▼
                ┌───────────────────────────────┐
                │   PostGIS / pgRouting DB      │
                │  • roads_lines                │
                │  • water_polys                │
                │  • dem_rasters (optional)     │
                └─────────┬─────────┬───────────┘
                          │         │
          (2a) water buf  │         │ (2b) terrain grid
           + graph build  │         │   + slope cost
                          ▼         ▼
                   water_edges   terrain_edges
                          └─────────┬───────────┐
                                    ▼
                        unified_edges / nodes
                                    ▼
                (3) Python (GeoAlchemy2 + NetworkX)
                                    ▼
                        final_graph.graphml
```

## Key Features

- **Parameterized water buffers** - Configurable buffer distances around water features
- **Customizable terrain grid** - Adjustable hex grid density (coarse, default, fine)
- **Efficient slicing** - Export only the subgraph reachable within a specified time
- **Multiple export formats** - GraphML for analysis, Valhalla tiles for routing
- **OSM attribute preservation** - Retain OSM tags like highway type, names, and surface in the graph
- **Benchmarking tools** - Memory and performance profiling for different AOI sizes
- **Docker-based development** - Easy setup with PostgreSQL, PostGIS, and pgAdmin

## System Requirements

- Docker and Docker Compose
- Python 3.9+
- 8GB+ RAM for development (64GB recommended for production/large AOIs)
- OSM PBF data file (sample provided in data/iowa-latest.osm.pbf)

## Quick Start

```bash
# Start Docker containers
docker compose up -d

# Set up Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Load OSM data and build the graph
# (See docs/quick_start.md for detailed steps)

# Export a 1-hour drive GraphML slice (basic)
python tools/export_slice.py slice \
       --lon -93.63 --lat 41.99 \
       --minutes 60 \
       --outfile ia_central.graphml

# Export a 1-hour drive GraphML slice (enhanced with isochrone)
python tools/export_slice_enhanced_fixed.py \
       --lon -93.63 --lat 41.99 \
       --minutes 60 \
       --outfile isochrone_enhanced.graphml

# Visualize the exported graph
python visualize_graph.py isochrone_enhanced.graphml

# Reset the database and rerun the pipeline (if needed)
python scripts/reset_database.py --reset-all
python scripts/run_pipeline.py  # Basic pipeline
python scripts/run_pipeline_enhanced.py  # Enhanced pipeline with OSM attributes
```

For detailed instructions, see [Quick Start Guide](docs/quick_start.md).

## Pipeline Stages

| Stage | Tooling | Key Commands/Concepts | Parallel Hints |
|-------|---------|------------------------|----------------|
| 1. Ingest OSM | osm2pgsql 1.12+ with a Flex style file | `osm2pgsql --create --database osm_na --style flex.lua --slim -G --hstore --tag-transform-script tags.lua north-america-latest.osm.pbf` | `--number-processes=N` uses all cores; mount the WAL on fast SSD |
| 2a. Water buffer graph | PostGIS + pgRouting | Create buffered water polygons, simplify to reduce vertices, build topology | PostGIS 3.4 gains ST_Parallelize; set max_parallel_workers_per_gather |
| 2b. Terrain grid | PostGIS + raster DEM + plpgsql | Create hex grid, remove cells intersecting water/roads, add slope-based cost, build topology | Raster slope pre-computed in a materialized view; parallel query works well |
| 2c. Merge graphs | PostGIS | Union all edge tables into unified graph | Ensure unique node IDs by adding table prefixes before pgr_createTopology |
| 3. Export to GraphML | Python 3.12, GeoAlchemy2, NetworkX | Read edges from database, create NetworkX graph, write to GraphML | Use dask-geopandas if edges > 50M rows; chunk by node ID ranges |

## Documentation

- [Quick Start Guide](docs/quick_start.md) - Get up and running quickly
- [Project Notes](docs/project_notes.md) - Comprehensive documentation
- [OSM Attributes Guide](docs/osm_attributes.md) - Preserving OSM attributes in the graph
- [Enhanced Pipeline](docs/enhanced_pipeline.md) - Isochrone-based graph slicing and OSM attribute preservation
- [Water Edge Comparison](docs/water_edge_comparison.md) - Comparison of original vs. dissolved water edges
- [Project Plan](docs/terrain_graph_project_plan.md) - Project timeline and deliverables
- [Code Audit](docs/code_audit.md) - Analysis of existing codebase

## Benchmark AOI Test Cases

| Label | Approx center (lon, lat) | Notes |
|-------|--------------------------|-------|
| **LA-Contrail** | -92.95, 31.14 | Region around Fort Johnson/JRTC in western Louisiana |
| **IA-Central** | -93.63, 41.99 | Iowa State → rural & interstate mix |
| **IA-West** | -95.86, 41.26 | Council Bluffs / Omaha approaches |
| **CA-NTC** | -116.68, 35.31 | Fort Irwin & National Training Center desert |

## License

This project is licensed under the MIT License - see the LICENSE file for details.
