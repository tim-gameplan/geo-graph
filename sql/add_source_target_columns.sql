-- Add source and target columns to road_edges
ALTER TABLE road_edges ADD COLUMN source bigint;
ALTER TABLE road_edges ADD COLUMN target bigint;

-- Add source and target columns to water_edges (if they don't already exist)
ALTER TABLE water_edges ADD COLUMN source bigint;
ALTER TABLE water_edges ADD COLUMN target bigint;

-- Add source and target columns to terrain_edges (if they don't already exist)
ALTER TABLE terrain_edges ADD COLUMN source bigint;
ALTER TABLE terrain_edges ADD COLUMN target bigint;
