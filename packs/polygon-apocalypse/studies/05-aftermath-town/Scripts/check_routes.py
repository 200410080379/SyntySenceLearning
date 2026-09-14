"""Portable read-only Unreal editor collision queries for AftermathTown.

Run inside UE, never from the host Python interpreter::

    import runpy
    task = runpy.run_path('.../Scripts/check_routes.py')
    task['main']()
    del task

All Unreal imports/references live inside main() and its local helpers. No
source assets, component settings, actor transforms, world or save state are
changed. Only the task-owned JSON report is written.
"""


def main():
    import collections
    import datetime
    import hashlib
    import json
    import math
    import pathlib
    import time
    import traceback
    import unreal

    base = pathlib.Path(__file__).resolve().parents[1]
    output_root = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())) / 'SyntySenceLearning' / 'AftermathTown'
    destination = output_root / 'CollisionRoutes.json'
    start_time = time.perf_counter()
    report = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': (
            'Read-only queries against the current AftermathTown editor world. '
            'Visibility-channel vertical rays sample ground response with trace_complex '
            'False then True. Horizontal capsules sample three tracks in each named '
            '4 m corridor and the nine vehicle entrances. Capsules have radius 35 cm, '
            'half_height 88 cm and fixed centre Z=100 cm. This is a sampled human-size '
            'clearance query, not character movement, vehicle clearance, step/slope '
            'handling, NavMesh, AI reachability or a proof that every point of a 4 m '
            'wide band is clear. No actors are ignored.'
        ),
        'world': None,
        'run_status': 'started',
        'configuration': {
            'trace_channel_intent': 'Visibility',
            'trace_type_query': 'TRACE_TYPE_QUERY1',
            'draw_debug': 'NONE',
            'trace_complex_modes': [False, True],
            'ground_ray_z_cm': [200.0, -300.0],
            'ground_sample_step_cm': 250.0,
            'capsule_segment_max_length_cm': 500.0,
            'capsule_radius_cm': 35.0,
            'capsule_half_height_cm': 88.0,
            'capsule_center_z_cm': 100.0,
            'track_lateral_offsets_cm': [-150.0, 0.0, 150.0],
            'ignore_self': False,
            'actors_to_ignore': [],
        },
        'local_api_evidence': [
            'Engine/Source/Runtime/Engine/Classes/Kismet/KismetSystemLibrary.h:1270,1366: LineTraceSingle and CapsuleTraceSingle return bool plus OutHit; bTraceComplex selects simplified versus complex query.',
            'Engine/Plugins/Experimental/PythonScriptPlugin/Source/PythonScriptPlugin/Private/PyGenUtil.cpp:1152-1191: bool-return functions with output parameters return None for false, otherwise the packed outputs without bool. Single OutHit is directly a HitResult.',
            'Engine/Source/Runtime/Engine/Classes/Kismet/GameplayStatics.h:1078: BreakHitResult outputs blocking_hit, initial_overlap, time, distance, location, impact_point, normal, impact_normal, phys_mat, hit_actor, hit_component, hit_bone_name, bone_name, hit_item, element_index, face_index, trace_start, trace_end.',
            'Current UE Python runtime probe: GameplayStatics.break_hit_result is not exposed. HitResult.to_tuple() invokes its NativeBreakFunction and returns the 18 fields above; a ground hit was successfully decoded by the root agent.',
            'Engine/Source/Runtime/Engine/Private/Collision/CollisionProfile.cpp:373-377: Visibility then Camera are inserted as the built-in trace types; TRACE_TYPE_QUERY1 is Visibility.',
            'Engine/Source/Editor/StaticMeshEditor/Private/StaticMeshEditorSubsystem.cpp:1398-1477: GetSimpleCollisionCount counts Box/Sphere/Sphyl only; GetConvexCollisionCount is separate; GetCollisionComplexity reads BodySetup CollisionTraceFlag.',
        ],
        'api_docs': {},
        'routes': [],
        'ground_line_samples': [],
        'capsule_segment_samples': [],
        'asset_collision_samples': [],
        'warnings': [],
        'errors': [],
    }
    seam_destination = output_root / 'CollisionSeamProbes.json'
    seam_evidence = {
        'created_utc': report['created_utc'],
        'world': None,
        'run_status': 'not_run',
        'scope': (
            'Additional complex Visibility ray diagnostics for original failed '
            'ground samples only. Repeat the exact original point, then offset '
            'perpendicular to its nearest 500 cm ground-tile seam by -1, -0.1, '
            '+0.1 and +1 cm. These results never replace original samples or '
            'change original query counts. A nearby hit does not turn the '
            'original miss into a pass.'
        ),
        'source_ground_sample_count': 0,
        'source_complex_miss_count': 0,
        'samples': [],
        'errors': [],
    }

    def read_json(name):
        return json.loads((base / 'Data' / name).read_text(encoding='utf-8-sig'))

    def error(stage, exc, **context):
        item = dict(stage=stage, error_type=type(exc).__name__, message=str(exc))
        item.update(context)
        report['errors'].append(item)

    def save_report():
        report['elapsed_seconds'] = round(time.perf_counter() - start_time, 4)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + '.writing')
        temporary.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
        temporary.replace(destination)
        seam_temporary = seam_destination.with_name(seam_destination.name + '.writing')
        seam_temporary.write_bytes((json.dumps(seam_evidence, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
        seam_temporary.replace(seam_destination)

    def object_label(value):
        if value is None:
            return None
        try:
            return value.get_actor_label()
        except Exception:
            try:
                return value.get_name()
            except Exception:
                return str(value)

    def object_path(value):
        if value is None:
            return None
        try:
            return value.get_path_name()
        except Exception:
            return str(value)

    def vector_list(value):
        return [float(value.x), float(value.y), float(value.z)]

    def vector(value):
        return unreal.Vector(x=float(value[0]), y=float(value[1]), z=float(value[2]))

    def dirty_packages():
        utility = unreal.EditorLoadingAndSavingUtils
        return {
            'maps': sorted(object_path(p) for p in utility.get_dirty_map_packages()),
            'content': sorted(object_path(p) for p in utility.get_dirty_content_packages()),
        }

    def component_data(component):
        if component is None:
            return None
        data = {'path': object_path(component), 'name': object_label(component)}
        try:
            mesh = component.get_editor_property('static_mesh')
            data['mesh'] = object_path(mesh)
        except Exception:
            data['mesh'] = None
        for name, args in (
            ('get_collision_profile_name', ()),
            ('get_collision_enabled', ()),
            ('get_collision_response_to_channel', (unreal.CollisionChannel.ECC_VISIBILITY,)),
            ('is_query_collision_enabled', ()),
        ):
            try:
                value = getattr(component, name)(*args)
                data[name] = value if isinstance(value, (bool, int, float, str)) else str(value)
            except Exception as exc:
                data[name + '_error'] = str(exc)
        return data

    def find_hit_result(value):
        if isinstance(value, unreal.HitResult):
            return value
        if isinstance(value, (tuple, list)):
            for part in value:
                found = find_hit_result(part)
                if found is not None:
                    return found
        if isinstance(value, dict):
            for key in ('out_hit', 'hit', 'hit_result'):
                if key in value:
                    found = find_hit_result(value[key])
                    if found is not None:
                        return found
        return None

    def decode_hit(raw):
        """Handle native UE HitResult|None and legacy bool/HitResult tuples."""
        data = {'raw_return_type': type(raw).__name__}
        if raw is None or raw is False:
            data.update(query_return_hit=False, blocking_hit=False, initial_overlap=False)
            return data
        hit = find_hit_result(raw)
        if hit is None:
            # Never turn an unrecognised wrapper shape into a 'clear' result.
            raise TypeError('Unrecognised trace result: {} {!r}'.format(type(raw).__name__, raw))
        data['raw_hit_repr'] = str(hit)
        data['query_return_hit'] = True
        if isinstance(raw, (tuple, list)) and raw and isinstance(raw[0], bool):
            data['query_return_hit'] = raw[0]
        broken = hit.to_tuple()
        fields = (
            'blocking_hit', 'initial_overlap', 'time', 'distance', 'location',
            'impact_point', 'normal', 'impact_normal', 'phys_mat', 'hit_actor',
            'hit_component', 'hit_bone_name', 'bone_name', 'hit_item',
            'element_index', 'face_index', 'trace_start', 'trace_end',
        )
        if isinstance(broken, dict):
            values = {k: broken.get(k) for k in fields}
        elif isinstance(broken, (tuple, list)) and len(broken) == len(fields):
            values = dict(zip(fields, broken))
        else:
            raise TypeError('Unexpected HitResult.to_tuple schema (expected 18 NativeBreakFunction fields): {!r}'.format(broken))
        for name in ('blocking_hit', 'initial_overlap'):
            if not isinstance(values[name], bool):
                raise TypeError('Unexpected {} field {!r}'.format(name, values[name]))
            data[name] = values[name]
        for name in ('time', 'distance'):
            data[name] = float(values[name])
        for name in ('location', 'impact_point', 'normal', 'impact_normal', 'trace_start', 'trace_end'):
            data[name] = vector_list(values[name])
        for name in ('hit_item', 'element_index', 'face_index'):
            data[name] = int(values[name])
        for name in ('hit_bone_name', 'bone_name'):
            data[name] = str(values[name])
        data['physical_material'] = object_path(values['phys_mat'])
        data['actor_label'] = object_label(values['hit_actor'])
        data['actor_path'] = object_path(values['hit_actor'])
        data['component'] = component_data(values['hit_component'])
        return data

    def trace(kind, start, end, complex_mode, world, trace_channel, draw_debug, record_errors=True):
        try:
            if kind == 'line':
                raw = unreal.SystemLibrary.line_trace_single(
                    world, vector(start), vector(end), trace_channel, complex_mode,
                    [], draw_debug, False,
                )
            else:
                raw = unreal.SystemLibrary.capsule_trace_single(
                    world, vector(start), vector(end),
                    report['configuration']['capsule_radius_cm'],
                    report['configuration']['capsule_half_height_cm'],
                    trace_channel, complex_mode, [], draw_debug, False,
                )
            return decode_hit(raw)
        except Exception as exc:
            if record_errors:
                error('{}_trace_or_decode'.format(kind), exc, start=start, end=end, trace_complex=complex_mode)
            return {'query_error': str(exc), 'blocking_hit': None}

    def count_results(samples):
        modes = {}
        for complex_mode in (False, True):
            subset = [s for s in samples if s['trace_complex'] == complex_mode]
            blocking = sum(s['result'].get('blocking_hit') is True for s in subset)
            no_blocking = sum(s['result'].get('blocking_hit') is False for s in subset)
            errors = sum(s['result'].get('blocking_hit') is None for s in subset)
            modes[str(complex_mode).lower()] = dict(
                queries=len(subset), blocking_hits=blocking, no_blocking_hits=no_blocking,
                errors=errors,
                blocking_actor_counts=dict(collections.Counter(s['result'].get('actor_label', '<unresolved>') for s in subset if s['result'].get('blocking_hit') is True)),
            )
        return modes

    try:
        editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        world = editor.get_editor_world()
        report['world'] = object_path(world)
        route_plan = read_json('Routes.json')
        report['configuration'] = dict(route_plan['configuration'])
        report['layout_sha256'] = hashlib.sha256((base / 'Data' / 'Layout.json').read_bytes()).hexdigest()
        report['routes_sha256'] = hashlib.sha256((base / 'Data' / 'Routes.json').read_bytes()).hexdigest()
        expected = route_plan['map']
        if world is None or not report['world'].startswith(expected + '.'):
            raise RuntimeError('Current editor world is not the required AftermathTown map: {}'.format(report['world']))
        report['engine_version'] = unreal.SystemLibrary.get_engine_version()
        report['dirty_packages_before'] = dirty_packages()
        for name in ('line_trace_single', 'capsule_trace_single'):
            report['api_docs'][name] = getattr(unreal.SystemLibrary, name).__doc__
        report['api_docs']['HitResult.to_tuple'] = getattr(unreal.HitResult.to_tuple, '__doc__', None)
        trace_channel = unreal.TraceTypeQuery.TRACE_TYPE_QUERY1
        draw_debug = unreal.DrawDebugTrace.NONE
        report['configuration']['trace_type_query_runtime'] = str(trace_channel)

        layout = read_json('Layout.json')
        criteria = route_plan['asset_sample_selection']
        ground_rows = [r for r in layout if criteria['ground_tag'] in r.get('tags', [])]
        building_rows = [r for r in layout if criteria['building_tag'] in r.get('tags', [])]
        vehicle_rows = [
            r for r in layout if criteria['vehicle_tag'] in r.get('tags', [])
            and criteria['vehicle_name_contains'] in r['name']
            and not any(term in r['name'] for term in criteria['vehicle_name_excludes'])
        ]
        if not ground_rows or not building_rows or not vehicle_rows:
            raise RuntimeError('Required ground/building/vehicle tagged records were not found in Layout.json')
        ground_meshes = {r['mesh'] for r in ground_rows}
        requested = collections.defaultdict(set)
        for path in ground_meshes:
            requested[path].add('ground')
        requested_body_names = set(criteria['building_body_mesh_names'])
        found_body_names = set()
        for r in building_rows:
            if r['name'] in requested_body_names:
                requested[r['mesh']].add('building_body')
                found_body_names.add(r['name'])
        if found_body_names != requested_body_names:
            raise RuntimeError('Missing building body samples: {}'.format(sorted(requested_body_names - found_body_names)))
        for r in vehicle_rows:
            requested[r['mesh']].add('vehicle')
        expected_counts = route_plan['expected_query_counts']
        if len(requested) != expected_counts['collision_asset_samples']:
            raise RuntimeError('Collision asset sample count changed: {} instead of {}'.format(len(requested), expected_counts['collision_asset_samples']))
        report['asset_selection_counts'] = dict(
            ground_instances=len(ground_rows), building_components=len(building_rows),
            selected_vehicle_instances=len(vehicle_rows), unique_collision_assets=len(requested),
        )
        routes = route_plan['routes']
        if len({r['name'] for r in routes}) != len(routes):
            raise RuntimeError('Duplicate route names in Routes.json')
        actual_entries = set()
        for r in ground_rows:
            if r.get('folder', '').split('/')[-1] != 'VehicleAccess':
                continue
            tile_tags = [t for t in r.get('tags', []) if t.startswith('Tile_')]
            if len(tile_tags) != 1:
                raise RuntimeError('Vehicle entrance has no unique Tile_i_j tag: ' + r['id'])
            parts = tile_tags[0].split('_')
            actual_entries.add((int(parts[1]), int(parts[2])))
        planned_entries = {tuple(r['cell']) for r in routes if 'cell' in r}
        if actual_entries != planned_entries or len(actual_entries) != expected_counts['vehicle_entrances']:
            raise RuntimeError('Vehicle entry tags and Routes.json disagree: actual={!r}, planned={!r}'.format(sorted(actual_entries), sorted(planned_entries)))
        cfg = report['configuration']
        for key in ('ground_sample_step_cm', 'capsule_segment_max_length_cm', 'capsule_radius_cm', 'capsule_half_height_cm'):
            if cfg[key] <= 0:
                raise ValueError('Sampling parameter must be positive: ' + key)
        modes = len(cfg['trace_complex_modes'])
        tracks = len(cfg['track_lateral_offsets_cm'])
        planned_rays = planned_capsules = 0
        for route in routes:
            length = math.dist(route['start_xy'], route['end_xy'])
            if length <= 0:
                raise ValueError('Zero length route: ' + route['name'])
            planned_rays += (int(math.ceil(length / cfg['ground_sample_step_cm'])) + 1) * modes * tracks
            planned_capsules += int(math.ceil(length / cfg['capsule_segment_max_length_cm'])) * modes * tracks
        if planned_rays != expected_counts['ground_lines'] or planned_capsules != expected_counts['capsule_segments']:
            raise RuntimeError('Routes.json query counts disagree with sampling configuration')
        report['planned_query_counts'] = dict(ground_lines=planned_rays, capsule_segments=planned_capsules)
        report['routes'] = routes

        for route in routes:
            x0, y0 = route['start_xy']; x1, y1 = route['end_xy']
            distance = math.hypot(x1 - x0, y1 - y0)
            px, py = -(y1 - y0) / distance, (x1 - x0) / distance
            ray_steps = max(1, int(math.ceil(distance / cfg['ground_sample_step_cm'])))
            capsule_steps = max(1, int(math.ceil(distance / cfg['capsule_segment_max_length_cm'])))
            for offset in cfg['track_lateral_offsets_cm']:
                for step in range(ray_steps + 1):
                    t = step / ray_steps
                    x, y = x0 + (x1 - x0) * t + px * offset, y0 + (y1 - y0) * t + py * offset
                    a, b = [x, y, cfg['ground_ray_z_cm'][0]], [x, y, cfg['ground_ray_z_cm'][1]]
                    for complex_mode in cfg['trace_complex_modes']:
                        result = trace('line', a, b, complex_mode, world, trace_channel, draw_debug)
                        component = result.get('component') or {}
                        result['hit_is_original_ground_tile_mesh'] = component.get('mesh') in ground_meshes if result.get('blocking_hit') is True else None
                        report['ground_line_samples'].append(dict(route=route['name'], lateral_offset_cm=offset, sample_index=step, start=a, end=b, trace_complex=complex_mode, result=result))
                for step in range(capsule_steps):
                    ta, tb = step / capsule_steps, (step + 1) / capsule_steps
                    a = [x0 + (x1 - x0) * ta + px * offset, y0 + (y1 - y0) * ta + py * offset, cfg['capsule_center_z_cm']]
                    b = [x0 + (x1 - x0) * tb + px * offset, y0 + (y1 - y0) * tb + py * offset, cfg['capsule_center_z_cm']]
                    for complex_mode in cfg['trace_complex_modes']:
                        result = trace('capsule', a, b, complex_mode, world, trace_channel, draw_debug)
                        report['capsule_segment_samples'].append(dict(route=route['name'], lateral_offset_cm=offset, segment_index=step, start=a, end=b, trace_complex=complex_mode, result=result))

        # Diagnostic evidence is kept separate from all original pass/miss counts.
        # The exact-point repeat can reveal nondeterminism; off-seam probes can
        # distinguish a seam-sensitive triangle query from a wider uncovered area.
        original_misses = [
            s for s in report['ground_line_samples']
            if s['trace_complex'] and s['result'].get('blocking_hit') is False
        ]
        seam_evidence.update(
            world=report['world'], run_status='started',
            source_ground_sample_count=len(report['ground_line_samples']),
            source_complex_miss_count=len(original_misses),
        )
        original_simple = {
            (s['route'], s['lateral_offset_cm'], s['sample_index']): s['result']
            for s in report['ground_line_samples'] if not s['trace_complex']
        }
        for sample in original_misses:
            x, y = sample['start'][:2]
            origin_x, origin_y = route_plan['ground_grid']['origin_xy_cm']
            cell = route_plan['ground_grid']['cell_size_cm']
            seam_x = origin_x + round((x - origin_x) / cell) * cell
            seam_y = origin_y + round((y - origin_y) / cell) * cell
            dx, dy = abs(x - seam_x), abs(y - seam_y)
            normal_axis = 'x' if dx <= dy else 'y'
            sample_key = (sample['route'], sample['lateral_offset_cm'], sample['sample_index'])
            evidence = {
                'route': sample['route'],
                'lateral_offset_cm': sample['lateral_offset_cm'],
                'sample_index': sample['sample_index'],
                'original_start': list(sample['start']),
                'original_end': list(sample['end']),
                'original_complex_result': sample['result'],
                'original_simple_result': original_simple.get(sample_key),
                'nearest_tile_seams_cm': {'x': seam_x, 'y': seam_y},
                'distance_to_tile_seams_cm': {'x': dx, 'y': dy},
                'offset_normal_axis': normal_axis,
                'nearest_seam_exact_within_1e_6_cm': min(dx, dy) <= 0.000001,
                'probes': [],
            }
            for offset in (0.0, -1.0, -0.1, 0.1, 1.0):
                a, b = list(sample['start']), list(sample['end'])
                axis = 0 if normal_axis == 'x' else 1
                a[axis] += offset
                b[axis] += offset
                result = trace('line', a, b, True, world, trace_channel, draw_debug, record_errors=False)
                component = result.get('component') or {}
                result['hit_is_original_ground_tile_mesh'] = component.get('mesh') in ground_meshes if result.get('blocking_hit') is True else None
                evidence['probes'].append(dict(
                    perpendicular_offset_cm=offset, start=a, end=b,
                    trace_complex=True, result=result,
                ))
                if result.get('blocking_hit') is None:
                    seam_evidence['errors'].append(dict(route=sample['route'], sample_index=sample['sample_index'], perpendicular_offset_cm=offset, error=result.get('query_error')))
            off_seam = [p for p in evidence['probes'] if p['perpendicular_offset_cm'] != 0]
            evidence['off_seam_blocking_hit_count'] = sum(p['result'].get('blocking_hit') is True for p in off_seam)
            evidence['off_seam_no_hit_count'] = sum(p['result'].get('blocking_hit') is False for p in off_seam)
            evidence['off_seam_error_count'] = sum(p['result'].get('blocking_hit') is None for p in off_seam)
            seam_evidence['samples'].append(evidence)
        all_probes = [p for s in seam_evidence['samples'] for p in s['probes']]
        seam_evidence['summary'] = {
            'probe_queries': len(all_probes),
            'blocking_hits': sum(p['result'].get('blocking_hit') is True for p in all_probes),
            'no_blocking_hits': sum(p['result'].get('blocking_hit') is False for p in all_probes),
            'errors': len(seam_evidence['errors']),
        }
        seam_evidence['run_status'] = 'completed_with_errors' if seam_evidence['errors'] else 'completed'
        report['additional_complex_seam_evidence_file'] = str(seam_destination)

        # Actual asset collision data and representative placed component state.
        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        mesh_subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        report['api_docs']['get_simple_collision_count'] = mesh_subsystem.get_simple_collision_count.__doc__
        report['api_docs']['get_convex_collision_count'] = mesh_subsystem.get_convex_collision_count.__doc__
        report['api_docs']['get_collision_complexity'] = mesh_subsystem.get_collision_complexity.__doc__
        placed = collections.defaultdict(list)
        assets = {}
        profile_counts = collections.Counter()
        component_errors = collections.Counter()
        component_count = 0
        for actor in actor_subsystem.get_all_level_actors():
            for component in actor.get_components_by_class(unreal.StaticMeshComponent):
                mesh = component.get_editor_property('static_mesh')
                if mesh is None:
                    continue
                component_count += 1
                path = object_path(mesh)
                try:
                    profile_counts[str(component.get_collision_profile_name())] += 1
                except Exception as exc:
                    component_errors[str(exc)] += 1
                if path not in requested:
                    continue
                assets[path] = mesh
                if len(placed[path]) < 3:
                    placed[path].append(dict(actor=object_label(actor), component=component_data(component)))
        report['world_static_mesh_component_count'] = component_count
        report['world_component_collision_profile_counts'] = dict(profile_counts)
        report['component_scan_errors'] = dict(component_errors)

        try:
            settings = unreal.get_default_object(unreal.PhysicsSettings)
            report['project_default_shape_complexity'] = str(settings.get_editor_property('default_shape_complexity'))
        except Exception as exc:
            report['warnings'].append(dict(stage='project_default_shape_complexity', message=str(exc)))

        for path in sorted(requested):
            record = {'mesh': path, 'categories': sorted(requested[path]), 'placed_component_examples': placed.get(path, [])}
            try:
                mesh = assets.get(path)
                if mesh is None:
                    mesh = unreal.load_asset(path)
                if mesh is None:
                    raise RuntimeError('Requested static mesh could not be read')
                simple_count = mesh_subsystem.get_simple_collision_count(mesh)
                convex_count = mesh_subsystem.get_convex_collision_count(mesh)
                record['simple_box_sphere_sphyl_count'] = int(simple_count)
                record['convex_count'] = int(convex_count)
                record['collision_complexity'] = str(mesh_subsystem.get_collision_complexity(mesh))
                if simple_count < 0 or convex_count < 0:
                    raise RuntimeError('Collision-count query returned negative failure result')
                try:
                    body = mesh.get_editor_property('body_setup')
                    record['body_setup'] = object_path(body)
                    record['body_setup_collision_trace_flag'] = str(body.get_editor_property('collision_trace_flag')) if body is not None else None
                except Exception as exc:
                    record['body_setup_read_error'] = str(exc)
                    report['warnings'].append(dict(stage='body_setup_property', mesh=path, message=str(exc)))
            except Exception as exc:
                record['inspection_error'] = str(exc)
                error('asset_collision_inspection', exc, mesh=path)
            report['asset_collision_samples'].append(record)

        report['dirty_packages_after'] = dirty_packages()
        report['dirty_package_sets_unchanged'] = report['dirty_packages_before'] == report['dirty_packages_after']
        report['summary'] = {
            'ground_line_queries': count_results(report['ground_line_samples']),
            'capsule_queries': count_results(report['capsule_segment_samples']),
            'ground_hits_on_other_meshes': sum(s['result'].get('blocking_hit') is True and s['result'].get('hit_is_original_ground_tile_mesh') is False for s in report['ground_line_samples']),
            'route_count': len(routes),
            'vehicle_entry_count': len(actual_entries),
            'asset_collision_samples': len(report['asset_collision_samples']),
            'errors': len(report['errors']),
            'seam_probe_errors': len(seam_evidence['errors']),
        }
        if len(report['ground_line_samples']) != expected_counts['ground_lines'] or len(report['capsule_segment_samples']) != expected_counts['capsule_segments']:
            error('incomplete_query_count', RuntimeError('Not every planned query produced a sample record'))
        report['run_status'] = 'completed_with_errors' if report['errors'] or seam_evidence['errors'] else 'completed'
        if report['errors']:
            report['validation_outcome'] = 'incomplete_due_to_query_or_asset_errors'
        elif seam_evidence['errors']:
            report['validation_outcome'] = 'incomplete_due_to_seam_probe_errors'
        elif any(s['result'].get('blocking_hit') is True for s in report['capsule_segment_samples']):
            report['validation_outcome'] = 'blocked_sampled_capsule_tracks'
        elif any(s['result'].get('blocking_hit') is False for s in report['ground_line_samples'] if not s['trace_complex']):
            report['validation_outcome'] = 'missing_simple_ground_hits'
        elif any(s['result'].get('blocking_hit') is False for s in report['ground_line_samples'] if s['trace_complex']):
            report['validation_outcome'] = 'sampled_capsule_tracks_clear_with_complex_seam_misses'
        else:
            report['validation_outcome'] = 'sampled_queries_without_reported_collision_issues'
    except Exception as exc:
        error('fatal_setup_or_execution', exc, traceback=traceback.format_exc())
        report['run_status'] = 'failed'
        report['validation_outcome'] = 'incomplete_due_to_execution_error'
    finally:
        save_report()

    compact = {
        'output': str(destination), 'run_status': report['run_status'],
        'validation_outcome': report.get('validation_outcome'),
        'world': report['world'], 'line_samples': len(report['ground_line_samples']),
        'capsule_samples': len(report['capsule_segment_samples']),
        'asset_samples': len(report['asset_collision_samples']),
        'errors': len(report['errors']), 'elapsed_seconds': report['elapsed_seconds'],
    }
    print(json.dumps(compact, ensure_ascii=False))
    return compact


if __name__ == '__main__':
    main()
