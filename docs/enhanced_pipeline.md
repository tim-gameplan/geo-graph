# Enhanced Terrain Graph Pipeline

This document describes the enhanced version of the terrain graph pipeline, which adds support for isochrone-based graph slicing and preserves OSM attributes in the exported graph.

## Overview

The enhanced pipeline builds on the original pipeline by adding the following features:

1. **Isochrone-based graph slicing**: Instead of using a simple radius-based approach, the enhanced pipeline uses pgRouting's driving distance function to calculate areas reachable within a specified travel time.
2. **OSM attribute preservation**: The enhanced pipeline preserves all OSM attributes in the exported graph, allowing for more detailed analysis and visualization.
3. **Improved visualization**: The enhanced pipeline includes a visualization script that can be used to visualize the exported graph.

## Pipeline Architecture

The enhanced pipeline follows the same general architecture as the original pipeline, but with some key differences:

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

## Key Components

### 1. Enhanced SQL Scripts

The enhanced pipeline uses modified versions of the original SQL scripts:

- `derive_road_and_water_enhanced_fixed.sql`: Extracts road and water features from OSM data, preserving all OSM attributes.
- `create_edge_tables_enhanced.sql`: Creates edge tables for the unified graph, preserving all OSM attributes.
- `create_unified_edges_enhanced_fixed_v2.sql`: Combines all edge tables into a unified graph, preserving all OSM attributes.
- `refresh_topology_fixed_v2.sql`: Creates topology for the unified graph, ensuring that all edges have valid source and target nodes.

### 2. Enhanced Export Script

The enhanced pipeline includes a new export script, `export_slice_enhanced_fixed.py`, which:

1. Uses pgRouting's `pgr_drivingDistance` function to calculate areas reachable within a specified travel time.
2. Creates a convex hull of the reachable nodes to approximate an isochrone.
3. Extracts edges that intersect with the isochrone polygon.
4. Preserves all OSM attributes in the exported GraphML file.
5. Optionally exports to Valhalla tiles for routing.

### 3. Visualization Script

The enhanced pipeline includes a visualization script, `visualize_graph.py`, which:

1. Loads a GraphML file.
2. Extracts node positions from the graph.
3. Creates a visualization of the graph using matplotlib.
4. Saves the visualization as a PNG file.

## Usage

### Running the Enhanced Pipeline

```bash
# Run the complete enhanced pipeline
python scripts/run_pipeline_enhanced.py

# Run the enhanced pipeline and export a slice
python scripts/run_pipeline_enhanced.py --export --lon -93.63 --lat 41.99 --minutes 60 --output isochrone_enhanced.graphml
```

### Exporting a Slice

```bash
# Export a slice around a specific coordinate with a 60-minute travel time
python tools/export_slice_enhanced_fixed.py --lon -93.63 --lat 41.99 --minutes 60 --outfile isochrone_enhanced.graphml

# Export a slice with Valhalla tiles
python tools/export_slice_enhanced_fixed.py --lon -93.63 --lat 41.99 --minutes 60 --outfile isochrone_enhanced.zip --valhalla
```

### Visualizing a Graph

```bash
# Visualize a GraphML file
python visualize_graph.py isochrone_enhanced.graphml
```

## Implementation Details

### Isochrone Calculation

The enhanced pipeline uses pgRouting's `pgr_drivingDistance` function to calculate areas reachable within a specified travel time. This function takes a source vertex ID, a maximum travel time, and a cost column, and returns a set of vertices that can be reached within the specified travel time.

The pipeline then creates a convex hull of the reachable vertices to approximate an isochrone polygon. This polygon is used to extract edges that intersect with the isochrone.

### OSM Attribute Preservation

The enhanced pipeline preserves all OSM attributes in the exported graph. This is done by:

1. Extracting all OSM attributes from the OSM data in the `derive_road_and_water_enhanced_fixed.sql` script.
2. Preserving these attributes in the edge tables created by the `create_edge_tables_enhanced.sql` script.
3. Combining all edge tables into a unified graph with all attributes preserved in the `create_unified_edges_enhanced_fixed_v2.sql` script.
4. Including all attributes in the exported GraphML file.

### Graph Visualization

The visualization script uses matplotlib to create a visualization of the graph. It extracts node positions from the graph and draws the graph with nodes and edges. Node labels are added to help identify nodes in the graph.

## Troubleshooting

### Common Issues

- **No vertex found near coordinates**: This can happen if there are no vertices near the specified coordinates. Try using different coordinates or increasing the search radius.
- **No reachable nodes found**: This can happen if the specified travel time is too short or if there are no connected edges near the specified coordinates. Try increasing the travel time or using different coordinates.
- **No edges found within the isochrone polygon**: This can happen if the isochrone polygon is too small or if there are no edges that intersect with the polygon. Try increasing the travel time or using different coordinates.

### Debugging

- Use the `--include-geometry` flag with the export script to include geometry in the exported GraphML file. This can be useful for debugging.
- Check the SQL queries in the export script to ensure they are correctly extracting edges that intersect with the isochrone polygon.
- Use the visualization script to visualize the exported graph and check if it looks correct.

## Future Improvements

- **Improved isochrone calculation**: The current implementation uses a convex hull to approximate an isochrone. A more accurate approach would be to use a concave hull or a more sophisticated isochrone calculation algorithm.
- **Support for multiple travel modes**: The current implementation uses a single cost column for all edges. A more flexible approach would be to support multiple cost columns for different travel modes (e.g., car, bike, foot).
- **Integration with other routing engines**: The current implementation supports export to Valhalla tiles. Future versions could support export to other routing engines like OSRM or GraphHopper.
