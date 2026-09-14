"""Read-only evidence export from the original Apocalypse Demo in UE.

Raw mesh geometry and full Demo placements are local generated inputs, not
repository distributables. All UE object references stay inside main().
"""
import collections
import json
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[1]
SOURCE_WORLD = '/Game/PolygonApocalypse/Maps/Demo.Demo'
PREFIXES = ('SM_Env_Road', 'SM_Env_Sidewalk', 'SM_Env_Dirt', 'SM_Generic_Ground',
            'SM_Env_GrassBlob', 'SM_Env_GroundLeaves')


def vec(value):
    return [round(value.x, 5), round(value.y, 5), round(value.z, 5)]


def rot(value):
    return {'pitch': value.pitch, 'yaw': value.yaw, 'roll': value.roll}


def main():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name() != SOURCE_WORLD:
        raise RuntimeError('Open the original Apocalypse Demo before exporting: ' + SOURCE_WORLD)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    records, meshes, context = [], {}, []
    for actor in actors:
        for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh = comp.static_mesh
            if not mesh:
                continue
            name = mesh.get_name()
            location = comp.get_world_location()
            if not name.startswith(PREFIXES):
                if (-5000 < location.x < 1000 and -5000 < location.y < 1000
                        and ('Bld_' in name or 'Gaspump' in name)):
                    context.append({'name': name, 'loc': vec(location), 'rot': rot(comp.get_world_rotation())})
                continue
            path = mesh.get_path_name()
            bounds = actor.get_actor_bounds(False)
            records.append({
                'actor': actor.get_actor_label(), 'actor_path': actor.get_path_name(), 'component': comp.get_name(),
                'mesh': path, 'name': name, 'loc': vec(location), 'rot': rot(comp.get_world_rotation()),
                'scale': vec(comp.get_world_scale()), 'actor_loc': vec(actor.get_actor_location()),
                'relative_loc': vec(comp.get_editor_property('relative_location')),
                'bounds_center': vec(bounds[0]), 'bounds_extent': vec(bounds[1]),
                'materials': [comp.get_material(i).get_path_name() if comp.get_material(i) else None
                              for i in range(comp.get_num_materials())],
            })
            if path not in meshes:
                box, sections = mesh.get_bounding_box(), []
                for section in range(mesh.get_num_sections(0)):
                    vertices, triangles, normals, uvs, tangents = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(
                        mesh, 0, section)
                    sections.append({'vertices': [vec(point) for point in vertices], 'triangles': list(triangles)})
                meshes[path] = {
                    'name': name, 'min': vec(box.min), 'max': vec(box.max), 'sections': sections,
                    'materials': [slot.material_interface.get_path_name() if slot.material_interface else None
                                  for slot in mesh.static_materials],
                }
    data = ROOT / 'Data'
    data.mkdir(parents=True, exist_ok=True)
    (data / 'SourceGroundPlacements.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    (data / 'SourceGroundGeometry.json').write_text(json.dumps(meshes, separators=(',', ':')), encoding='utf-8')
    (data / 'SourceContext.json').write_text(json.dumps(context, indent=2), encoding='utf-8')
    summary = {
        'source_world': SOURCE_WORLD, 'ground_components': len(records), 'unique_ground_meshes': len(meshes),
        'component_z_histogram': collections.Counter(round(row['loc'][2], 2) for row in records).most_common(15),
        'mesh_counts': collections.Counter(row['name'] for row in records).most_common(),
        'components_offset_from_actor_world_location': sum(
            any(abs(v - a) > .01 for v, a in zip(row['loc'], row['actor_loc'])) for row in records),
    }
    (data / 'SourceSummary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in summary.items() if key != 'mesh_counts'}))


if __name__ == '__main__':
    main()
