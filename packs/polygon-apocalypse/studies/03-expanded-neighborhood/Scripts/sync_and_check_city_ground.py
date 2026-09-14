"""Apply reviewed layout changes to this test map only; verify live instances."""
import hashlib,json
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[1]
LEVEL='/Game/SyntySenceLearning/PolygonApocalypse/ExpandedNeighborhood/L_ExpandedNeighborhood'

def main(sync=True):
    raw=(ROOT/'Data/Layout.json').read_bytes();plan=json.loads(raw)
    assert plan['map']==LEVEL,'Unexpected output map: '+plan['map']
    override_path=ROOT/'Data/MaterialOverride.json'
    override=json.loads(override_path.read_text()) if override_path.exists() else None
    world_path=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()
    assert world_path==plan['map']+'.'+plan['map'].split('/')[-1],world_path
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    parts=[a for a in actors if unreal.Name('CityGroundValidation') in a.tags]
    assert len(parts)==len(plan['tiles']), 'Unexpected tile count; refusing sync'
    changed=0
    for r in plan['tiles']:
        candidates=[a for a in parts if unreal.Name('Tile_%02d_%02d'%(r['i'],r['j'])) in a.tags]
        assert len(candidates)==1,(r['i'],r['j'],len(candidates))
        a=candidates[0];c=a.static_mesh_component
        if not sync:continue
        if c.static_mesh.get_path_name()!=r['mesh']:
            c.set_static_mesh(unreal.load_asset(r['mesh']));changed+=1
        if override:
            for i,s in enumerate(c.static_mesh.static_materials):
                original=s.material_interface
                desired=override['instance_material'] if original and original.get_path_name()==override['source_material'] else original.get_path_name() if original else None
                if desired:c.set_material(i,unreal.load_asset(desired))
        # The only modifications are to instances owned by this validation map.
        x,y,z=r['location'];a.set_actor_location(unreal.Vector(x=x,y=y,z=z),False,False)
        a.set_actor_rotation(unreal.Rotator(yaw=r['yaw']),False)
        a.set_actor_label('Ground_%02d_%02d_%s'%(r['i'],r['j'],r['name'].removeprefix('SM_Env_')))
        a.set_folder_path('CityGround/'+r['role'])
    if sync:assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    failures=[]
    for r in plan['tiles']:
        a=next(a for a in parts if unreal.Name('Tile_%02d_%02d'%(r['i'],r['j'])) in a.tags)
        c=a.static_mesh_component
        if c.static_mesh.get_path_name()!=r['mesh']:failures.append('mesh '+a.get_actor_label())
        if max(abs(a-b) for a,b in zip(a.get_actor_location().to_tuple(),r['location']))>.001:failures.append('location '+a.get_actor_label())
        rot=a.get_actor_rotation()
        if abs((rot.yaw-r['yaw']+180)%360-180)>.001 or abs(rot.pitch)>.001 or abs(rot.roll)>.001:failures.append('rotation '+a.get_actor_label())
        if max(abs(v-1) for v in a.get_actor_scale3d().to_tuple())>.001:failures.append('scale '+a.get_actor_label())
        source_mats=[s.material_interface.get_path_name() if s.material_interface else None for s in c.static_mesh.static_materials]
        if override:source_mats=[override['instance_material'] if m==override['source_material'] else m for m in source_mats]
        actual_mats=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]
        if actual_mats!=source_mats or None in actual_mats:failures.append('material '+a.get_actor_label())
    result={'world':world_path,'surface_size_m':plan['surface_size_m'],'mesh_instances':len(parts),
        'unique_meshes':len(set(r['mesh'] for r in plan['tiles'])),'layout_sha256':hashlib.sha256(raw).hexdigest(),
        'changed_mesh_instances':changed,'read_only':not sync,'instance_validation_failures':failures,
        'expected_material_override':override,
        'all_original_source_meshes':all(a.static_mesh_component.static_mesh.get_path_name().startswith('/Game/PolygonApocalypse/') for a in parts),
        'all_scale_one':all(max(abs(v-1) for v in a.get_actor_scale3d().to_tuple())<.001 for a in parts)}
    (ROOT/'Data/BuildValidation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
    assert not failures,failures

if __name__=='__main__':main()
