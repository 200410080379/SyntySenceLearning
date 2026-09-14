"""Switch to one of the saved building study cameras."""
import unreal

def view(name='01_Overview'):
    e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert e.get_editor_world().get_path_name()=='/Game/SyntySenceLearning/PolygonApocalypse/ExpandedNeighborhood/L_ExpandedNeighborhood.L_ExpandedNeighborhood'
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    a=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='BUILDING_VIEW_'+name)
    e.set_level_viewport_camera_info(a.get_actor_location(),a.get_actor_rotation())
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    levels.set_level_viewport_fov(a.camera_component.field_of_view,levels.get_active_viewport_config_key())
    levels.editor_set_game_view(True);actors.clear_actor_selection_set()

if __name__=='__main__':view()
