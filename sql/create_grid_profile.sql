-- Create grid_profile table
CREATE TABLE IF NOT EXISTS grid_profile (
  name text PRIMARY KEY,
  cell_m integer  -- hexagon diameter in metres
);

-- Insert default profiles
INSERT INTO grid_profile VALUES
  ('coarse', 400),
  ('default', 200),
  ('fine', 100)
ON CONFLICT (name) DO NOTHING;
