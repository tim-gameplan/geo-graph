#!/usr/bin/env python3
"""
Unified EPSG:3857 Pipeline Runner

This script runs the complete EPSG:3857 pipeline:
1. Reset the database
2. Run the water obstacle pipeline with EPSG:3857
3. Export a graph slice
4. Visualize the results
"""

import os
import sys
import argparse
from pathlib import Path

# Add the parent directory to the path so we can import from core packages
sys.path.append(str(Path(__file__).parent))

# Import our core script
from core.scripts.run_epsg3857_pipeline import main as core_main

if __name__ == "__main__":
    sys.exit(core_main())
