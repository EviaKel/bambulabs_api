---
name: stl-bounding-box
description: Compute bounding box dimensions, surface area, aspect ratios, and basic geometric stats of an STL mesh. Use as a quick first-pass analysis before deeper skills.
argument-hint: [stl-file-path]
---

# STL Bounding Box & Dimensions

Quick geometric overview of an STL model — dimensions, surface area, aspect ratios, and fit check against a build volume.

## How to run
```bash
python scripts/compute_bbox.py <stl_path> [--bed-x 256] [--bed-y 256] [--bed-z 256]
```

Default bed size is Bambu Lab X1C: 256 × 256 × 256 mm.

## Output (JSON)
- `min` / `max` — bounding box corners [x, y, z]
- `dimensions` — width, depth, height in mm
- `surface_area_mm2` — total surface area
- `aspect_ratio` — max_dim / min_dim
- `fits_bed` — whether the model fits the build volume
- `volume_utilization` — % of build volume used
