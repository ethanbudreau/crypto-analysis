#!/usr/bin/env python3
"""
Dataset Inflation Script

Artificially inflate the Elliptic dataset to larger scales for GPU benchmarking.
Creates synthetic larger datasets by replicating and modifying the original data.

Usage:
    python scripts/inflate_dataset.py --target 1M
    python scripts/inflate_dataset.py --target 5M --output-suffix inflated_5m
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path


def load_original_data():
    """Load the full Elliptic dataset."""
    print("Loading original Elliptic dataset...")

    nodes = pd.read_csv('data/processed/nodes_full.csv')
    edges = pd.read_csv('data/processed/edges_full.csv')

    print(f"  Original nodes: {len(nodes):,}")
    print(f"  Original edges: {len(edges):,}")

    return nodes, edges


def inflate_dataset(nodes, edges, target_edges, method='replicate'):
    """
    Inflate dataset to target number of edges.

    Args:
        nodes: Original nodes DataFrame
        edges: Original edges DataFrame
        target_edges: Target number of edges (e.g., 1000000 for 1M)
        method: 'replicate' (copy and offset IDs) or 'permute' (shuffle connections)

    Returns:
        Inflated nodes and edges DataFrames
    """
    original_edge_count = len(edges)
    original_node_count = len(nodes)

    # Calculate how many copies we need
    replication_factor = int(np.ceil(target_edges / original_edge_count))

    print(f"\nInflating dataset:")
    print(f"  Target edges: {target_edges:,}")
    print(f"  Replication factor: {replication_factor}x")

    if method == 'replicate':
        # Replicate the graph multiple times with offset IDs
        inflated_nodes_list = []
        inflated_edges_list = []

        for i in range(replication_factor):
            # Offset node IDs
            node_offset = i * original_node_count

            # Copy nodes with offset IDs
            nodes_copy = nodes.copy()
            nodes_copy['txId'] = nodes_copy['txId'] + node_offset
            inflated_nodes_list.append(nodes_copy)

            # Copy edges with offset IDs
            edges_copy = edges.copy()
            edges_copy['txId1'] = edges_copy['txId1'] + node_offset
            edges_copy['txId2'] = edges_copy['txId2'] + node_offset
            inflated_edges_list.append(edges_copy)

            print(f"  Created copy {i+1}/{replication_factor}")

        # Combine all copies
        inflated_nodes = pd.concat(inflated_nodes_list, ignore_index=True)
        inflated_edges = pd.concat(inflated_edges_list, ignore_index=True)

        # Add some cross-replica edges to maintain connectivity (10% of edges)
        cross_edges = []
        num_cross_edges = min(int(target_edges * 0.1), original_edge_count)

        for _ in range(num_cross_edges):
            # Random edge between different replicas
            replica1 = np.random.randint(0, replication_factor)
            replica2 = np.random.randint(0, replication_factor)
            if replica1 != replica2:
                offset1 = replica1 * original_node_count
                offset2 = replica2 * original_node_count

                # Pick random nodes from each replica
                node1 = np.random.randint(0, original_node_count) + offset1
                node2 = np.random.randint(0, original_node_count) + offset2

                cross_edges.append({
                    'txId1': node1,
                    'txId2': node2
                })

        if cross_edges:
            cross_edges_df = pd.DataFrame(cross_edges)
            inflated_edges = pd.concat([inflated_edges, cross_edges_df], ignore_index=True)
            print(f"  Added {len(cross_edges):,} cross-replica edges")

    # Trim to exact target size
    if len(inflated_edges) > target_edges:
        inflated_edges = inflated_edges.sample(n=target_edges, random_state=42).reset_index(drop=True)

    print(f"\nInflated dataset:")
    print(f"  Final nodes: {len(inflated_nodes):,}")
    print(f"  Final edges: {len(inflated_edges):,}")
    print(f"  Inflation ratio: {len(inflated_edges)/original_edge_count:.1f}x")

    return inflated_nodes, inflated_edges


def save_inflated_data(nodes, edges, suffix):
    """Save inflated dataset to processed directory."""
    output_dir = Path('data/processed')
    output_dir.mkdir(exist_ok=True, parents=True)

    nodes_file = output_dir / f'nodes_{suffix}.csv'
    edges_file = output_dir / f'edges_{suffix}.csv'

    print(f"\nSaving inflated dataset...")
    nodes.to_csv(nodes_file, index=False)
    edges.to_csv(edges_file, index=False)

    # Show file sizes
    nodes_size_mb = nodes_file.stat().st_size / (1024 ** 2)
    edges_size_mb = edges_file.stat().st_size / (1024 ** 2)

    print(f"  Nodes: {nodes_file} ({nodes_size_mb:.1f} MB)")
    print(f"  Edges: {edges_file} ({edges_size_mb:.1f} MB)")
    print(f"✓ Saved inflated dataset as '{suffix}'")


def main():
    parser = argparse.ArgumentParser(description='Inflate Elliptic dataset for GPU benchmarking')
    parser.add_argument('--target', required=True,
                        help='Target edge count (e.g., 1M, 5M, 10M)')
    parser.add_argument('--output-suffix',
                        help='Output file suffix (default: based on target)')
    parser.add_argument('--method', choices=['replicate', 'permute'],
                        default='replicate',
                        help='Inflation method (default: replicate)')

    args = parser.parse_args()

    # Parse target size
    target_str = args.target.upper()
    if target_str.endswith('M'):
        target_edges = int(float(target_str[:-1]) * 1_000_000)
    elif target_str.endswith('K'):
        target_edges = int(float(target_str[:-1]) * 1_000)
    else:
        target_edges = int(target_str)

    # Default suffix based on target
    if args.output_suffix:
        suffix = args.output_suffix
    else:
        if target_edges >= 1_000_000:
            suffix = f"{target_edges // 1_000_000}m"
        else:
            suffix = f"{target_edges // 1_000}k"

    print("="*60)
    print("DATASET INFLATION")
    print("="*60)
    print(f"Target: {target_edges:,} edges")
    print(f"Output suffix: {suffix}")
    print(f"Method: {args.method}")
    print("="*60)

    # Load original data
    nodes, edges = load_original_data()

    # Check if target is reasonable
    if target_edges < len(edges):
        print(f"\n⚠ Warning: Target ({target_edges:,}) is smaller than original ({len(edges):,})")
        print("Use --sizes full for the original dataset instead.")
        return

    # Inflate dataset
    inflated_nodes, inflated_edges = inflate_dataset(
        nodes, edges, target_edges, method=args.method
    )

    # Save inflated data
    save_inflated_data(inflated_nodes, inflated_edges, suffix)

    print("\n" + "="*60)
    print("INFLATION COMPLETE")
    print("="*60)
    print("\nTo benchmark this dataset:")
    print(f"  python scripts/02_run_benchmarks.py --db both --sizes {suffix} --queries 1_hop")
    print("\nNote: This is synthetic data for performance testing only.")
    print("Results should be interpreted as computational benchmarks,")
    print("not as analysis of real Bitcoin transaction patterns.")


if __name__ == "__main__":
    main()
