"""
Master STL print optimizer — runs all analysis skills and produces
a unified print recommendation.
"""
import argparse
import json
import os
import sys

# Add parent paths so we can import sibling skill scripts
SKILLS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.path.insert(0, os.path.join(SKILLS_DIR, "stl-centroid", "scripts"))
sys.path.insert(0, os.path.join(SKILLS_DIR, "stl-bounding-box", "scripts"))
sys.path.insert(0, os.path.join(SKILLS_DIR, "stl-optimal-orientation", "scripts"))
sys.path.insert(0, os.path.join(SKILLS_DIR, "stl-overhang-detection", "scripts"))
sys.path.insert(0, os.path.join(SKILLS_DIR, "stl-thin-wall-detection", "scripts"))
sys.path.insert(0, os.path.join(SKILLS_DIR, "stl-support-analysis", "scripts"))

from compute_centroid import compute_centroid
from compute_bbox import compute_bbox
from find_orientation import find_optimal_orientation
from detect_overhangs import detect_overhangs
from detect_thin_walls import detect_thin_walls
from analyze_support import analyze_support


def optimize_print(stl_path: str, nozzle: float = 0.4,
                   bed_x: float = 256.0, bed_y: float = 256.0,
                   bed_z: float = 256.0) -> dict:
    # Run all analyses
    bbox = compute_bbox(stl_path, bed_x, bed_y, bed_z)
    centroid = compute_centroid(stl_path)
    orientation = find_optimal_orientation(stl_path, n_samples=200)
    overhangs = detect_overhangs(stl_path)
    thin_walls = detect_thin_walls(stl_path, min_thickness=nozzle * 1.5, nozzle_diameter=nozzle)
    supports = analyze_support(stl_path)

    # Build recommendations
    warnings = []
    settings = {}

    # Layer height
    has_thin = len(thin_walls["thin_regions"]) > 0
    if has_thin and thin_walls["min_detected_thickness_mm"] and thin_walls["min_detected_thickness_mm"] < nozzle:
        settings["layer_height_mm"] = 0.12
        warnings.append(f"Thin walls detected ({thin_walls['min_detected_thickness_mm']:.2f}mm) below nozzle diameter. Using fine layer height.")
    elif has_thin:
        settings["layer_height_mm"] = 0.16
        warnings.append("Thin features present — reduced layer height recommended.")
    else:
        settings["layer_height_mm"] = 0.20

    # Support type
    oh_pct = overhangs["overhang_area_pct"]
    if oh_pct < 3:
        settings["support_type"] = "none"
    elif oh_pct < 15:
        settings["support_type"] = "tree"
        settings["support_density_pct"] = 10
    else:
        settings["support_type"] = "grid"
        settings["support_density_pct"] = 15
        warnings.append(f"High overhang area ({oh_pct:.1f}%). Grid supports recommended.")

    # Infill
    aspect = bbox["aspect_ratio"]
    if aspect > 3:
        settings["infill_pct"] = 25
        warnings.append(f"High aspect ratio ({aspect:.1f}). Increased infill for stability.")
    elif bbox["volume_mm3"] > 100000:
        settings["infill_pct"] = 10
    else:
        settings["infill_pct"] = 15

    # Speed
    if has_thin:
        settings["print_speed"] = "reduced (thin walls)"
    else:
        settings["print_speed"] = "normal"

    # Fit check
    if not bbox["fits_bed"]:
        dims = bbox["dimensions_mm"]
        warnings.append(
            f"Model does NOT fit build volume! "
            f"Dimensions: {dims['width']:.1f} x {dims['depth']:.1f} x {dims['height']:.1f}mm "
            f"vs bed {bed_x} x {bed_y} x {bed_z}mm. "
            f"Scale down or split the model."
        )

    # Bridge warning
    if overhangs["max_bridge_distance_mm"] > 10:
        warnings.append(
            f"Long bridge detected ({overhangs['max_bridge_distance_mm']:.1f}mm). "
            f"Enable bridge detection in slicer and reduce bridge speed."
        )

    # Summary
    if not warnings:
        summary = "Model is straightforward to print with default settings."
    elif len(warnings) <= 2 and bbox["fits_bed"]:
        summary = "Model is printable with minor adjustments (see warnings)."
    else:
        summary = "Model requires careful setup — review warnings before printing."

    return {
        "summary": summary,
        "dimensions": bbox,
        "centroid": centroid,
        "recommended_orientation": orientation["best_orientation"],
        "overhang_analysis": {
            "severity": overhangs["severity"],
            "overhang_area_pct": overhangs["overhang_area_pct"],
            "max_bridge_mm": overhangs["max_bridge_distance_mm"],
        },
        "thin_wall_analysis": {
            "has_thin_walls": has_thin,
            "min_thickness_mm": thin_walls["min_detected_thickness_mm"],
            "thin_area_pct": thin_walls["thin_area_pct"],
            "region_count": len(thin_walls["thin_regions"]),
        },
        "support_estimate": {
            "volume_mm3": supports["support_volume_mm3"],
            "filament_m": supports["support_filament_m"],
            "time_min": supports["estimated_support_time_min"],
            "ratio": supports["support_to_part_ratio"],
        },
        "recommended_settings": settings,
        "warnings": warnings,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Full STL print optimization")
    parser.add_argument("stl_path", help="Path to STL file")
    parser.add_argument("--nozzle", type=float, default=0.4)
    parser.add_argument("--bed-x", type=float, default=256.0)
    parser.add_argument("--bed-y", type=float, default=256.0)
    parser.add_argument("--bed-z", type=float, default=256.0)
    args = parser.parse_args()
    result = optimize_print(args.stl_path, args.nozzle, args.bed_x, args.bed_y, args.bed_z)
    print(json.dumps(result, indent=2))
