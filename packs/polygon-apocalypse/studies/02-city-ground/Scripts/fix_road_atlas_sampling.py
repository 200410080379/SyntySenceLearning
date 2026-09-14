"""Keep source assets intact; prevent distant palette bleed in road instances."""
import json
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[1]
SOURCE_BASE='/Game/PolygonApocalypse/Materials/Base/M_PolygonApocalypse_Base'
SOURCE_INSTANCE='/Game/PolygonApocalypse/Materials/Misc/MI_PolygonApocalypse_Road_Mat_01'
ASSET_ROOT='/Game/SyntySenceLearning/PolygonApocalypse/CityGround'
BASE=ASSET_ROOT+'/Materials/M_Road_AtlasSampling'
INSTANCE=ASSET_ROOT+'/Materials/MI_Road_AtlasSampling'

def main():
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()
    assert world==ASSET_ROOT+'/L_CityGround_Validation.L_CityGround_Validation',world
    lib=unreal.EditorAssetLibrary
    base=unreal.load_asset(BASE) if lib.does_asset_exist(BASE) else lib.duplicate_asset(SOURCE_BASE,BASE)
    inst=unreal.load_asset(INSTANCE) if lib.does_asset_exist(INSTANCE) else lib.duplicate_asset(SOURCE_INSTANCE,INSTANCE)
    assert base and inst
    todo=[unreal.MaterialEditingLibrary.get_material_property_input_node(base,unreal.MaterialProperty.MP_BASE_COLOR)]
    seen=set();changed=0
    while todo:
        node=todo.pop()
        if not node or node.get_path_name() in seen:continue
        seen.add(node.get_path_name())
        if isinstance(node,unreal.MaterialExpressionTextureSampleParameter2D) and str(node.get_editor_property('parameter_name'))=='BaseTexture':
            # Source road atlas contains a thin palette strip at its bottom edge.
            # Sampling a finer mip protects asphalt UVs near that strip at distance.
            node.set_editor_property('mip_value_mode',unreal.TextureMipValueMode.TMVM_MIP_BIAS)
            node.set_editor_property('const_mip_value',-3)
            changed+=1
        todo.extend(unreal.MaterialEditingLibrary.get_inputs_for_material_expression(base,node))
    assert changed==1,changed
    unreal.MaterialEditingLibrary.recompile_material(base)
    unreal.MaterialEditingLibrary.set_material_instance_parent(inst,base)
    unreal.MaterialEditingLibrary.update_material_instance(inst)
    assert lib.save_loaded_asset(base)
    assert lib.save_loaded_asset(inst)
    count=0
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if unreal.Name('CityGroundValidation') not in a.tags:continue
        c=a.static_mesh_component
        for i in range(c.get_num_materials()):
            original=c.static_mesh.static_materials[i].material_interface
            if original and original.get_path_name()==SOURCE_INSTANCE+'.'+SOURCE_INSTANCE.split('/')[-1]:
                c.set_material(i,inst);count+=1
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    result={'source_material':SOURCE_INSTANCE+'.'+SOURCE_INSTANCE.split('/')[-1],
        'instance_material':INSTANCE+'.'+INSTANCE.split('/')[-1],
        'base_material':BASE+'.'+BASE.split('/')[-1], 'base_texture_mip_bias':-3,
        'affected_component_slots':count,'source_assets_modified':False,
        'reason':'Source road texture includes a bottom palette strip; distant mip filtering bled yellow into asphalt tile edges.',
        'tradeoff':'Road BaseTexture samples finer mip levels; no global rendering or texture-cache setting is changed.'}
    (ROOT/'Data/MaterialOverride.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__':main()
