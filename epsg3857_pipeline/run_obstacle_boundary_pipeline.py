#!/usr/bin/env python3
"""
Obstacle Boundary Pipeline Runner

This script runs the complete pipeline to generate a terrain graph with water obstacles
using the direct water boundary conversion approach.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from core packages
sys.path.append(str(Path(__file__).parent))

# Import our core script
from core.obstacle_boundary.run_obstacle_boundary_pipeline import main as core_main

if __name__ == "__main__":
    sys.exit(core_main())
