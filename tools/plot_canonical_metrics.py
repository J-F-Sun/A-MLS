#!/usr/bin/env python3
"""Canonical cost, error and gain figure from independent batch statistics."""
from __future__ import annotations

import argparse
import csv
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(Path(os.environ.get("TMPDIR", "/tmp")) / "mls-matplotlib"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import LogFormatterMathtext, NullLocator, StrMethodFormatter
import numpy as np

DISTANCES = (5, 8, 13, 21, 34)
RADIUS_UM = 1.0
METHODS = ("monc", "mls_lb", "ams_mod")
COLORS = {"monc": "#B64342", "mls_lb": "#0F4D92", "ams_mod": "#3B8E6E"}
STYLES = {"monc": "-", "mls_lb": "--", "ams_mod": "-."}
MARKERS = {"monc": "o", "mls_lb": "s", "ams_mod": "^"}
LABELS = {"monc": "MonC", "mls_lb": "uni. A-MLS", "ams_mod": "adap. A-MLS"}
PANEL_KEYS = ("error_percent", "wall_seconds", "S_seconds", "G_percent")
YLABELS = (r"$\varepsilon_{\mathrm{rel}}$ (\%)", r"$\bar{W}$ (s)", r"$S$ (s)", r"$G$ (\%)")
CAPTIONS = (r"(a) Relative $L_2$ error", "(b) Wall-clock time", "(c) Primary metric", "(d) Relative gain")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def summarize(source, bootstrap, seed):
    with source.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    points, distributions = {}, {}
    for distance in DISTANCES:
        for method_index, method in enumerate(METHODS):
            batch_rows = sorted((r for r in rows if r["scene"] == "canonical"
                                 and float(r["distance_R"]) == distance and r["algorithm"] == method),
                                key=lambda r: int(r["experiment"]))
            require(len(batch_rows) == 50, f"Expected 50 batches: {distance}R {method}")
            require([int(r["experiment"]) for r in batch_rows] == list(range(1, 51)), "Batch IDs differ")
            require(all(int(r["inner_repeats"]) == 32 and r["accepted_run"].lower() == "true"
                        and int(r["iteration_caps"]) == 0 for r in batch_rows), "Invalid experiment status")
            error = np.array([float(r["relative_l2"]) for r in batch_rows])
            wall = np.array([float(r["wall_seconds"]) for r in batch_rows])
            require(np.isfinite([error, wall]).all() and np.all(error >= 0) and np.all(wall > 0), "Invalid metrics")
            require(all(math.isclose(float(r["relative_l2"])**2, float(r["relative_mse"]), rel_tol=1e-12)
                        for r in batch_rows), "Stored errors do not match")
            mean_error = math.fsum(error) / 50
            mean_wall = math.fsum(wall) / 50
            point = {"error_percent": mean_error * 100, "wall_seconds": mean_wall,
                     "S_seconds": mean_error * mean_wall}
            rng = np.random.default_rng(np.random.SeedSequence([seed, distance, method_index]))
            indices = rng.integers(0, 50, size=(bootstrap, 50))
            boot_error = error[indices].mean(axis=1)
            boot_wall = wall[indices].mean(axis=1)
            draws = {"error_percent": boot_error * 100, "wall_seconds": boot_wall,
                     "S_seconds": boot_error * boot_wall}
            points[distance, method] = point
            distributions[distance, method] = draws
        for method in METHODS:
            point = points[distance, method]
            draws = distributions[distance, method]
            point["G_percent"] = 100 * (points[distance, "monc"]["S_seconds"] / point["S_seconds"] - 1)
            draws["G_percent"] = 100 * (distributions[distance, "monc"]["S_seconds"] / draws["S_seconds"] - 1)
    intervals = {key: {metric: np.quantile(draws[metric], [0.025, 0.975]) for metric in PANEL_KEYS}
                 for key, draws in distributions.items()}
    return points, intervals


def configure_metric_axis(ax, metric, lows, highs):
    """Use the requested fixed ranges, retaining zero in the gain panel."""
    if metric == "error_percent":
        ax.set_yscale("log", base=10)
        ax.set_ylim(1, 100)
        ax.set_yticks([1, 10, 100])
        ax.yaxis.set_major_formatter(LogFormatterMathtext(base=10))
    elif metric == "wall_seconds":
        ax.set_yscale("linear")
        ax.set_ylim(1.5, 4.5)
        ax.set_yticks([1.5, 2.5, 3.5, 4.5])
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:g}"))
    elif metric == "S_seconds":
        ax.set_yscale("log", base=10)
        ax.set_ylim(1e-2, 2)
        ax.set_yticks([1e-2, 1e-1, 1])
        ax.yaxis.set_major_formatter(LogFormatterMathtext(base=10))
    else:
        # A short linear segment around zero preserves the MonC baseline.
        ax.set_yscale("symlog", base=10, linthresh=1, linscale=0.35)
        ax.set_ylim(0, 1200)
        ax.set_yticks([0, 10, 100, 1000])
        ax.yaxis.set_major_formatter(LogFormatterMathtext(base=10))
    ax.yaxis.set_minor_locator(NullLocator())
    lower, upper = ax.get_ylim()
    require(min(lows) >= lower and max(highs) <= upper, f"Data outside axis range: {metric}")


def annotate_gains(ax, points, font_size):
    """Stack gain labels below green markers at 5, 21 and 34 micrometres."""
    annotations = []
    below_offsets = {5: (-4.3, -10.0), 21: (-8.0, -14.3), 34: (-15.0, -21.3)}
    for distance in DISTANCES:
        x = distance * RADIUS_UM
        anchor_method = "ams_mod" if distance in below_offsets else "mls_lb"
        y = points[distance, anchor_method]["G_percent"]
        # Keep edge labels inside the canvas and centre the other groups.
        dx, align = {5: (-4.5, "left"), 8: (-3.5, "center"), 34: (0, "right")}.get(distance, (0, "center"))
        lower_offset = {8: 8.5, 13: 8.5}.get(distance, font_size)
        if distance in below_offsets:
            offsets = tuple(zip(("mls_lb", "ams_mod"), below_offsets[distance]))
        else:
            offsets = (("mls_lb", lower_offset + font_size + 0.8), ("ams_mod", lower_offset))
        for method, offset in offsets:
            text = rf"${points[distance, method]['G_percent']:.2f}$"
            annotation = ax.annotate(text, xy=(x, y), xytext=(dx, offset),
                                     textcoords="offset points", ha=align, va="center",
                                     fontsize=font_size, color=COLORS[method],
                                     annotation_clip=False, clip_on=False, zorder=5)
            annotations.append(annotation)
    return annotations


def plot(points, intervals, args):
    plt.rcParams.update({
        "text.usetex": True, "text.latex.preamble": r"\usepackage{amsmath}",
        "pgf.texsystem": "pdflatex", "pgf.rcfonts": False, "pgf.preamble": r"\usepackage{amsmath}",
        "font.family": "serif", "font.serif": ["Computer Modern Roman"],
        "font.size": args.tick_font, "axes.labelsize": args.label_font,
        "xtick.labelsize": args.tick_font, "ytick.labelsize": args.tick_font,
        "axes.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
        "xtick.direction": "out", "ytick.direction": "out", "axes.unicode_minus": False,
        "legend.frameon": False,
    })
    fig, axes = plt.subplots(2, 2, figsize=(args.width, args.height))
    fig.subplots_adjust(left=0.18, right=0.98, bottom=0.17, top=0.97,
                        wspace=args.column_gap, hspace=args.row_gap)
    x = np.array(DISTANCES) * RADIUS_UM
    legend_handles = []
    gain_annotations = []
    for index, (ax, metric) in enumerate(zip(axes.flat, PANEL_KEYS)):
        methods = METHODS if metric != "G_percent" else METHODS[1:]
        low_values, high_values = [], []
        show_ci = not args.no_ci and metric != "G_percent"
        for method in methods:
            y = np.array([points[d, method][metric] for d in DISTANCES])
            bounds = np.array([intervals[d, method][metric] for d in DISTANCES])
            require(np.all(bounds[:, 0] <= y) and np.all(bounds[:, 1] >= y), "CI does not contain estimate")
            low_values.extend(bounds[:, 0] if show_ci else y)
            high_values.extend(bounds[:, 1] if show_ci else y)
            style = dict(color=COLORS[method], linestyle=STYLES[method], marker=MARKERS[method],
                         linewidth=0.85, markersize=2.7, markeredgewidth=0.5, label=LABELS[method], zorder=3)
            if not show_ci:
                handle, = ax.plot(x, y, **style)
            else:
                handle = ax.errorbar(x, y, yerr=np.vstack([y - bounds[:, 0], bounds[:, 1] - y]),
                                     capsize=1.25, capthick=0.5, elinewidth=0.5, **style)
            if index == 0:
                legend_handles.append(handle)
        if metric == "G_percent":
            ax.axhline(0, color=COLORS["monc"], linestyle=":", linewidth=0.75,
                       zorder=4, clip_on=False)
        ax.set_xscale("linear")
        configure_metric_axis(ax, metric, low_values, high_values)
        ax.set_xlim(3 * RADIUS_UM, 36 * RADIUS_UM)
        ax.set_xticks(x)
        if metric == "G_percent":
            gain_annotations = annotate_gains(ax, points, args.gain_label_font)
        ax.xaxis.set_minor_locator(NullLocator())
        ax.tick_params(axis="both", length=2.0, width=0.55, pad=1.8)
        ax.set_xlabel(r"$d_{\mathrm{TR}}\;(\mu\mathrm{m})$", labelpad=1.1)
        ax.set_ylabel(YLABELS[index], labelpad=2.1)
        ax.grid(color="#999999", alpha=0.18, linewidth=0.4)
        box = ax.get_position()
        fig.text((box.x0 + box.x1) / 2, box.y0 - args.caption_gap, CAPTIONS[index],
                 ha="center", va="center", fontsize=args.caption_font)
        require(len(ax.get_yticks()) <= 5, "Too many y ticks")
    legend = axes[0, 0].legend(legend_handles, [LABELS[m] for m in METHODS], loc="upper left",
                              fontsize=args.legend_font, borderaxespad=0.3, borderpad=0.1,
                              handlelength=1.4, handletextpad=0.3, labelspacing=0.15)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = [*fig.texts, *gain_annotations]
    for ax in axes.flat:
        texts.extend([*ax.get_xticklabels(), *ax.get_yticklabels(), ax.xaxis.label, ax.yaxis.label])
    for text in texts:
        if text.get_visible() and text.get_text():
            box = text.get_window_extent(renderer)
            require(box.x0 >= 0 and box.y0 >= 0 and box.x1 <= fig.bbox.width + 0.1
                    and box.y1 <= fig.bbox.height + 0.1, f"Label outside figure: {text.get_text()}")
    gain_boxes = [annotation.get_window_extent(renderer) for annotation in gain_annotations]
    for index, box in enumerate(gain_boxes):
        overlaps = [j for j in range(index+1, len(gain_boxes)) if box.overlaps(gain_boxes[j])]
        require(not overlaps, f"Gain labels overlap: {index} {gain_annotations[index].get_text()} with "
                f"{[(j, gain_annotations[j].get_text(), tuple(gain_boxes[j].bounds)) for j in overlaps]}; "
                f"bounds={tuple(box.bounds)}")
        require(not box.overlaps(fig.texts[1].get_window_extent(renderer)), "Gain label overlaps panel (b) caption")
        for line in axes[1, 1].lines:
            if line.get_label() in [LABELS[m] for m in METHODS[1:]]:
                path = line.get_transform().transform_path(line.get_path())
                require(not path.intersects_bbox(box, filled=False),
                        f"Gain label obscures a curve: {gain_annotations[index].get_text()}")
    require(axes[0, 0].get_window_extent(renderer).contains(*legend.get_window_extent(renderer).p0)
            and axes[0, 0].get_window_extent(renderer).contains(*legend.get_window_extent(renderer).p1),
            "Legend exceeds upper-left panel")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, format="pdf", backend="pgf", facecolor="white", metadata={
        "Title": "Canonical performance comparison - 50 outer experiments",
        "Subject": "Mean per-batch relative L2 error and wall time; S is product of means; relative gain in percent",
        "Creator": "Matplotlib PGF and LaTeX; 50-batch main comparison",
    })
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=ROOT / "outputs/analysis/outer_experiments.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/reproduced/02_canonical_metrics_2x2.pdf")
    parser.add_argument("--width", type=float, default=3.5)
    parser.add_argument("--height", type=float, default=2.85)
    parser.add_argument("--column-gap", type=float, default=0.42)
    parser.add_argument("--row-gap", type=float, default=0.73)
    parser.add_argument("--caption-gap", type=float, default=0.12,
                        help="Panel caption offset below its axes, in figure coordinates.")
    parser.add_argument("--tick-font", type=float, default=6.8)
    parser.add_argument("--label-font", type=float, default=8.0)
    parser.add_argument("--caption-font", type=float, default=7.4)
    parser.add_argument("--legend-font", type=float, default=6.2)
    parser.add_argument("--gain-label-font", type=float, default=5.5)
    parser.add_argument("--bootstrap", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--no-ci", action="store_true", help="Hide bootstrap error bars.")
    args = parser.parse_args()
    require(args.output.suffix.lower() == ".pdf", "Output must be PDF")
    require(args.bootstrap >= 1000, "Use at least 1000 bootstrap draws")
    points, intervals = summarize(args.source, args.bootstrap, args.seed)
    plot(points, intervals, args)
    print(args.output)


if __name__ == "__main__":
    main()
