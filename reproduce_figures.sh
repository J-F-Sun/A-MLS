#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -gt 2 ]]; then
    echo "Usage: bash reproduce_figures.sh [DATA_ROOT] [OUTPUT_DIR]" >&2
    exit 2
fi
DATA_ROOT="${1:-$ROOT/outputs}"
OUTPUT_DIR="${2:-$ROOT/outputs/reproduced}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONDONTWRITEBYTECODE=1
export MPLCONFIGDIR="${MPLCONFIGDIR:-${TMPDIR:-/tmp}/mls-matplotlib}"
command -v pdflatex >/dev/null || { echo "pdflatex is required for the paper figure fonts." >&2; exit 1; }
"$PYTHON_BIN" "$ROOT/tools/analyze.py" --data-root "$DATA_ROOT" --output-root "$OUTPUT_DIR/statistics"
"$PYTHON_BIN" "$ROOT/tools/plot_parameters.py" --data-root "$DATA_ROOT" --output "$OUTPUT_DIR/parameter_search_S.pdf"
"$PYTHON_BIN" "$ROOT/tools/plot_cdf.py" --data-root "$DATA_ROOT" --output "$OUTPUT_DIR/01_canonical_CDF.pdf"
"$PYTHON_BIN" "$ROOT/tools/plot_canonical_metrics.py" --source "$OUTPUT_DIR/statistics/outer_experiments.csv" --output "$OUTPUT_DIR/02_canonical_metrics_2x2.pdf"
"$PYTHON_BIN" "$ROOT/tools/plot_extended_gain.py" --source "$OUTPUT_DIR/statistics/outer_experiments.csv" --output "$OUTPUT_DIR/03_extended_gain_2x2.pdf"
