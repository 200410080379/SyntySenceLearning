"""Read-only LOD0 seam audit; standard-library Python, no Unreal required.

Run from any directory. Inputs are ../Data/{CandidateGeometry,Layout}.json.
The only output is ../Data/GeometryValidation.json. --self-test writes nothing.
"""

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHOR_DRIFT_CM = 0.01
HEIGHT_LIMIT_CM = 0.1
GAP_LIMIT_CM = 0.1
EPS = 1e-8


def rotate(x, y, yaw):
    """Use an exact quarter turn; tolerate only numerical drift in the angle."""
    turns = round(float(yaw) / 90)
    if abs(float(yaw) - turns * 90) > EPS:
        raise ValueError('rotation is not a quarter turn')
    return ((x, y), (-y, x), (-x, -y), (y, -x))[turns % 4]


def snap_border(value, size):
    if abs(value) <= AUTHOR_DRIFT_CM:
        return 0.0
    if abs(value - size) <= AUTHOR_DRIFT_CM:
        return float(size)
    return value


def mesh_profiles(mesh, yaw, pivot, size):
    """Intersect nonvertical triangle surfaces with each nominal tile border.

    Each output segment is (along_start, along_end, z_start, z_end).
    Actual local triangle Z is retained, including cracks and curb gutters.
    Rejecting vertical XY projections prevents wall faces from filling holes.
    Vertex drift <=0.01 cm at the nominal border is snapped before slicing.
    """
    profiles = {edge: [] for edge in ('west', 'east', 'south', 'north')}
    for section in mesh['sections']:
        vertices = []
        for x, y, z in section['vertices']:
            x, y = rotate(x, y, yaw)
            vertices.append((snap_border(x + pivot[0], size),
                             snap_border(y + pivot[1], size), z + pivot[2]))
        indices = section['triangles']
        if len(indices) % 3:
            raise ValueError('Triangle index count is not divisible by three')
        for start in range(0, len(indices), 3):
            tri = [vertices[k] for k in indices[start:start + 3]]
            a, b, c = tri
            xy_area = ((b[0] - a[0]) * (c[1] - a[1])
                       - (b[1] - a[1]) * (c[0] - a[0]))
            if abs(xy_area) <= EPS:
                continue
            for edge, axis, coordinate in [('west', 0, 0), ('east', 0, size),
                                            ('south', 1, 0), ('north', 1, size)]:
                if min(v[axis] for v in tri) > coordinate + EPS:
                    continue
                if max(v[axis] for v in tri) < coordinate - EPS:
                    continue
                points = []
                for first, second in zip(tri, tri[1:] + tri[:1]):
                    da, db = first[axis] - coordinate, second[axis] - coordinate
                    if abs(da) <= EPS:
                        points.append((first[1 - axis], first[2]))
                    if da * db < -EPS * EPS:
                        t = -da / (db - da)
                        points.append((first[1 - axis] + t * (second[1 - axis] - first[1 - axis]),
                                       first[2] + t * (second[2] - first[2])))
                if len(points) < 2:
                    continue
                points.sort()
                (lo, zlo), (hi, zhi) = points[0], points[-1]
                if hi - lo <= EPS or hi < 0 or lo > size:
                    continue
                slope = (zhi - zlo) / (hi - lo)
                left, right = max(0.0, lo), min(float(size), hi)
                if right - left > EPS:
                    profiles[edge].append((left, right, zlo + (left - lo) * slope,
                                           zlo + (right - lo) * slope))
    return {edge: sorted(set(segments)) for edge, segments in profiles.items()}


def value(segment, t):
    lo, hi, zlo, zhi = segment
    return zlo + (zhi - zlo) * ((t - lo) / (hi - lo))


def registered_segments(first, second, size):
    """Co-register authored nodes within horizontal tolerance, without flattening Z."""
    nodes = sorted(set([0.0, float(size)] + [t for s in first + second for t in s[:2]]))
    groups = []
    for node in nodes:
        if groups and node - groups[-1][0] <= AUTHOR_DRIFT_CM:
            groups[-1].append(node)
        else:
            groups.append([node])
    mapping = {}
    for group in groups:
        representative = (0.0 if 0.0 in group else
                          float(size) if float(size) in group else sum(group) / len(group))
        mapping.update((node, representative) for node in group)
    def adjusted(segments):
        return [(mapping[a], mapping[b], za, zb) for a, b, za, zb in segments
                if mapping[b] - mapping[a] > EPS]
    return adjusted(first), adjusted(second)


def envelope_nodes(segments):
    """All segment ends and possible upper-envelope changes (line intersections)."""
    nodes = {t for s in segments for t in s[:2]}
    for index, a in enumerate(segments):
        for b in segments[index + 1:]:
            left, right = max(a[0], b[0]), min(a[1], b[1])
            if right - left <= EPS:
                continue
            dl, dr = value(a, left) - value(b, left), value(a, right) - value(b, right)
            if dl * dr < 0:
                nodes.add(left - dl * (right - left) / (dr - dl))
    return nodes


def merge_intervals(intervals):
    result = []
    for left, right in sorted(intervals):
        if result and left <= result[-1][1] + EPS:
            result[-1][1] = max(result[-1][1], right)
        else:
            result.append([left, right])
    return result


def compare_profiles(first, second, size):
    first, second = registered_segments(first, second, size)
    nodes = sorted({0.0, float(size)} | envelope_nodes(first) | envelope_nodes(second))
    maximum = 0.0
    worst = None
    holes = {'first': [], 'second': []}
    mismatch_intervals = []
    sample_count = 0
    for left, right in zip(nodes, nodes[1:]):
        if right - left <= EPS:
            continue
        mid = (left + right) / 2
        active_a = [s for s in first if s[0] < mid < s[1]]
        active_b = [s for s in second if s[0] < mid < s[1]]
        if not active_a:
            holes['first'].append((left, right))
        if not active_b:
            holes['second'].append((left, right))
        if not active_a or not active_b:
            continue
        # One-sided endpoint values retain vertical curb steps. On each open
        # interval the selected upper surface is linear: endpoint extrema are exact.
        top_a = max(active_a, key=lambda s: value(s, mid))
        top_b = max(active_b, key=lambda s: value(s, mid))
        deltas = []
        for t in (left, mid, right):
            za, zb = value(top_a, t), value(top_b, t)
            delta = abs(za - zb)
            deltas.append(delta)
            sample_count += 1
            if worst is None or delta > maximum:
                maximum = delta
                worst = {'along_cm': t, 'first_z_cm': za, 'second_z_cm': zb,
                         'delta_cm': delta, 'interval_cm': [left, right]}
        if max(deltas) > HEIGHT_LIMIT_CM + EPS:
            mismatch_intervals.append((left, right))
    holes = {key: merge_intervals(intervals) for key, intervals in holes.items()}
    largest_gap = max((hi - lo for spans in holes.values() for lo, hi in spans), default=0.0)
    return {'passed': maximum <= HEIGHT_LIMIT_CM + EPS and largest_gap <= GAP_LIMIT_CM + EPS,
            'max_height_difference_cm': maximum, 'maximum_uncovered_span_cm': largest_gap,
            'worst_height_sample': worst, 'uncovered_spans_cm': holes,
            'height_mismatch_intervals_cm': merge_intervals(mismatch_intervals),
            'profile_segment_counts': [len(first), len(second)],
            'comparison_node_count': len(nodes), 'height_sample_count': sample_count}


def tile_brief(tile):
    return {key: tile[key] for key in ('i', 'j', 'mesh', 'name', 'yaw', 'location') if key in tile}


def audit(layout, geometry):
    size, count = float(layout['cell_size_cm']), int(layout['grid_size'])
    origin = layout['origin_cm']
    cells = defaultdict(list)
    errors = []
    for tile in layout['tiles']:
        i, j = tile['i'], tile['j']
        if not isinstance(i, int) or not isinstance(j, int) or not (0 <= i < count and 0 <= j < count):
            errors.append({'reason': 'tile outside declared integer grid', 'tile': tile_brief(tile)})
            continue
        cells[i, j].append(tile)
    missing = [[i, j] for i in range(count) for j in range(count) if (i, j) not in cells]
    duplicates = [{'cell': list(cell), 'tiles': [tile_brief(t) for t in tiles]}
                  for cell, tiles in sorted(cells.items()) if len(tiles) > 1]
    profiles, cache = {}, {}
    for cell, tiles in sorted(cells.items()):
        if len(tiles) != 1:
            continue
        tile = tiles[0]
        try:
            yaw = float(tile['yaw']) % 360
            if abs(yaw - round(yaw / 90) * 90) > EPS:
                raise ValueError('rotation is not a quarter turn')
            if tile.get('scale', [1, 1, 1]) != [1, 1, 1]:
                raise ValueError('scale is not [1,1,1]')
            pivot = tuple(tile['location'][k] - (origin[k] + cell[k] * size if k < 2 else 0)
                          for k in range(3))
            rx, ry = rotate(-size / 2, -size / 2, yaw)
            error = max(abs(pivot[0] + rx - size / 2), abs(pivot[1] + ry - size / 2))
            if error > AUTHOR_DRIFT_CM:
                raise ValueError('local (-250,-250) center misses nominal grid center by %.6f cm' % error)
            key = (tile['mesh'], yaw, pivot)
            if key not in cache:
                cache[key] = mesh_profiles(geometry[tile['mesh']], yaw, pivot, size)
            profiles[cell] = cache[key]
        except (KeyError, ValueError, TypeError, IndexError) as exc:
            errors.append({'reason': str(exc), 'tile': tile_brief(tile)})
    seams, groups = [], {}
    for cell in sorted(profiles):
        i, j = cell
        for other, first_edge, second_edge, axis in [((i + 1, j), 'east', 'west', 'X'),
                                                    ((i, j + 1), 'north', 'south', 'Y')]:
            if other not in profiles:
                continue
            first, second = cells[cell][0], cells[other][0]
            result = compare_profiles(profiles[cell][first_edge], profiles[other][second_edge], size)
            along_start = origin[1] + j * size if axis == 'X' else origin[0] + i * size
            cross = origin[0] + (i + 1) * size if axis == 'X' else origin[1] + (j + 1) * size
            seam = {'axis': axis, 'constant_coordinate_cm': cross,
                    'along_world_range_cm': [along_start, along_start + size],
                    'first': tile_brief(first), 'second': tile_brief(second),
                    'first_edge': first_edge, 'second_edge': second_edge, **result}
            if result['worst_height_sample'] is not None:
                t = result['worst_height_sample']['along_cm'] + along_start
                seam['worst_world_xy_cm'] = [cross, t] if axis == 'X' else [t, cross]
            seams.append(seam)
            label = '%s@%s:%s | %s@%s:%s' % (first.get('name', first['mesh']), first['yaw'], first_edge,
                                            second.get('name', second['mesh']), second['yaw'], second_edge)
            group = groups.setdefault(label, {'seam_count': 0, 'failed_seam_count': 0,
                                               'max_height_difference_cm': 0.0,
                                               'maximum_uncovered_span_cm': 0.0, 'example_cell_pairs': []})
            group['seam_count'] += 1
            group['failed_seam_count'] += not result['passed']
            for metric in ('max_height_difference_cm', 'maximum_uncovered_span_cm'):
                group[metric] = max(group[metric], result[metric])
            if len(group['example_cell_pairs']) < 3:
                group['example_cell_pairs'].append([list(cell), list(other)])
    expected_seams = 2 * count * (count - 1)
    failures = [seam for seam in seams if not seam['passed']]
    coverage_ok = not (missing or duplicates or errors) and len(cells) == count * count
    passed = coverage_ok and len(seams) == expected_seams and not failures
    return {'passed': passed, 'units': 'centimeters',
            'method': 'LOD0 triangle-plane sections at nominal borders; XY drift registration; '
                      'piecewise linear upper envelopes evaluated at both meshes nodes, line crossings '
                      'and one-sided endpoints, with midpoint coverage tests.',
            'tolerances_cm': {'author_horizontal_vertex_drift': AUTHOR_DRIFT_CM,
                              'height_difference': HEIGHT_LIMIT_CM, 'uncovered_span': GAP_LIMIT_CM},
            'limits': ['Checks adjacent tile seams and declared grid occupancy, not arbitrary holes inside a mesh.',
                       'Includes sculpted cracks, raised curb and gutters in actual triangle Z; no flattening to actor Z.',
                       'Only nonvertical XY-projected triangle surfaces count as floor coverage.',
                       'Does not validate collision, UV continuity, shading, draw order or outer-edge scenery.'],
            'coverage': {'grid_size': count, 'expected_tile_count': count * count,
                         'input_tile_count': len(layout['tiles']), 'occupied_cell_count': len(cells),
                         'missing_cells': missing, 'duplicate_cells': duplicates, 'errors': errors},
            'summary': {'expected_adjacent_seams': expected_seams, 'checked_adjacent_seams': len(seams),
                        'failed_seam_count': len(failures),
                        'maximum_height_difference_cm': max((s['max_height_difference_cm'] for s in seams), default=None),
                        'maximum_uncovered_span_cm': max((s['maximum_uncovered_span_cm'] for s in seams), default=None),
                        'unique_mesh_yaw_profile_count': len(cache)},
            'pair_groups': groups, 'failures': failures, 'seams': seams}


def self_test():
    # A near-90 value must round to one turn instead of truncating to zero.
    assert rotate(2, 3, 90 - 1e-10) == (-3, 2)
    assert rotate(2, 3, -90 + 1e-10) == (3, -2)
    try:
        rotate(2, 3, 45)
    except ValueError:
        pass
    else:
        raise AssertionError('Non-quarter-turn angle was accepted')
    # Raised matching curbs pass; shifted curbs, height steps and absent surfaces fail.
    curb = [(0, 10, 0, 7), (10, 30, 7, 7), (30, 40, 7, -23), (40, 50, -23, 0)]
    assert compare_profiles(curb, curb, 50)['passed']
    assert not compare_profiles(curb, [(0, 50, 0, 0)], 50)['passed']
    assert not compare_profiles([(0, 50, 0, 0)], [(0, 50, 0.101, 0.101)], 50)['passed']
    hole = compare_profiles([(0, 24, 0, 0), (25, 50, 0, 0)], [(0, 50, 0, 0)], 50)
    assert not hole['passed'] and hole['maximum_uncovered_span_cm'] == 1
    drifting = [(a + (0.005 if a not in (0, 50) else 0),
                 b + (0.005 if b not in (0, 50) else 0), za, zb) for a, b, za, zb in curb]
    assert compare_profiles(curb, drifting, 50)['passed']
    crossing = compare_profiles([(0, 50, 0, 10), (0, 50, 10, 0)], [(0, 50, 10, 10)], 50)
    assert abs(crossing['max_height_difference_cm'] - 5) < EPS
    plane = {'sections': [{'vertices': [[-500, -500, 3], [0, -500, 3], [0, 0, 3], [-500, 0, 3]],
                            'triangles': [0, 1, 2, 0, 2, 3]}]}
    for yaw in (0, 90, 180, 270):
        rx, ry = rotate(-250, -250, yaw)
        profiles = mesh_profiles(plane, yaw, (250 - rx, 250 - ry, 0), 500)
        assert all(compare_profiles(s, [(0, 500, 3, 3)], 500)['passed'] for s in profiles.values())
    print('SELF_TEST_PASS: sculpted profile, step, hole, horizontal drift, envelope crossing, four rotations')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    geometry_path, layout_path = ROOT / 'Data/CandidateGeometry.json', ROOT / 'Data/Layout.json'
    geometry_raw, layout_raw = geometry_path.read_bytes(), layout_path.read_bytes()
    result = audit(json.loads(layout_raw), json.loads(geometry_raw))
    result['inputs'] = {p.name: {'path': str(p), 'sha256': hashlib.sha256(raw).hexdigest()}
                        for p, raw in [(geometry_path, geometry_raw), (layout_path, layout_raw)]}
    output = ROOT / 'Data/GeometryValidation.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'passed': result['passed'], 'output': str(output), **result['summary']}, ensure_ascii=False))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
