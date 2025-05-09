# SQL Script Modification Approach

This document outlines the approach for modifying the SQL scripts to use the Pipeline Stage Prefixing naming convention.

## General Approach

For each SQL script, we'll apply the following changes:

1. Add a header comment explaining the purpose of the script
2. Rename tables according to the naming convention
3. Update references to other tables to use their new names
4. Update spatial index names to match the new table names
5. Update log messages to use the new table names

## Step-by-Step Process

### 1. Add Header Comment

Add a header comment to the script that explains its purpose and the changes made:

```sql
/*
 * Script: 01_extract_water_features_3857.sql
 * Purpose: Extract water features from OSM data
 * 
 * This script extracts water features (polygons and lines) from OSM data
 * and creates tables with the following naming convention:
 * - s01_water_features_polygon: Water feature polygons
 * - s01_water_features_line: Water feature lines
 * - s01_water_features_view: View combining polygon and line water features
 */
```

### 2. Rename Tables

Replace all table creation statements to use the new table names:

```sql
-- Old code
CREATE TABLE water_features_polygon AS
SELECT ...

-- New code
CREATE TABLE s01_water_features_polygon AS
SELECT ...
```

### 3. Update References to Other Tables

Replace all references to other tables with their new names:

```sql
-- Old code
SELECT * FROM water_features_polygon;

-- New code
SELECT * FROM s01_water_features_polygon;
```

### 4. Update Spatial Index Names

Replace all spatial index names to match the new table names:

```sql
-- Old code
CREATE INDEX water_features_polygon_geom_idx ON water_features_polygon USING GIST (geom);

-- New code
CREATE INDEX s01_water_features_polygon_geom_idx ON s01_water_features_polygon USING GIST (geom);
```

### 5. Update Log Messages

Replace all log messages to use the new table names:

```sql
-- Old code
RAISE NOTICE 'Created water_features_polygon table with % rows', count;

-- New code
RAISE NOTICE 'Created s01_water_features_polygon table with % rows', count;
```

## Example: Modifying 03_dissolve_water_buffers_3857.sql

Let's walk through the process of modifying `03_dissolve_water_buffers_3857.sql` as an example.

### Original Script (Simplified)

```sql
-- Dissolve water buffers
CREATE TABLE dissolved_water_buffers AS
SELECT ST_Union(geom) AS geom
FROM water_buffers;

-- Create spatial index
CREATE INDEX dissolved_water_buffers_geom_idx ON dissolved_water_buffers USING GIST (geom);

-- Extract individual polygons
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

### Modified Script

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

-- Dissolve water buffers
CREATE TABLE s03_water_buffers_dissolved AS
SELECT ST_Union(geom) AS geom
FROM s02_water_buffers;

-- Create spatial index
CREATE INDEX s03_water_buffers_dissolved_geom_idx ON s03_water_buffers_dissolved USING GIST (geom);

-- Extract individual polygons
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

## Special Considerations

### Views

For views, we'll create new views with the new naming convention and update the view definition to reference the new table names:

```sql
-- Old code
CREATE VIEW water_features AS
SELECT * FROM water_features_polygon
UNION ALL
SELECT * FROM water_features_line;

-- New code
CREATE VIEW s01_water_features_view AS
SELECT * FROM s01_water_features_polygon
UNION ALL
SELECT * FROM s01_water_features_line;
```

### Temporary Tables

For temporary tables, we'll keep the original names since they are only used within the script and don't persist in the database:

```sql
-- Keep the original name for temporary tables
CREATE TEMPORARY TABLE temp_water_features AS
SELECT * FROM s01_water_features_polygon;
```

### Functions and Procedures

For functions and procedures, we'll update the function body to reference the new table names:

```sql
-- Old code
CREATE OR REPLACE FUNCTION get_water_features()
RETURNS TABLE (id INTEGER, geom GEOMETRY) AS $$
BEGIN
    RETURN QUERY SELECT id, geom FROM water_features_polygon;
END;
$$ LANGUAGE plpgsql;

-- New code
CREATE OR REPLACE FUNCTION get_water_features()
RETURNS TABLE (id INTEGER, geom GEOMETRY) AS $$
BEGIN
    RETURN QUERY SELECT id, geom FROM s01_water_features_polygon;
END;
$$ LANGUAGE plpgsql;
```

## Testing

After modifying each script, we'll test it to ensure it works correctly:

1. Reset the database to a clean state
2. Run all previous scripts in the pipeline
3. Run the modified script
4. Verify that the expected tables are created
5. Check that the tables have the expected structure
6. Validate that the data in the tables is correct
7. Verify that spatial indexes are created

## Conclusion

This approach provides a systematic way to modify the SQL scripts to use the Pipeline Stage Prefixing naming convention. By following this approach, we can ensure that all scripts are modified consistently and correctly.