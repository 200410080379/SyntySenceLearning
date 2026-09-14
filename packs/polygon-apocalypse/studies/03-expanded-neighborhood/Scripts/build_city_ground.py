"""Build this study once; refuse existing maps or unsaved editor packages.

Save or discard your current changes yourself before running this script. It
never saves the source Demo or other currently open content on your behalf.
"""
import json
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[1]
LEVEL='/Game/SyntySenceLearning/PolygonApocalypse/ExpandedNeighborhood/L_ExpandedNeighborhood'

def main():
    plan=json.loads((ROOT/'Data/Layout.json').read_text(encoding='utf-8'))
    level=plan['map']
    assert level==LEVEL,'Unexpected output map: '+level
    assert not unreal.EditorAssetLibrary.does_asset_exist(level),'Map exists: use targeted edits instead of overwriting'
    dirty=(list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())+
           list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()))
    assert not dirty,('Unsaved editor packages detected. Save or discard your changes before running; '
                      'this script will not save source assets: '+', '.join(p.get_path_name() for p in dirty))
    # Check every source reference before closing the current clean map.
    cache={}
    for r in plan['tiles']:
        assert r['mesh'].startswith('/Game/PolygonApocalypse/Meshes/Environments/'),r['mesh']
        assert r.get('scale',[1,1,1])==[1,1,1],'This study uses unscaled source modules'
        if r['mesh'] not in cache:cache[r['mesh']]=unreal.load_asset(r['mesh'])
        assert isinstance(cache[r['mesh']],unreal.StaticMesh),'Missing licensed source mesh: '+r['mesh']
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assert levels.new_level(level,is_partitioned_world=False)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for r in plan['tiles']:
        x,y,z=r['location']
        a=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(x=x,y=y,z=z),unreal.Rotator(yaw=r['yaw']))
        a.static_mesh_component.set_static_mesh(cache[r['mesh']])
        a.set_actor_label('Ground_%02d_%02d_%s'%(r['i'],r['j'],r['name'].removeprefix('SM_Env_')))
        a.set_folder_path('CityGround/'+r['role'])
        a.tags=[unreal.Name('CityGroundValidation'),unreal.Name('Tile_%02d_%02d'%(r['i'],r['j']))]
    sun=actors.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(z=2500),unreal.Rotator(pitch=-55,yaw=-30))
    sun.set_folder_path('CityGround/Lighting');sun.set_actor_label('CityGround_Sun')
    sun.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun.light_component.set_intensity(3)
    sun.light_component.set_light_color(unreal.LinearColor(r=1,g=.96,b=.9,a=1))
    sky=actors.spawn_actor_from_class(unreal.SkyLight,unreal.Vector(z=2000))
    sky.set_folder_path('CityGround/Lighting');sky.set_actor_label('CityGround_Fill')
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property('source_type',unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sky.light_component.set_editor_property('cubemap',unreal.load_asset('/Engine/EngineResources/GrayLightTextureCube.GrayLightTextureCube'))
    sky.light_component.set_intensity(.5)
    views=[('01_Overview',(16240,-23200,30160),(0,0,0),55),
           ('02_NorthT',(-7000,-5000,6800),(-3000,500,0),55),
           ('03_SouthT',(7200,4700,6500),(3000,-1000,0),55),
           ('04_GasAndShops',(-12000,-10000,10000),(-3500,-4000,0),55),
           ('05_Diner',(-12500,1500,8000),(-6000,3500,0),55),
           ('06_Motel',(12000,-2500,10500),(3200,3400,0),55),
           ('07_Pedestrian',(-5200,-2200,700),(-4800,-200,0),65),
           ('08_Top',(0,0,42000),(0,0,0),55)]
    for name,pos,target,fov in views:
        p=unreal.Vector(x=pos[0],y=pos[1],z=pos[2]);t=unreal.Vector(x=target[0],y=target[1],z=target[2])
        rotation=unreal.Rotator(pitch=-89.9,yaw=-90,roll=0) if name=='08_Top' else unreal.MathLibrary.find_look_at_rotation(p,t)
        c=actors.spawn_actor_from_class(unreal.CameraActor,p,rotation)
        c.set_actor_label('VIEW_'+name);c.set_folder_path('CityGround/Views')
        c.camera_component.set_field_of_view(fov)
    p=unreal.Vector(x=16240,y=-23200,z=30160)
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(p,
        unreal.MathLibrary.find_look_at_rotation(p,unreal.Vector(x=0,y=0,z=0)))
    levels.set_level_viewport_fov(55,levels.get_active_viewport_config_key())
    levels.editor_set_game_view(True);actors.clear_actor_selection_set()
    assert levels.save_current_level()
    print(json.dumps({'level':level,'ground_tiles':len(plan['tiles']),'mesh_types':len(cache)}))

if __name__=='__main__':main()
