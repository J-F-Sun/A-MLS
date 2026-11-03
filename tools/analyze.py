#!/usr/bin/env python3
"""Compute the manuscript's mean relative L2 error, mean wall time, S and G."""
from __future__ import annotations
import argparse
import collections
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENES = ('canonical', 'ob_complete', 'ob_half', 'rx2_competitive', 'rx2_half')
METHODS = ('monc', 'mls_lb', 'ams_mod')
DISTANCES = (5, 8, 13, 21, 34)


def read_csv(path):
    with path.open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def analyze(data_root, output_root):
    rows = []
    for scene in SCENES:
        path = data_root / scene / 'main/experiments.csv'
        if path.is_file():
            rows.extend(read_csv(path))
    if not rows:
        raise ValueError(f'No main experiment data under {data_root}')
    # A reduced run may contain any subset of scenes, distances and methods.
    common = [k for k in rows[0] if all(k in r for r in rows)]
    rows = [{k: r[k] for k in common} for r in rows]
    groups = collections.defaultdict(list)
    for row in rows:
        if row['accepted_run'].lower() != 'true' or int(row['iteration_caps']) != 0:
            raise ValueError('Unfinished estimate in experiment data')
        groups[row['scene'], float(row['distance_R']), row['algorithm']].append(row)
    summaries = {}
    for key, group in sorted(groups.items()):
        ids = [int(r['experiment']) for r in group]
        if len(ids) != len(set(ids)):
            raise ValueError(f'Duplicate experiment IDs for {key}')
        err = math.fsum(float(r['relative_l2']) for r in group) / len(group)
        wall = math.fsum(float(r['wall_seconds']) for r in group) / len(group)
        if not math.isfinite(err + wall) or wall <= 0:
            raise ValueError(f'Invalid metrics for {key}')
        summaries[key] = dict(scene=key[0], distance_R=key[1], algorithm=key[2],
                              batches=len(group), estimates_per_batch=int(group[0]['inner_repeats']),
                              mean_relative_l2=err, mean_relative_l2_percent=100*err,
                              mean_wall_seconds=wall, S_seconds=err*wall,
                              reference_endpoint=float(group[0]['q_ref_final']))
    for (scene, distance, method), row in summaries.items():
        baseline = summaries.get((scene, distance, 'monc'))
        row['G_percent'] = 100*(baseline['S_seconds']/row['S_seconds']-1) if baseline and row['S_seconds'] else ''
    output_root.mkdir(parents=True, exist_ok=True)
    write_csv(output_root / 'outer_experiments.csv', rows)
    write_csv(output_root / 'metrics.csv', list(summaries.values()))
    lines = [r'\begin{tabular}{lrr|rrr|rrr|rrr}', r'\hline',
             r'Scenario & $d_{\rm TR}$ & $p_{\rm ref}(T)$ & \multicolumn{3}{c|}{MonC} & \multicolumn{3}{c|}{Uniform A-MLS} & \multicolumn{3}{c}{Adaptive A-MLS} \\',
             r' & & & Error (\%) & $\bar W$ (s) & $S$ (s) & Error (\%) & $\bar W$ (s) & $S$ (s) & Error (\%) & $\bar W$ (s) & $S$ (s) \\', r'\hline']
    for index, scene in enumerate(SCENES[1:], 1):
        for distance in DISTANCES:
            if not all((scene, float(distance), m) in summaries for m in METHODS):
                continue
            points = [summaries[scene, float(distance), m] for m in METHODS]
            best = min(p['S_seconds'] for p in points)
            cells = [f'Ext{index}', str(distance), f"{points[0]['reference_endpoint']:.2e}"]
            for p in points:
                score = f"{p['S_seconds']:.3f}"
                if p['S_seconds'] == best:
                    score = r'\textbf{' + score + '}'
                cells.extend([f"{p['mean_relative_l2_percent']:.2f}", f"{p['mean_wall_seconds']:.3f}", score])
            lines.append(' & '.join(cells) + r' \\')
        lines.append(r'\hline')
    lines.append(r'\end{tabular}')
    (output_root / 'extended_performance.tex').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(f'{len(groups)} configurations, {len(rows)} batches -> {output_root}')
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=ROOT / 'outputs')
    parser.add_argument('--output-root', type=Path)
    args = parser.parse_args()
    analyze(args.data_root, args.output_root or args.data_root / 'analysis')


if __name__ == '__main__':
    main()
