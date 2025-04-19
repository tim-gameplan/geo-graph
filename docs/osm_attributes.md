# Preserving OSM Attributes in the Terrain Graph

## Overview

The terrain graph pipeline now supports preserving OpenStreetMap (OSM) attributes in the exported graph. This allows for more detailed analysis and visualization of the graph, as well as more accurate routing and other applications.

## Using the Preserve Attributes Feature

To preserve OSM attributes in the terrain graph, use the `--preserve-attributes` flag with the `run_pipeline.py` script:

```bash
python scripts/run_pipeline.py --preserve-attributes
```

This will:
1. Preserve OSM attributes like name, highway, ref, oneway, surface, bridge, tunnel, etc. in the road_edges table
2. Preserve OSM attributes like name, water, natural, waterway, landuse, etc. in the water_polys table
3. Include these attributes in the unified_edges table
4. Add an edge_type attribute to distinguish between road, water, and terrain edges

## Exporting a Graph with Attributes

To export a graph slice with all OSM attributes preserved, use the `export_slice_with_attributes.py` script:

```bash
python scripts/export_slice_with_attributes.py --lon -93.63 --lat 41.99 --radius 5 --outfile data/iowa_central_with_attributes.graphml
```

This will create a GraphML file with all OSM attributes preserved, which can be used for more detailed analysis and visualization.

## Available OSM Attributes

The following OSM attributes are preserved in the exported graph:

### Road Attributes
- name: Street name
- highway: Road type (motorway, primary, secondary, residential, service, track, etc.)
- ref: Road reference number
- oneway: Whether the road is one-way
- surface: Road surface type
- bridge: Whether the road is a bridge
- tunnel: Whether the road is a tunnel
- layer: Vertical layer for overlapping roads
- access: Access restrictions
- service: Service road type
- junction: Junction type

### Water Attributes
- name: Water feature name
- water: Water type
- natural: Natural feature type
- waterway: Waterway type
- landuse: Land use type
- water_type: Derived water type (water, natural, reservoir)

### Edge Type
- edge_type: Type of edge (road, water, terrain)

## Implementation Details

The OSM attributes are preserved through the following process:

1. The `derive_road_and_water_fixed.sql` script is enhanced to include additional columns from the OSM data.
2. The `create_unified_edges_with_attributes.sql` script is used instead of `create_unified_edges.sql` to preserve the attributes in the unified_edges table.
3. The `export_slice_with_attributes.py` script is used to export the graph with all attributes preserved.

## Example Usage

Here's an example of how to use the preserved attributes in a Python script:

```python
import networkx as nx
import matplotlib.pyplot as plt

# Load the graph with attributes
G = nx.read_graphml('data/iowa_central_with_attributes.graphml')

# Color edges by highway type
edge_colors = []
for u, v, data in G.edges(data=True):
    if data.get('edge_type') == 'road':
        if data.get('highway') == 'motorway':
            edge_colors.append('red')
        elif data.get('highway') == 'primary':
            edge_colors.append('orange')
        elif data.get('highway') == 'secondary':
            edge_colors.append('yellow')
        elif data.get('highway') == 'residential':
            edge_colors.append('green')
        else:
            edge_colors.append('blue')
    elif data.get('edge_type') == 'water':
        edge_colors.append('cyan')
    else:
        edge_colors.append('gray')

# Draw the graph
pos = {n: (float(G.nodes[n]['x']), float(G.nodes[n]['y'])) for n in G.nodes()}
nx.draw(G, pos, edge_color=edge_colors, node_size=0, width=0.5)
plt.savefig('graph_with_attributes.png')
```

This will create a visualization of the graph with edges colored by highway type.
