"""
Estimate support material volume and contact area for an STL mesh.

Projects overhang faces downward to the bed (or nearest surface below)
to approximate the support columns needed.
"""
import argparse
import json
import sys
import numpy as np
from stl import mesh as stl_mesh


def analyze_support(stl_path: str, angle_threshold: float = 45.0,
                    support_density: float = 0.15) -> dict:
    m = stl_mesh.Mesh.from_file(stl_path)
    v0 = m.vectors[:, 0, :]
    v1 = m.vectors[:, 1, :]
    v2 = m.vectors[:, 2, :]

    # Face normals and areas
    edges1 = v1 - v0
    edges2 = v2 - v0
    normals = np.cross(edges1, edges2)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    norms[norms < 1e-10] = 1e-10
    normals = normals / norms
    face_areas = norms.flatten() / 2.0

    # Face centroids
    centroids = (v0 + v1 + v2) / 3.0

    # Part volume (signed tetrahedra)
    cross = np.cross(v1, v2)
    signed_volumes = np.einsum("ij,ij->i", v0, cross) / 6.0
    part_volume = abs(float(np.sum(signed_volumes)))

    # Shift mesh so bottom = Z=0
    z_offset = centroids[:, 2].min()
    centroids_shifted = centroids.copy()
    centroids_shifted[:, 2] -= z_offset

    # Overhang faces
    overhang_mask = normals[:, 2] < -np.cos(np.radians(angle_threshold))
    bed_mask = centroids_shifted[:, 2] < 0.5
    overhang_mask = overhang_mask & (~bed_mask)

    overhang_areas = face_areas[overhang_mask]
    overhang_centroids = centroids_shifted[overhang_mask]

    # For each overhang face, estimate drop height to nearest support below
    # Simple approach: for each overhang face, find the nearest non-overhang
    # face below it (or the bed at Z=0)
    support_volume = 0.0
    contact_area = 0.0
    n_overhang = len(overhang_areas)

    if n_overhang > 0:
        # Get non-overhang face centroids (potential support landing surfaces)
        non_overhang_mask = ~overhang_mask & ~bed_mask
        non_oh_centroids = centroids_shifted[non_overhang_mask]
        non_oh_normals = normals[non_overhang_mask]
        # Only upward-facing surfaces can catch supports
        upward_mask = non_oh_normals[:, 2] > 0.5
        landing_centroids = non_oh_centroids[upward_mask] if np.any(upward_mask) else np.empty((0, 3))

        for i in range(n_overhang):
            oh_z = overhang_centroids[i, 2]
            oh_xy = overhang_centroids[i, :2]
            area = overhang_areas[i]

            # Find nearest landing surface directly below (within 5mm XY)
            drop_to = 0.0  # default: drop to bed
            if len(landing_centroids) > 0:
                below = landing_centroids[landing_centroids[:, 2] < oh_z]
                if len(below) > 0:
                    xy_dist = np.linalg.norm(below[:, :2] - oh_xy, axis=1)
                    nearby = xy_dist < 5.0
                    if np.any(nearby):
                        drop_to = float(below[nearby][:, 2].max())

            drop_height = max(oh_z - drop_to, 0.0)
            # Support column = projected area × height × density
            support_volume += area * drop_height * support_density
            contact_area += area

    # Filament estimate: 1.75mm diameter filament
    filament_cross_section = np.pi * (1.75 / 2) ** 2  # mm²
    filament_meters = (support_volume / filament_cross_section) / 1000.0

    # Time estimate: ~15mm³/s typical support print speed
    support_time_min = support_volume / 15.0 / 60.0

    support_ratio = support_volume / max(part_volume, 1e-10)

    # Per-height breakdown
    z_max = float(centroids_shifted[:, 2].max())
    n_bands = 10
    band_h = z_max / max(n_bands, 1)
    regions = []
    for i in range(n_bands):
        lo = i * band_h
        hi = lo + band_h
        in_band = (overhang_centroids[:, 2] >= lo) & (overhang_centroids[:, 2] < hi) if n_overhang > 0 else np.array([], dtype=bool)
        if np.any(in_band):
            regions.append({
                "z_range_mm": [round(lo, 1), round(hi, 1)],
                "overhang_area_mm2": round(float(overhang_areas[in_band].sum()), 2),
                "face_count": int(np.sum(in_band)),
            })

    return {
        "support_volume_mm3": round(support_volume, 2),
        "support_filament_m": round(filament_meters, 3),
        "support_contact_area_mm2": round(contact_area, 2),
        "support_to_part_ratio": round(support_ratio, 4),
        "part_volume_mm3": round(part_volume, 2),
        "support_regions": regions,
        "estimated_support_time_min": round(support_time_min, 1),
        "support_density": support_density,
        "angle_threshold_deg": angle_threshold,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Estimate support material for STL")
    parser.add_argument("stl_path", help="Path to STL file")
    parser.add_argument("--angle", type=float, default=45.0)
    parser.add_argument("--density", type=float, default=0.15)
    args = parser.parse_args()
    result = analyze_support(args.stl_path, args.angle, args.density)
    print(json.dumps(result, indent=2))
