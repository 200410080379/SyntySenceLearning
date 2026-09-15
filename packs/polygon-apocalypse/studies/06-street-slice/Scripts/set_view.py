"""Set one of the recorded editor cameras without changing the map's actors."""
import json
from pathlib import Path
import unreal
def main(camera='overview'):
    rows=json.loads((Path(__file__).resolve().parents[1]/'Data/Cameras.json').read_text(encoding='utf-8'))
    r=next(r for r in rows if r['id']==camera)
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert editor.get_editor_world().get_name()=='L_StreetSlice'
    p=unreal.Vector(*r['location']);t=unreal.Vector(*r['target'])
    editor.set_level_viewport_camera_info(p,unreal.MathLibrary.find_look_at_rotation(p,t))
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    levels.editor_set_game_view(True)
    levels.set_level_viewport_fov(r['fov'],levels.get_active_viewport_config_key())
if __name__=='__main__':main()
