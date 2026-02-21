---
name: stl-optimal-orientation
description: Find the optimal print orientation by testing rotations and scoring each by cross-section area at centroid plane, overhang area, and bed contact. Use when deciding how to orient a model on the print bed.
argument-hint: [stl-file-path]
---

# STL Optimal Print Orientation

Finds the best rotation to place a model on the print bed by sampling orientations and scoring each on multiple criteria.

## Algorithm
1. Sample ~200 orientations on a unit hemisphere (fibonacci sphere)
2. For each candidate "down" direction:
   - Rotate mesh so that direction points down (-Z)
   - Compute **bed contact area** (faces within 0.1mm of bottom with normal pointing down)
   - Compute **overhang area** (faces with normal > 45° from vertical)
   - Compute **cross-section area at centroid height** (slice through center of mass)
   - Compute **center of gravity height** (lower = more stable)
3. Score = weighted combination: maximize bed contact, minimize overhangs, maximize centroid cross-section, minimize CoG height
4. Return top 3 orientations with rotation matrices

## How to run
```bash
python scripts/find_orientation.py <stl_path> [--samples 200] [--overhang-angle 45]
```

## Output (JSON)
- `best_orientation` — rotation matrix + Euler angles
- `bed_contact_area_mm2` — flat area touching the bed
- `overhang_area_mm2` — area needing support
- `cross_section_at_centroid_mm2` — stability indicator
- `score` — composite score (higher = better)
- `top_3` — the three best candidates

## References
See [references/scoring.md](references/scoring.md) for weight tuning.
