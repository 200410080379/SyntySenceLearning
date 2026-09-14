"""Read-only comparison of saved actors with the portable authoring recipe."""
import hashlib,json
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[1]
LEVEL='/Game/SyntySenceLearning/PolygonApocalypse/AftermathTown/L_AftermathTown'

def main(level=LEVEL,output=None):
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert world.get_path_name()==level+'.'+level.rsplit('/',1)[-1],world.get_path_name()
    actors=list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
    by_label={};errors=[]
    for a in actors:by_label.setdefault(a.get_actor_label(),[]).append(a)
    meshrows=json.loads((ROOT/'Data/Layout.json').read_text());decals=json.loads((ROOT/'Data/Decals.json').read_text());cameras=json.loads((ROOT/'Data/Cameras.json').read_text())
    def vec(v):return [v.x,v.y,v.z]
    def close(a,b,tol):return max(abs(x-y) for x,y in zip(a,b))<=tol
    def actor(row,label):
        found=by_label.get(label,[])
        if len(found)!=1:errors.append({'id':label,'error':'actor_count','count':len(found)});return None
        a=found[0]
        if not close(vec(a.get_actor_location()),row['location'],.01):errors.append({'id':label,'error':'position'})
        if 'scale' in row and not close(vec(a.get_actor_scale3d()),row['scale'],.0001):errors.append({'id':label,'error':'scale'})
        r=unreal.Rotator(**row['rotation'])
        for method in ['get_forward_vector','get_right_vector','get_up_vector']:
            f=getattr(unreal.MathLibrary,method)
            if not close(vec(f(a.get_actor_rotation())),vec(f(r)),.0001):errors.append({'id':label,'error':'orientation'});break
        return a
    for row in meshrows:
        a=actor(row,row['id'])
        if not a:continue
        if not isinstance(a,unreal.StaticMeshActor):errors.append({'id':row['id'],'error':'class'});continue
        c=a.static_mesh_component
        if not c.static_mesh or c.static_mesh.get_path_name()!=row['mesh']:errors.append({'id':row['id'],'error':'mesh'})
        actual=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]
        if actual!=row['materials']:errors.append({'id':row['id'],'error':'materials'})
        if str(c.get_collision_profile_name())!=row['collision_profile']:errors.append({'id':row['id'],'error':'collision_profile'})
        if set(str(t) for t in a.tags)!=set(row['tags']):errors.append({'id':row['id'],'error':'tags'})
        if str(a.get_folder_path())!=row['folder']:errors.append({'id':row['id'],'error':'folder'})
    for row in decals:
        a=actor(row,row['id'])
        if not a:continue
        c=a.get_component_by_class(unreal.DecalComponent)
        if not c:errors.append({'id':row['id'],'error':'decal_component'});continue
        m=c.get_editor_property('decal_material')
        if not m or m.get_path_name()!=row['material']:errors.append({'id':row['id'],'error':'decal_material'})
        if not close(vec(c.get_editor_property('decal_size')),row['size'],.01):errors.append({'id':row['id'],'error':'decal_size'})
    for row in cameras:
        a=actor(row,'TOWN_VIEW_'+row['name'])
        if a and abs(a.camera_component.field_of_view-row['fov'])>.001:errors.append({'id':row['name'],'error':'camera_fov'})
    actual_counts={'mesh_instances':sum(isinstance(a,unreal.StaticMeshActor) for a in actors),'decals':sum(isinstance(a,unreal.DecalActor) for a in actors),'cameras':sum(isinstance(a,unreal.CameraActor) for a in actors)}
    expected={'mesh_instances':len(meshrows),'decals':len(decals),'cameras':len(cameras)}
    if actual_counts!=expected:errors.append({'error':'inventory','expected':expected,'actual':actual_counts})
    result={'map':level,'engine':unreal.SystemLibrary.get_engine_version(),'layout_sha256':hashlib.sha256((ROOT/'Data/Layout.json').read_bytes()).hexdigest(),'decals_sha256':hashlib.sha256((ROOT/'Data/Decals.json').read_bytes()).hexdigest(),'cameras_sha256':hashlib.sha256((ROOT/'Data/Cameras.json').read_bytes()).hexdigest(),'expected':expected,'actual':actual_counts,'unique_meshes':len({r['mesh'] for r in meshrows}),'errors':errors,'scope':'Actor identity, mesh/material references, transforms, folders, tags, collision profiles, decal bounds and camera FOV. This is not mesh contact, collision geometry, navigation or target-platform performance certification.'}
    path=Path(output) if output else Path(unreal.Paths.project_saved_dir())/'SyntySenceLearning/AftermathTown/InstanceValidation.json'
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'map':level,**actual_counts,'errors':len(errors),'output':str(path)}))
    assert not errors,errors[:10]
    return result

if __name__=='__main__':main()
