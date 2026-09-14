"""Create this study's derived materials without overwriting existing assets."""
import unreal

ASSET='/Game/SyntySenceLearning/PolygonApocalypse/AftermathTown'
ROAD='/Game/SyntySenceLearning/PolygonApocalypse/ExpandedNeighborhood/Materials'

def duplicate_if_missing(source,target):
    lib=unreal.EditorAssetLibrary
    if lib.does_asset_exist(target):
        material=unreal.load_asset(target)
        assert isinstance(material,unreal.MaterialInterface),target
        return material,False
    assert lib.does_asset_exist(source),'Missing required source: '+source
    material=lib.duplicate_asset(source,target)
    assert material,target
    return material,True

def main():
    lib=unreal.EditorAssetLibrary;ml=unreal.MaterialEditingLibrary
    base,new=duplicate_if_missing('/Game/PolygonApocalypse/Materials/Base/M_PolygonApocalypse_Base',ROAD+'/M_Road_AtlasSampling')
    if new:
        todo=[ml.get_material_property_input_node(base,unreal.MaterialProperty.MP_BASE_COLOR)];seen=set();changed=0
        while todo:
            node=todo.pop()
            if not node or node.get_path_name() in seen:continue
            seen.add(node.get_path_name())
            if isinstance(node,unreal.MaterialExpressionTextureSampleParameter2D) and str(node.get_editor_property('parameter_name'))=='BaseTexture':
                node.set_editor_property('mip_value_mode',unreal.TextureMipValueMode.TMVM_MIP_BIAS)
                node.set_editor_property('const_mip_value',-3);changed+=1
            todo.extend(ml.get_inputs_for_material_expression(base,node))
        assert changed==1,'Unexpected source road material graph'
        ml.recompile_material(base);assert lib.save_loaded_asset(base)
    inst,new=duplicate_if_missing('/Game/PolygonApocalypse/Materials/Misc/MI_PolygonApocalypse_Road_Mat_01',ROAD+'/MI_Road_AtlasSampling')
    if new:
        ml.set_material_instance_parent(inst,base);ml.update_material_instance(inst);assert lib.save_loaded_asset(inst)
    specs=[('Dirt03','Generic_Decal_Grunge_03',.48,(.035,.029,.020)),('Dirt04','Generic_Decal_Grunge_04',.42,(.042,.034,.021)),('Moss','Generic_Decal_Grunge_04',.45,(.084,.102,.047)),('Crack01','Generic_Decal_Crack_01',.65,(.018,.020,.015)),('Crack02','Generic_Decal_Crack_02',.6,(.018,.019,.015)),('Oil','Generic_Decal_Pool_01',.67,(.016,.018,.014)),('Tyre','Generic_Decals_Tyre_01',.36,(.022,.023,.019))]
    for key,source,opacity,color in specs:
        m,new=duplicate_if_missing('/Game/Synty/PolygonGeneric/Materials/Decals/'+source,ASSET+'/Materials/MI_Surface_'+key)
        if new:
            ml.set_material_instance_scalar_parameter_value(m,'Opasity_Level',opacity)
            ml.set_material_instance_vector_parameter_value(m,'color',unreal.LinearColor(r=color[0],g=color[1],b=color[2],a=1))
            ml.update_material_instance(m);assert lib.save_loaded_asset(m)
    for name in ['MI_Alpine_GroundCover_01','MI_Alpine_Bush_02']:
        m,new=duplicate_if_missing('/Game/Synty/PolygonNatureBiomes/PNB_Alpine_Mountain/Materials/Plants/'+name,ASSET+'/Materials/'+name+'_Roof')
        if new:
            ml.set_material_instance_vector_parameter_value(m,'Leaf_Colour_Overlay',unreal.LinearColor(r=.12,g=.20,b=.065,a=1))
            ml.set_material_instance_scalar_parameter_value(m,'LargeWindIntensityMultiplier',25)
            ml.update_material_instance(m);assert lib.save_loaded_asset(m)
    print('Study materials available; existing assets retained.')

if __name__=='__main__':main()
