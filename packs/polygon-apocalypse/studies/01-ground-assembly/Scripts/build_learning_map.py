"""Build the editable study from its public 30-instance manifest in UE.

Import the licensed Apocalypse content first. Existing maps and unsaved maps
are never overwritten or automatically saved by this script.
"""
import json
import math
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[1]
MAP = '/Game/SyntySenceLearning/PolygonApocalypse/GroundAssembly/L_GroundAssembly_Study'
TAG = 'GroundAssemblyStudy'
CUBEMAP = '/Engine/EngineResources/GrayLightTextureCube.GrayLightTextureCube'


def require_clean_maps():
    names = [package.get_path_name()
             for package in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if names:
        raise RuntimeError('Unsaved maps detected; save or discard their changes deliberately before building: '
                           + ', '.join(names))


def preflight():
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        raise RuntimeError('Learning map already exists; refusing overwrite: ' + MAP)
    require_clean_maps()
    rows = json.loads((ROOT / 'Data/LearningMapManifest.json').read_text(encoding='utf-8'))
    if not isinstance(rows, list) or not rows:
        raise ValueError('LearningMapManifest.json must contain instance records')
    assets, failures = {}, []
    for index, row in enumerate(rows):
        try:
            for key in ('study_location', 'scale'):
                if len(row[key]) != 3 or not all(math.isfinite(v) for v in row[key]):
                    raise ValueError('Invalid ' + key)
            if set(row['rotation']) != {'pitch', 'yaw', 'roll'} or not all(
                    math.isfinite(v) for v in row['rotation'].values()):
                raise ValueError('Invalid rotation')
            if not isinstance(row['folder'], str) or not row['folder']:
                raise ValueError('Missing folder')
            if not isinstance(row['materials'], list):
                raise ValueError('Missing material slot list')
            mesh_path = row['mesh']
            if mesh_path not in assets:
                assets[mesh_path] = unreal.load_asset(mesh_path)
            mesh = assets[mesh_path]
            if not isinstance(mesh, unreal.StaticMesh):
                raise ValueError('Missing StaticMesh: ' + mesh_path)
            if len(row['materials']) != len(mesh.static_materials):
                raise ValueError('Material slot count does not match source mesh: ' + mesh_path)
            for path in row['materials']:
                if path is None:
                    continue
                if path not in assets:
                    assets[path] = unreal.load_asset(path)
                if not isinstance(assets[path], unreal.MaterialInterface):
                    raise ValueError('Missing material: ' + path)
        except (KeyError, TypeError, ValueError) as error:
            failures.append('Record %d: %s' % (index, error))
    assets[CUBEMAP] = unreal.load_asset(CUBEMAP)
    if not assets[CUBEMAP]:
        failures.append('Missing engine lighting cubemap: ' + CUBEMAP)
    if failures:
        raise RuntimeError('No map was created. Resolve asset/manifest errors:\n' + '\n'.join(failures))
    return rows, assets


def main():
    rows, assets = preflight()
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    # Check again after asset loading, immediately before the destructive world switch.
    require_clean_maps()
    if not levels.new_level(MAP, is_partitioned_world=False):
        raise RuntimeError('Could not create study map: ' + MAP)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for index, row in enumerate(rows):
        x, y, z = row['study_location']
        actor = actors.spawn_actor_from_class(
            unreal.StaticMeshActor, unreal.Vector(x=x, y=y, z=z), unreal.Rotator(**row['rotation']))
        if not actor:
            raise RuntimeError('Could not spawn manifest record %d' % index)
        actor.static_mesh_component.set_static_mesh(assets[row['mesh']])
        x, y, z = row['scale']
        actor.set_actor_scale3d(unreal.Vector(x=x, y=y, z=z))
        for slot, path in enumerate(row['materials']):
            actor.static_mesh_component.set_material(slot, assets[path] if path else None)
        actor.set_actor_label('%02d_%s' % (index + 1, row['mesh'].rsplit('.', 1)[-1]))
        actor.set_folder_path('Learning/' + row['folder'])
        actor.tags = [unreal.Name(TAG), unreal.Name('StudyInstance_%02d' % index)]

    sun = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(z=2000),
                                         unreal.Rotator(pitch=-55, yaw=-30))
    sun.set_folder_path('Learning/Lighting')
    sun.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun.light_component.set_intensity(3)
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(z=1000))
    sky.set_folder_path('Learning/Lighting')
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property('source_type', unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sky.light_component.set_editor_property('cubemap', assets[CUBEMAP])
    sky.light_component.set_intensity(.4)
    views = [
        ('A_AssembledAndSeparated', (300, -2400, 2550), (0, 500, 0), 55),
        ('B_GasApronCorner', (5500, -2000, 2400), (4450, -50, 0), 55),
        ('C_Driveway', (9800, -1500, 1600), (8500, 50, 0), 55),
    ]
    for name, position, target, fov in views:
        p = unreal.Vector(x=position[0], y=position[1], z=position[2])
        t = unreal.Vector(x=target[0], y=target[1], z=target[2])
        camera = actors.spawn_actor_from_class(unreal.CameraActor, p,
                                                unreal.MathLibrary.find_look_at_rotation(p, t))
        camera.set_actor_label('VIEW_' + name)
        camera.set_folder_path('Learning/Views')
        camera.camera_component.set_field_of_view(fov)
    p, target = unreal.Vector(x=300, y=-2400, z=2550), unreal.Vector(x=0, y=500, z=0)
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
        p, unreal.MathLibrary.find_look_at_rotation(p, target))
    levels.set_level_viewport_fov(55, levels.get_active_viewport_config_key())
    levels.editor_set_game_view(True)
    actors.clear_actor_selection_set()
    if not levels.save_current_level():
        raise RuntimeError('Study map could not be saved')
    print(json.dumps({'map': MAP, 'mesh_actors': len(rows),
                      'groups': sorted({row['folder'] for row in rows})}))


if __name__ == '__main__':
    main()
