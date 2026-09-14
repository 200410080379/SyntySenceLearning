"""Show an authored town camera from the portable camera recipe."""
import json
from pathlib import Path

import unreal


ROOT = Path(__file__).resolve().parents[1]
LEVEL = '/Game/SyntySenceLearning/PolygonApocalypse/AftermathTown/L_AftermathTown'


def view(name='01_Overview'):
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_editor_world().get_path_name() != LEVEL + '.L_AftermathTown':
        raise RuntimeError('Open the AftermathTown study map before changing its view')
    cameras = json.loads((ROOT / 'Data/Cameras.json').read_text(encoding='utf-8-sig'))
    matches = [row for row in cameras if row['name'] == name]
    if len(matches) != 1:
        raise ValueError('Choose one camera name: ' + ', '.join(row['name'] for row in cameras))
    row = matches[0]
    position = row['location']
    angles = row['rotation']
    editor.set_level_viewport_camera_info(
        unreal.Vector(x=position[0], y=position[1], z=position[2]),
        unreal.Rotator(pitch=angles['pitch'], yaw=angles['yaw'], roll=angles['roll']))
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    levels.set_level_viewport_fov(row['fov'], levels.get_active_viewport_config_key())
    levels.editor_set_game_view(True)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).clear_actor_selection_set()
    print(json.dumps({'view': name, 'fov': row['fov']}))


if __name__ == '__main__':
    view()
