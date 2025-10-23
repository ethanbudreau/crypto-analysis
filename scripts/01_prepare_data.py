#!/usr/bin/env python3
"""
Data Preparation Script
Downloads and preprocesses the Elliptic Bitcoin Transaction Dataset.

Creates subsets of 10K, 50K, 100K, and 200K nodes for scalability testing.
Converts data to formats compatible with both DuckDB and Sirius.

Usage:
    python scripts/01_prepare_data.py
"""

import os
import sys
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

    TODO: Implement preprocessing logic
    - Merge features with labels
    - Handle unknown labels
    - Create graph representation
    - Validate data integrity
    """
    print("\nPreprocessing data...")

    # Example preprocessing (to be implemented)
    # Rename first column to 'txId'
    features.rename(columns={0: 'txId'}, inplace=True)

    # Merge with classes
    data = features.merge(classes, left_on='txId', right_on='txId', how='left')

    print(f"✓ Merged features and labels: {len(data)} nodes")
    print(f"  - Illicit: {(data['class'] == '1').sum()}")
    print(f"  - Licit: {(data['class'] == '2').sum()}")
    print(f"  - Unknown: {data['class'].isna().sum()}")

    return data, edges


def create_subsets(data, edges, sizes=[10000, 50000, 100000, None]):
    """
    Create subsets of different sizes for scalability testing.

    Args:
        data: Node features and labels
        edges: Edge list
        sizes: List of subset sizes (None = full dataset)

    TODO: Implement subset creation
    - Sample nodes strategically (preserve illicit nodes)
    - Extract corresponding edges
    - Save to processed directory
    """
    print("\nCreating dataset subsets...")

    for size in sizes:
        if size is None:
            subset_name = "full"
            subset_data = data
            subset_edges = edges
        else:
            subset_name = f"{size//1000}k"
            # TODO: Implement smart sampling
            # For now, just take first N rows
            subset_data = data.head(size)
            node_ids = set(subset_data['txId'])
            subset_edges = edges[
                edges['txId1'].isin(node_ids) & edges['txId2'].isin(node_ids)
            ]

        print(f"\n{subset_name} dataset:")
        print(f"  - Nodes: {len(subset_data)}")
        print(f"  - Edges: {len(subset_edges)}")

        # Save subsets
        subset_data.to_csv(f"data/processed/nodes_{subset_name}.csv", index=False)
        subset_edges.to_csv(f"data/processed/edges_{subset_name}.csv", index=False)
        print(f"  ✓ Saved to data/processed/")


def convert_to_duckdb_format():
    """
    Convert processed data to DuckDB-optimized format.

    TODO: Implement DuckDB format conversion
    - Create Parquet files for efficient loading
    - Optimize column types
    - Create indices if needed
    """
    print("\nConverting to DuckDB format...")
    print("TODO: Implement Parquet conversion")


def convert_to_sirius_format():
    """
    Convert processed data to Sirius-compatible format.

    TODO: Implement Sirius format conversion
    - Research Sirius data loading requirements
    - Create appropriate format (Parquet, Arrow, etc.)
    """
    print("\nConverting to Sirius format...")
    print("TODO: Implement Sirius format conversion")


def main():
    """Main execution function."""
    print("="*50)
    print("ELLIPTIC DATASET PREPARATION")
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

    # Step 4: Preprocess
    data, edges = preprocess_data(features, classes, edges)

    # Step 5: Create subsets
    create_subsets(data, edges, sizes=[10000, 50000, 100000, None])

    # Step 6: Format conversions
    convert_to_duckdb_format()
    convert_to_sirius_format()

    print("\n" + "="*50)
    print("DATA PREPARATION COMPLETE")
    print("="*50)
    print("\nNext steps:")
    print("  - Review data in data/processed/")
    print("  - Run benchmarks: python scripts/02_run_benchmarks.py")


if __name__ == "__main__":
    main()
