# Deprecated Files

This directory contains files that have been deprecated in favor of newer, more comprehensive versions. These files are kept for reference but should not be used in production.

## Why These Files Were Deprecated

The project has evolved to use a unified approach for pipeline, export, and visualization operations. The files in this directory have been superseded by:

- `scripts/run_unified_pipeline.py` - Unified pipeline script that can run any of the three pipelines
- `tools/export_unified.py` - Unified export script that can export using any of the export methods
- `visualize_unified.py` - Unified visualization script that can visualize any of the visualization types

## Directory Structure

- `scripts/` - Deprecated script files
- `sql/` - Deprecated SQL files
- `tools/` - Deprecated tool files

## Recommended Workflow

For the most complete and feature-rich pipeline, we recommend using:

```bash
# Run the enhanced pipeline with the unified script
python scripts/run_pipeline_enhanced.py

# Export a slice with the enhanced export script
python tools/export_slice_enhanced_fixed.py --lon -93.63 --lat 41.99 --minutes 60 --outfile slice.graphml

# Visualize the exported graph with the unified visualization script
python visualize_unified.py --mode graphml --input slice.graphml
```

## Note

These files are kept in version control for reference and historical purposes. They may be removed in a future release.
