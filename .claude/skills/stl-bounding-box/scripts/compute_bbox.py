"""
Compute bounding box, dimensions, surface area, and aspect ratios of an STL mesh.
Checks whether the model fits a given build volume (default: Bambu X1C 256mm³).
"""
import argparse
import json
import sys
import numpy as np
from stl import mesh as stl_mesh


def compute_bbox(stl_path: str, bed_x=256.0, bed_y=256.0, bed_z=256.0) -> dict:
    m = stl_mesh.Mesh.from_file(stl_path)
    all_points = m.vectors.reshape(-1, 3)

    mn = all_points.min(axis=0)
    mx = all_points.max(axis=0)
    dims = mx - mn

    # Surface area
    v0 = m.vectors[:, 0, :]
    v1 = m.vectors[:, 1, :]
    v2 = m.vectors[:, 2, :]
    areas = np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1) / 2.0
    total_area = float(np.sum(areas))

    sorted_dims = sorted(dims)
    aspect_ratio = sorted_dims[2] / max(sorted_dims[0], 1e-10)

    fits = bool(dims[0] <= bed_x and dims[1] <= bed_y and dims[2] <= bed_z)
    bed_volume = bed_x * bed_y * bed_z

    # Volume via signed tetrahedra
    cross = np.cross(v1, v2)
    signed_volumes = np.einsum("ij,ij->i", v0, cross) / 6.0
    volume = abs(float(np.sum(signed_volumes)))

    return {
        "min": [round(v, 4) for v in mn.tolist()],
        "max": [round(v, 4) for v in mx.tolist()],
        "dimensions_mm": {
            "width": round(float(dims[0]), 4),
            "depth": round(float(dims[1]), 4),
            "height": round(float(dims[2]), 4),
        },
        "surface_area_mm2": round(total_area, 4),
        "volume_mm3": round(volume, 4),
        "aspect_ratio": round(aspect_ratio, 2),
        "fits_bed": fits,
        "volume_utilization_pct": round(volume / bed_volume * 100, 2),
        "face_count": len(m.vectors),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="STL bounding box analysis")
    parser.add_argument("stl_path", help="Path to STL file")
    parser.add_argument("--bed-x", type=float, default=256.0)
    parser.add_argument("--bed-y", type=float, default=256.0)
    parser.add_argument("--bed-z", type=float, default=256.0)
    args = parser.parse_args()
    result = compute_bbox(args.stl_path, args.bed_x, args.bed_y, args.bed_z)
    print(json.dumps(result, indent=2))
