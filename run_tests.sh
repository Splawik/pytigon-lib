#!/bin/bash
set -euo pipefail

echo "=== pytigon-lib ptig @pytest ==="
ptig @pytest tests/ -m "$@"
echo
