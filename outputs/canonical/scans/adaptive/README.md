# Adaptive A-MLS parameter scan

[中文说明](README.zh-CN.md)

Canonical distances: 5,13,34 μm. Parameters: 1, 5, 10, 25, 50, 100, 150, 200; `parameter` is the k-worst elimination parameter for adaptive A-MLS; it is not a prescribed level count. Ties at the selected score are all eliminated, so the actual number removed can exceed k. Each configuration uses 20 batches × 32 independent estimates, with 250 initial replicas.

`experiments.csv` contains 480 rows of per-batch relative L2 error, squared error and wall time. `seeds.csv` contains 15360 independent estimate seeds; parameter and distance columns identify the configuration. Full-grid errors are dimensionless; wall times are seconds. The plotted S is mean wall time times mean relative L2 error. The final panel is the arithmetic mean of the three distance-specific S values.

The 95% bootstrap bands use 20,000 draws, independently resampling each adaptive-scan cell. Run `bash run_simulations.sh --study adaptive-scan` from the repository root.

This scan archive retains batch summaries and seeds only. Reruns additionally save per-batch curves, per-estimate records and hit times; see the [root README](../../../../README.md#recorded-data-and-rerun-format). To plot this scan together with its companion scan, use `python tools/plot_parameters.py --data-root outputs/rerun` after completing both. `tools/analyze.py` handles main comparisons only.
