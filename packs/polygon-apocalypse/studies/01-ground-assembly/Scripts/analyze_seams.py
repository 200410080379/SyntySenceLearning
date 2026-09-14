"""Reproduce seam evidence from exported mesh triangles; requires only Python.

Run: python Scripts/analyze_seams.py
Reads Data/SourceGroundGeometry.json and writes Data/SeamAnalysis.json.
No Unreal imports, asset writes, or third-party dependencies are used.
"""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Data" / "SourceGroundGeometry.json"
OUTPUT = ROOT / "Data" / "SeamAnalysis.json"
PLANE_EPSILON = 0.00001
EDGE_EPSILON = 0.002


def unique_points(points, decimals=5):
    return sorted(set(tuple(round(value, decimals) for value in point)
                      for point in points))


def cross_section(mesh, axis, coordinate):
    """Intersect all triangles with a constant local X or Y plane.

    Return segments as ((other horizontal coordinate, Z), (..., Z)).
    These include every intersected surface, including overlapping debris
    and undersides. They are geometry evidence, not a walkability test.
    """
    result = []
    horizontal_axis = 1 - axis
    for section in mesh["sections"]:
        vertices = section["vertices"]
        indices = section["triangles"]
        if len(indices) % 3:
            raise ValueError("Triangle index count is not divisible by three")
        for start in range(0, len(indices), 3):
            triangle = [vertices[i] for i in indices[start:start + 3]]
            points = []
            for first, second in zip(triangle, triangle[1:] + triangle[:1]):
                first_distance = first[axis] - coordinate
                second_distance = second[axis] - coordinate
                if abs(first_distance) <= PLANE_EPSILON:
                    points.append((first[horizontal_axis], first[2]))
                if first_distance * second_distance < 0:
                    fraction = -first_distance / (second[axis] - first[axis])
                    points.append(tuple(
                        first[i] + fraction * (second[i] - first[i])
                        for i in (horizontal_axis, 2)
                    ))
            points = unique_points(points)
            if len(points) >= 2 and points[0] != points[-1]:
                result.append((points[0], points[-1]))
    return sorted(set(result))


def heights_at(segments, coordinate):
    """All intersections of a cross-section with a horizontal position."""
    values = []
    for first, second in segments:
        if abs(first[0] - coordinate) <= EDGE_EPSILON:
            values.append(first[1])
        if abs(second[0] - coordinate) <= EDGE_EPSILON:
            values.append(second[1])
        if min(first[0], second[0]) < coordinate < max(first[0], second[0]):
            fraction = (coordinate - first[0]) / (second[0] - first[0])
            values.append(first[1] + fraction * (second[1] - first[1]))
    return sorted(set(round(value, 5) for value in values))


def horizontal_positive_runs(segments):
    """Merge contiguous horizontal segments above Z=0; no surface inference."""
    candidates = []
    for first, second in segments:
        if (abs(first[1] - second[1]) <= PLANE_EPSILON
                and first[1] > 0.1 and second[0] - first[0] > 0.001):
            candidates.append([first[0], second[0], first[1]])
    result = []
    for left, right, z in sorted(candidates):
        if (result and abs(result[-1]["z"] - z) <= PLANE_EPSILON
                and left <= result[-1]["local_x_range"][1] + EDGE_EPSILON):
            result[-1]["local_x_range"][1] = max(
                result[-1]["local_x_range"][1], right)
        else:
            result.append({"local_x_range": [left, right], "z": z})
    return result


def boundary_profile(mesh, local_y):
    """Vertices on a longitudinal end plane, expressed as local (X, Z)."""
    return unique_points(
        (vertex[0], vertex[2])
        for section in mesh["sections"]
        for vertex in section["vertices"]
        if abs(vertex[1] - local_y) <= EDGE_EPSILON
    )


def profile_distance(first, second):
    """Symmetric nearest-point distance using max absolute coordinate delta."""
    if not first or not second:
        raise ValueError("Cannot compare an empty boundary profile")
    def directed(a, b):
        return max(min(max(abs(p[0] - q[0]), abs(p[1] - q[1]))
                       for q in b) for p in a)
    return round(max(directed(first, second), directed(second, first)), 6)


def transformed_section(mesh, location, yaw, world_y):
    """Support the quarter-turn, unit-scale source placements used below."""
    if yaw == 0:
        local_segments = cross_section(mesh, 1, world_y - location[1])
        return sorted((tuple((location[0] + p[0], location[2] + p[1])
                             for p in segment)) for segment in local_segments)
    if yaw == 90:
        local_segments = cross_section(mesh, 0, world_y - location[1])
        return sorted(tuple(sorted((location[0] - p[0], location[2] + p[1])
                                   for p in segment))
                      for segment in local_segments)
    raise ValueError("Only yaw 0 and 90 are needed for this source sample")


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(
            'Local source geometry is missing. Open the original Apocalypse Demo '
            'in Unreal and run Scripts/export_source_ground.py first: ' + str(SOURCE))
    raw = SOURCE.read_bytes()
    meshes = {mesh["name"]: mesh for mesh in json.loads(raw).values()}
    world_y = -1750
    placements = [
        ("SM_Env_Sidewalk_01", [-900, -1500, 0], 0),
        ("SM_Env_Sidewalk_Panel_01", [-400, -1500, 0], 0),
        ("SM_Env_Road_01", [-400, -1500, 0], 90),
    ]
    placed = []
    for name, location, yaw in placements:
        segments = transformed_section(meshes[name], location, yaw, world_y)
        horizontal_values = [p[0] for segment in segments for p in segment]
        low, high = min(horizontal_values), max(horizontal_values)
        placed.append({
            "mesh": name, "world_location": location, "yaw_degrees": yaw,
            "scale": [1, 1, 1], "world_x_extent_at_slice": [low, high],
            "left_boundary_z": heights_at(segments, low),
            "right_boundary_z": heights_at(segments, high),
            "slice_segment_count": len(segments),
            "all_slice_points_z_zero": all(abs(p[1]) <= PLANE_EPSILON
                                          for segment in segments for p in segment),
        })

    module_sections = {}
    profiles = {}
    for name in ("SM_Env_Sidewalk_01", "SM_Env_Sidewalk_Panel_01",
                 "SM_Env_Sidewalk_Straight_01", "SM_Env_Sidewalk_Edge_01"):
        segments = cross_section(meshes[name], 1, -250)
        points = [point for segment in segments for point in segment]
        lowest_z = min(point[1] for point in points)
        module_sections[name] = {
            "local_y": -250,
            "local_x_extent": [min(p[0] for p in points), max(p[0] for p in points)],
            "horizontal_positive_runs": horizontal_positive_runs(segments),
            "lowest_intersection_points_xz": unique_points(
                point for point in points if abs(point[1] - lowest_z) <= PLANE_EPSILON),
        }
        profiles[name] = {
            str(y): boundary_profile(meshes[name], y) for y in (-500, 0)
        }

    comparisons = []
    panel = "SM_Env_Sidewalk_Panel_01"
    straight = "SM_Env_Sidewalk_Straight_01"
    for first_name, first_y, second_name, second_y in [
        (panel, -500, panel, 0), (straight, -500, straight, 0),
        (panel, -500, straight, -500), (panel, 0, straight, 0),
        (panel, 0, straight, -500), (straight, 0, panel, -500),
    ]:
        delta = profile_distance(profiles[first_name][str(first_y)],
                                 profiles[second_name][str(second_y)])
        comparisons.append({
            "first": {"mesh": first_name, "local_y": first_y},
            "second": {"mesh": second_name, "local_y": second_y},
            "max_nearest_vertex_delta_cm": delta,
            "matches_within_0_01_cm": delta <= 0.01,
        })

    evidence = {
        "source_file": "Data/SourceGroundGeometry.json",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "units": "centimeters",
        "method": "Triangle-plane intersections and source boundary vertices; no bounding-box heights.",
        "limits": [
            "All intersected triangles are included; this is not a collision or walkability analysis.",
            "World placements below are fixed source-demo samples previously read from SourceGroundPlacements.json.",
            "Panel/Straight transverse X borders return to Z=0; longitudinal Y ends retain the curb profile.",
            "Nearest boundary-vertex agreement supports matching geometry; it does not test UVs, shading, or materials.",
        ],
        "world_y_slice": world_y,
        "source_demo_row": placed,
        "seams": [
            {"world_x": -900, "first": placements[0][0], "second": placements[1][0],
             "first_z": placed[0]["right_boundary_z"], "second_z": placed[1]["left_boundary_z"]},
            {"world_x": -400, "first": placements[1][0], "second": placements[2][0],
             "first_z": placed[1]["right_boundary_z"], "second_z": placed[2]["left_boundary_z"]},
        ],
        "local_cross_sections": module_sections,
        "boundary_profiles_xz": {
            name: {y: unique_points(points, 3) for y, points in ends.items()}
            for name, ends in profiles.items()
        },
        "panel_straight_profile_comparisons": comparisons,
    }
    OUTPUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT), "seams": evidence["seams"],
        "maximum_profile_delta_cm": max(item["max_nearest_vertex_delta_cm"] for item in comparisons),
        "all_profiles_match_within_0_01_cm": all(item["matches_within_0_01_cm"] for item in comparisons),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
