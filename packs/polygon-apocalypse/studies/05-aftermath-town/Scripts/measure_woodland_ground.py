"""Read selected Woodland ground nodes and LOD0 surfaces without saving assets.

Open the original Woodland Demo with the recorded dependencies before running.
Measurements go to the current project's Saved directory, never back to the
historical evidence or source map. No complete mesh geometry is exported.
"""
import json
from pathlib import Path
import unreal


def top_height(vertices, indices, x, y):
    result = None
    for i in range(0, len(indices), 3):
        a, b, c = [vertices[indices[i + j]] for j in range(3)]
        den = (b[1]-c[1])*(a[0]-c[0]) + (c[0]-b[0])*(a[1]-c[1])
        if abs(den) < 1e-9:
            continue
        u = ((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1])) / den
        v = ((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1])) / den
        w = 1-u-v
        if min(u, v, w) >= -1e-7:
            z = u*a[2] + v*b[2] + w*c[2]
            result = z if result is None else max(result, z)
    return result


def main():
    study = Path(__file__).resolve().parents[1]
    recipe = json.loads((study/'Data/WoodlandGroundRecipes.json').read_text(encoding='utf-8'))
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name() != recipe['source_map']:
        raise RuntimeError('Open the recorded original Woodland map first; no map will be loaded automatically.')
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    by_name = {a.get_name(): a for a in actors}
    geometry, issues = {}, []
    checked = 0
    for case in recipe['cases'].values():
        for node in case['nodes']:
            actor = by_name.get(node['actor_name'])
            components = actor.get_components_by_class(unreal.StaticMeshComponent) if actor else []
            comp = next((c for c in components if c.get_name() == node['component']), None)
            if comp is None or comp.static_mesh is None:
                issues.append(node['actor_name'] + ': missing actor/component/mesh')
                continue
            checked += 1
            mesh = comp.static_mesh
            if mesh.get_path_name() != node['mesh']:
                issues.append(node['actor_name'] + ': mesh reference differs')
            t = comp.get_world_transform()
            r = t.rotation.rotator()
            actual = [t.translation.x,t.translation.y,t.translation.z,r.pitch,r.yaw,r.roll,t.scale3d.x,t.scale3d.y,t.scale3d.z]
            expected = [*node['location'],*[node['rotation'][k] for k in ('pitch','yaw','roll')],*node['scale']]
            if any(abs(a-b) > 0.001 for a,b in zip(actual,expected)):
                issues.append(node['actor_name'] + ': transform differs')
            materials = [comp.get_material(i).get_path_name() if comp.get_material(i) else None for i in range(comp.get_num_materials())]
            if materials != node['materials']:
                issues.append(node['actor_name'] + ': effective materials differ')
            if node['actor_name'] not in recipe['measure_geometry_actors']:
                continue
            vertices, indices = [], []
            for section in range(mesh.get_num_sections(0)):
                v, tri, normals, uvs, tangents = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh,0,section)
                start = len(vertices)
                for p in v:
                    q = unreal.MathLibrary.transform_location(t,p)
                    vertices.append([q.x,q.y,q.z])
                indices.extend(int(i)+start for i in tri)
            geometry[node['actor_name']] = (vertices,indices)
    if issues:
        raise RuntimeError('Source nodes differ; review the source/version instead of silently substituting: ' + json.dumps(issues))
    landscapes = [a for a in actors if isinstance(a,unreal.LandscapeProxy)]
    if not landscapes:
        raise RuntimeError('No Landscape found.')
    ignore = [a for a in actors if not isinstance(a,unreal.LandscapeProxy)]
    components = []
    for a in landscapes:
        layers = a.get_target_layer_names(False)
        for c in a.get_components_by_class(unreal.LandscapeComponent):
            o,e,r = unreal.SystemLibrary.get_component_bounds(c)
            components.append((c,o.x-e.x,o.x+e.x,o.y-e.y,o.y+e.y,layers))
    profiles = {}
    for key, positions in recipe['probe_positions'].items():
        rows = []
        for x,y in positions:
            hit = unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,5000),unreal.Vector(x,y,-5000),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,unreal.DrawDebugTrace.NONE)
            row = {'xy':[x,y], 'landscape_collision_height':None, 'landscape_actor':None, 'paint_weights':{}, 'lod0_top_heights':{}}
            if hit:
                h = hit.to_tuple()
                if h[0] and isinstance(h[9],unreal.LandscapeProxy):
                    row['landscape_collision_height'] = h[5].z
                    row['landscape_actor'] = h[9].get_name()
            for c,x0,x1,y0,y1,layers in components:
                if x0 <= x <= x1 and y0 <= y <= y1:
                    weights = {}
                    for layer in layers:
                        value = c.editor_get_paint_layer_weight_by_name_at_location(unreal.Vector(x,y,0),layer)
                        if value > 0.00001:
                            weights[str(layer)] = value
                    if sum(weights.values()) > sum(row['paint_weights'].values()):
                        row['paint_weights'] = weights
            for actor_name, (vertices,indices) in geometry.items():
                height = top_height(vertices,indices,x,y)
                if height is not None:
                    row['lod0_top_heights'][actor_name] = height
            rows.append(row)
        profiles[key] = rows
    result = {
        'source_map':world.get_path_name(), 'engine':unreal.SystemLibrary.get_engine_version(),
        'units':'centimeters', 'selected_nodes_checked':checked, 'node_issues':issues,
        'geometry_instances_measured':len(geometry),
        'sample_count':sum(len(rows) for rows in profiles.values()),
        'landscape_misses':sum(row['landscape_collision_height'] is None for rows in profiles.values() for row in rows),
        'landscape_collision_mips':[{'actor':a.get_name(),'collision':a.get_editor_property('collision_mip_level'),'simple':a.get_editor_property('simple_collision_mip_level')} for a in landscapes],
        'method':'Selected current LOD0 world triangles, vertical XY barycentric intersection, maximum Z per actor. Landscape-only complex collision query with all other actors ignored. Paint weights are shader inputs, not final visible percentages.',
        'limitations':['Discrete samples are not an exhaustive seam or collision/navigation validation.', 'Landscape collision reference is not a direct rendered Landscape vertex export.', 'Top triangle intersection does not test foliage opacity, shader displacement, or full-scene occlusion.'],
        'profiles':profiles,
        'dirty_maps':[p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
        'dirty_content':[p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
    }
    output = Path(unreal.Paths.project_saved_dir()).resolve()/'SyntySenceLearning/WoodlandGroundStudy'
    output.mkdir(parents=True,exist_ok=True)
    (output/'MeasuredSamples.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('profiles','method','limitations')},ensure_ascii=False))


if __name__ == '__main__':
    main()
