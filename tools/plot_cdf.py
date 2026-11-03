#!/usr/bin/env python3
"""Single-experiment CDF: 32 estimates and original pointwise confidence intervals."""
from __future__ import annotations

import argparse
import csv
import gzip
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(Path(os.environ.get("TMPDIR", "/tmp")) / "mls-matplotlib"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullLocator, ScalarFormatter
import numpy as np

DISTANCES = (5, 8, 13, 21, 34)
METHODS = ("monc", "mls_lb", "ams_mod")
COLORS = {"monc": "#B64342", "mls_lb": "#0F4D92", "ams_mod": "#3B8E6E"}
STYLES = {"monc": "-", "mls_lb": "--", "ams_mod": "-."}
LABELS = {"monc": "MonC", "mls_lb": "uni. A-MLS", "ams_mod": "adap. A-MLS"}
# Major ticks and axis limits used in the manuscript figure.
YTICKS = {5: [0, 0.05, 0.10, 0.15], 8: [0, 0.02, 0.04, 0.06],
          13: [0, 0.01, 0.02], 21: [0, 0.001, 0.002, 0.003, 0.004],
          34: [0, 0.0001, 0.0002]}


def paper_curves(data_root, distance):
    data, intervals = {}, {}
    time = reference = None
    for method in METHODS:
        path = data_root / f"canonical/cdf/curves/{method}/d{distance:02d}R.csv.gz"
        if path.is_file():
            stream = gzip.open(path, "rt", newline="")
        else:
            path = data_root / f"canonical/cdf/runs/{method}/d{distance:02d}R/p0/e01/curves.csv"
            stream = path.open(newline="")
        with stream:
            rows = list(csv.DictReader(stream))
        t = np.array([float(r["t"]) for r in rows])
        ref = np.array([float(r["q_ref"]) for r in rows])
        if time is not None:
            assert np.array_equal(t, time) and np.array_equal(ref, reference)
        time, reference = t, ref
        data[method] = np.array([float(r["q_mean"]) for r in rows])
        intervals[method] = tuple(np.array([float(r[k]) if r[k] else np.nan for r in rows])
                                  for k in ("ci95_lower", "ci95_upper"))
    return time, reference, data, intervals


def configure_y_axis(ax, distance, reference, data, intervals):
    maxima = [float(reference.max()), *(float(y.max()) for y in data.values())]
    for lower, upper in intervals.values():
        finite = upper[np.isfinite(upper)]
        if finite.size:
            maxima.append(float(finite.max()))
    ymax = 2e-4 if distance == 34 else max(maxima) * 1.07
    ax.set_ylim(0, ymax)
    ax.set_yticks(YTICKS[distance])
    formatter = ScalarFormatter(useMathText=True)
    formatter.set_powerlimits((-2, 2))
    formatter.set_useOffset(False)
    ax.yaxis.set_major_formatter(formatter)
    ax.yaxis.set_minor_locator(NullLocator())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-root", type=Path, default=ROOT / "outputs")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/reproduced/01_canonical_CDF.pdf")
    parser.add_argument("--width", type=float, default=7.16)
    parser.add_argument("--height", type=float, default=1.85)
    parser.add_argument("--tick-font", type=float, default=8.5)
    parser.add_argument("--label-font", type=float, default=9.0)
    parser.add_argument("--caption-font", type=float, default=9.5)
    parser.add_argument("--legend-font", type=float, default=6.3)
    parser.add_argument("--distances", default=",".join(map(str, DISTANCES)),
                        help="Comma-separated distances in R; defaults to 5,8,13,21,34")
    parser.add_argument("--column-gap", type=float, default=0.42)
    parser.add_argument("--caption-y", type=float, default=0.025)
    parser.add_argument("--ci-alpha", type=float, default=0.15)
    args = parser.parse_args()
    assert args.output.suffix.lower() == ".pdf"
    distances = tuple(int(d) for d in args.distances.split(","))
    assert len(distances) >= 2 and len(set(distances)) == len(distances)
    assert all(d in YTICKS for d in distances)
    plt.rcParams.update({
        "text.usetex": True,
        "text.latex.preamble": r"\usepackage{amsmath}",
        "pgf.texsystem": "pdflatex", "pgf.rcfonts": False,
        "pgf.preamble": r"\usepackage{amsmath}",
        "font.family": "serif", "font.serif": ["Computer Modern Roman"],
        "font.size": args.tick_font, "axes.labelsize": args.label_font,
        "xtick.labelsize": args.tick_font, "ytick.labelsize": args.tick_font,
        "axes.linewidth": 0.65, "axes.spines.top": False, "axes.spines.right": False,
        "xtick.direction": "out", "ytick.direction": "out",
        "legend.frameon": False, "axes.unicode_minus": False,
    })
    fig, axes = plt.subplots(1, len(distances), figsize=(args.width, args.height))
    # Same overall width, horizontal bounds and relative gap as the parameter plot.
    fig.subplots_adjust(left=0.105, right=0.983, top=0.865, bottom=0.300,
                        wspace=args.column_gap)
    for col, (ax, distance) in enumerate(zip(axes, distances)):
        t, reference, data, intervals = paper_curves(args.data_root, distance)
        for method in METHODS:
            lower, upper = intervals[method]
            valid = np.isfinite(lower) & np.isfinite(upper)
            ax.fill_between(t, lower, upper, where=valid, step="post",
                            color=COLORS[method], alpha=args.ci_alpha,
                            linewidth=0, zorder=1)
            ax.step(t, data[method], where="post", color=COLORS[method],
                    linestyle=STYLES[method], linewidth=1.05, label=LABELS[method], zorder=2)
        ax.plot(t, reference, color="black", linestyle=":", linewidth=0.95,
                label="analy.", zorder=3)
        ax.set_xlim(0, float(t[-1]))
        configure_y_axis(ax, distance, reference, data, intervals)
        ax.set_xticks([0, 0.25, 0.50, 0.75])
        ax.set_xticklabels([r"$0$", r"$0.25$", r"$0.5$", r"$0.75$"])
        ax.xaxis.set_minor_locator(NullLocator())
        ax.tick_params(axis="both", length=2.2, width=0.6, pad=2.0)
        ax.set_xlabel(r"$t$ (s)", labelpad=1.6)
        if col == 0:
            ax.set_ylabel(r"$p(t)$", labelpad=2.1)
            ax.legend(loc="lower right", fontsize=args.legend_font,
                      borderaxespad=0.30, borderpad=0.15, handlelength=1.4,
                      handletextpad=0.25, labelspacing=0.17)
        ax.grid(color="#999999", alpha=0.18, linewidth=0.45)
        box = ax.get_position()
        fig.text((box.x0 + box.x1) / 2, args.caption_y,
                 rf"({chr(97+col)}) $d_{{\mathrm{{TR}}}}={distance}\,R$",
                 ha="center", va="bottom", fontsize=args.caption_font)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    outside = []
    texts = list(fig.texts)
    for ax in axes:
        texts += [*ax.get_xticklabels(), *ax.get_yticklabels(), ax.xaxis.label,
                  ax.yaxis.label, ax.yaxis.get_offset_text()]
    for text in texts:
        if text.get_visible() and text.get_text():
            box = text.get_window_extent(renderer)
            if box.x0 < 0 or box.y0 < 0 or box.x1 > fig.bbox.width + 0.1 or box.y1 > fig.bbox.height + 0.1:
                outside.append((text.get_text(), tuple(box.bounds)))
    assert not outside, f"Labels outside PDF canvas: {outside}"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, format="pdf", backend="pgf", facecolor="white", metadata={
        "Title": "Canonical absorption probability - single experiment",
        "Subject": "32 estimates; pointwise 95 percent Wilson / Student-t confidence intervals",
    })
    plt.close(fig)
    print(args.output)


if __name__ == "__main__":
    main()
