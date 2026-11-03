# Paper datasets

[中文说明](README.zh-CN.md)

The supplied archive contains five scene datasets, two canonical parameter scans, and the canonical single-experiment CDF data. Together they provide the inputs for rebuilding the manuscript's numerical comparisons.

| Dataset | Paper role | Documentation |
|---|---|---|
| `canonical/main/` | Canonical three-method comparison | [Canonical scene](canonical/README.md) |
| `canonical/cdf/` | Single-experiment CDF figure | [CDF dataset](canonical/cdf/README.md) |
| `canonical/scans/uniform/` | Uniform threshold-count scan | [Uniform scan](canonical/scans/uniform/README.md) |
| `canonical/scans/adaptive/` | Adaptive elimination-parameter scan | [Adaptive scan](canonical/scans/adaptive/README.md) |
| `ob_complete/main/` | Ext1: completely shadowing reflector | [Ext1](ob_complete/README.md) |
| `ob_half/main/` | Ext2: partially shadowing reflector | [Ext2](ob_half/README.md) |
| `rx2_competitive/main/` | Ext3: competing absorber without shadowing | [Ext3](rx2_competitive/README.md) |
| `rx2_half/main/` | Ext4: partially shadowing competing absorber | [Ext4](rx2_half/README.md) |

The four extended scenes each include five FEM reference CSVs under `reference/`, with columns `t,q` and 1,001 sample times. The simulator linearly interpolates these samples onto its error-evaluation grid. The canonical reference is evaluated analytically. FEM generation projects are not included.

## Shared archive fields

- `experiments.csv`: one row per batch. Main and CDF records include `scene`, `distance_R`, `algorithm`, `experiment`, `inner_repeats`, `relative_l2`, `relative_mse`, `wall_seconds`, endpoint probabilities and work counters. Scan records use `parameter` and retain a smaller set of batch fields.
- `seeds.csv`: one row per estimate, identified by method, distance, experiment and repeat; scans also include `parameter`. `seed_hex` is the hexadecimal RNG seed. Keep these files when replaying simulations into another output directory.
- `inner_estimates.csv.gz`: per-estimate records for the five main comparisons and CDF, including `P_hat`, `relative_mse`, work counters, completion status and `elapsed_seconds`. These files are not supplied for the scans.
- `curves/<method>/dXXR.csv.gz`: main files contain `t,q_ref,q_mean,outer_curve_sd,q_experiment_1,...,q_experiment_50`; CDF files contain `t,q_ref,q_mean,q_std,ci95_lower,ci95_upper,q_repeat_1,...,q_repeat_32`. Both use 1,001 display times. Main `outer_curve_sd` is a sample standard deviation across batch curves, not a confidence interval.

Method IDs are `monc` (MonC), `mls_lb` (uniform A-MLS), and `ams_mod` (adaptive A-MLS). `distance_R` is the TX-to-target-center distance divided by R. `experiment` identifies a batch, and `repeat` identifies an estimate within that batch. Here R=1 μm. `relative_mse` is the squared relative L2 error; it is dimensionless. Times are in seconds. Batch `wall_seconds` measures the threaded batch and is not the sum of individual `elapsed_seconds`.

## Derived manuscript outputs

- `analysis/outer_experiments.csv`: 3,750 main batch records across five scenes.
- `analysis/metrics.csv`: 75 method–scene–distance summaries, using mean relative L2 error, mean wall time, S and relative gain G.
- `analysis/extended_performance.tex`: the 20-configuration extended-scenario table in a standalone tabular layout; the manuscript adds its own table styling.
- `figures/`: the four numerical-result PDFs used in the manuscript.

`rerun/` and `reproduced/` are the default destinations for new simulations and reconstructed figures, respectively. Reruns save individual batch directories and combined `experiments.csv` files; they do not recreate the archive's packed layout. See the [root README](../README.md#recorded-data-and-rerun-format) for that format and the running commands.
