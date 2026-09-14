"""Read-only UE instance check against the public learning manifest.

Open the saved study map before running. This records what is currently loaded;
it cannot itself prove that the caller reopened a previously saved map.
"""
import collections
import hashlib
import json
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[1]
MAP = '/Game/SyntySenceLearning/PolygonApocalypse/GroundAssembly/L_GroundAssembly_Study'
TAG = 'GroundAssemblyStudy'


def angle_delta(first, second):
    return abs((first - second + 180) % 360 - 180)


def main():
    world_path = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()
    expected_world = MAP + '.' + MAP.rsplit('/', 1)[-1]
    if world_path != expected_world:
        raise RuntimeError('Open the learning map before validating: ' + expected_world)
    raw = (ROOT / 'Data/LearningMapManifest.json').read_bytes()
    manifest = json.loads(raw)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    parts = [actor for actor in actors if unreal.Name(TAG) in actor.tags]
    failures, matched = [], set()
    for index, row in enumerate(manifest):
        # Match by geometry placement, not Location alone: different rotations can
        # intentionally share a corner pivot and occupy adjacent areas.
        candidates = []
        for actor in parts:
            if not isinstance(actor, unreal.StaticMeshActor):
                continue
            comp = actor.static_mesh_component
            if not comp.static_mesh or comp.static_mesh.get_path_name() != row['mesh']:
                continue
            if str(actor.get_folder_path()) != 'Learning/' + row['folder']:
                continue
            if max(abs(a - b) for a, b in zip(actor.get_actor_location().to_tuple(), row['study_location'])) > .01:
                continue
            rotation = actor.get_actor_rotation()
            if max(angle_delta(getattr(rotation, key), value) for key, value in row['rotation'].items()) > .01:
                continue
            candidates.append(actor)
        if len(candidates) != 1:
            failures.append({'record': index, 'mesh': row['mesh'], 'matching_actors': len(candidates)})
            continue
        actor = candidates[0]
        actor_path = actor.get_path_name()
        if actor_path in matched:
            failures.append({'record': index, 'error': 'Actor matches more than one manifest record'})
        matched.add(actor_path)
        if max(abs(a - b) for a, b in zip(actor.get_actor_scale3d().to_tuple(), row['scale'])) > .001:
            failures.append({'record': index, 'error': 'Scale differs'})
        comp = actor.static_mesh_component
        materials = [comp.get_material(i).get_path_name() if comp.get_material(i) else None
                     for i in range(comp.get_num_materials())]
        if materials != row['materials']:
            failures.append({'record': index, 'error': 'Materials differ', 'actual_materials': materials})
    if len(parts) != len(manifest):
        failures.append({'error': 'Actor count mismatch', 'actual': len(parts), 'expected': len(manifest)})
    unmatched = [actor.get_path_name() for actor in parts if actor.get_path_name() not in matched]
    if unmatched:
        failures.append({'error': 'Unmatched tagged actors', 'actors': unmatched})
    result = {
        'world': world_path, 'read_only': True, 'manifest_sha256': hashlib.sha256(raw).hexdigest(),
        'expected_mesh_actors': len(manifest), 'actual_mesh_actors': len(parts),
        'group_counts': dict(collections.Counter(row['folder'] for row in manifest)),
        'tolerances': {'position_cm': .01, 'angle_degrees': .01, 'scale': .001},
        'failures': failures,
    }
    (ROOT / 'Data/Validation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
    if failures:
        raise RuntimeError('Learning map validation failed; see Data/Validation.json')


if __name__ == '__main__':
    main()
