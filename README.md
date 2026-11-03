# Absorption-aware multilevel splitting (A-MLS)

[中文说明](README.zh-CN.md)

Simulation code and numerical datasets accompanying *Absorption-Aware Multilevel Splitting for Efficient Rare-Event Simulation in Molecular Communication*, submitted to IEEE ICC 2027.

A-MLS stands for **absorption-aware multilevel splitting**. Uniform distance-based partitioning and adaptive partitioning are its two level-selection strategies. The implementation compares direct Monte Carlo (MonC), uniform A-MLS, and adaptive A-MLS in the canonical channel and four extended geometries.

## Repository layout

```text
config/                 Physical parameters and five scene definitions
src/                    Julia simulation kernels and experiment runner
tools/                  Statistics and four paper figure scripts
outputs/
  canonical/            Main comparison, single-experiment CDF and parameter scans
  ob_complete/          Ext1: completely shadowing reflector
  ob_half/              Ext2: partially shadowing reflector
  rx2_competitive/      Ext3: competing absorber without shadowing
  rx2_half/             Ext4: partially shadowing competing absorber
  analysis/             Paper metrics and extended-scenario table
  figures/              The four numerical figure PDFs used in the manuscript
run_simulations.sh      Simulation entry point
reproduce_figures.sh    Statistics and figure entry point
```

Each scene has English and Chinese dataset documentation, indexed in [outputs/README.md](outputs/README.md). Physical parameters and geometry inputs are under `config/`; recorded seeds, simulation results and FEM reference curves are under `outputs/`.

## Environment

- Julia **1.11.8** is the recorded simulation version and is recommended for seed replay; the runner requires Julia 1.11 or newer. Simulations use Julia standard-library dependencies listed in `Project.toml`.
- Bash on Linux or macOS (or WSL on Windows).
- Python 3.11 or newer for statistics and figures. `requirements.txt` pins [NumPy 2.4.6](https://pypi.org/project/numpy/2.4.6/) and [Matplotlib 3.11.0](https://pypi.org/project/matplotlib/3.11.0/); statistics alone use the Python standard library.
- A TeX installation providing `latex`, `pdflatex`, `dvipng`, `amsmath` and Computer Modern fonts (including the packages needed by Matplotlib's [LaTeX text renderer](https://matplotlib.org/stable/users/explain/text/usetex.html)). Label measurements use the Agg backend with LaTeX; vector PDF export uses PGF with `pdflatex`.

From the repository root:

```bash
julia --project=. -e 'using Pkg; Pkg.instantiate()'
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The supplied FEM reference curves are ready to use. Running the particle simulations does not require a PDE solver or Python. FEM meshes, solver projects and reference-generation scripts are not included; this repository supports particle simulations and analysis against the supplied references, rather than regenerating the FEM solutions.

## Run simulations

```bash
# List the complete paper experiment plan without generating results.
bash run_simulations.sh --dry-run

# Run all paper experiments, including the CDF and parameter scans.
THREADS=32 JOBS=2 bash run_simulations.sh

# Run the 50-batch comparison only.
THREADS=32 JOBS=2 bash run_simulations.sh --study main

# Run the canonical comparison at one distance.
THREADS=32 JOBS=2 bash run_simulations.sh \
  --study main --scenes canonical --distances 34

# Run the two parameter scans separately.
bash run_simulations.sh --study uniform-scan
bash run_simulations.sh --study adaptive-scan

# Run the supplied single-experiment CDF seed configuration.
bash run_simulations.sh --study cdf
```

Use `JULIA_BIN=/path/to/julia` to select a Julia installation. `THREADS` controls threads per worker; `JOBS` controls the maximum simultaneous A-MLS workers. MonC uses one worker. Each batch averages 32 independently seeded estimates, independently of the number of threads. Defaults are 32 threads and two A-MLS workers.

Fresh results go to `outputs/rerun/`. Use `--output-root PATH` for another directory. Repeat the identical command to resume completed batches. A batch records its settings, seeds and numerical output; changing source code, configuration, Julia version, thread count or other run settings requires a new output directory.

The runner reads seeds and extended-scene reference curves from the supplied `outputs/` tree, including when a different output root is selected. Keep these input files in place. This entry point replays the supplied paper configurations; it does not generate new seed sets or reference curves for arbitrary geometries.

Seeds alone do not guarantee bitwise-identical results across Julia versions or implementation changes.

Additional selectors are `--methods monc,mls_lb,ams_mod`, `--scenes`, `--distances`, and `--parameters` for the scans. `--experiments` and `--repeats` select the first recorded experiments and repeats; `--steps` changes the time grid while retaining the 0.8 s horizon. Their defaults reproduce the paper protocol. The complete plan contains **138 cases, 5,445 batches and 174,240 estimator runs**.

## Recorded data and rerun format

The supplied archive uses `experiments.csv`, `seeds.csv`, `inner_estimates.csv.gz`, and compressed display curves. Parameter scans retain batch summaries and seeds. These formats are described in the [dataset index](outputs/README.md) and scene READMEs.

New simulations save each batch under `<output-root>/<scene>/<study>/runs/<method>/dXXR/p<parameter>/eXX/`, where `<study>` is `main`, `cdf`, `scans/uniform` or `scans/adaptive`. Each completed batch contains:

- `experiment.csv`: one batch summary with full-grid error and measured wall time.
- `curves.csv`: display-grid reference, mean, standard deviation, confidence bounds and individual estimate curves.
- `repeats.csv`: per-estimate seeds, errors, work counters and elapsed times.
- `taus.csv`: target-hit times, with one row per recorded hit in each estimate.
- `run.toml`: source/settings fingerprint and output-file checksums used when resuming.

After the selected jobs finish, the runner assembles `<scene>/<study>/experiments.csv`. It does not recreate the archive's combined `inner_estimates.csv.gz` or compressed main-curve files. The analysis and figure scripts accept the rerun format; the CDF plot reads its batch `curves.csv` directly. Temporary `.batch-*` directories left by a killed process are excluded from aggregation.

## Rebuild statistics and figures

```bash
# Recompute tables directly from the supplied paper data.
python tools/analyze.py

# Rebuild all four figures and their statistics from the supplied data.
PYTHON_BIN=python bash reproduce_figures.sh

# Rebuild them after a complete simulation rerun.
PYTHON_BIN=python bash reproduce_figures.sh outputs/rerun outputs/rerun/figures
```

The figure script writes to `outputs/reproduced/` by default. Its first optional argument is the input data root; the second is the output directory. Rebuilding all four figures requires all five main scenes at five distances and three methods, 50 main batches of 32 estimates, both complete parameter scans, and the canonical CDF experiment at all five distances. Reduced main simulations can be summarized with:

```bash
python tools/analyze.py --data-root outputs/rerun
```

`analyze.py` summarizes `main/experiments.csv` only; it does not summarize scan-only or CDF-only reruns. For example, plot a complete scan rerun with `python tools/plot_parameters.py --data-root outputs/rerun`, or a complete CDF rerun with `python tools/plot_cdf.py --data-root outputs/rerun`. These direct plotting commands use their default destinations under `outputs/reproduced/`; pass `--output PATH.pdf` to change the destination.

| Paper item | Data | Figure |
|---|---|---|
| Parameter sensitivity | `outputs/canonical/scans/` | `parameter_search_S.pdf` |
| Single-experiment CDF | `outputs/canonical/cdf/` | `01_canonical_CDF.pdf` |
| Canonical performance | `outputs/canonical/main/` | `02_canonical_metrics_2x2.pdf` |
| Extended performance table and gains | Four extended scene `main/` directories | `03_extended_gain_2x2.pdf` |

The plotting scripts retain the manuscript's axis ranges and annotations. New wall times or estimates can fall outside those ranges and trigger a plotting check; they may require axis or annotation changes before plotting a rerun.

## Experimental definitions

All scenes use `R=1 μm`, `D=79.4 μm²/s`, `Δt=4 μs`, 200,000 steps and `T=0.8 s`. Distances are 5, 8, 13, 21 and 34 μm. MonC uses 1,000 molecules per estimate; A-MLS uses 250 initial replicas. Main comparisons use **50 batches × 32 estimates** per method and distance, with 32 threshold points (`L=31`) for uniform A-MLS and `k=5` for adaptive A-MLS.

The uniform parameter scan uses **50 × 32** estimates per setting; the adaptive parameter scan uses **20 × 32**. Both scan the canonical channel at 5, 13 and 34 μm. The CDF figure uses one **32-estimate experiment** at each distance and method, with its own supplied seeds and pointwise confidence limits. Its curves must be read from `canonical/cdf/`.

For each batch, relative L2 error is computed from its mean estimated curve and the reference on the full **200,001-point** grid. Extended-scene references are linearly interpolated from the supplied FEM samples onto that grid. The paper uses the arithmetic mean of the 50 main batch errors, `S = mean(wall_seconds) × mean(relative_l2)`, and `G = 100 × (S_MonC / S_A-MLS − 1)`. Parameter-scan bands and canonical error, wall-time and S error bars use 95% percentile bootstrap intervals; the gain panels display point estimates. CDF intervals use pooled-molecule Wilson intervals for MonC and Student-t intervals across 32 estimates for A-MLS.

Stored display curves have 1,001 time points. The supplied full-grid error statistics are used directly in the tables; the plotting grid is for displaying curves. Saved hexadecimal seeds permit recomputation on the full grid. All CSV time values are seconds; probabilities and errors are dimensionless.

Recorded wall times were measured with Julia 1.11.8 on an Intel Xeon Gold 6430 using 32 threads per worker, with one MonC worker and two A-MLS workers. They measure the threaded estimator batch after warm-up. New timings depend on hardware, Julia version, concurrency and scheduling; use the supplied results to reconstruct the manuscript's timing-dependent tables and figures.

## Numerical implementation

All methods share Gaussian diffusion steps. Absorption is checked at step endpoints; reflecting spheres use straight-segment intersection and specular reflection of the remaining displacement. This is a finite-step approximation to the continuous diffusion model. The adaptive implementation removes all ties at the selected score, uses the actual surviving fraction, and replays parent RNG streams to recover branching checkpoints before generating independent continuations. Terminal target absorptions retain their original hit times.

Physical quantities in the Julia configuration and kernels use SI units (metres, seconds and m²/s). Scene distances, sphere radii and transverse offsets are specified in multiples of R. The legacy keys `obstacle_offset_x_R` and `competitor_offset_x_R` specify a fraction of the TX–RX distance d: `0.5` places the additional sphere at x=d/2. README distances and figure labels are expressed in micrometres.
