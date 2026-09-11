#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 -m py_compile "$project_dir/scripts/server.py"
python3 -m unittest discover -s "$project_dir/tests" -p 'test_*.py'

echo "Validation passed."
