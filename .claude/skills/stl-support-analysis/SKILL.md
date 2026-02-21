---
name: stl-support-analysis
description: Estimate support material volume, contact area with the model, and support-to-part ratio for an STL mesh. Use to predict material waste and post-processing effort.
argument-hint: [stl-file-path]
---

# STL Support Analysis

Estimates the support material needed for a given orientation by projecting overhang regions downward to the bed or to the nearest supporting surface below.

## Algorithm
1. Identify overhang faces (normals > 45° from vertical)
2. For each overhang face, project downward to find the nearest surface or bed below
3. Compute the support column volume (face area × drop height)
4. Calculate support-model contact area (where supports touch the part)
5. Estimate total support volume and filament usage

## How to run
```bash
python scripts/analyze_support.py <stl_path> [--angle 45] [--density 0.15]
```

`--density` is support infill density (default 15% for typical tree/grid supports).

## Output (JSON)
- `support_volume_mm3` — estimated support material volume
- `support_filament_m` — meters of 1.75mm filament needed for supports
- `support_contact_area_mm2` — area where supports touch the model
- `support_to_part_ratio` — support_volume / part_volume
- `support_regions` — per-region breakdown by Z height
- `estimated_support_time_min` — rough print time for supports
