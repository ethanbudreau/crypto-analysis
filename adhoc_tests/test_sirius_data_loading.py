#!/usr/bin/env python3
"""
Test that Sirius actually loads different dataset sizes correctly.
"""
import subprocess
import tempfile
import os

sirius_binary = os.path.expanduser("~/crypto-transaction-analysis/sirius/build/release/duckdb")

def test_dataset_loading(dataset_size):
    """Test that Sirius loads and counts the correct dataset."""
    script = f"""
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_{dataset_size}.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_{dataset_size}.csv');

.mode line
SELECT COUNT(*) as node_count FROM nodes;
SELECT COUNT(*) as edge_count FROM edges;
SELECT COUNT(*) as illicit_count FROM nodes WHERE class = '1';
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write(script)
        temp_file = f.name

    try:
        result = subprocess.run(
            [sirius_binary, "-init", temp_file],
            capture_output=True,
            text=True,
            timeout=60
        )

        print(f"\n{dataset_size} dataset:")
        print("-" * 60)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"Error: {result.stderr}")

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

print("="*60)
print("VERIFYING SIRIUS LOADS CORRECT DATASET SIZES")
print("="*60)

test_dataset_loading('5m')
test_dataset_loading('20m')

print("\n" + "="*60)
