# Database Schema

This document describes the database schema used in the EPSG:3857 pipeline.

## Water Features Tables

### water_features_polygon
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| osm_id | BIGINT | OpenStreetMap ID |
| name | TEXT | Feature name |
| type | TEXT | Water feature type (water, reservoir) |
| geom | GEOMETRY(POLYGON) | Geometry in EPSG:3857 |

### water_features_line
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| osm_id | BIGINT | OpenStreetMap ID |
| name | TEXT | Feature name |
| type | TEXT | Water feature type (river, stream, canal, etc.) |
| geom | GEOMETRY(LINESTRING) | Geometry in EPSG:3857 |

### water_features (VIEW)
A unified view combining water_features_polygon and water_features_line.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key from source table |
| osm_id | BIGINT | OpenStreetMap ID |
| name | TEXT | Feature name |
| type | TEXT | Water feature type |
| geometry_type | TEXT | 'polygon' or 'line' |
| geom | GEOMETRY | Geometry in EPSG:3857 |

## Water Buffers Table

### water_buffers
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| water_feature_id | INTEGER | ID of the water feature |
| feature_type | TEXT | 'polygon' or 'line' |
| buffer_size | NUMERIC | Buffer size in meters |
| geom | GEOMETRY | Buffer geometry in EPSG:3857 |

## Dissolved Water Buffers Table

### dissolved_water_buffers
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| geom | GEOMETRY | Dissolved buffer geometry in EPSG:3857 |

## Water Obstacles Table

### water_obstacles
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| geom | GEOMETRY | Water obstacle geometry in EPSG:3857 |

## Terrain Grid Tables

### terrain_grid
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| geom | GEOMETRY(POLYGON) | Hexagonal grid cell geometry in EPSG:3857 |
| cost | NUMERIC | Base cost for traversing the cell |

### terrain_grid_points
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| grid_id | INTEGER | Reference to terrain_grid.id |
| geom | GEOMETRY(POINT) | Centroid point geometry in EPSG:3857 |

## Terrain Edges Table

### terrain_edges
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| source_id | INTEGER | Source terrain grid point ID |
| target_id | INTEGER | Target terrain grid point ID |
| length | NUMERIC | Edge length in meters |
| cost | NUMERIC | Edge cost (travel time) |
| geom | GEOMETRY(LINESTRING) | Edge geometry in EPSG:3857 |

## Water Edges Table

### water_edges
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| source_id | INTEGER | Source terrain grid point ID |
| target_id | INTEGER | Target terrain grid point ID |
| length | NUMERIC | Edge length in meters |
| cost | NUMERIC | Edge cost (travel time) |
| water_obstacle_id | INTEGER | ID of the water obstacle |
| speed_factor | NUMERIC | Speed factor for water (< 1.0) |
| geom | GEOMETRY(LINESTRING) | Edge geometry in EPSG:3857 |

## Environmental Conditions Table

### environmental_conditions
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| edge_id | INTEGER | Edge ID |
| edge_type | TEXT | Edge type (terrain, water) |
| condition | TEXT | Environmental condition |
| factor | NUMERIC | Speed factor |

## Unified Edges Table

### unified_edges
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| source_id | INTEGER | Source terrain grid point ID |
| target_id | INTEGER | Target terrain grid point ID |
| length | NUMERIC | Edge length in meters |
| cost | NUMERIC | Edge cost (travel time) |
| edge_type | TEXT | Edge type (terrain, water) |
| speed_factor | NUMERIC | Speed factor for the edge |
| geom | GEOMETRY(LINESTRING) | Edge geometry in EPSG:3857 |

## Graph Tables

### graph_vertices
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| geom | GEOMETRY(POINT) | Vertex geometry in EPSG:3857 |

### graph_edges
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| source | INTEGER | Source vertex ID |
| target | INTEGER | Target vertex ID |
| cost | NUMERIC | Edge cost (travel time) |
| edge_type | TEXT | Edge type (terrain, water) |
| geom | GEOMETRY(LINESTRING) | Edge geometry in EPSG:3857 |

### graph_topology
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| source | INTEGER | Source vertex ID |
| target | INTEGER | Target vertex ID |
| cost | NUMERIC | Edge cost (travel time) |
| edge_type | TEXT | Edge type (terrain, water) |
| geom | GEOMETRY(LINESTRING) | Edge geometry in EPSG:3857 |
