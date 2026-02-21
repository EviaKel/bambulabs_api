---
name: stl-overhang-detection
description: Detect overhanging faces in an STL mesh that exceed a given angle threshold and will need support material during printing. Use to estimate support needs and identify problematic geometry.
argument-hint: [stl-file-path]
---

# STL Overhang Detection

Identifies all downward-facing triangles whose angle from vertical exceeds a threshold (default 45°) — these require support material during FDM printing.

## Algorithm
1. Compute face normals for all triangles
2. Measure angle between each normal and the -Z (gravity) direction
3. Faces where `acos(normal · -Z) < threshold` are overhangs
4. Group overhang faces by Z-height bands for per-layer analysis
5. Compute bridging distances for horizontal overhangs

## How to run
```bash
python scripts/detect_overhangs.py <stl_path> [--angle 45] [--z-bands 20]
```

## Output (JSON)
- `overhang_faces` — count and percentage
- `overhang_area_mm2` — total area needing support
- `overhang_by_height` — overhang area per Z-band
- `max_bridge_distance_mm` — longest unsupported horizontal span
- `severity` — low / medium / high classification
