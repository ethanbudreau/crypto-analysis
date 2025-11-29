#!/usr/bin/env python3
"""
Data Preparation Script
Downloads and preprocesses the Elliptic Bitcoin Transaction Dataset.

Creates slim datasets (100K, 1M, 5M, 20M edges) optimized for benchmarking.
Only keeps required columns: nodes (txId, class), edges (txId1, txId2).

Usage:
    python scripts/01_prepare_data.py
"""

import os
import sys
import shutil
import zipfile
import pandas as pd
import numpy as np
from pathlib import Path


def setup_directories():
    """Create necessary data directories."""
    print("Creating data directories...")
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    print("✓ Directories created")


def check_for_zip():
    """Check if the downloaded ZIP file exists and extract it."""
    zip_path = "data/raw/elliptic-data-set.zip"

    if os.path.exists(zip_path):
        print(f"\n✓ Found ZIP file: {zip_path}")
        print("Extracting files...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall("data/raw/")
            print("✓ Files extracted successfully!")

            # Move files from subdirectory if needed
            subdir = "data/raw/elliptic_bitcoin_dataset"
            if os.path.exists(subdir):
                print("Moving files from subdirectory...")
                for filename in os.listdir(subdir):
                    src = os.path.join(subdir, filename)
                    dst = os.path.join("data/raw", filename)
                    if os.path.isfile(src):
                        shutil.move(src, dst)
                        print(f"  ✓ Moved {filename}")
                # Remove empty subdirectory
                os.rmdir(subdir)
                print("✓ Files organized!")

            return True
        except Exception as e:
            print(f"✗ Error extracting ZIP: {e}")
            return False
    return False


def download_dataset():
    """
    Check for and prepare the Elliptic Bitcoin Transaction Dataset.

    The dataset must be manually downloaded from Kaggle.
    """
    print("\n" + "="*50)
    print("DATASET DOWNLOAD")
    print("="*50)

    # Required CSV files
    required_files = [
        "data/raw/elliptic_txs_features.csv",
        "data/raw/elliptic_txs_classes.csv",
        "data/raw/elliptic_txs_edgelist.csv"
    ]

    # Check if CSV files already exist
    all_exist = all(os.path.exists(f) for f in required_files)

    if all_exist:
        print("\n✓ Dataset files already exist!")
        print("\nFound files:")
        for f in required_files:
            print(f"  ✓ {f}")
        return True

    # Check for ZIP file and extract if present
    if check_for_zip():
        # Check again if extraction was successful
        if all(os.path.exists(f) for f in required_files):
            print("\n✓ All required files ready!")
            return True

    # Dataset not found - provide download instructions
    print("\n" + "-"*50)
    print("DATASET NOT FOUND - MANUAL DOWNLOAD REQUIRED")
    print("-"*50)
    print("\nPlease follow these steps:")
    print("\n1. Create a Kaggle account (free):")
    print("   https://www.kaggle.com/account/login")
    print("\n2. Download the Elliptic dataset:")
    print("   https://www.kaggle.com/datasets/ellipticco/elliptic-data-set")
    print("   Click the 'Download' button (top right)")
    print("\n3. Move the ZIP file to this directory:")
    print("   mv ~/Downloads/archive.zip data/raw/elliptic-data-set.zip")
    print("   (The downloaded file might be named 'archive.zip')")
    print("\n4. Run this script again:")
    print("   python scripts/01_prepare_data.py")
    print("\nThe script will automatically extract the ZIP file.")

    print("\n" + "-"*50)
    print("Expected files after extraction:")
    for f in required_files:
        print(f"  - {f}")

    print("\n" + "-"*50)
    return False


def load_raw_data():
    """Load the raw Elliptic dataset files."""
    print("\nLoading raw dataset...")

    # Load node features
    features = pd.read_csv("data/raw/elliptic_txs_features.csv", header=None)
    print(f"✓ Loaded {len(features)} transaction features")

    # Load node labels (illicit/licit/unknown)
    classes = pd.read_csv("data/raw/elliptic_txs_classes.csv")
    print(f"✓ Loaded {len(classes)} transaction labels")

    # Load edges
    edges = pd.read_csv("data/raw/elliptic_txs_edgelist.csv")
    print(f"✓ Loaded {len(edges)} edges")

    return features, classes, edges


def preprocess_data(features, classes, edges):
    """
    Clean and preprocess the dataset.
    Keep only required columns for slim format.
    """
    print("\nPreprocessing data...")

    # Rename first column to 'txId'
    features.rename(columns={0: 'txId'}, inplace=True)

    # Merge with classes - keep only txId and class
    data = features[['txId']].merge(classes, left_on='txId', right_on='txId', how='left')

    print(f"✓ Merged features and labels: {len(data)} nodes")
    print(f"  - Illicit: {(data['class'] == '1').sum()}")
    print(f"  - Licit: {(data['class'] == '2').sum()}")
    print(f"  - Unknown: {data['class'].isna().sum()}")

    # Convert class labels to readable format
    data['class'] = data['class'].replace({'1': 'illicit', '2': 'licit'})
    data['class'] = data['class'].fillna('unknown')

    return data, edges


def create_base_subset(nodes, edges, target_edges=100000):
    """
    Create base 100k subset for further inflation.

    Args:
        nodes: Node features and labels
        edges: Edge list
        target_edges: Target number of edges (default: 100k)

    Returns:
        Subset of nodes and edges
    """
    print(f"\nCreating base subset ({target_edges:,} edges)...")

    # Sample edges
    if len(edges) > target_edges:
        subset_edges = edges.sample(n=target_edges, random_state=42).reset_index(drop=True)
    else:
        subset_edges = edges

    # Get unique node IDs from sampled edges
    node_ids = set(subset_edges['txId1']).union(set(subset_edges['txId2']))

    # Filter nodes
    subset_nodes = nodes[nodes['txId'].isin(node_ids)].reset_index(drop=True)

    print(f"  ✓ Nodes: {len(subset_nodes):,}")
    print(f"  ✓ Edges: {len(subset_edges):,}")

    return subset_nodes, subset_edges


def inflate_dataset(nodes, edges, target_edges, suffix):
    """
    Inflate dataset to target number of edges.

    Args:
        nodes: Original nodes DataFrame (txId, class)
        edges: Original edges DataFrame (txId1, txId2)
        target_edges: Target number of edges
        suffix: Output file suffix
    """
    original_edge_count = len(edges)
    original_node_count = len(nodes)

    # Calculate replication factor
    replication_factor = int(np.ceil(target_edges / original_edge_count))

    print(f"\nInflating to {target_edges:,} edges ({suffix}):")
    print(f"  Replication factor: {replication_factor}x")

    # Replicate the graph multiple times with offset IDs
    inflated_nodes_list = []
    inflated_edges_list = []

    for i in range(replication_factor):
        # Offset node IDs
        node_offset = i * original_node_count * 10  # Large offset to avoid collisions

        # Copy nodes with offset IDs
        nodes_copy = nodes.copy()
        nodes_copy['txId'] = nodes_copy['txId'] + node_offset
        inflated_nodes_list.append(nodes_copy)

        # Copy edges with offset IDs
        edges_copy = edges.copy()
        edges_copy['txId1'] = edges_copy['txId1'] + node_offset
        edges_copy['txId2'] = edges_copy['txId2'] + node_offset
        inflated_edges_list.append(edges_copy)

        if (i + 1) % 10 == 0 or i + 1 == replication_factor:
            print(f"  Created copy {i+1}/{replication_factor}")

    # Combine all copies
    print("  Concatenating copies...")
    inflated_nodes = pd.concat(inflated_nodes_list, ignore_index=True)
    inflated_edges = pd.concat(inflated_edges_list, ignore_index=True)

    # Add cross-replica edges (10% of target)
    print("  Adding cross-replica edges...")
    num_cross_edges = min(int(target_edges * 0.1), original_edge_count)
    cross_edges = []

    np.random.seed(42)
    for _ in range(num_cross_edges):
        # Random edge between different replicas
        replica1 = np.random.randint(0, replication_factor)
        replica2 = np.random.randint(0, replication_factor)
        if replica1 != replica2:
            offset1 = replica1 * original_node_count * 10
            offset2 = replica2 * original_node_count * 10

            # Pick random nodes from each replica
            node1 = nodes['txId'].iloc[np.random.randint(0, original_node_count)] + offset1
            node2 = nodes['txId'].iloc[np.random.randint(0, original_node_count)] + offset2

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
        print("  Trimming to target size...")
        inflated_edges = inflated_edges.sample(n=target_edges, random_state=42).reset_index(drop=True)

    print(f"  ✓ Final: {len(inflated_nodes):,} nodes, {len(inflated_edges):,} edges")

    return inflated_nodes, inflated_edges


def save_dataset(nodes, edges, suffix):
    """Save dataset to CSV files."""
    nodes_file = f"data/processed/nodes_{suffix}.csv"
    edges_file = f"data/processed/edges_{suffix}.csv"

    nodes.to_csv(nodes_file, index=False)
    edges.to_csv(edges_file, index=False)

    # Show file sizes
    nodes_size_mb = Path(nodes_file).stat().st_size / (1024 ** 2)
    edges_size_mb = Path(edges_file).stat().st_size / (1024 ** 2)

    print(f"  ✓ Saved: {suffix} ({nodes_size_mb + edges_size_mb:.1f} MB)")


def main():
    """Main execution function."""
    print("="*50)
    print("ELLIPTIC DATASET PREPARATION (SLIM)")
    print("="*50)
    print("\nCreates optimized datasets with only required columns:")
    print("  - Nodes: txId, class")
    print("  - Edges: txId1, txId2")
    print("\nDataset sizes: 100k, 1M, 5M, 20M edges")
    print("="*50)

    # Step 1: Setup
    setup_directories()

    # Step 2: Download
    if not download_dataset():
        print("\nExiting: Dataset not available.")
        print("Please download the dataset and run again.")
        sys.exit(1)

    # Step 3: Load
    features, classes, edges = load_raw_data()

    # Step 4: Preprocess (keep only required columns)
    nodes, edges = preprocess_data(features, classes, edges)

    # Step 5: Create base 100k subset
    base_nodes, base_edges = create_base_subset(nodes, edges, target_edges=100000)
    save_dataset(base_nodes, base_edges, "100k")

    # Step 6: Inflate to larger sizes
    for target_edges, suffix in [
        (1_000_000, "1m"),
        (5_000_000, "5m"),
        (20_000_000, "20m"),
    ]:
        inflated_nodes, inflated_edges = inflate_dataset(
            base_nodes, base_edges, target_edges, suffix
        )
        save_dataset(inflated_nodes, inflated_edges, suffix)

    print("\n" + "="*50)
    print("DATA PREPARATION COMPLETE")
    print("="*50)
    print("\nCreated datasets:")
    print("  - 100k:  100,000 edges (base)")
    print("  - 1m:  1,000,000 edges")
    print("  - 5m:  5,000,000 edges")
    print("  - 20m: 20,000,000 edges")
    print("\nNext steps:")
    print("  - Review data in data/processed/")
    print("  - Run benchmarks:")
    print("    python scripts/run_persistent_session_benchmarks.py")


if __name__ == "__main__":
    main()
