"""Export local read-only LOD0 evidence from the user's licensed source assets.

Inputs: ../Data/Layout.json and the installed Polygon Apocalypse UE content.
Output: ../Data/CandidateGeometry.json, intentionally excluded from Git because
it contains source vertex data. No previous study or open Demo is required.
"""
import json
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[1]
ENV='/Game/PolygonApocalypse/Meshes/Environments/'
COUNTEREXAMPLES=(
    'SM_Env_Sidewalk_Straight_02',
    'SM_Env_Sidewalk_Driveway_01',
    'SM_Env_Sidewalk_Driveway_Wide_01',
    'SM_Env_Sidewalk_Straight_09',
    'SM_Env_Sidewalk_Straight_10',
    'SM_Env_Sidewalk_Crossing_01',
    'SM_Env_Sidewalk_Crossing_02',
)


def vec(value):
    return [round(value.x,5),round(value.y,5),round(value.z,5)]


def main():
    plan=json.loads((ROOT/'Data/Layout.json').read_text(encoding='utf-8'))
    paths={tile['mesh'] for tile in plan['tiles']}
    paths.update(ENV+name+'.'+name for name in COUNTEREXAMPLES)
    meshes={}
    for path in sorted(paths):
        assert path.startswith(ENV),'Unexpected source asset: '+path
        mesh=unreal.load_asset(path)
        assert isinstance(mesh,unreal.StaticMesh),'Missing licensed source mesh: '+path
        bounds=mesh.get_bounding_box()
        sections=[]
        for index in range(mesh.get_num_sections(0)):
            vertices,triangles,normals,uvs,tangents=unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh,0,index)
            sections.append({'vertices':[vec(vertex) for vertex in vertices],
                             'triangles':list(triangles)})
        assert sections and any(s['triangles'] for s in sections),'Empty LOD0 mesh: '+path
        meshes[mesh.get_path_name()]={
            'name':mesh.get_name(),'min':vec(bounds.min),'max':vec(bounds.max),
            'sections':sections,
            'materials':[slot.material_interface.get_path_name() if slot.material_interface else None
                         for slot in mesh.static_materials]}
    output=ROOT/'Data/CandidateGeometry.json'
    output.write_text(json.dumps(meshes,separators=(',',':'))+'\n',encoding='utf-8')
    print(json.dumps({'output':str(output),'mesh_count':len(meshes),
                      'read_only_source_assets':True,'include_in_git':False}))

if __name__=='__main__':main()
