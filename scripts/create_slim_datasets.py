#!/usr/bin/env python3
"""
Create Slim Datasets - Keep Only Required Columns

Reduces dataset size by 98% by keeping only columns used in queries:
- nodes: txId, class (2 of 168 columns)
- edges: txId1, txId2 (all columns - already minimal)

Usage:
    python scripts/create_slim_datasets.py --input-suffix full --output-suffix full_slim
    python scripts/create_slim_datasets.py --input-suffix 5m --output-suffix 5m_slim
"""

import argparse
import pandas as pd
from pathlib import Path


def create_slim_dataset(input_suffix, output_suffix):
    """
    Create slim version of dataset with only required columns.

    Args:
        input_suffix: Input dataset suffix (e.g., 'full', '5m', '1m')
        output_suffix: Output dataset suffix (e.g., 'full_slim', '5m_slim')
    """
    print("=" * 60)
    print("SLIM DATASET CREATION")
    print("=" * 60)
    print(f"Input: {input_suffix}")
    print(f"Output: {output_suffix}")
    print("=" * 60)

    # Input files
    nodes_input = f"data/processed/nodes_{input_suffix}.csv"
    edges_input = f"data/processed/edges_{input_suffix}.csv"

    # Output files
    nodes_output = f"data/processed/nodes_{output_suffix}.csv"
    edges_output = f"data/processed/edges_{output_suffix}.csv"

    # Check input files exist
    if not Path(nodes_input).exists():
        print(f"✗ Error: {nodes_input} not found")
        return
    if not Path(edges_input).exists():
        print(f"✗ Error: {edges_input} not found")
        return

    # Process nodes - keep only txId and class
    print(f"\nProcessing nodes...")
    print(f"  Reading: {nodes_input}")

    # Get file size before
    nodes_size_before = Path(nodes_input).stat().st_size / (1024**2)
    print(f"  Size before: {nodes_size_before:.1f} MB")

    # Read and filter columns
    nodes = pd.read_csv(nodes_input, usecols=['txId', 'class'])
    print(f"  Rows: {len(nodes):,}")
    print(f"  Columns: {len(nodes.columns)} (reduced from 168)")

    # Save slim version
    nodes.to_csv(nodes_output, index=False)
    nodes_size_after = Path(nodes_output).stat().st_size / (1024**2)
    print(f"  Size after: {nodes_size_after:.1f} MB")
    print(f"  Reduction: {(1 - nodes_size_after/nodes_size_before)*100:.1f}%")
    print(f"  ✓ Saved: {nodes_output}")

    # Process edges - copy as-is (already minimal)
    print(f"\nProcessing edges...")
    print(f"  Reading: {edges_input}")

    edges_size = Path(edges_input).stat().st_size / (1024**2)
    print(f"  Size: {edges_size:.1f} MB")

    edges = pd.read_csv(edges_input)
    print(f"  Rows: {len(edges):,}")
    print(f"  Columns: {len(edges.columns)}")

    # Save (same as input, but for consistency)
    edges.to_csv(edges_output, index=False)
    print(f"  ✓ Saved: {edges_output}")

    # Summary
    total_size_before = nodes_size_before + edges_size
    total_size_after = nodes_size_after + edges_size

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print("=" * 60)
    print(f"Total size before: {total_size_before:.1f} MB")
    print(f"Total size after:  {total_size_after:.1f} MB")
    print(f"Reduction:         {(1 - total_size_after/total_size_before)*100:.1f}%")
    print(f"Space saved:       {total_size_before - total_size_after:.1f} MB")
    print()
    print(f"✓ Slim dataset created: {output_suffix}")
    print()
    print("To benchmark this dataset:")
    print(f"  python scripts/02_run_benchmarks.py --db both --sizes {output_suffix} --queries 1_hop")


def main():
    parser = argparse.ArgumentParser(description='Create slim datasets with only required columns')
    parser.add_argument('--input-suffix', required=True,
                        help='Input dataset suffix (e.g., full, 5m, 1m)')
    parser.add_argument('--output-suffix', required=True,
                        help='Output dataset suffix (e.g., full_slim, 5m_slim)')

    args = parser.parse_args()

    create_slim_dataset(args.input_suffix, args.output_suffix)


if __name__ == "__main__":
    main()
