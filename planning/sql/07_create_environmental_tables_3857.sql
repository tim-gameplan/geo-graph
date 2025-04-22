-- 07_create_environmental_tables_3857.sql
-- Create tables and functions for dynamic environmental condition adjustments
-- Compatible with EPSG:3857 (Web Mercator) standardized pipeline
-- Parameters:
-- :env_rainfall - Initial rainfall value (0.0 = dry, 1.0 = heavy rain)
-- :env_snow_depth - Initial snow depth in meters
-- :env_temperature - Initial temperature in Celsius

-- Create environmental_conditions table
CREATE TABLE IF NOT EXISTS environmental_conditions (
    condition_name TEXT PRIMARY KEY,
    value NUMERIC,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert or update default conditions
INSERT INTO environmental_conditions (condition_name, value) VALUES
    ('rainfall', :env_rainfall),
    ('snow_depth', :env_snow_depth),
    ('temperature', :env_temperature)
ON CONFLICT (condition_name) DO UPDATE
    SET value = EXCLUDED.value,
        last_updated = CURRENT_TIMESTAMP;

-- Create function to update water crossability based on environmental conditions
CREATE OR REPLACE FUNCTION update_water_crossability() RETURNS VOID AS $$
DECLARE
    rainfall NUMERIC;
    snow_depth NUMERIC;
    temperature NUMERIC;
    original_water_edges_count INTEGER;
    updated_water_edges_count INTEGER;
BEGIN
    -- Get current environmental conditions
    SELECT value INTO rainfall FROM environmental_conditions WHERE condition_name = 'rainfall';
    SELECT value INTO snow_depth FROM environmental_conditions WHERE condition_name = 'snow_depth';
    SELECT value INTO temperature FROM environmental_conditions WHERE condition_name = 'temperature';
    
    -- Count original water edges
    SELECT COUNT(*) INTO original_water_edges_count FROM water_edges;
    
    -- Create a backup of the original water edges if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'water_edges_original') THEN
        CREATE TABLE water_edges_original AS SELECT * FROM water_edges;
    END IF;
    
    -- Update water edges cost based on environmental conditions
    UPDATE water_edges
    SET cost = (
        SELECT 
            CASE
                -- Frozen water (below freezing and no rainfall)
                WHEN temperature < 0 AND rainfall < 0.1 THEN 
                    CASE
                        -- Deep snow makes crossing harder
                        WHEN snow_depth > 0.5 THEN original.cost * 0.8
                        -- Frozen water with little snow is easier to cross
                        ELSE original.cost * 0.5
                    END
                -- Heavy rainfall makes crossing harder
                WHEN rainfall > 0.7 THEN original.cost * (1.0 + rainfall)
                -- Moderate rainfall
                WHEN rainfall > 0.3 THEN original.cost * (1.0 + (rainfall * 0.5))
                -- Light rainfall
                WHEN rainfall > 0 THEN original.cost * (1.0 + (rainfall * 0.2))
                -- Default - no change
                ELSE original.cost
            END
        FROM water_edges_original original
        WHERE original.id = water_edges.id
    );
    
    -- Count updated water edges
    SELECT COUNT(*) INTO updated_water_edges_count FROM water_edges;
    
    -- Log the update
    RAISE NOTICE 'Updated water crossability with environmental factors:';
    RAISE NOTICE '  - Rainfall: %', rainfall;
    RAISE NOTICE '  - Snow depth: % m', snow_depth;
    RAISE NOTICE '  - Temperature: % °C', temperature;
    RAISE NOTICE '  - Updated % water edges', updated_water_edges_count;
END;
$$ LANGUAGE plpgsql;

-- Create a view to show the current environmental conditions
CREATE OR REPLACE VIEW current_environment AS
SELECT 
    condition_name,
    value,
    last_updated,
    CASE
        WHEN condition_name = 'rainfall' THEN
            CASE
                WHEN value = 0 THEN 'Dry'
                WHEN value < 0.3 THEN 'Light rain'
                WHEN value < 0.7 THEN 'Moderate rain'
                ELSE 'Heavy rain'
            END
        WHEN condition_name = 'snow_depth' THEN
            CASE
                WHEN value = 0 THEN 'No snow'
                WHEN value < 0.1 THEN 'Light snow'
                WHEN value < 0.5 THEN 'Moderate snow'
                ELSE 'Deep snow'
            END
        WHEN condition_name = 'temperature' THEN
            CASE
                WHEN value < 0 THEN 'Below freezing'
                WHEN value < 10 THEN 'Cold'
                WHEN value < 25 THEN 'Moderate'
                ELSE 'Hot'
            END
        ELSE 'Unknown'
    END AS description
FROM environmental_conditions;

-- Run the update function to initialize water edge costs
SELECT update_water_crossability();

-- Show the current environmental conditions
SELECT * FROM current_environment;

-- Show the effect on water edges
SELECT 
    MIN(cost) as min_cost,
    MAX(cost) as max_cost,
    AVG(cost) as avg_cost
FROM water_edges;
