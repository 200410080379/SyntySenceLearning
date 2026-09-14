"""Rebuild the authored town in a new map from the three portable layout files.

Run once in UE Python with the source packs installed. A large build may outlive
an MCP response timeout: inspect the editor/world before attempting another call.
An existing target map is never replaced, including an incomplete previous run.
"""
import json
import math
from pathlib import Path
import runpy

import unreal


ROOT = Path(__file__).resolve().parents[1]
LEVEL = '/Game/SyntySenceLearning/PolygonApocalypse/AftermathTown/L_AftermathTown'
MATERIAL_ROOTS = (
    '/Game/SyntySenceLearning/PolygonApocalypse/AftermathTown/Materials/',
    '/Game/SyntySenceLearning/PolygonApocalypse/ExpandedNeighborhood/Materials/',
)
SKY_CLASS = '/Engine/EngineSky/BP_Sky_Sphere.BP_Sky_Sphere_C'
SKY_CUBE = '/Engine/EngineResources/GrayLightTextureCube'


def _read(name):
    rows = json.loads((ROOT / 'Data' / name).read_text(encoding='utf-8-sig'))
    if not isinstance(rows, list) or not rows:
        raise ValueError(name + ' must contain a nonempty list')
    return rows


def _vector(values):
    return unreal.Vector(x=values[0], y=values[1], z=values[2])


def _rotation(value):
    return unreal.Rotator(pitch=value['pitch'], yaw=value['yaw'], roll=value['roll'])


def _validate_rows(meshes, decals, cameras):
    identifiers = set()
    for rows, kind in ((meshes, 'mesh'), (decals, 'decal'), (cameras, 'camera')):
        for row in rows:
            label = row['id'] if kind != 'camera' else 'TOWN_VIEW_' + row['name']
            if not label or label in identifiers:
                raise ValueError('Empty or duplicate actor label: ' + label)
            identifiers.add(label)
            vectors = ['location'] + ([] if kind == 'camera' else ['scale'])
            if kind == 'decal':
                vectors.append('size')
            for field in vectors:
                values = row[field]
                if len(values) != 3 or not all(math.isfinite(v) for v in values):
                    raise ValueError('Invalid ' + field + ' for ' + label)
            if not all(math.isfinite(row['rotation'][key]) for key in ('pitch', 'yaw', 'roll')):
                raise ValueError('Invalid rotation for ' + label)
            if kind == 'camera' and not 0 < row['fov'] < 180:
                raise ValueError('Invalid camera FOV: ' + label)
            if kind == 'mesh':
                if not row['collision_profile']:
                    raise ValueError('Missing collision profile: ' + label)
                if not all(isinstance(t, str) for t in row['tags']):
                    raise ValueError('Invalid actor tags: ' + label)
            if kind == 'decal' and (any(v <= 0 for v in row['size']) or row['fade_screen_size'] < 0):
                raise ValueError('Invalid decal extent/fade: ' + label)


def _package_name(package):
    return package.get_path_name().split('.', 1)[0]


def _require_clean_editor():
    dirty = unreal.EditorLoadingAndSavingUtils
    if dirty.get_dirty_map_packages() or dirty.get_dirty_content_packages():
        raise RuntimeError('Save your current maps and assets before creating this study')


def _preload(mesh_rows, decal_rows):
    """Resolve source references before material creation, and all refs before a new map."""
    lib = unreal.EditorAssetLibrary
    meshes = {}
    for path in sorted({row['mesh'] for row in mesh_rows}):
        mesh = unreal.load_asset(path)
        if not isinstance(mesh, unreal.StaticMesh):
            raise RuntimeError('Required source mesh is unavailable: ' + path)
        meshes[path] = mesh
    paths = {path for row in mesh_rows for path in row['materials']}
    paths.update(row['material'] for row in decal_rows)
    if any(not isinstance(path, str) or not path for path in paths):
        raise ValueError('Layout contains an empty material reference')
    materials = {}
    for path in sorted(paths):
        if path.startswith(MATERIAL_ROOTS):
            continue
        material = unreal.load_asset(path)
        if not isinstance(material, unreal.MaterialInterface):
            raise RuntimeError('Required source material is unavailable: ' + path)
        materials[path] = material
    cube = unreal.load_asset(SKY_CUBE)
    sky_class = unreal.load_class(None, SKY_CLASS)
    if not cube or not sky_class:
        raise RuntimeError('Required engine sky assets are unavailable')
    setup_path = ROOT / 'Scripts' / 'setup_materials.py'
    if not setup_path.is_file():
        raise RuntimeError('Missing material setup script: ' + str(setup_path))
    setup = runpy.run_path(str(setup_path), run_name='aftermath_material_setup')
    setup['main']()
    # The setup owns only its derived materials; never save unrelated dirty work.
    dirty = unreal.EditorLoadingAndSavingUtils
    if dirty.get_dirty_map_packages():
        raise RuntimeError('Material setup unexpectedly dirtied a map; no map will be created')
    unexpected = [_package_name(p) for p in dirty.get_dirty_content_packages()
                  if not _package_name(p).startswith(MATERIAL_ROOTS)]
    if unexpected:
        raise RuntimeError('Unexpected dirty assets after material setup: ' + ', '.join(unexpected))
    for path in sorted(paths):
        material = materials.get(path) or unreal.load_asset(path)
        if not isinstance(material, unreal.MaterialInterface):
            raise RuntimeError('Required derived material is unavailable: ' + path)
        materials[path] = material
    # Save only materials generated by setup if it left its own packages dirty.
    for package in list(dirty.get_dirty_content_packages()):
        if not lib.save_asset(_package_name(package), only_if_is_dirty=True):
            raise RuntimeError('Could not save derived material: ' + _package_name(package))
    return meshes, materials, cube, sky_class


def _spawn(actors, actor_class, label, location, rotation=None, folder='00_Environment'):
    actor = actors.spawn_actor_from_class(actor_class, _vector(location),
                                         _rotation(rotation or {'pitch': 0, 'yaw': 0, 'roll': 0}))
    if not actor:
        raise RuntimeError('Could not create actor: ' + label)
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    return actor


def _environment(actors, cube, sky_class):
    sun = _spawn(actors, unreal.DirectionalLight, 'Town_Sun', [0, 0, 5000],
                 {'pitch': -43, 'yaw': -38, 'roll': 0})
    sun.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun.light_component.set_intensity(3.2)
    sun.light_component.set_light_color(unreal.LinearColor(r=1, g=.91, b=.77, a=1))
    sky = _spawn(actors, unreal.SkyLight, 'Town_Skylight', [0, 0, 3000])
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property('source_type', unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sky.light_component.set_editor_property('cubemap', cube)
    sky.light_component.set_intensity(.65)
    sky.light_component.set_light_color(unreal.LinearColor(r=.72, g=.85, b=1, a=1))
    sphere = _spawn(actors, sky_class, 'Town_Sky', [0, 0, 0])
    sphere.set_editor_property('Directional light actor', sun)
    sphere.set_editor_property('Cloud opacity', 1.1)
    sphere.set_editor_property('Sun brightness', 18.0)
    sphere.call_method('UpdateSunDirection')
    fog = _spawn(actors, unreal.ExponentialHeightFog, 'Town_DistantHaze', [0, 0, 400])
    component = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    component.set_editor_property('fog_density', .006)
    component.set_editor_property('fog_height_falloff', .22)
    component.set_editor_property('start_distance', 6500.0)
    component.set_editor_property('fog_max_opacity', .25)
    component.set_fog_inscattering_color(unreal.LinearColor(r=.30, g=.35, b=.33, a=1))
    post = _spawn(actors, unreal.PostProcessVolume, 'Town_Grade', [0, 0, 0])
    post.set_editor_property('unbound', True)
    settings = post.get_editor_property('settings')
    parameters = {
        'color_saturation': unreal.Vector4(x=.90, y=.91, z=.91, w=1),
        'color_contrast': unreal.Vector4(x=1.07, y=1.07, z=1.07, w=1),
        'ambient_occlusion_intensity': .9,
        'ambient_occlusion_radius': 80.0,
        'bloom_intensity': .12,
        'vignette_intensity': .15,
    }
    for key, value in parameters.items():
        settings.set_editor_property('override_' + key, True)
        settings.set_editor_property(key, value)
    post.set_editor_property('settings', settings)


def main():
    lib = unreal.EditorAssetLibrary
    if lib.does_asset_exist(LEVEL):
        raise RuntimeError('Refuse to replace an existing town map: ' + LEVEL)
    _require_clean_editor()
    mesh_rows = _read('Layout.json')
    decal_rows = _read('Decals.json')
    cameras = _read('Cameras.json')
    _validate_rows(mesh_rows, decal_rows, cameras)
    meshes, materials, cube, sky_class = _preload(mesh_rows, decal_rows)
    # Material preparation must finish before any world switch or actor creation.
    _require_clean_editor()
    if lib.does_asset_exist(LEVEL):
        raise RuntimeError('Target map appeared during preflight; refusing to replace it')
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not levels.new_level(LEVEL, is_partitioned_world=False):
        raise RuntimeError('Could not create town map: ' + LEVEL)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for index, row in enumerate(mesh_rows, 1):
        actor = _spawn(actors, unreal.StaticMeshActor, row['id'], row['location'],
                       row['rotation'], row['folder'])
        component = actor.static_mesh_component
        component.set_static_mesh(meshes[row['mesh']])
        actor.set_actor_scale3d(_vector(row['scale']))
        for slot, path in enumerate(row['materials']):
            component.set_material(slot, materials[path])
        component.set_collision_profile_name(unreal.Name(row['collision_profile']))
        actor.tags = [unreal.Name(tag) for tag in row['tags']]
        if index % 500 == 0:
            print('Town meshes: %d / %d' % (index, len(mesh_rows)), flush=True)
    for row in decal_rows:
        actor = _spawn(actors, unreal.DecalActor, row['id'], row['location'],
                       row['rotation'], row['folder'])
        actor.set_actor_scale3d(_vector(row['scale']))
        component = actor.get_component_by_class(unreal.DecalComponent)
        component.set_decal_material(materials[row['material']])
        component.set_editor_property('decal_size', _vector(row['size']))
        component.set_editor_property('fade_screen_size', row['fade_screen_size'])
        actor.tags = [unreal.Name(tag) for tag in row.get('tags', [])]
    for row in cameras:
        actor = _spawn(actors, unreal.CameraActor, 'TOWN_VIEW_' + row['name'],
                       row['location'], row['rotation'], '00_Environment/Views')
        actor.camera_component.set_field_of_view(row['fov'])
        actor.tags = [unreal.Name('AftermathView')]
    _environment(actors, cube, sky_class)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name() != LEVEL + '.L_AftermathTown':
        raise RuntimeError('Current map changed during build; refusing to save it')
    if not levels.save_current_level():
        raise RuntimeError('Town was built but its map could not be saved')
    print(json.dumps({'map': LEVEL, 'mesh_instances': len(mesh_rows),
                      'unique_meshes': len(meshes), 'decals': len(decal_rows),
                      'cameras': len(cameras), 'saved': True,
                      'verification': 'Run the separate read-only verifier after saving and reopening.'}))


if __name__ == '__main__':
    main()
