"""Prepare an independent map; build final authored rows after native Landscape creation."""
import json, runpy
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[1]
LEVEL='/Game/SyntySenceLearning/PolygonApocalypse/StreetSlice/L_StreetSlice'
MATERIAL='/Game/SyntySenceLearning/PolygonApocalypse/StreetSlice/Materials/M_StreetLandscape'

def main(stage='build'):
    lib=unreal.EditorAssetLibrary
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if stage=='prepare':
        if lib.does_asset_exist(LEVEL):raise RuntimeError('Target already exists; preserve it and use the existing map')
        dirty=list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())
        if dirty:raise RuntimeError('Save your current work before switching maps')
        if not lib.does_asset_exist(MATERIAL):
            mat=lib.duplicate_asset('/Game/Synty/PolygonGeneric/LandscapeMaterial/M_Land_Woods',MATERIAL)
            if not mat:raise RuntimeError('Missing Woodland Landscape material dependency')
            lib.save_loaded_asset(mat)
        if not levels.new_level(LEVEL,False):raise RuntimeError('Cannot create target map')
        print('Create native Landscape: 63 quads, 1 section, 2x2 components, scale100, centre0, own M_StreetLandscape. Then run create_terrain.py and build_scene.py.')
        return
    if stage!='build':raise ValueError(stage)
    w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert w.get_path_name()==LEVEL+'.L_StreetSlice'
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    existing=actors.get_all_level_actors()
    assert any(isinstance(a,unreal.Landscape) and len(a.get_components_by_class(unreal.LandscapeComponent))==4 for a in existing), 'Native Landscape must be created first'
    assert not any(a.get_actor_label().startswith(('STREET_','Town_')) for a in existing), 'Existing scene preserved: do not duplicate it'
    rows=json.loads((ROOT/'Data/Layout.json').read_text(encoding='utf-8'))
    decals=json.loads((ROOT/'Data/Decals.json').read_text(encoding='utf-8'))
    meshes={p:unreal.load_asset(p) for p in {r['mesh'] for r in rows}}
    mats={p:unreal.load_asset(p) for p in {p for r in rows for p in r['materials']}|{r['material'] for r in decals}}
    missing=[p for p,a in {**meshes,**mats}.items() if not a]
    if missing:raise RuntimeError('Missing dependencies: '+str(missing))
    cube=unreal.load_asset('/Engine/EngineResources/GrayLightTextureCube')
    skyclass=unreal.load_class(None,'/Engine/EngineSky/BP_Sky_Sphere.BP_Sky_Sphere_C')
    assert cube and skyclass
    for r in rows:
        a=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*r['location']),unreal.Rotator(**r['rotation']))
        a.set_actor_label(r['id']);a.set_folder_path(r['folder']);a.set_actor_scale3d(unreal.Vector(*r['scale']));a.tags=[unreal.Name(t) for t in r['tags']]
        c=a.static_mesh_component;c.set_static_mesh(meshes[r['mesh']])
        for i,p in enumerate(r['materials']):c.set_material(i,mats[p])
        c.set_collision_profile_name(r['collision_profile'])
    for r in decals:
        a=actors.spawn_actor_from_class(unreal.DecalActor,unreal.Vector(*r['location']),unreal.Rotator(**r['rotation']))
        a.set_actor_label(r['id']);a.set_folder_path(r['folder']);a.set_actor_scale3d(unreal.Vector(*r['scale']))
        c=a.get_component_by_class(unreal.DecalComponent);c.set_decal_material(mats[r['material']]);c.set_editor_property('decal_size',unreal.Vector(*r['size']));c.set_editor_property('fade_screen_size',.001)
    runpy.run_path(str(ROOT/'Scripts/environment.py'))['_environment'](actors,cube,skyclass)
    if not levels.save_current_level():raise RuntimeError('Save failed')
    runpy.run_path(str(ROOT/'Scripts/set_view.py'))['main']('overview')
    print(json.dumps({'meshes':len(rows),'decals':len(decals),'saved':True}))

if __name__=='__main__':main()
