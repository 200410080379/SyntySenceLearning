"""Read-only UE editor validation of the current StreetSlice world.

Run main(reloaded=True) only after the operator has saved and reopened the map.
This script does not save, reload, modify actors, or test navigation/gameplay.
Reports belong to the current project's Learning directory, outside this repo.
"""
import collections
import datetime
import hashlib
import json
import math
from pathlib import Path


LEVEL = '/Game/SyntySenceLearning/PolygonApocalypse/StreetSlice/L_StreetSlice'
LAND_MATERIAL = '/Game/SyntySenceLearning/PolygonApocalypse/StreetSlice/Materials/M_StreetLandscape.M_StreetLandscape'
ROUTES = [
    ('main_road', [200, -3000, 125], [200, 3000, 125]),
    ('shop_approach', [200, 700, 125], [900, 700, 125]),
    ('repair_approach', [200, -1300, 125], [1500, -1300, 125]),
    ('diner_approach', [200, -450, 125], [-800, -450, 125]),
    ('east_yard', [2000, -2700, 125], [3350, -2300, 125]),
    ('east_sidewalk', [650, -2400, 125], [650, 1500, 125]),
]


def main(reloaded=False):
    import unreal

    data_dir = Path(__file__).resolve().parents[1] / 'Data'
    output = (Path(unreal.Paths.project_dir()).resolve() / 'Learning' /
              'SyntySenceLearning/polygon-apocalypse/06-street-slice/Validation.json')
    report = {
        'schema_version': 1, 'read_only': True,
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'operator_declared_after_reload': bool(reloaded),
        'reload_performed_by_script': False, 'expected_map': LEVEL,
        'status': 'running', 'errors': [], 'source_counters': {},
        'scope': {
            'instances': 'STREET_ labels: mesh/materials/transform/folder/collision profile; decals include size.',
            'terrain': 'Landscape component count, assigned layer infos, material, and sampled Visibility traces.',
            'collision': 'Six simple Visibility capsule sweeps, radius 34 cm and half-height 88 cm, center Z 125 cm. Blockers are evidence, not an automatic failure of the scene.',
            'excluded': ['navigation', 'AI', 'player gameplay', 'all surface seams', 'visual art quality', 'unsampled collision'],
        },
        'tolerances': {'location_cm': 0.05, 'scale': 0.0001, 'rotation_degrees': 0.02, 'ground_z_cm': 0.1},
        'instances': [], 'ground_traces': [], 'capsule_traces': [],
    }

    def error(scope, detail, **extra):
        report['errors'].append(dict(scope=scope, detail=str(detail), **extra))

    def path(obj):
        return obj.get_path_name() if obj is not None else None

    def vec(v):
        return [float(v.x), float(v.y), float(v.z)]

    def rotation(r):
        return {n: float(getattr(r, n)) for n in ('pitch', 'yaw', 'roll')}

    def quat(r):
        # A consistent Euler-to-quaternion conversion handles equivalent Euler
        # representations, including the +/-180 wrap and vertical decals.
        p, y, r = (math.radians(r[n]) / 2 for n in ('pitch', 'yaw', 'roll'))
        cp, sp, cy, sy, cr, sr = math.cos(p), math.sin(p), math.cos(y), math.sin(y), math.cos(r), math.sin(r)
        return (sr*cp*cy-cr*sp*sy, cr*sp*cy+sr*cp*sy,
                cr*cp*sy-sr*sp*cy, cr*cp*cy+sr*sp*sy)

    def compare(row, actual, decal=False):
        for key in ('mesh', 'materials', 'material', 'folder', 'collision_profile'):
            if key in row and actual.get(key) != row[key]:
                error('instance_' + key, 'Mismatch', label=row['id'], expected=row[key], actual=actual.get(key))
        for key, tol in [('location', 0.05), ('scale', 0.0001), ('size', 0.05)]:
            if key in row:
                delta = max(abs(a-b) for a, b in zip(actual[key], row[key]))
                if delta > tol:
                    error('instance_' + key, 'Mismatch', label=row['id'], max_delta=delta, expected=row[key], actual=actual[key])
        qa, qb = quat(actual['rotation']), quat(row['rotation'])
        angle = math.degrees(2 * math.acos(min(1., abs(sum(a*b for a, b in zip(qa, qb))))))
        if angle > 0.02:
            error('instance_rotation', 'Mismatch', label=row['id'], delta_degrees=angle, expected=row['rotation'], actual=actual['rotation'])

    def decode(raw):
        if raw is None:
            return {'blocking_hit': False, 'returned_none': True}
        # Current UE returns HitResult or None; support the optional (hit, bool)
        # wrapper without ever interpreting an undecodable value as a pass.
        if isinstance(raw, (tuple, list)) and len(raw) == 2:
            candidates = [x for x in raw if hasattr(x, 'to_tuple')]
            if candidates:
                raw = candidates[0]
        t = raw.to_tuple() if hasattr(raw, 'to_tuple') else raw
        if not isinstance(t, (tuple, list)) or len(t) != 18 or not isinstance(t[0], bool):
            raise TypeError('Unexpected HitResult native-break schema: ' + repr(t))
        actor, component = t[9], t[10]
        return {'blocking_hit': t[0], 'initial_overlap': bool(t[1]),
                'time': float(t[2]), 'distance_cm': float(t[3]),
                'location': vec(t[4]), 'impact_point': vec(t[5]),
                'normal': vec(t[6]), 'impact_normal': vec(t[7]),
                'physical_material': path(t[8]), 'actor_path': path(actor),
                'actor_label': actor.get_actor_label() if actor else None,
                'actor_class': actor.get_class().get_name() if actor else None,
                'component_path': path(component),
                'native_break_field_count': len(t)}

    def line(world, start, end, complex_mode, ignored):
        return decode(unreal.SystemLibrary.line_trace_single(
            world, unreal.Vector(*start), unreal.Vector(*end),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, complex_mode,
            ignored, unreal.DrawDebugTrace.NONE))

    try:
        layouts = {}
        for name in ('Layout', 'Decals'):
            content = (data_dir / (name + '.json')).read_bytes()
            layouts[name] = json.loads(content.decode('utf-8-sig'))
            report[name.lower() + '_sha256'] = hashlib.sha256(content).hexdigest()
        rows, decals = layouts['Layout'], layouts['Decals']
        report['source_counters'] = {
            'layout_mesh_instances': len(rows), 'layout_unique_meshes': len({r['mesh'] for r in rows}),
            'layout_decals': len(decals),
        }
        expected = rows + decals
        counts = collections.Counter(r['id'] for r in expected)
        for label, count in counts.items():
            if count != 1:
                error('source_duplicate_label', count, label=label)
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        report['actual_world'] = path(world)
        if path(world) != LEVEL + '.L_StreetSlice':
            raise RuntimeError('Wrong current world; no scene queries performed')
        actors = list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
        by_label = collections.defaultdict(list)
        for actor in actors:
            if actor.get_actor_label().startswith('STREET_'):
                by_label[actor.get_actor_label()].append(actor)
        for label, group in by_label.items():
            if len(group) != 1:
                error('actual_duplicate_label', len(group), label=label)
            if label not in counts:
                error('unexpected_actor', label)
        actual_meshes = []
        actual_decals = 0
        for row in expected:
            label = row['id']
            if len(by_label.get(label, [])) != 1:
                error('missing_or_ambiguous_actor', label)
                continue
            a = by_label[label][0]
            try:
                actual = {'id': label, 'location': vec(a.get_actor_location()),
                          'rotation': rotation(a.get_actor_rotation()), 'scale': vec(a.get_actor_scale3d()),
                          'folder': str(a.get_folder_path()), 'class': a.get_class().get_name()}
                if 'mesh' in row:
                    if not isinstance(a, unreal.StaticMeshActor):
                        raise TypeError('Expected StaticMeshActor')
                    c = a.static_mesh_component
                    actual['mesh'] = path(c.get_editor_property('static_mesh'))
                    actual['materials'] = [path(c.get_material(i)) for i in range(c.get_num_materials())]
                    actual['collision_profile'] = str(c.get_collision_profile_name())
                    actual_meshes.append(actual['mesh'])
                else:
                    if not isinstance(a, unreal.DecalActor):
                        raise TypeError('Expected DecalActor')
                    c = a.get_component_by_class(unreal.DecalComponent)
                    actual['material'] = path(c.get_decal_material())
                    actual['size'] = vec(c.get_editor_property('decal_size'))
                    actual_decals += 1
                compare(row, actual)
                report['instances'].append(actual)
            except Exception as exc:
                error('instance_query', exc, label=label)
        report['actual_counters'] = {
            'street_labels': len(by_label), 'mesh_instances': len(actual_meshes),
            'unique_meshes': len(set(actual_meshes)), 'decals': actual_decals,
        }
        lands = [a for a in actors if isinstance(a, unreal.Landscape)]
        report['landscape_actor_count'] = len(lands)
        if len(lands) != 1:
            error('landscape_count', len(lands), expected=1)
        else:
            a = lands[0]
            infos = {str(k): path(v.get_editor_property('layer_info_obj'))
                     for k, v in a.get_editor_property('target_layers').items()}
            land = {'actor_path': path(a), 'location': vec(a.get_actor_location()),
                    'scale': vec(a.get_actor_scale3d()),
                    'components': len(a.get_components_by_class(unreal.LandscapeComponent)),
                    'material': path(a.get_editor_property('landscape_material')),
                    'target_layer_infos': infos}
            report['landscape'] = land
            if land['components'] != 4:
                error('landscape_components', land['components'], expected=4)
            if land['material'] != LAND_MATERIAL:
                error('landscape_material', land['material'], expected=LAND_MATERIAL)
            for name in ('Base', 'Dirt', 'Grass_02'):
                if not infos.get(name):
                    error('landscape_layer_info', 'Missing assigned info', layer=name)
        ignored_meshes = [a for a in actors if isinstance(a, unreal.StaticMeshActor)]
        report['ground_configuration'] = {
            'channel': 'Visibility / TRACE_TYPE_QUERY1', 'x_cm': 200,
            'y_cm': [-3000, 3000], 'step_cm': 200, 'start_z_cm': 600, 'end_z_cm': -100,
            'scene_expected_z_cm': 25, 'landscape_expected_z_cm': 24.21875,
            'landscape_only_ignored_static_mesh_actors': len(ignored_meshes),
            'planned_rays': 124,
        }
        for y in range(-3000, 3001, 200):
            for scope, ignored, expected_z in [('scene', [], 25.), ('landscape', ignored_meshes, 24.21875)]:
                for complex_mode in (False, True):
                    sample = dict(scope=scope, x=200, y=y, trace_complex=complex_mode, expected_z_cm=expected_z)
                    try:
                        sample['hit'] = line(world, [200, y, 600], [200, y, -100], complex_mode, ignored)
                        h = sample['hit']
                        sample['hit_height_matches_expected'] = bool(h['blocking_hit'] and abs(h['impact_point'][2]-expected_z) <= 0.1)
                        if h['blocking_hit']:
                            sample['z_delta_cm'] = h['impact_point'][2]-expected_z
                            sample['hit_is_landscape'] = h['actor_path'] in [path(a) for a in lands]
                    except Exception as exc:
                        sample['query_error'] = str(exc)
                        error('ground_trace', exc, sample={k: sample[k] for k in ('scope', 'x', 'y', 'trace_complex')})
                    report['ground_traces'].append(sample)
        for name, start, end in ROUTES:
            sample = dict(name=name, start=start, end=end, radius_cm=34, half_height_cm=88, trace_complex=False)
            try:
                sample['hit'] = decode(unreal.SystemLibrary.capsule_trace_single(
                    world, unreal.Vector(*start), unreal.Vector(*end), 34., 88.,
                    unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE))
            except Exception as exc:
                sample['query_error'] = str(exc)
                error('capsule_trace', exc, route=name)
            report['capsule_traces'].append(sample)
    except Exception as exc:
        error('verification_runtime', exc)
    report['sample_counts'] = {
        'ground_attempted': len(report['ground_traces']),
        'ground_decoded': sum('hit' in s for s in report['ground_traces']),
        'ground_blocking_hits': sum(s.get('hit', {}).get('blocking_hit', False) for s in report['ground_traces']),
        'ground_height_matches': sum(s.get('hit_height_matches_expected', False) for s in report['ground_traces']),
        'capsules_attempted': len(report['capsule_traces']),
        'capsules_decoded': sum('hit' in s for s in report['capsule_traces']),
        'capsules_blocked': sum(s.get('hit', {}).get('blocking_hit', False) for s in report['capsule_traces']),
    }
    report['error_count'] = len(report['errors'])
    report['status'] = 'completed_with_errors' if report['errors'] else 'completed'
    report['instance_and_landscape_structure_match'] = not report['errors']
    report['collision_outcome'] = 'See raw ground and capsule results; completion does not certify navigation or gameplay.'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('status', 'error_count', 'source_counters', 'sample_counts', 'operator_declared_after_reload')}, ensure_ascii=False))
    return report


if __name__ == '__main__':
    main()
