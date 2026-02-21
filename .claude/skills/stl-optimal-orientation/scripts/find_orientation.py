"""
Find optimal print orientation for an STL by sampling rotations and scoring
each on bed contact area, overhang area, cross-section at centroid, and
center-of-gravity height.
"""
import argparse
import json
import sys
import numpy as np
from stl import mesh as stl_mesh


def fibonacci_hemisphere(n: int) -> np.ndarray:
    """Generate n approximately-uniform points on upper unit hemisphere."""
    indices = np.arange(n, dtype=float)
    phi = np.arccos(1 - indices / n)  # 0 to pi/2 for hemisphere
    theta = np.pi * (1 + 5**0.5) * indices
    x = np.sin(phi) * np.cos(theta)
    y = np.sin(phi) * np.sin(theta)
    z = np.cos(phi)
    return np.column_stack([x, y, z])


def rotation_matrix_from_vectors(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Rotation matrix that aligns unit vector a to unit vector b."""
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = np.dot(a, b)
    if abs(c + 1.0) < 1e-8:
        # 180-degree rotation
        return -np.eye(3)
    s = np.linalg.norm(v)
    if s < 1e-10:
        return np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * ((1 - c) / (s * s))


def rotation_to_euler(R: np.ndarray) -> dict:
    """Extract ZYX Euler angles (degrees) from rotation matrix."""
    sy = np.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)
    if sy > 1e-6:
        x = np.degrees(np.arctan2(R[2, 1], R[2, 2]))
        y = np.degrees(np.arctan2(-R[2, 0], sy))
        z = np.degrees(np.arctan2(R[1, 0], R[0, 0]))
    else:
        x = np.degrees(np.arctan2(-R[1, 2], R[1, 1]))
        y = np.degrees(np.arctan2(-R[2, 0], sy))
        z = 0.0
    return {"x": round(x, 2), "y": round(y, 2), "z": round(z, 2)}


def slice_cross_section_area(points: np.ndarray, normals: np.ndarray,
                             v0: np.ndarray, v1: np.ndarray, v2: np.ndarray,
                             z_height: float, tolerance: float = 0.5) -> float:
    """Approximate cross-section area at a given Z height.

    Finds triangles that straddle the Z plane and sums the area of each
    triangle's intersection with a thin slab around z_height.
    """
    min_z = np.minimum(np.minimum(v0[:, 2], v1[:, 2]), v2[:, 2])
    max_z = np.maximum(np.maximum(v0[:, 2], v1[:, 2]), v2[:, 2])

    # Faces that cross this z plane
    crossing = (min_z <= z_height) & (max_z >= z_height)
    if not np.any(crossing):
        return 0.0

    # Approximate: project crossing faces onto XY and sum projected areas
    cv0 = v0[crossing]
    cv1 = v1[crossing]
    cv2 = v2[crossing]
    edges1 = cv1 - cv0
    edges2 = cv2 - cv0
    cross = np.cross(edges1, edges2)
    # Projected area onto XY plane = |cross_z| / 2
    projected_areas = np.abs(cross[:, 2]) / 2.0
    return float(np.sum(projected_areas))


def score_orientation(m: stl_mesh.Mesh, down_dir: np.ndarray,
                      overhang_angle_deg: float = 45.0) -> dict:
    """Score a single orientation where down_dir becomes -Z."""
    R = rotation_matrix_from_vectors(down_dir, np.array([0.0, 0.0, -1.0]))

    # Rotate all vertices
    v0 = (R @ m.vectors[:, 0, :].T).T
    v1 = (R @ m.vectors[:, 1, :].T).T
    v2 = (R @ m.vectors[:, 2, :].T).T

    # Shift so bottom sits at Z=0
    all_z = np.concatenate([v0[:, 2], v1[:, 2], v2[:, 2]])
    z_shift = all_z.min()
    v0[:, 2] -= z_shift
    v1[:, 2] -= z_shift
    v2[:, 2] -= z_shift

    # Recompute normals
    edges1 = v1 - v0
    edges2 = v2 - v0
    normals = np.cross(edges1, edges2)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    norms[norms < 1e-10] = 1e-10
    normals = normals / norms
    face_areas = norms.flatten() / 2.0

    # Bed contact: faces near Z=0 with normal pointing down
    face_centers_z = (v0[:, 2] + v1[:, 2] + v2[:, 2]) / 3.0
    bed_mask = (face_centers_z < 0.1) & (normals[:, 2] < -0.9)
    bed_contact_area = float(np.sum(face_areas[bed_mask]))

    # Overhang area: faces with normal more than overhang_angle from vertical
    overhang_cos = np.cos(np.radians(overhang_angle_deg))
    # A face overhangs if its normal Z-component is negative (facing down)
    # and the angle from downward exceeds the threshold
    overhang_mask = (normals[:, 2] < -overhang_cos) & (~bed_mask)
    overhang_area = float(np.sum(face_areas[overhang_mask]))

    # Center of gravity height
    all_points = np.vstack([v0, v1, v2])
    cog_z = float(np.mean(all_points[:, 2]))
    max_z = float(all_points[:, 2].max())

    # Cross section at centroid height
    cross_area = slice_cross_section_area(
        all_points, normals, v0, v1, v2, cog_z
    )

    # Composite score (higher = better)
    total_area = float(np.sum(face_areas))
    norm_bed = bed_contact_area / max(total_area, 1e-10)
    norm_overhang = overhang_area / max(total_area, 1e-10)
    norm_cog = cog_z / max(max_z, 1e-10)
    norm_cross = cross_area / max(total_area, 1e-10)

    # Weights: bed contact (0.35), low overhangs (0.30), low CoG (0.15), large cross-section (0.20)
    score = (
        0.35 * norm_bed
        + 0.30 * (1.0 - norm_overhang)
        + 0.15 * (1.0 - norm_cog)
        + 0.20 * norm_cross
    )

    return {
        "rotation_matrix": [[round(v, 6) for v in row] for row in R.tolist()],
        "euler_angles_deg": rotation_to_euler(R),
        "bed_contact_area_mm2": round(bed_contact_area, 2),
        "overhang_area_mm2": round(overhang_area, 2),
        "cross_section_at_centroid_mm2": round(cross_area, 2),
        "cog_height_mm": round(cog_z, 2),
        "model_height_mm": round(max_z, 2),
        "score": round(float(score), 4),
    }


def find_optimal_orientation(stl_path: str, n_samples: int = 200,
                             overhang_angle: float = 45.0) -> dict:
    m = stl_mesh.Mesh.from_file(stl_path)
    directions = fibonacci_hemisphere(n_samples)

    results = []
    for d in directions:
        res = score_orientation(m, d, overhang_angle)
        results.append(res)

    results.sort(key=lambda r: r["score"], reverse=True)
    top3 = results[:3]

    return {
        "best_orientation": top3[0],
        "top_3": top3,
        "orientations_tested": n_samples,
        "overhang_angle_threshold": overhang_angle,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find optimal STL print orientation")
    parser.add_argument("stl_path", help="Path to STL file")
    parser.add_argument("--samples", type=int, default=200)
    parser.add_argument("--overhang-angle", type=float, default=45.0)
    args = parser.parse_args()
    result = find_optimal_orientation(args.stl_path, args.samples, args.overhang_angle)
    print(json.dumps(result, indent=2))
