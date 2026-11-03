#!/usr/bin/env python3
"""Extended-scenario relative gains from 50 independent batches per method."""
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
from matplotlib.lines import Line2D
from matplotlib.ticker import LogFormatterMathtext, NullLocator

DISTANCES = (5, 8, 13, 21, 34)
SCENES = (("ob_complete", "Ext1"), ("ob_half", "Ext2"),
          ("rx2_competitive", "Ext3"), ("rx2_half", "Ext4"))
METHODS = ("monc", "mls_lb", "ams_mod")
COLORS = {"monc": "#B64342", "mls_lb": "#0F4D92", "ams_mod": "#3B8E6E"}
STYLES = {"mls_lb": "--", "ams_mod": "-."}
MARKERS = {"mls_lb": "s", "ams_mod": "^"}
LABELS = {"monc": "MonC", "mls_lb": "uni. A-MLS", "ams_mod": "adap. A-MLS"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def summarize(source):
    raw = read_csv(source)
    values = {}
    for scene, label in SCENES:
        for distance in DISTANCES:
            for method in METHODS:
                rows = [r for r in raw if r["scene"] == scene and float(r["distance_R"]) == distance
                        and r["algorithm"] == method]
                require(len(rows) == 50 and sorted(int(r["experiment"]) for r in rows) == list(range(1, 51)),
                        f"Expected 50 distinct batches: {scene}, {distance}, {method}")
                require(all(int(r["inner_repeats"]) == 32 and r["accepted_run"].lower() == "true"
                            and int(r["iteration_caps"]) == 0 for r in rows), "Invalid experiment status")
                error = math.fsum(float(r["relative_l2"]) for r in rows) / 50
                wall = math.fsum(float(r["wall_seconds"]) for r in rows) / 50
                values[scene, distance, method] = dict(mean_relative_l2=error,
                                                      mean_wall_seconds=wall, S_seconds=wall*error)
            for method in METHODS:
                point = values[scene, distance, method]
                point["G_percent"] = 100 * (values[scene, distance, "monc"]["S_seconds"] / point["S_seconds"] - 1)
    return values


def plot(values, args):
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
    fig.subplots_adjust(left=0.17, right=0.98, bottom=0.17, top=0.97,
                        wspace=args.column_gap, hspace=args.row_gap)
    annotations = []
    for index, (ax, (scene, label)) in enumerate(zip(axes.flat, SCENES)):
        top_row = index < 2
        ymin = args.top_ymin if top_row else args.bottom_ymin
        for method in METHODS[1:]:
            gains = [values[scene, distance, method]["G_percent"] for distance in DISTANCES]
            require(max(gains) <= args.ymax, "Gain outside requested range")
            # Do not clamp the negative observation to the displayed lower
            # limit or connect it as a boundary-valued data point.
            plotted_gains = [g if g >= ymin else float("nan") for g in gains]
            ax.plot(DISTANCES, plotted_gains, color=COLORS[method], linestyle=STYLES[method],
                    marker=MARKERS[method], linewidth=0.85, markersize=2.8,
                    markeredgewidth=0.5, label=LABELS[method], zorder=3)
        ax.set_xscale("linear")
        ax.set_yscale("log", base=10)
        ax.set_xlim(3, 36)
        ax.set_ylim(ymin, args.ymax)
        ax.set_xticks(DISTANCES)
        ax.set_yticks([10, 100, 1000])
        ax.yaxis.set_major_formatter(LogFormatterMathtext(base=10))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.yaxis.set_minor_locator(NullLocator())
        ax.tick_params(axis="both", length=2.0, width=0.55, pad=1.8)
        ax.set_xlabel(r"$d_{\mathrm{TR}}\;(\mu\mathrm{m})$", labelpad=1.1)
        if index % 2 == 0:
            ax.set_ylabel(r"$G$ (\%)", labelpad=2.0)
        ax.grid(color="#999999", alpha=0.18, linewidth=0.4)
        box = ax.get_position()
        fig.text((box.x0 + box.x1) / 2, box.y0 - args.caption_gap,
                 f"({chr(97+index)}) {label}", ha="center", va="center", fontsize=args.caption_font)
        if scene == "rx2_half":
            value = values[scene, 5, "ams_mod"]["G_percent"]
            ax.annotate("", xy=(5, ymin), xytext=(5, ymin*2.6),
                        arrowprops=dict(arrowstyle="-|>", color=COLORS["ams_mod"],
                                        linewidth=0.7, shrinkA=0, shrinkB=0,
                                        mutation_scale=5), annotation_clip=False, zorder=6)
            annotations.append(ax.annotate(rf"${value:.2f}$", xy=(5, ymin), xytext=(4, 4),
                                            textcoords="offset points", ha="left", va="bottom",
                                            fontsize=args.annotation_font, color=COLORS["ams_mod"], zorder=5))
        require(len(ax.get_yticks()) == 3, "Expected three logarithmic ticks")
    handles = [Line2D([], [], color=COLORS[m], linestyle=STYLES[m], marker=MARKERS[m],
                       markersize=2.8, linewidth=0.85, label=LABELS[m]) for m in METHODS[1:]]
    legend = axes[1, 0].legend(handles=handles, loc="lower right", ncol=1,
                        fontsize=args.legend_font, handlelength=1.6, handletextpad=0.4,
                        labelspacing=0.35, borderaxespad=0.4, borderpad=0)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    require(len(annotations) == 1, "Only the negative off-scale gain should be labeled")
    texts = [*fig.texts, *annotations]
    for ax in axes.flat:
        texts.extend([*ax.get_xticklabels(), *ax.get_yticklabels(), ax.xaxis.label, ax.yaxis.label])
    for text in texts:
        if text.get_visible() and text.get_text():
            box = text.get_window_extent(renderer)
            require(box.x0 >= 0 and box.y0 >= 0 and box.x1 <= fig.bbox.width + 0.1
                    and box.y1 <= fig.bbox.height + 0.1, f"Text outside figure: {text.get_text()}")
    legend_box = legend.get_window_extent(renderer)
    require(legend_box.x0 >= 0 and legend_box.x1 <= fig.bbox.width and legend_box.y1 <= fig.bbox.height,
            "Legend outside figure")
    require(axes[1, 0].get_window_extent(renderer).contains(legend_box.x0, legend_box.y0)
            and axes[1, 0].get_window_extent(renderer).contains(legend_box.x1, legend_box.y1),
            "Legend must remain within panel (c)")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, format="pdf", backend="pgf", facecolor="white", metadata={
        "Title": "Relative performance gains in four extended scenarios",
        "Subject": "50 batches x 32 estimates; gain from unrounded product of mean error and mean wall time",
        "Creator": "Matplotlib PGF and LaTeX; 50-batch main comparison",
    })
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=ROOT / "outputs/analysis/outer_experiments.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/reproduced/03_extended_gain_2x2.pdf")
    parser.add_argument("--width", type=float, default=3.5)
    parser.add_argument("--height", type=float, default=3.05)
    parser.add_argument("--column-gap", type=float, default=0.37)
    parser.add_argument("--row-gap", type=float, default=0.70)
    parser.add_argument("--caption-gap", type=float, default=0.12)
    parser.add_argument("--tick-font", type=float, default=6.8)
    parser.add_argument("--label-font", type=float, default=8.0)
    parser.add_argument("--caption-font", type=float, default=7.4)
    parser.add_argument("--legend-font", type=float, default=6.2)
    parser.add_argument("--annotation-font", type=float, default=6.0)
    parser.add_argument("--top-ymin", type=float, default=10)
    parser.add_argument("--bottom-ymin", type=float, default=4)
    parser.add_argument("--ymax", type=float, default=2000)
    args = parser.parse_args()
    require(args.output.suffix.lower() == ".pdf", "Output must be PDF")
    require(0 < args.top_ymin < args.ymax and 0 < args.bottom_ymin < args.ymax,
            "Logarithmic axes require positive lower limits below ymax")
    values = summarize(args.source)
    plot(values, args)
    print(args.output)


if __name__ == "__main__":
    main()
