"""Expose original Demo ground temporarily; restore without saving the map.

Snapshot files are local session state and must not be committed. Repeated
ground_only() calls refuse to replace the original visibility snapshot.
"""
import json
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'Data/SourceVisibility.json'
SOURCE_WORLD = '/Game/PolygonApocalypse/Maps/Demo.Demo'
PREFIXES = ('SM_Env_Road', 'SM_Env_Sidewalk', 'SM_Env_Dirt', 'SM_Generic_Ground',
            'SM_Env_GrassBlob', 'SM_Env_GroundLeaves')


def source_actors():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name() != SOURCE_WORLD:
        raise RuntimeError('This operation requires the original Apocalypse Demo: ' + SOURCE_WORLD)
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()


def ground_only():
    actors = source_actors()
    if SNAPSHOT.exists():
        raise RuntimeError('Visibility snapshot exists. Call restore() before hiding again: ' + str(SNAPSHOT))
    state = {actor.get_path_name(): actor.is_temporarily_hidden_in_editor() for actor in actors}
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects even against a second script racing this call.
    # Persist BEFORE hiding actors so interruption leaves a usable recovery record.
    with SNAPSHOT.open('x', encoding='utf-8') as handle:
        json.dump({'source_world': SOURCE_WORLD, 'actors': state}, handle)
    hidden = 0
    for actor in actors:
        components = actor.get_components_by_class(unreal.StaticMeshComponent)
        keep = any(comp.static_mesh and (comp.static_mesh.get_name().startswith(PREFIXES)
                   or '/EngineSky/' in comp.static_mesh.get_path_name()) for comp in components)
        keep = keep or isinstance(actor, (unreal.Light, unreal.SkyLight, unreal.ExponentialHeightFog,
                                         unreal.PostProcessVolume, unreal.SkyAtmosphere, unreal.VolumetricCloud))
        keep = keep or 'Sky_Sphere' in actor.get_class().get_name()
        if not keep:
            actor.set_is_temporarily_hidden_in_editor(True)
            hidden += 1
    print('Temporarily hidden %d non-ground actors; source map was not saved' % hidden)


def restore():
    actors = source_actors()
    snapshot = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    if snapshot.get('source_world') != SOURCE_WORLD:
        raise RuntimeError('Visibility snapshot belongs to another world')
    state = snapshot['actors']
    if not isinstance(state, dict) or not all(isinstance(value, bool) for value in state.values()):
        raise ValueError('Invalid visibility snapshot')
    restored = set()
    for actor in actors:
        path = actor.get_path_name()
        if path in state:
            actor.set_is_temporarily_hidden_in_editor(state[path])
            restored.add(path)
    missing = sorted(set(state) - restored)
    if missing:
        raise RuntimeError('Restored %d actors, but %d snapshot actors are missing. Snapshot retained.'
                           % (len(restored), len(missing)))
    SNAPSHOT.unlink()
    print('Restored original visibility for %d actors; source map was not saved' % len(restored))


if __name__ == '__main__':
    ground_only()
