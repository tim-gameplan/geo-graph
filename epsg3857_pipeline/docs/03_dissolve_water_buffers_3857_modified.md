# Modified SQL Script: 03_dissolve_water_buffers_3857.sql

This document provides an example of how the `03_dissolve_water_buffers_3857.sql` script would be modified to use the Pipeline Stage Prefixing naming convention.

## Original Script

```sql
-- Dissolve water buffers to create a single geometry
DROP TABLE IF EXISTS dissolved_water_buffers;
CREATE TABLE dissolved_water_buffers AS
SELECT ST_Union(geom) AS geom
FROM water_buffers;

-- Create spatial index
CREATE INDEX dissolved_water_buffers_geom_idx ON dissolved_water_buffers USING GIST (geom);

-- Extract individual polygons from the dissolved water buffers
DROP TABLE IF EXISTS water_obstacles;
CREATE TABLE water_obstacles AS
SELECT ROW_NUMBER() OVER () AS id, (ST_Dump(geom)).geom AS geom
FROM dissolved_water_buffers;

-- Create spatial index
CREATE INDEX water_obstacles_geom_idx ON water_obstacles USING GIST (geom);

-- Log the number of water obstacles
DO $$
DECLARE
    count INTEGER;
BEGIN
    SELECT COUNT(*) INTO count FROM water_obstacles;
    RAISE NOTICE 'Created water_obstacles table with % rows', count;
END $$;
```

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

## Changes Made

1. **Added Header Comment**: Added a header comment explaining the purpose of the script and the tables it creates.

2. **Renamed Tables**:
   - `dissolved_water_buffers` → `s03_water_buffers_dissolved`
   - `water_obstacles` → `s03_water_obstacles`

3. **Updated References to Other Tables**:
   - `water_buffers` → `s02_water_buffers`

4. **Updated Spatial Index Names**:
   - `dissolved_water_buffers_geom_idx` → `s03_water_buffers_dissolved_geom_idx`
   - `water_obstacles_geom_idx` → `s03_water_obstacles_geom_idx`

5. **Updated Log Messages**:
   - `Created water_obstacles table with % rows` → `Created s03_water_obstacles table with % rows`

## Testing

After modifying the script, the following tests should be performed:

1. Reset the database to a clean state
2. Run the previous scripts in the pipeline:
   - `01_extract_water_features_3857.sql`
   - `02_create_water_buffers_3857.sql`
3. Run the modified script
4. Verify that the expected tables are created:
   - `s03_water_buffers_dissolved`
   - `s03_water_obstacles`
5. Check that the tables have the expected structure
6. Validate that the data in the tables is correct
7. Verify that spatial indexes are created:
   - `s03_water_buffers_dissolved_geom_idx`
   - `s03_water_obstacles_geom_idx`

## Conclusion

This example demonstrates how to modify the `03_dissolve_water_buffers_3857.sql` script to use the Pipeline Stage Prefixing naming convention. The same approach can be applied to all other SQL scripts in the pipeline.