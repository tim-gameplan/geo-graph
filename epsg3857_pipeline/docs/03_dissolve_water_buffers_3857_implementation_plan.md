# Implementation Plan for 03_dissolve_water_buffers_3857.sql

This document outlines the implementation plan for modifying the `03_dissolve_water_buffers_3857.sql` script to use the Pipeline Stage Prefixing naming convention.

## Current Script Analysis

The current script performs the following operations:

1. Dissolves water buffers to create a single geometry
2. Creates a spatial index on the dissolved water buffers
3. Extracts individual polygons from the dissolved water buffers as water obstacles
4. Creates a spatial index on the water obstacles
5. Logs the number of water obstacles created

The script creates the following tables:
- `dissolved_water_buffers`: Contains the dissolved water buffers
- `water_obstacles`: Contains the individual polygons extracted from the dissolved water buffers

The script references the following tables:
- `water_buffers`: Contains the water buffers created in the previous stage

## Modification Plan

### 1. Rename Tables

The tables will be renamed according to the Pipeline Stage Prefixing naming convention:

- `dissolved_water_buffers` → `s03_water_buffers_dissolved`
- `water_obstacles` → `s03_water_obstacles`

### 2. Update References to Other Tables

References to other tables will be updated to use their new names:

- `water_buffers` → `s02_water_buffers`

### 3. Update Spatial Index Names

Spatial index names will be updated to match the new table names:

- `dissolved_water_buffers_geom_idx` → `s03_water_buffers_dissolved_geom_idx`
- `water_obstacles_geom_idx` → `s03_water_obstacles_geom_idx`

### 4. Update Log Messages

Log messages will be updated to use the new table names:

- `Created water_obstacles table with % rows` → `Created s03_water_obstacles table with % rows`

### 5. Add Header Comment

A header comment will be added to explain the purpose of the script and the tables it creates:

```sql
/*
 * Script: 03_dissolve_water_buffers_3857.sql
 * Purpose: Dissolve water buffers and extract water obstacles
 * 
 * This script dissolves water buffers and extracts individual polygons
 * as water obstacles, creating the following tables:
 * - s03_water_buffers_dissolved: Dissolved water buffers
 * - s03_water_obstacles: Water obstacles extracted from dissolved buffers
 */
```

## Implementation Steps

1. Create the directory for the modified scripts if it doesn't exist:
   ```bash
   mkdir -p epsg3857_pipeline/core/sql/renamed
   ```

2. Create the modified script:
   ```bash
   touch epsg3857_pipeline/core/sql/renamed/03_dissolve_water_buffers_3857.sql
   ```

3. Add the header comment to the script

4. Copy the original script and make the following changes:
   - Rename tables
   - Update references to other tables
   - Update spatial index names
   - Update log messages

5. Save the modified script

## Modified Script

```sql
/*
 * Script: 03_dissolve_water_buffers_3857.sql
 * Purpose: Dissolve water buffers and extract water obstacles
 * 
 * This script dissolves water buffers and extracts individual polygons
 * as water obstacles, creating the following tables:
 * - s03_water_buffers_dissolved: Dissolved water buffers
 * - s03_water_obstacles: Water obstacles extracted from dissolved buffers
 */

-- Dissolve water buffers to create a single geometry
DROP TABLE IF EXISTS s03_water_buffers_dissolved;
CREATE TABLE s03_water_buffers_dissolved AS
SELECT ST_Union(geom) AS geom
FROM s02_water_buffers;

-- Create spatial index
CREATE INDEX s03_water_buffers_dissolved_geom_idx ON s03_water_buffers_dissolved USING GIST (geom);

-- Extract individual polygons from the dissolved water buffers
DROP TABLE IF EXISTS s03_water_obstacles;
CREATE TABLE s03_water_obstacles AS
SELECT ROW_NUMBER() OVER () AS id, (ST_Dump(geom)).geom AS geom
FROM s03_water_buffers_dissolved;

-- Create spatial index
CREATE INDEX s03_water_obstacles_geom_idx ON s03_water_obstacles USING GIST (geom);

-- Log the number of water obstacles
DO $$
DECLARE
    count INTEGER;
BEGIN
    SELECT COUNT(*) INTO count FROM s03_water_obstacles;
    RAISE NOTICE 'Created s03_water_obstacles table with % rows', count;
END $$;
```

## Testing Plan

After implementing the modified script, the following tests will be performed:

1. Reset the database to a clean state:
   ```bash
   python epsg3857_pipeline/tools/database/reset_non_osm_tables.py
   ```

2. Run the previous scripts in the pipeline:
   ```bash
   docker compose exec db psql -U gis -d gis -f /path/to/renamed/01_extract_water_features_3857.sql
   docker compose exec db psql -U gis -d gis -f /path/to/renamed/02_create_water_buffers_3857.sql
   ```

3. Run the modified script:
   ```bash
   docker compose exec db psql -U gis -d gis -f /path/to/renamed/03_dissolve_water_buffers_3857.sql
   ```

4. Verify that the expected tables are created:
   ```bash
   docker compose exec db psql -U gis -d gis -c "SELECT COUNT(*) FROM s03_water_buffers_dissolved;"
   docker compose exec db psql -U gis -d gis -c "SELECT COUNT(*) FROM s03_water_obstacles;"
   ```

5. Check that the tables have the expected structure:
   ```bash
   docker compose exec db psql -U gis -d gis -c "\\d s03_water_buffers_dissolved"
   docker compose exec db psql -U gis -d gis -c "\\d s03_water_obstacles"
   ```

6. Verify that spatial indexes are created:
   ```bash
   docker compose exec db psql -U gis -d gis -c "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 's03_water_buffers_dissolved';"
   docker compose exec db psql -U gis -d gis -c "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 's03_water_obstacles';"
   ```

7. Compare the results with the original script:
   ```bash
   docker compose exec db psql -U gis -d gis -c "SELECT COUNT(*) FROM water_obstacles;"
   docker compose exec db psql -U gis -d gis -c "SELECT COUNT(*) FROM s03_water_obstacles;"
   ```

## Conclusion

This implementation plan provides a detailed approach for modifying the `03_dissolve_water_buffers_3857.sql` script to use the Pipeline Stage Prefixing naming convention. By following this plan, we can ensure that the script is modified correctly and works as expected.