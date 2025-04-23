# CRS Standardization and Water Feature Processing Plan

## 1. Problem Statement

After analyzing the terrain system codebase, we've identified two key issues that need to be addressed:

### 1.1 Coordinate Reference System (CRS) Inconsistency

The current implementation has inconsistent CRS handling throughout the pipeline:

- In `02_create_water_buffers.sql`, geometries are transformed to EPSG:4326 (WGS84) before buffering:
  ```sql
  ST_Buffer(ST_Transform(geom, 4326)::geography, :buffer_size)::geometry(MultiPolygon, 4326)
  ```

- The improved dissolve script (`03_dissolve_water_buffers_improved.sql`) correctly transforms to EPSG:3857 (Web Mercator) for simplification:
  ```sql
  ST_Transform(
      ST_SimplifyPreserveTopology(
          ST_Transform(geom, 3857),
          5
      ),
      4326
  )
  ```
  
- The original dissolve script (`03_dissolve_water_buffers.sql`) performs simplification directly on EPSG:4326 geometries, which causes distortion:
  ```sql
  ST_SimplifyPreserveTopology(geom, 1.0)
  ```

This inconsistency leads to:
- Inaccurate buffer distances (degrees vs. meters)
- Distorted simplification (especially at higher latitudes)
- Potential topology errors when combining features processed with different CRS

### 1.2 Linear Water Feature Processing

While linear water features (rivers, streams, etc.) are correctly extracted and buffered in the pipeline, there may be issues with how they're processed:

- Linear features may not be properly visualized due to CRS issues
- The buffer sizes may not be appropriate for all types of linear water features
- The dissolve step may not be handling linear features optimally

## 2. Proposed Solutions

### 2.1 Standardize CRS Usage

We will adopt a consistent approach to CRS throughout the pipeline:

1. **Store and Process All Data in EPSG:3857 (Web Mercator)**:
   - Web Mercator is appropriate for analysis as it uses meters as units
   - All spatial operations (buffering, simplification) should be performed in this CRS
   - This ensures consistent and accurate measurements across the entire pipeline

2. **Convert to EPSG:4326 Only for Export**:
   - WGS84 (EPSG:4326) is appropriate for the final exported graph
   - This conversion should happen at the export stage
   - This ensures compatibility with standard GIS tools and web mapping libraries

### 2.2 Improve Water Feature Processing

1. **Enhance Linear Water Feature Handling**:
   - Ensure all linear water features (rivers, streams, canals, etc.) are properly extracted
   - Apply appropriate buffer sizes based on water feature type and attributes
   - Ensure linear features are properly dissolved with adjacent features of the same type

2. **Optimize Buffer Parameters**:
   - Review and adjust buffer sizes for different water feature types
   - Consider additional attributes (width, seasonal flow, etc.) when determining buffer sizes
   - Implement more sophisticated buffer rules based on feature characteristics

3. **Improve Dissolve Process**:
   - Always use the improved dissolve script that correctly handles CRS transformations
   - Ensure the dissolve process preserves important feature characteristics
   - Optimize the clustering parameters to better group related water features

## 3. Implementation Plan

### 3.1 Phase 1: CRS Standardization

#### 3.1.1 Update `01_extract_water_features.sql`

```sql
-- Transform all geometries to EPSG:3857 when extracting
SELECT
    osm_id AS id,
    ST_Transform(way, 3857) AS geom,  -- Transform to Web Mercator
    'polygon' AS feature_type,
    -- other fields...
FROM planet_osm_polygon
WHERE (water IS NOT NULL)
   OR ("natural" = 'water')
   OR (landuse = 'reservoir')

UNION ALL

SELECT
    osm_id AS id,
    ST_Transform(way, 3857) AS geom,  -- Transform to Web Mercator
    'line' AS feature_type,
    -- other fields...
FROM planet_osm_line
WHERE waterway = ANY(ARRAY[:line_types]);
```

#### 3.1.2 Update `02_create_water_buffers.sql`

```sql
-- Perform buffering directly on EPSG:3857 geometries
CASE
    WHEN feature_type = 'polygon' THEN
        CASE
            WHEN water_type = 'water' AND name ILIKE '%lake%' THEN 
                ST_Buffer(geom, :buffer_lake)::geometry(MultiPolygon, 3857)
            -- other cases...
        END
    -- other cases...
END AS geom
```

#### 3.1.3 Update `03_dissolve_water_buffers.sql`

Replace with the improved version that already handles EPSG:3857 correctly, but ensure it doesn't transform back to EPSG:4326 until necessary:

```sql
-- Apply different simplification strategies based on water feature characteristics
simplified_groups AS (
    SELECT
        crossability_group,
        min_crossability,
        -- other fields...
        -- Simplify directly in EPSG:3857 without transforming back
        ST_SimplifyPreserveTopology(
            geom,  -- Already in EPSG:3857
            5      -- 5 meters tolerance
        ) AS geom
    FROM crossability_groups
)
```

#### 3.1.4 Update Configuration Files

Add explicit CRS configuration to the JSON config files:

```json
{
    "crs": {
        "storage": 3857,
        "export": 4326,
        "analysis": 3857
    },
    "water_features": {
        // existing configuration...
    }
}
```

### 3.2 Phase 2: Improve Water Feature Processing

#### 3.2.1 Enhance Linear Water Feature Extraction

Review and update the line types extracted from OSM:

```json
{
    "water_features": {
        "line_types": [
            "river", "stream", "canal", "drain", "ditch",
            "weir", "dam", "waterfall"  // Add additional types
        ],
        // other settings...
    }
}
```

#### 3.2.2 Optimize Buffer Parameters

Review and adjust buffer sizes based on water feature characteristics:

```json
{
    "buffer_sizes": {
        "default": 50,
        "river": {
            "default": 100,
            "width_attribute": true,  // Use width attribute if available
            "width_multiplier": 1.5,  // Add safety margin
            "min_width": 20          // Minimum buffer size
        },
        "stream": {
            "default": 30,
            "width_attribute": true,
            "width_multiplier": 1.5,
            "min_width": 10
        },
        // other water types...
    }
}
```

#### 3.2.3 Update Buffer Creation Logic

Enhance the buffer creation logic to use more sophisticated rules:

```sql
-- For lines with width attribute
WHEN width IS NOT NULL THEN 
    ST_Buffer(
        geom,
        GREATEST(width::numeric * :width_multiplier, :min_width)
    )::geometry(MultiPolygon, 3857)
```

#### 3.2.4 Improve Dissolve Process

Enhance the dissolve process to better handle different water feature types:

```sql
-- Use more sophisticated clustering
connected_clusters AS (
    SELECT
        -- Cluster by water type as well
        water_type,
        CASE
            WHEN crossability < 20 THEN 'low'
            WHEN crossability < 50 THEN 'medium'
            ELSE 'high'
        END AS crossability_group,
        -- Use ST_ClusterDBSCAN with appropriate parameters
        ST_ClusterDBSCAN(geom, 5, 1) OVER (
            PARTITION BY 
                water_type,
                CASE
                    WHEN crossability < 20 THEN 'low'
                    WHEN crossability < 50 THEN 'medium'
                    ELSE 'high'
                END
        ) AS cluster_id,
        -- other fields...
    FROM water_buf
)
```

### 3.3 Phase 3: Update Visualization and Export

#### 3.3.1 Update Visualization Scripts

Ensure visualization scripts handle the CRS correctly:

```python
# Transform geometries to EPSG:4326 for visualization if needed
if gdf.crs and gdf.crs != 'EPSG:4326':
    gdf = gdf.to_crs('EPSG:4326')
```

#### 3.3.2 Update Export Scripts

Ensure export scripts convert to EPSG:4326 appropriately:

```sql
-- In export SQL
SELECT 
    id,
    source,
    target,
    cost,
    -- Transform to EPSG:4326 for export
    ST_Transform(geom, 4326) AS geom
FROM unified_edges 
WHERE -- conditions...
```

## 4. Testing and Validation

### 4.1 Unit Tests

1. **CRS Validation Tests**:
   - Verify that geometries are in the expected CRS at each stage
   - Check that buffer distances are consistent and accurate
   - Ensure simplification preserves topology correctly

2. **Water Feature Tests**:
   - Verify that all water feature types are correctly extracted
   - Check that buffer sizes are appropriate for each feature type
   - Ensure linear features are properly dissolved with adjacent features

### 4.2 Integration Tests

1. **Pipeline Tests**:
   - Run the complete pipeline on test datasets
   - Verify that the output is consistent and accurate
   - Compare results with the previous implementation

2. **Visualization Tests**:
   - Verify that water features are correctly visualized
   - Check that linear features are properly represented
   - Ensure the visualization is consistent with the data

### 4.3 Performance Tests

1. **Benchmark Tests**:
   - Measure the performance of the updated pipeline
   - Compare with the previous implementation
   - Identify any bottlenecks or areas for optimization

## 5. Implementation Timeline

### 5.1 Week 1: CRS Standardization

- Day 1-2: Update SQL scripts for CRS standardization
- Day 3-4: Update configuration files and test
- Day 5: Review and refine

### 5.2 Week 2: Water Feature Processing

- Day 1-2: Enhance linear water feature extraction and buffering
- Day 3-4: Improve dissolve process
- Day 5: Review and refine

### 5.3 Week 3: Visualization and Export

- Day 1-2: Update visualization scripts
- Day 3-4: Update export scripts
- Day 5: Final testing and documentation

## 6. Conclusion

By implementing this plan, we will address the CRS inconsistency issues and improve water feature processing in the terrain system. This will result in more accurate and consistent results, better visualization, and improved performance.

The standardized approach to CRS will ensure that all spatial operations are performed in the appropriate coordinate system, while the enhanced water feature processing will ensure that all water features, including linear features, are correctly represented in the terrain graph.
