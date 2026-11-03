# Uniform A-MLS parameter scan

[中文说明](README.zh-CN.md)

Canonical distances: 5,13,34 μm. Parameters: 2, 4, 6, 8, 12, 16, 24, 32; `parameter` is the threshold-point count L+1 for uniform A-MLS (there are L transitions). Each configuration uses 50 batches × 32 independent estimates, with 250 initial replicas.

`experiments.csv` contains 1200 rows of per-batch relative L2 error, squared error and wall time. `seeds.csv` contains 38400 independent estimate seeds; parameter and distance columns identify the configuration. Full-grid errors are dimensionless; wall times are seconds. The plotted S is mean wall time times mean relative L2 error. The final panel is the arithmetic mean of the three distance-specific S values.

The 95% bootstrap bands use 20,000 draws, jointly resampling batch indices across uniform-scan cells. Run `bash run_simulations.sh --study uniform-scan` from the repository root.

This scan archive retains batch summaries and seeds only. Reruns additionally save per-batch curves, per-estimate records and hit times; see the [root README](../../../../README.md#recorded-data-and-rerun-format). To plot this scan together with its companion scan, use `python tools/plot_parameters.py --data-root outputs/rerun` after completing both. `tools/analyze.py` handles main comparisons only.
