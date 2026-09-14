"""Read-only live verification of building parts and the unchanged ground recipe."""
import hashlib,json
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[1]

def main():
    raw=(ROOT/'Data/Layout.json').read_bytes();rows=json.loads(raw)
    plan=json.loads((ROOT/'Data/Plan.json').read_text())
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()
    assert world==plan['map']+'.'+plan['map'].rsplit('/',1)[-1]
    all_actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    parts=[a for a in all_actors if unreal.Name('LearnedBuildingPlacement') in a.tags]
    failures=[];by_id={}
    for a in parts:
        keys=[str(t).removeprefix('BuildingId_') for t in a.tags if str(t).startswith('BuildingId_')]
        if len(keys)!=1 or keys[0] in by_id:failures.append('duplicate/missing building id '+a.get_actor_label())
        else:by_id[keys[0]]=a
    if len(parts)!=len(rows):failures.append('building component count mismatch')
    for r in rows:
        if r['id'] not in by_id:failures.append('missing '+r['id']);continue
        a=by_id[r['id']];c=a.static_mesh_component
        if not c.static_mesh or c.static_mesh.get_path_name()!=r['mesh']:failures.append('mesh '+r['id'])
        if max(abs(v-w) for v,w in zip(a.get_actor_location().to_tuple(),r['location']))>.002:failures.append('location '+r['id'])
        if max(abs(v-w) for v,w in zip(a.get_actor_scale3d().to_tuple(),r['scale']))>.0001:failures.append('scale '+r['id'])
        actual=a.get_actor_rotation();expected=unreal.Rotator(pitch=r['rotation']['pitch'],yaw=r['rotation']['yaw'],roll=r['rotation']['roll'])
        # Compare orientation axes, allowing equivalent Euler representations at gimbal lock.
        for axis in ('get_forward_vector','get_right_vector','get_up_vector'):
            fn=getattr(unreal.MathLibrary,axis)
            if (fn(actual)-fn(expected)).length()>.0001:failures.append('rotation '+r['id']);break
        mats=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]
        if mats!=r['materials']:failures.append('materials '+r['id'])
    ground_raw=(ROOT.parent/'03-expanded-neighborhood/Data/Layout.json').read_bytes()
    ground=json.loads(ground_raw);ground_failures=[]
    if hashlib.sha256(ground_raw).hexdigest()!=plan['ground_layout_sha256']:ground_failures.append('ground recipe hash')
    ground_actors=[a for a in all_actors if unreal.Name('CityGroundValidation') in a.tags]
    if len(ground_actors)!=len(ground['tiles']):ground_failures.append('ground actor count')
    for r in ground['tiles']:
        tag=unreal.Name('Tile_%02d_%02d'%(r['i'],r['j']))
        found=[a for a in ground_actors if tag in a.tags]
        if len(found)!=1:ground_failures.append(str(tag));continue
        a=found[0];rot=a.get_actor_rotation()
        if a.static_mesh_component.static_mesh.get_path_name()!=r['mesh']:ground_failures.append('ground mesh '+str(tag))
        if max(abs(v-w) for v,w in zip(a.get_actor_location().to_tuple(),r['location']))>.002:ground_failures.append('ground position '+str(tag))
        if max(abs(v-1) for v in a.get_actor_scale3d().to_tuple())>.0001:ground_failures.append('ground scale '+str(tag))
        if abs((rot.yaw-r['yaw']+180)%360-180)>.001 or abs(rot.pitch)>.001 or abs(rot.roll)>.001:ground_failures.append('ground rotation '+str(tag))
    result={'world':world,'read_only':True,'layout_sha256':hashlib.sha256(raw).hexdigest(),
            'mesh_instances':len(parts),'main_buildings':plan['building_main_count'],'canopies':plan['canopy_count'],
            'unique_meshes':len({r['mesh'] for r in rows}),'instance_validation_failures':failures,
            'ground_instances':len(ground_actors),'ground_layout_sha256':hashlib.sha256(ground_raw).hexdigest(),'ground_failures':ground_failures,
            'limits':['Checks declared building component transforms and materials; does not establish collision/navigation/interior gameplay.',
                      'Ground geometry placement verified unchanged; visual occlusion by buildings is a separate consideration.']}
    (ROOT/'Data/BuildValidation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
    assert not failures and not ground_failures

if __name__=='__main__':main()
