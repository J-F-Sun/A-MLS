# Canonical point-to-sphere channel

[中文说明](README.zh-CN.md)

One absorbing sphere at the origin. TX=(d,0,0); target RX=(0,0,0); all sphere radii are R=1 μm. Distances are 5,8,13,21,34 μm; D=79.4 μm²/s; Δt=4 μs; T=0.8 s.

## Dataset

- `main/experiments.csv`: 750 rows = 3 methods × 5 distances × 50 independent batches. Each batch averages 32 estimates.
- `main/seeds.csv`: 24,000 rows, one hexadecimal RNG seed per independent estimate.
- `main/inner_estimates.csv.gz`: 24,000 per-estimate records with probabilities, errors, work counters and elapsed times.
- `main/curves/<method>/dXXR.csv.gz`: 15 curve files, each containing the reference, the mean curve and all 50 batch mean curves at 1,001 times.

- `cdf/`: the single 32-estimate experiment used in the CDF figure.
- `scans/uniform/`: threshold counts 2,4,6,8,12,16,24,32; three distances; 50 batches each.
- `scans/adaptive/`: k=1,5,10,25,50,100,150,200; three distances; 20 batches each.

The canonical reference is analytical: p(t) = (R/d) erfc((d−R)/sqrt(4Dt)).

Methods `monc`, `mls_lb`, `ams_mod` mean MonC, uniform A-MLS (32 threshold points) and adaptive A-MLS (k=5). Main error values are computed on the full 200,001-point grid; use the stored errors for statistics. Time and wall time are seconds. Probabilities, `relative_l2` and `relative_mse` are dimensionless; `relative_mse = relative_l2²`. S is mean wall time multiplied by mean relative L2 error.

Run from the repository root:

```bash
bash run_simulations.sh --study main --scenes canonical
```

This section describes the supplied archive. New simulations use the batch-directory format described in the [root README](../../README.md#recorded-data-and-rerun-format). Field definitions are in the [dataset index](../README.md#shared-archive-fields).
