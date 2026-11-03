# Single-experiment CDF dataset

[中文说明](README.zh-CN.md)

This dataset supplies the exact single experiment displayed in the paper's canonical CDF figure: 3 methods × 5 distances × 32 estimates = 480 estimate records.

- `experiments.csv`: 15 batch records, each with experiment ID 1.
- `seeds.csv`: 480 estimate seeds.
- `inner_estimates.csv.gz`: 480 per-estimate records.
- `curves/<method>/dXXR.csv.gz`: 15 files, each with 1,001 times, the analytical reference, batch mean, sample standard deviation, 95% pointwise confidence bounds, and 32 individual estimate curves.

CDF intervals are Wilson intervals over 32,000 independent MonC molecules or Student-t intervals over 32 independent A-MLS estimates. Empty A-MLS bounds represent undefined degenerate intervals. MonC uses experiment 1 of the main comparison; the A-MLS curves use the supplied CDF-specific seeds. Main performance statistics are stored in `../main/`.

Run `bash run_simulations.sh --study cdf` from the repository root. Time is in seconds; probabilities and relative errors are dimensionless.

The files above describe the supplied archive. CDF reruns save `runs/<method>/dXXR/p0/e01/curves.csv`, which the CDF plot also accepts. See the [root README](../../../README.md#recorded-data-and-rerun-format). After completing all five distances and three methods, run `python tools/plot_cdf.py --data-root outputs/rerun` from the repository root. `tools/analyze.py` handles main comparisons only.
