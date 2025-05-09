#!/usr/bin/env python3
"""
Wrapper script that redirects to the renamed pipeline in the pipelines directory.
This maintains backward compatibility with existing scripts or documentation.
"""

import os
import sys
from pathlib import Path

# Get the directory of this script
script_dir = Path(__file__).parent.resolve()

# Path to the actual pipeline script
pipeline_script = script_dir / "pipelines" / "run_renamed_boundary_hexagon_layer_pipeline.py"

# Execute the pipeline script with the same arguments
os.execv(sys.executable, [sys.executable, str(pipeline_script)] + sys.argv[1:])