"""
Detect thin walls in an STL mesh by ray-casting from each face inward
and measuring the distance to the nearest opposing surface.

Thin walls are regions where the mesh thickness is below a printable
threshold (default: 1.5x nozzle diameter).
"""
import argparse
import json
import sys
import numpy as np
from stl import mesh as stl_mesh


def ray_mesh_intersect_batch(origins: np.ndarray, directions: np.ndarray,
                             v0: np.ndarray, v1: np.ndarray, v2: np.ndarray,
                             source_faces: np.ndarray) -> np.ndarray:
    """Moller-Trumbore ray-triangle intersection for batched rays against all faces.

    For efficiency, we sample a subset of rays and test against all triangles.
    Returns the nearest hit distance for each ray (np.inf if no hit).
    """
    n_rays = len(origins)
    n_faces = len(v0)
    hit_distances = np.full(n_rays, np.inf)

    # Process in chunks to avoid memory explosion
    chunk_size = min(500, n_rays)
    for ray_start in range(0, n_rays, chunk_size):
        ray_end = min(ray_start + chunk_size, n_rays)
        batch_origins = origins[ray_start:ray_end]
        batch_dirs = directions[ray_start:ray_end]
        batch_src = source_faces[ray_start:ray_end]

        for ri in range(len(batch_origins)):
            o = batch_origins[ri]
            d = batch_dirs[ri]
            src = batch_src[ri]

            # Vectorized Moller-Trumbore against all triangles
            e1 = v1 - v0  # (n_faces, 3)
            e2 = v2 - v0
            h = np.cross(np.broadcast_to(d, (n_faces, 3)), e2)
            a = np.einsum("ij,ij->i", e1, h)

            valid = np.abs(a) > 1e-8
            f = np.zeros(n_faces)
            f[valid] = 1.0 / a[valid]

            s = np.broadcast_to(o, (n_faces, 3)) - v0
            u = f * np.einsum("ij,ij->i", s, h)

            valid &= (u >= 0.0) & (u <= 1.0)

            q = np.cross(s, e1)
            v = f * np.einsum("ij,ij->i", np.broadcast_to(d, (n_faces, 3)), q)

            valid &= (v >= 0.0) & (u + v <= 1.0)

            t = f * np.einsum("ij,ij->i", e2, q)
            valid &= t > 0.01  # small offset to avoid self-intersection

            # Exclude source face
            valid[src] = False

            if np.any(valid):
                hit_distances[ray_start + ri] = np.min(t[valid])

    return hit_distances


def detect_thin_walls(stl_path: str, min_thickness: float = 0.6,
                      nozzle_diameter: float = 0.4, max_sample: int = 2000) -> dict:
    m = stl_mesh.Mesh.from_file(stl_path)
    v0 = m.vectors[:, 0, :]
    v1 = m.vectors[:, 1, :]
    v2 = m.vectors[:, 2, :]
    n_faces = len(v0)

    # Compute face normals
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

    # Sample faces if too many (weighted by area for better coverage)
    if n_faces > max_sample:
        probs = face_areas / face_areas.sum()
        sample_idx = np.random.choice(n_faces, size=max_sample, replace=False, p=probs)
    else:
        sample_idx = np.arange(n_faces)

    # Cast rays inward (inverted normal)
    ray_origins = centroids[sample_idx] - normals[sample_idx] * 0.005  # tiny offset inward
    ray_dirs = -normals[sample_idx]

    distances = ray_mesh_intersect_batch(
        ray_origins, ray_dirs, v0, v1, v2, sample_idx
    )

    # Find thin faces
    thin_mask = distances < min_thickness
    thin_indices = sample_idx[thin_mask]
    thin_distances = distances[thin_mask]
    thin_areas_arr = face_areas[thin_indices]

    thin_area = float(np.sum(thin_areas_arr))
    min_detected = float(np.min(thin_distances)) if len(thin_distances) > 0 else None

    # Cluster thin faces into regions (simple: by proximity of centroids)
    regions = []
    if len(thin_indices) > 0:
        thin_centroids = centroids[thin_indices]
        thin_dists = thin_distances

        # Simple clustering: group faces within 2mm of each other
        visited = np.zeros(len(thin_indices), dtype=bool)
        for i in range(len(thin_indices)):
            if visited[i]:
                continue
            dists_to_i = np.linalg.norm(thin_centroids - thin_centroids[i], axis=1)
            cluster_mask = (dists_to_i < 2.0) & (~visited)
            visited[cluster_mask] = True

            cluster_faces = thin_indices[cluster_mask]
            cluster_thicknesses = thin_dists[cluster_mask]
            cluster_areas = face_areas[cluster_faces]

            regions.append({
                "face_count": int(len(cluster_faces)),
                "centroid": [round(v, 2) for v in centroids[cluster_faces].mean(axis=0).tolist()],
                "min_thickness_mm": round(float(cluster_thicknesses.min()), 3),
                "avg_thickness_mm": round(float(cluster_thicknesses.mean()), 3),
                "area_mm2": round(float(cluster_areas.sum()), 2),
            })
        regions.sort(key=lambda r: r["min_thickness_mm"])

    # Recommendation
    rec = "No thin walls detected." if not regions else ""
    if regions:
        if min_detected and min_detected < nozzle_diameter:
            rec = (f"WARNING: Thinnest wall ({min_detected:.2f}mm) is below nozzle "
                   f"diameter ({nozzle_diameter}mm). These features will likely not print. "
                   f"Consider: enable 'Detect thin wall' in slicer, or thicken the model.")
        elif min_detected and min_detected < min_thickness:
            rec = (f"Thin walls detected ({min_detected:.2f}mm). Enable 'Detect thin wall' "
                   f"in slicer settings. Consider reducing layer height to improve thin wall quality.")

    return {
        "thin_regions": regions,
        "total_thin_area_mm2": round(thin_area, 2),
        "thin_area_pct": round(thin_area / max(total_area, 1e-10) * 100, 2),
        "min_detected_thickness_mm": round(min_detected, 3) if min_detected else None,
        "threshold_mm": min_thickness,
        "nozzle_diameter_mm": nozzle_diameter,
        "faces_sampled": len(sample_idx),
        "recommendation": rec,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect thin walls in STL")
    parser.add_argument("stl_path", help="Path to STL file")
    parser.add_argument("--min-thickness", type=float, default=0.6)
    parser.add_argument("--nozzle", type=float, default=0.4)
    args = parser.parse_args()
    result = detect_thin_walls(args.stl_path, args.min_thickness, args.nozzle)
    print(json.dumps(result, indent=2))
