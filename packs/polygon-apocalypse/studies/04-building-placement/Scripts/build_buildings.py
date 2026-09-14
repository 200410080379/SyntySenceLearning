"""Add measured building assemblies to lesson 03 without changing its ground."""
import hashlib,json
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[1]
TAG='LearnedBuildingPlacement'

def main():
    plan=json.loads((ROOT/'Data/Plan.json').read_text())
    rows=json.loads((ROOT/'Data/Layout.json').read_text())
    e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world=e.get_editor_world().get_path_name()
    assert world==plan['map']+'.'+plan['map'].rsplit('/',1)[-1],world
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(),'Save current map changes first'
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages(),'Save current content changes first'
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    before=list(actors.get_all_level_actors())
    assert not any(unreal.Name(TAG) in a.tags for a in before),'This lesson is already placed; use targeted edits, not duplicate placement'
    assert sum(unreal.Name('CityGroundValidation') in a.tags for a in before)==plan['expected_ground_tiles']
    ground_path=ROOT.parent/'03-expanded-neighborhood/Data/Layout.json'
    assert hashlib.sha256(ground_path.read_bytes()).hexdigest()==plan['ground_layout_sha256'],'Unexpected ground recipe'
    meshes={};materials={}
    for row in rows:
        path=row['mesh'];assert path.startswith('/Game/PolygonApocalypse/'),path
        if path not in meshes:meshes[path]=unreal.load_asset(path)
        assert isinstance(meshes[path],unreal.StaticMesh),path
        for p in row['materials']:
            assert p,'Missing material'
            if p not in materials:materials[p]=unreal.load_asset(p)
            assert materials[p],p
    with unreal.ScopedEditorTransaction('Place measured building assemblies'):
        for row in rows:
            p=row['location'];r=row['rotation'];scale=row['scale']
            a=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(x=p[0],y=p[1],z=p[2]),unreal.Rotator(pitch=r['pitch'],yaw=r['yaw'],roll=r['roll']))
            assert a,row['id']
            a.static_mesh_component.set_static_mesh(meshes[row['mesh']])
            a.set_actor_scale3d(unreal.Vector(x=scale[0],y=scale[1],z=scale[2]))
            for i,p in enumerate(row['materials']):a.static_mesh_component.set_material(i,materials[p])
            a.set_actor_label('Building_'+row['id']+'_'+row['name'].removeprefix('SM_'))
            a.set_folder_path('Buildings/'+row['block']+'/'+row['group'])
            a.tags=[unreal.Name(TAG),unreal.Name('BuildingId_'+row['id']),unreal.Name('BuildingGroup_'+row['group'])]
        views=[('01_Overview',(16128,-23520,26320),(0,0,150),55),
               ('02_MainStreet',(-6500,-800,1600),(4500,-500,400),68),
               ('03_GasStation',(-9700,-1200,3900),(-5700,-4200,150),55),
               ('04_Diner',(-8100,1900,2400),(-6250,5100,180),55),
               ('05_Motel',(9600,-2100,5800),(2900,4800,180),55),
               ('06_AutoRepair',(4500,-1000,2200),(6800,-4000,180),55),
               ('07_Shops',(-3500,800,2300),(-1000,-3700,200),55),
               ('08_GasEntry',(-7600,-1500,280),(-5800,-3400,180),60)]
        for name,pos,target,fov in views:
            p=unreal.Vector(x=pos[0],y=pos[1],z=pos[2]);t=unreal.Vector(x=target[0],y=target[1],z=target[2])
            a=actors.spawn_actor_from_class(unreal.CameraActor,p,unreal.MathLibrary.find_look_at_rotation(p,t))
            a.set_actor_label('BUILDING_VIEW_'+name);a.set_folder_path('Buildings/Views');a.tags=[unreal.Name('BuildingStudyView')]
            a.camera_component.set_field_of_view(fov)
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assert levels.save_current_level()
    print(json.dumps({'map':plan['map'],'building_components':len(rows),'main_buildings':plan['building_main_count'],'canopies':plan['canopy_count'],'ground_actors_touched':0}))

if __name__=='__main__':main()
