#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export OPENBLAS_NUM_THREADS=1
exec "${JULIA_BIN:-julia}" --startup-file=no --threads="${THREADS:-32}" --project="$ROOT" "$ROOT/src/simulate.jl" "$@"
