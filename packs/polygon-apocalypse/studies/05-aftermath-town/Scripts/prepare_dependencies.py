"""Copy locally owned asset packages into their required mounts; never overwrite differences."""
import argparse,hashlib,json,shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True,type=Path,help='Destination .uproject')
    parser.add_argument('--apocalypse-content',required=True,type=Path,help='Source Content containing PolygonApocalypse')
    parser.add_argument('--woodland-content',required=True,type=Path,help='Source Content containing Synty/PolygonGeneric and PolygonMapsWoodlandApocalypse')
    parser.add_argument('--alpine-content',required=True,type=Path,help='Source Content containing Biomes/PNB_Alpine_Mountain')
    args=parser.parse_args();project=args.project.resolve(strict=True)
    assert project.suffix=='.uproject',project
    destination=project.parent/'Content';sources={'apocalypse':args.apocalypse_content.resolve(strict=True),'woodland':args.woodland_content.resolve(strict=True),'alpine':args.alpine_content.resolve(strict=True)}
    dependencies=json.loads((ROOT/'Data/Dependencies.json').read_text())
    plan={}
    for group in dependencies['copy_roots']:
        root=sources[group['source_pack']]/group['source_relative']
        assert root.is_dir(),'Missing source directory: '+str(root)
        for source in root.rglob('*'):
            if source.is_file() and source.suffix.lower() in {'.uasset','.umap','.uexp','.ubulk'}:
                target=destination/group['target_relative']/source.relative_to(root)
                plan[target]=source
    for alias in dependencies['aliases']:
        source=sources[alias['source_pack']]/alias['source_relative'];assert source.is_file(),source
        target=destination/alias['target_relative']
        if target in plan:assert digest(source)==digest(plan[target]),target
        plan[target]=source
    # Complete preflight before the first write. This leaves user-modified files intact.
    hashes={};conflicts=[]
    for target,source in plan.items():
        assert target.resolve().is_relative_to(destination.resolve()),target
        hashes[target]=digest(source)
        if target.exists() and digest(target)!=hashes[target]:conflicts.append(str(target))
    assert not conflicts,'Existing files differ; no files copied: '+json.dumps(conflicts)
    copied=0;existing=0
    for target,source in plan.items():
        if target.exists():existing+=1;continue
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        assert digest(target)==hashes[target],target
        copied+=1
    print(json.dumps({'copied_files':copied,'identical_existing_files':existing,'source_files_modified':0}))
    print('In UE: AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(["/Game/PolygonApocalypse", "/Game/Synty", "/Game/Biomes"], force_rescan=True)')

if __name__=='__main__':main()
