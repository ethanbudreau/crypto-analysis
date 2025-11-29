#!/usr/bin/env python3
"""
Verify that Sirius returns the correct number of results for each dataset.
"""
import subprocess
import tempfile
import os

sirius_binary = os.path.expanduser("~/crypto-transaction-analysis/sirius/build/release/duckdb")

expected_counts = {
    '100k': 1082,
    '1m': 15538,
    '5m': 95014,
    '20m': 482672
}

def verify_sirius_results(dataset_size, expected_count):
    """Run k_hop query in Sirius and verify result count."""

    # Load query
    with open('sql/sirius/k_hop_gpu.sql', 'r') as f:
        lines = [line for line in f.readlines() if not line.strip().startswith('--')]
        query = ''.join(lines).strip().rstrip(';')
        escaped_query = query.replace("'", "''")

    # Determine buffer size
    buffer_configs = {
        '100k': ('1 GB', '2 GB'),
        '1m': ('2 GB', '4 GB'),
        '5m': ('4 GB', '8 GB'),
        '20m': ('6 GB', '8 GB')
    }
    buffer_min, buffer_max = buffer_configs[dataset_size]

    script = f"""
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('data/processed/nodes_{dataset_size}.csv');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('data/processed/edges_{dataset_size}.csv');
call gpu_buffer_init('{buffer_min}', '{buffer_max}');

-- Count results from k_hop query
call gpu_processing('
    SELECT COUNT(*) as result_count FROM (
        {escaped_query}
    )
');
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write(script)
        temp_file = f.name

    try:
        result = subprocess.run(
            [sirius_binary, "-init", temp_file],
            capture_output=True,
            text=True,
            timeout=120
        )

        print(f"\n{dataset_size}:")
        print("-"*70)

        if result.returncode == 0:
            # Extract count from output
            count = None
            for line in result.stdout.split('\n'):
                # Look for the count value
                if '│' in line and line.strip().replace('│', '').strip().isdigit():
                    count = int(line.strip().replace('│', '').strip())
                    break

            if count is not None:
                status = "✅" if count == expected_count else "❌"
                print(f"  Expected: {expected_count:,}")
                print(f"  Got:      {count:,}")
                print(f"  Status:   {status}")

                if count != expected_count:
                    diff = count - expected_count
                    pct = (diff / expected_count * 100) if expected_count > 0 else 0
                    print(f"  Diff:     {diff:+,} ({pct:+.1f}%)")
            else:
                print(f"  ⚠️  Could not extract count from output")
                print(f"  Output: {result.stdout[-200:]}")
        else:
            print(f"  ❌ Query failed")
            print(f"  Error: {result.stderr[:300]}")

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

print("="*70)
print("VERIFYING SIRIUS RETURNS CORRECT RESULT COUNTS")
print("="*70)

for dataset_size in ['100k', '1m', '5m', '20m']:
    verify_sirius_results(dataset_size, expected_counts[dataset_size])

print("\n" + "="*70)
