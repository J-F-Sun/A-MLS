#!/usr/bin/env python3
"""Parameter sensitivity using S = mean wall time times mean relative L2 error."""
from __future__ import annotations

import argparse
import collections
import os
os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.environ.get("TMPDIR", "/tmp"), "mls-matplotlib"))
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, NullLocator
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs/canonical/scans"
DISTANCES = (5.0, 13.0, 34.0)
COLORS = {"uniform": "#0F4D92", "adaptive": "#3B8E6E"}


def statistics(adaptive: bool):
    path = DATA / ("adaptive" if adaptive else "uniform") / "experiments.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if adaptive:
        rows = [r for r in rows if r["algorithm"] == "ams_mod"]
    groups = collections.defaultdict(list)
    for row in rows:
        parameter = float(row["parameter"])
        distance = float(row["distance_R"])
        groups[parameter, distance].append(row)
    xs = sorted({p for p, _ in groups})
    expected = 20 if adaptive else 50
    assert len(groups) == 3 * len(xs)
    assert {len(rr) for rr in groups.values()} == {expected}
    rng = np.random.default_rng(2026102802 if adaptive else 2026102801)
    joint_indices = rng.integers(0, expected, (20000, expected))
    cells = {}
    for key, rr in sorted(groups.items()):
        rr.sort(key=lambda r: int(r["experiment"]))
        assert [int(r["experiment"]) for r in rr] == list(range(1, expected + 1))
        indices = rng.integers(0, expected, (20000, expected)) if adaptive else joint_indices
        # Convert each batch's squared relative L2 error before averaging.
        # Averaging first and taking the square root would instead give RMS error.
        arr = np.array([[float(r["wall_seconds"]), np.sqrt(float(r["relative_mse"]))]
                        for r in rr])
        assert np.isfinite(arr).all() and (arr > 0).all()
        means, boot = arr.mean(axis=0), arr[indices].mean(axis=1)
        cells[key] = (means[0] * means[1], boot[:, 0] * boot[:, 1])
    panels = []
    for distance in (*DISTANCES, None):
        ds = DISTANCES if distance is None else (distance,)
        values = np.array([np.mean([cells[x, d][0] for d in ds]) for x in xs])
        bounds = np.array([np.quantile(np.mean([cells[x, d][1] for d in ds], axis=0),
                                       [0.025, 0.975]) for x in xs])
        panels.append((values, bounds))
    return np.array(xs), panels


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-root", type=Path, default=ROOT / "outputs")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/reproduced/parameter_search_S.pdf")
    # Physical size is intended for an IEEE two-column figure.
    parser.add_argument("--width", type=float, default=7.16, help="PDF width in inches")
    parser.add_argument("--height", type=float, default=2.90, help="PDF height in inches")
    parser.add_argument("--tick-font", type=float, default=8.5)
    parser.add_argument("--label-font", type=float, default=9.0)
    parser.add_argument("--caption-font", type=float, default=9.5)
    parser.add_argument("--legend-font", type=float, default=7.2)
    parser.add_argument("--row-gap", type=float, default=0.44, help="Relative subplot row gap")
    parser.add_argument("--column-gap", type=float, default=0.42)
    parser.add_argument("--caption-y", type=float, default=0.025, help="Column caption y in figure coordinates")
    parser.add_argument("--ci-alpha", type=float, default=0.17)
    parser.add_argument("--minimum-size", type=float, default=6.2, help="Hollow minimum-point circle diameter in points")
    parser.add_argument("--minimum-font", type=float, default=8.0, help="Minimum S annotation font size")
    args = parser.parse_args()
    global DATA
    DATA = args.data_root / "canonical/scans"
    assert args.output.suffix.lower() == ".pdf", "Only PDF output is supported."

    plt.rcParams.update({
        "text.usetex": True,
        "text.latex.preamble": r"\usepackage{amsmath}",
        "pgf.texsystem": "pdflatex",
        "pgf.rcfonts": False,
        "pgf.preamble": r"\usepackage{amsmath}",
        "font.family": "serif",
        "font.serif": ["Computer Modern Roman"],
        "font.size": args.tick_font,
        "axes.labelsize": args.label_font,
        "xtick.labelsize": args.tick_font,
        "ytick.labelsize": args.tick_font,
        "axes.linewidth": 0.65,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "axes.unicode_minus": False,
    })
    scans = [statistics(False), statistics(True)]
    fig, axes = plt.subplots(2, 4, figsize=(args.width, args.height))
    fig.subplots_adjust(left=0.105, right=0.983, top=0.978, bottom=0.220,
                        wspace=args.column_gap, hspace=args.row_gap)
    for row, (xs, panels) in enumerate(scans):
        adaptive = row == 1
        color = COLORS["adaptive" if adaptive else "uniform"]
        marker = "^" if adaptive else "o"
        low = min(bounds[:, 0].min() for _, bounds in panels)
        high = max(bounds[:, 1].max() for _, bounds in panels)
        # Keep every interval visible, while fixing exactly the requested y ticks.
        ylim = (min(0.035, low / 1.07), max(0.60, high * 1.07)) if adaptive else (0.0008, max(1.65, high * 1.07))
        yticks = [0.05, 0.1, 0.5] if adaptive else [0.001, 0.01, 0.1, 1.0]
        ylabels = [r"$0.05$", r"$0.1$", r"$0.5$"] if adaptive else [
            r"$10^{-3}$", r"$10^{-2}$", r"$10^{-1}$", r"$10^{0}$"]
        # Log scales, numeric count labels, and all sampled values marked on the lines.
        xticks = [1, 5, 10, 50, 200] if adaptive else [2, 4, 8, 16, 32]
        for column, (values, bounds) in enumerate(panels):
            ax = axes[row, column]
            ax.fill_between(xs, bounds[:, 0], bounds[:, 1], color=color,
                            alpha=args.ci_alpha, linewidth=0, zorder=1)
            ax.plot(xs, values, color=color, marker=marker, markersize=3.1,
                    linewidth=1.1, markeredgewidth=0.4, zorder=2)
            best = int(np.argmin(values))
            ax.plot([xs[best]], [values[best]], marker="o", linestyle="none",
                    markersize=args.minimum_size, markerfacecolor="none",
                    markeredgecolor="black", markeredgewidth=0.8, zorder=5)
            # Keep endpoint labels inside their panel and leave the last legend clear.
            if best == 0:
                offset_x, align = 4, "left"
            elif best >= len(xs) - 2:
                offset_x, align = -2, "right"
            else:
                offset_x, align = 0, "center"
            below = adaptive and column == 2
            ax.annotate(rf"${values[best]:.3f}$", (xs[best], values[best]),
                        xytext=(offset_x, -8 if below else 8),
                        textcoords="offset points", ha=align,
                        va="top" if below else "bottom", color=color,
                        fontsize=args.minimum_font, zorder=6)
            ax.set_xscale("log", base=10 if adaptive else 2)
            ax.set_yscale("log")
            ax.set_ylim(*ylim)
            # Leave room for full hollow circles when a minimum is an endpoint.
            ax.set_xlim(xs[0] / 1.16, xs[-1] * 1.16)
            ax.xaxis.set_major_locator(FixedLocator(xticks))
            ax.set_xticklabels([rf"${x}$" for x in xticks])
            ax.yaxis.set_major_locator(FixedLocator(yticks))
            ax.set_yticklabels(ylabels)
            # A shared scale per row avoids repeating the long adaptive tick labels.
            if column > 0:
                ax.tick_params(axis="y", labelleft=False)
            ax.xaxis.set_minor_locator(NullLocator())
            ax.yaxis.set_minor_locator(NullLocator())
            ax.tick_params(axis="both", length=2.2, width=0.6, pad=2.0)
            ax.set_xlabel(r"$k$" if adaptive else r"$L+1$", labelpad=1.4)
            if column == 0:
                ax.set_ylabel(r"$S$", labelpad=1.5)
            ax.grid(axis="y", color="#999999", alpha=0.18, linewidth=0.45)
            assert ((bounds[:, 0] >= ylim[0]) & (bounds[:, 1] <= ylim[1])).all()

    handles = [Line2D([], [], color=COLORS["uniform"], marker="o", markersize=3.0,
                      linewidth=1.1, label="Uniform A-MLS"),
               Line2D([], [], color=COLORS["adaptive"], marker="^", markersize=3.0,
                      linewidth=1.1, label="Adaptive A-MLS")]
    axes[1, 3].legend(handles=handles, loc="lower left", fontsize=args.legend_font,
                      borderaxespad=0.10, handlelength=1.8, handletextpad=0.45,
                      labelspacing=0.25)
    labels = [rf"({chr(97+i)}) $d_{{\mathrm{{TR}}}}={int(d)}\,R$" for i, d in enumerate(DISTANCES)]
    labels.append(r"(d) three-distance mean")
    for column, label in enumerate(labels):
        box = axes[1, column].get_position()
        fig.text((box.x0 + box.x1) / 2, args.caption_y, label,
                 ha="center", va="bottom", fontsize=args.caption_font)
    # An explicit canvas preserves --width and --height exactly; nothing is auto-cropped.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    outside = []
    for ax in axes.flat:
        for txt in [*ax.get_xticklabels(), *ax.get_yticklabels(), ax.xaxis.label, ax.yaxis.label,
                    *ax.texts]:
            if not txt.get_text():
                continue
            box = txt.get_window_extent(renderer)
            if box.x0 < 0 or box.y0 < 0 or box.x1 > fig.bbox.width + 0.1 or box.y1 > fig.bbox.height + 0.1:
                outside.append((txt.get_text(), tuple(box.bounds)))
    assert not outside, f"Axis labels outside the PDF canvas: {outside}"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, format="pdf", backend="pgf", facecolor="white", metadata={
        "Title": "A-MLS parameter search using the time-error product S",
        "Subject": "S=mean wall time times mean batch relative L2 error; uniform 50 batches; adaptive 20 batches; 0.95 bootstrap confidence bands",
        "Creator": "plot_icc_parameter_search_combined.py; LaTeX Computer Modern fonts",
    })
    plt.close(fig)
    print(args.output)
    print(f"PDF size: {args.width:.2f} x {args.height:.2f} inches")
    for name, (_, panels) in zip(("Uniform", "Adaptive"), scans):
        print(name, "three-distance mean S:", panels[-1][0].tolist())
    for name, (xs, panels) in zip(("Uniform", "Adaptive"), scans):
        for distance, (values, _) in zip((*DISTANCES, "three-distance mean"), panels):
            best = int(np.argmin(values))
            print(f"{name}, {distance}: parameter={xs[best]:g}, min S={values[best]:.9f}")


if __name__ == "__main__":
    main()
