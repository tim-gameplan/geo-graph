#!/usr/bin/env python3
"""
Visualize a GraphML file.

This script loads a GraphML file and creates a visualization of the graph.
"""

import os
import sys
import argparse
import logging
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
from utils.file_management import get_visualization_path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('output/logs/visualization.log')
    ]
)
logger = logging.getLogger('graph_visualization')

def visualize_graph(input_file, output_file=None, title=None, dpi=300, show_labels=False):
    """
    Visualize a GraphML file.
    
    Args:
        input_file: Path to the GraphML file
        output_file: Path to save the visualization (optional)
        title: Title for the visualization (optional)
        dpi: DPI for the output image (optional)
        show_labels: Whether to show node labels (optional)
    
    Returns:
        Path to the saved visualization
    """
    logger.info(f"Loading graph from {input_file}...")
    
    # Load the graph
    G = nx.read_graphml(input_file)
    
    logger.info(f"Graph loaded with {len(G.nodes)} nodes and {len(G.edges)} edges")
    
    # Create the figure
    plt.figure(figsize=(12, 10))
    
    # Set the title
    if title:
        plt.title(title)
    else:
        plt.title(f"Graph Visualization: {os.path.basename(input_file)}")
    
    # Get node positions from the graph
    pos = {}
    for node in G.nodes():
        if 'x' in G.nodes[node] and 'y' in G.nodes[node]:
            pos[node] = (float(G.nodes[node]['x']), float(G.nodes[node]['y']))
    
    # If no positions are available, use spring layout
    if not pos:
        logger.warning("No position attributes found in the graph. Using spring layout.")
        pos = nx.spring_layout(G)
    
    # Draw the graph
    nx.draw(
        G,
        pos=pos,
        with_labels=show_labels,
        node_size=50,
        node_color='skyblue',
        edge_color='gray',
        width=1.0,
        alpha=0.8
    )
    
    # Determine the output file path
    if output_file is None:
        # Generate a path using the file management utilities
        description = os.path.splitext(os.path.basename(input_file))[0]
        output_file = get_visualization_path(
            viz_type='graphml',
            description=description,
            parameters={'dpi': dpi}
        )
    
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Save the visualization
    plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
    logger.info(f"Visualization saved to {output_file}")
    
    return output_file

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Visualize a GraphML file")
    parser.add_argument("input", help="Path to the GraphML file")
    parser.add_argument("--output", help="Path to save the visualization")
    parser.add_argument("--title", help="Title for the visualization")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for the output image")
    parser.add_argument("--show-labels", action="store_true", help="Show node labels")
    
    args = parser.parse_args()
    
    try:
        output_file = visualize_graph(
            args.input,
            args.output,
            args.title,
            args.dpi,
            args.show_labels
        )
        
        print(f"Visualization saved to {output_file}")
        return 0
    
    except Exception as e:
        logger.error(f"Error visualizing graph: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
