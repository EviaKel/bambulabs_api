---
name: stl-centroid
description: Compute the volume-weighted centroid (center of mass) of an STL mesh. Use when analyzing weight distribution, balance, or as input to orientation optimization.
argument-hint: [stl-file-path]
---

# STL Centroid Analysis

Compute the **volume-weighted centroid** of a closed triangle mesh using signed tetrahedra decomposition.

## Algorithm
For each face (v0, v1, v2), form a tetrahedron with the origin:
- Signed volume: `V_i = v0 · (v1 × v2) / 6`
- Tet centroid: `(v0 + v1 + v2) / 4`
- Final centroid: `Σ(V_i · C_i) / Σ(V_i)`

## How to run
```bash
python scripts/compute_centroid.py <stl_path>
```

## Output (JSON)
- `centroid` — [x, y, z] center of mass
- `volume` — total mesh volume in mm³
- `face_count` / `vertex_count` — mesh stats

## Notes
- Requires watertight mesh for accurate volume. Non-watertight meshes fall back to area-weighted face centroids.
- Volume sign indicates face winding consistency.
