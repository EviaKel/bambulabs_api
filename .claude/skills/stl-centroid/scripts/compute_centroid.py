"""
Compute the volume-weighted centroid of an STL mesh.

Uses signed tetrahedra decomposition: each triangle + origin forms a
tetrahedron whose signed volume contributes to the center of mass.
Falls back to area-weighted face centroid for non-watertight meshes.
"""
import json
import sys
import numpy as np
from stl import mesh as stl_mesh


def compute_centroid(stl_path: str) -> dict:
    m = stl_mesh.Mesh.from_file(stl_path)
    v0 = m.vectors[:, 0, :]
    v1 = m.vectors[:, 1, :]
    v2 = m.vectors[:, 2, :]

    # Signed tetrahedron volumes (origin -> triangle)
    cross = np.cross(v1, v2)
    signed_volumes = np.einsum("ij,ij->i", v0, cross) / 6.0
    total_volume = np.sum(signed_volumes)

    if abs(total_volume) < 1e-10:
        # Non-watertight fallback: area-weighted face centroids
        face_centroids = (v0 + v1 + v2) / 3.0
        edges1 = v1 - v0
        edges2 = v2 - v0
        areas = np.linalg.norm(np.cross(edges1, edges2), axis=1) / 2.0
        total_area = np.sum(areas)
        centroid = np.sum(areas[:, np.newaxis] * face_centroids, axis=0) / total_area
        method = "area-weighted (non-watertight)"
    else:
        tet_centroids = (v0 + v1 + v2) / 4.0
        centroid = np.sum(
            signed_volumes[:, np.newaxis] * tet_centroids, axis=0
        ) / total_volume
        method = "volume-weighted"

    return {
        "centroid": [round(c, 4) for c in centroid.tolist()],
        "volume_mm3": round(abs(float(total_volume)), 4),
        "method": method,
        "face_count": len(m.vectors),
        "vertex_count": len(m.vectors) * 3,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compute_centroid.py <stl_file>")
        sys.exit(1)
    result = compute_centroid(sys.argv[1])
    print(json.dumps(result, indent=2))
