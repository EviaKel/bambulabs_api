"""
Detect overhanging faces in an STL mesh that exceed a given angle from vertical.
Groups results by Z-height bands and estimates bridge distances.
"""
import argparse
import json
import sys
import numpy as np
from stl import mesh as stl_mesh


def detect_overhangs(stl_path: str, angle_threshold: float = 45.0,
                     n_z_bands: int = 20) -> dict:
    m = stl_mesh.Mesh.from_file(stl_path)
    v0 = m.vectors[:, 0, :]
    v1 = m.vectors[:, 1, :]
    v2 = m.vectors[:, 2, :]

    # Face normals
    edges1 = v1 - v0
    edges2 = v2 - v0
    normals = np.cross(edges1, edges2)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    norms[norms < 1e-10] = 1e-10
    normals = normals / norms
    face_areas = norms.flatten() / 2.0
    total_area = float(np.sum(face_areas))

    # Face centroids
    centroids = (v0 + v1 + v2) / 3.0

    # Overhang detection: normal dot -Z > cos(threshold)
    # A face is an overhang if its normal points downward at more than threshold degrees
    down = np.array([0.0, 0.0, -1.0])
    cos_angle = np.dot(normals, down)
    angle_cos_threshold = np.cos(np.radians(angle_threshold))

    # Overhang = normal aligns with downward direction beyond threshold
    # cos_angle > cos(threshold) means angle from down < threshold
    # But we want faces pointing down more than threshold from horizontal
    # Overhang angle from vertical: angle between normal and -Z
    # If this angle < (90 - threshold), face is overhang
    # Simpler: face is overhang if normal_z < -cos(threshold)
    overhang_mask = normals[:, 2] < -np.cos(np.radians(angle_threshold))

    # Exclude bottom face (within 0.5mm of lowest point)
    min_z = centroids[:, 2].min()
    bed_mask = centroids[:, 2] < (min_z + 0.5)
    overhang_mask = overhang_mask & (~bed_mask)

    overhang_count = int(np.sum(overhang_mask))
    overhang_area = float(np.sum(face_areas[overhang_mask]))

    # Z-band analysis
    z_min = float(centroids[:, 2].min())
    z_max = float(centroids[:, 2].max())
    z_range = z_max - z_min
    band_height = z_range / max(n_z_bands, 1)

    z_bands = []
    overhang_centroids = centroids[overhang_mask]
    overhang_areas = face_areas[overhang_mask]

    for i in range(n_z_bands):
        band_lo = z_min + i * band_height
        band_hi = band_lo + band_height
        in_band = (overhang_centroids[:, 2] >= band_lo) & (overhang_centroids[:, 2] < band_hi)
        band_area = float(np.sum(overhang_areas[in_band]))
        if band_area > 0:
            z_bands.append({
                "z_range_mm": [round(band_lo, 2), round(band_hi, 2)],
                "overhang_area_mm2": round(band_area, 2),
                "face_count": int(np.sum(in_band)),
            })

    # Estimate max bridge distance
    # Horizontal overhangs (normal nearly pointing straight down)
    near_horizontal = overhang_mask & (normals[:, 2] < -0.95)
    max_bridge = 0.0
    if np.any(near_horizontal):
        horiz_centroids = centroids[near_horizontal]
        # Estimate bridge distance as max spread in XY within connected regions
        if len(horiz_centroids) > 1:
            xy = horiz_centroids[:, :2]
            # Simple estimate: max pairwise distance (sample to avoid O(n²))
            n_sample = min(200, len(xy))
            idx = np.random.choice(len(xy), n_sample, replace=False) if len(xy) > n_sample else np.arange(len(xy))
            sampled = xy[idx]
            for i in range(len(sampled)):
                dists = np.linalg.norm(sampled[i] - sampled, axis=1)
                max_bridge = max(max_bridge, float(dists.max()))

    # Severity classification
    overhang_pct = overhang_area / max(total_area, 1e-10) * 100
    if overhang_pct < 5:
        severity = "low"
    elif overhang_pct < 20:
        severity = "medium"
    else:
        severity = "high"

    return {
        "total_faces": len(m.vectors),
        "overhang_face_count": overhang_count,
        "overhang_face_pct": round(overhang_count / max(len(m.vectors), 1) * 100, 2),
        "overhang_area_mm2": round(overhang_area, 2),
        "overhang_area_pct": round(overhang_pct, 2),
        "angle_threshold_deg": angle_threshold,
        "overhang_by_height": z_bands,
        "max_bridge_distance_mm": round(max_bridge, 2),
        "severity": severity,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect overhangs in STL")
    parser.add_argument("stl_path", help="Path to STL file")
    parser.add_argument("--angle", type=float, default=45.0, help="Overhang angle threshold")
    parser.add_argument("--z-bands", type=int, default=20)
    args = parser.parse_args()
    result = detect_overhangs(args.stl_path, args.angle, args.z_bands)
    print(json.dumps(result, indent=2))
