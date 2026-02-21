---
name: stl-thin-wall-detection
description: Detect thin walls and small features in an STL mesh that may fail to print or require special slicer settings. Use when checking printability or diagnosing failed prints.
argument-hint: [stl-file-path]
---

# STL Thin Wall Detection

Finds regions of the mesh where opposing surfaces are closer than a minimum printable thickness.

## Algorithm
1. Cast rays from each face centroid inward along the inverted normal
2. Find the nearest opposing face hit (ray-mesh intersection)
3. If hit distance < threshold (default: nozzle diameter × 1.5), flag as thin
4. Cluster thin faces into connected regions and report each

## How to run
```bash
python scripts/detect_thin_walls.py <stl_path> [--min-thickness 0.6] [--nozzle 0.4]
```

Default min thickness = 0.6mm (1.5× a 0.4mm nozzle).

## Output (JSON)
- `thin_regions` — list of regions with face indices, avg thickness, min thickness, centroid
- `total_thin_area_mm2` — total area below threshold
- `thin_area_pct` — percentage of total surface that is thin
- `min_detected_thickness_mm` — thinnest point found
- `recommendation` — slicer settings suggestion
