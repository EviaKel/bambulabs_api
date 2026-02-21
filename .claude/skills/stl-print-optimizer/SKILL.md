---
name: stl-print-optimizer
description: Run all STL analysis skills and produce a unified print recommendation with optimal orientation, layer height, support settings, and warnings. This is the master skill that ties all analysis together.
argument-hint: [stl-file-path]
---

# STL Print Optimizer

Runs **all analysis skills** on an STL file and produces a single unified report with printing recommendations.

## What it runs
1. **Bounding box** — dimensions, fit check
2. **Centroid** — center of mass, volume
3. **Optimal orientation** — best rotation for printing
4. **Overhang detection** — support-needing regions
5. **Thin wall detection** — unprintable features
6. **Support analysis** — material/time estimates

## How to run
```bash
python scripts/optimize_print.py <stl_path> [--nozzle 0.4] [--bed-x 256] [--bed-y 256] [--bed-z 256]
```

## Output (JSON)
Complete report with:
- `summary` — one-line printability verdict
- `dimensions` — from bounding-box skill
- `centroid` — from centroid skill
- `recommended_orientation` — from optimal-orientation skill
- `overhang_analysis` — from overhang-detection skill
- `thin_wall_analysis` — from thin-wall-detection skill
- `support_estimate` — from support-analysis skill
- `recommended_settings` — suggested layer height, support type, infill, speed
- `warnings` — list of issues to address before printing

## Recommendations Logic
- **Layer height**: 0.2mm default; 0.12mm if thin walls detected; 0.28mm if no fine features and speed priority
- **Support type**: tree if overhangs < 15%, grid if > 15%, none if < 3%
- **Infill**: 15% default; 25% if tall/thin (aspect ratio > 3); 10% if large flat object
- **Speed**: reduced near thin walls, normal elsewhere
