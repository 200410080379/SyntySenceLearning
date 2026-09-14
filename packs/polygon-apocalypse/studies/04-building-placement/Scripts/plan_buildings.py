"""Place measured building assemblies into the existing four-block ground study."""
import hashlib,json,math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAP='/Game/SyntySenceLearning/PolygonApocalypse/ExpandedNeighborhood/L_ExpandedNeighborhood'
GROUPS=[
    ('SW_GasShop','CommercialSmall','SW_GasAndShops',[-5800,-5750,0],90),
    ('SW_GasCanopy','GasCanopy','SW_GasAndShops',[-5800,-3400,0],90),
    ('SW_Commercial','CommercialMedium','SW_GasAndShops',[-1600,-4750,0],90),
    ('SW_FrontShopA','ShopSmall01','SW_GasAndShops',[-2400,-2550,0],90),
    ('SW_FrontShopB','ShopSmall02','SW_GasAndShops',[-1050,-2550,0],90),
    ('SW_CornerShop','ShopSmall01','SW_GasAndShops',[650,-4750,0],0),
    ('NW_Diner','Diner','NW_Diner',[-6450,5100,0],270),
    ('NW_Cafe','Cafe','NW_Diner',[-4350,4500,0],180),
    ('NE_MotelWest','Motel','NE_Motel',[0,5900,0],270),
    ('NE_MotelMiddle','Motel','NE_Motel',[2950,5900,0],270),
    ('NE_MotelEast','Motel','NE_Motel',[5900,5900,0],270),
    ('NE_Reception','CommercialSmall','NE_Motel',[3000,2750,0],270),
    ('SE_AutoRepair','AutoRepair','SE_ServiceCourt',[6700,-3800,1],90),
    ('SE_PartsShop','ShopLarge02','SE_ServiceCourt',[6500,-5600,0],180),
]

def rotate(x,y,yaw):
    a=math.radians(yaw);return x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a)

def main():
    assemblies=json.loads((ROOT/'Data/Assemblies.json').read_text())
    instances=[];groups=[]
    for group,key,block,anchor,yaw in GROUPS:
        recipe=assemblies[key]
        groups.append({'id':group,'assembly':key,'block':block,'anchor':anchor,'yaw':yaw,'main_mesh':recipe['main_mesh'],'main_bounds':recipe['main_bounds']})
        for index,c in enumerate(recipe['components']):
            # One roof sign identifies the shared motel compound; keep all room/door assemblies.
            if group in ('NE_MotelWest','NE_MotelEast') and c['name']=='SM_Bld_Motel_01_Sign_01':continue
            x,y=rotate(c['location'][0],c['location'][1],yaw)
            instances.append({'id':group+'_%02d'%index,'group':group,'block':block,'assembly':key,'name':c['name'],'mesh':c['mesh'],
                'location':[round(anchor[0]+x,5),round(anchor[1]+y,5),round(anchor[2]+c['location'][2],5)],
                'rotation':{'pitch':c['rotation']['pitch'],'yaw':round((c['rotation']['yaw']+yaw+180)%360-180,5),'roll':c['rotation']['roll']},
                'scale':c['scale'],'materials':c['materials'],'main':c['main']})
    plan={'map':MAP,'ground_study':'03-expanded-neighborhood','expected_ground_tiles':1280,
          'ground_layout_sha256':'0c2cd123cd7121e73c1801cea5a8f4930a65b64abb8a121ec86655e8217820cb',
          'groups':groups,'building_main_count':sum(g[1]!='GasCanopy' for g in GROUPS),'canopy_count':1,
          'component_choices':{'motel_roof_sign':'Only NE_MotelMiddle uses the measured roof sign; west/east omit this optional sign.'},
          'approach':'Additive architecture study on the existing 200 x 160 m ground; original ground placements remain unchanged.',
          'limits':['Building and canopy main meshes have unit scale; measured source doors/signs retain authored scale or mirror.',
                    'Building main bounds include roofs, stairs and projections; they are conservative spacing checks, not exact wall polygons.',
                    'No collision, navmesh, vehicle turning or interior gameplay is established by this layout.']}
    for name,value in [('Layout.json',instances),('Plan.json',plan)]:
        (ROOT/'Data'/name).write_bytes((json.dumps(value,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({'groups':len(groups),'main_buildings':plan['building_main_count'],'components':len(instances),'layout_sha256':hashlib.sha256((ROOT/'Data/Layout.json').read_bytes()).hexdigest()}))

if __name__=='__main__':main()
