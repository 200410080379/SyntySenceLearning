"""A new authored 80 m city ground layout, using measured source interfaces."""
import json,math,collections
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ENV='/Game/PolygonApocalypse/Meshes/Environments/'

def main():
    tiles=[]
    bands=[(0,1),(7,8),(14,15)]
    road_indices={n for pair in bands for n in pair}
    blocks=[(2,6,2,6,'SW_ParkingCourt'),(9,13,2,6,'SE_PavedSquare'),
            (2,6,9,13,'NW_PavedSquare'),(9,13,9,13,'NE_ServiceCourt')]
    crossing_cells={(i,j) for j in (5,10) for i in (7,8)}|{(i,j) for i in (5,10) for j in (7,8)}
    for j in range(16):
        for i in range(16):
            yaw=0;name='SM_Env_Road_Bare_01';role='Road/Junction'
            if i in road_indices or j in road_indices:
                if i in road_indices and j not in road_indices:
                    pair=next(p for p in bands if i in p)
                    name='SM_Env_Road_01';yaw=90 if i==pair[0] else 270;role='Road/Longitudinal'
                elif j in road_indices and i not in road_indices:
                    pair=next(p for p in bands if j in p)
                    name='SM_Env_Road_01';yaw=180 if j==pair[0] else 0;role='Road/Transverse'
                if (i in (7,8) and j in (6,9)) or (j in (7,8) and i in (6,9)):
                    name='SM_Env_Road_Bare_01';yaw=0;role='Road/Junction'
                if (i,j) in crossing_cells:
                    name='SM_Env_Road_Crossing_01';role='Road/Crosswalk'
                    yaw=(180 if j==10 else 0) if i in (7,8) else (270 if i==5 else 90)
            else:
                lo,hi,bot,top,block=next(b for b in blocks if b[0]<=i<=b[1] and b[2]<=j<=b[3])
                xside=-1 if i==lo else (1 if i==hi else 0)
                yside=-1 if j==bot else (1 if j==top else 0)
                role=block+'/Paving'
                if xside and yside:
                    name='SM_Env_Sidewalk_Corner_01'
                    yaw={(1,1):0,(-1,1):90,(-1,-1):180,(1,-1):270}[(xside,yside)]
                    role=block+'/Corner'
                elif xside or yside:
                    # Variation modules share the measured longitudinal end profile.
                    # Straight_02's rear edge rises 3.92862 cm: exclude it here.
                    name='SM_Env_Sidewalk_Panel_01' if (i+2*j)%3==2 else 'SM_Env_Sidewalk_Straight_01'
                    yaw=0 if xside==1 else 180 if xside==-1 else 90 if yside==1 else 270
                    role=block+'/Curb'
                else:
                    name='SM_Env_Sidewalk_01' if (3*i+j)%4==0 else 'SM_Env_Sidewalk_02'
                    yaw=90*((i+3*j)%4)
                    if block in ('SW_ParkingCourt','NE_ServiceCourt'):
                        name='SM_Env_Road_Bare_01';yaw=0;role=block+'/Asphalt'
                # Two source parking variants form a 10 m run along the west edge.
                if block=='SW_ParkingCourt' and i==3 and j in (3,4):
                    name='SM_Env_Road_Parking_01' if j==3 else 'SM_Env_Road_Parking_02'
                    yaw=0;role=block+'/ParkingBays'
                # Car access on the eastern / western frontage, clear of crosswalks.
                if (i,j) in ((6,4),(9,11)):
                    name='SM_Env_Sidewalk_Dip_01';yaw=0 if i==6 else 180;role=block+'/VehicleAccess'
                # Lowered pedestrian crossing, one tile away from curved corners.
                if ((i in (6,9) and j in (5,10)) or (j in (6,9) and i in (5,10))):
                    name='SM_Env_Sidewalk_Dip_01';role=block+'/PedestrianAccess'
            angle=math.radians(yaw)
            cx=-4000+(i+.5)*500;cy=-4000+(j+.5)*500
            location=[round(cx+250*math.cos(angle)-250*math.sin(angle),5),
                      round(cy+250*math.sin(angle)+250*math.cos(angle),5),0]
            tiles.append({'i':i,'j':j,'name':name,'mesh':ENV+name+'.'+name,'yaw':yaw,
                          'location':location,'role':role,'scale':[1,1,1]})
    result={'map':'/Game/SyntySenceLearning/PolygonApocalypse/CityGround/L_CityGround_Validation',
            'grid_size':16,'cell_size_cm':500,'origin_cm':[-4000,-4000],
            'surface_size_m':[80,80],'road_width_m':10,'tiles':tiles,
            'notes':['Each grid cell has one source surface module.',
                     'No overlapping base plane, no scaled tiles, original Z datum retained.']}
    (ROOT/'Data').mkdir(parents=True,exist_ok=True)
    (ROOT/'Data/Layout.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'tiles':len(tiles),'unique_meshes':len(set(t['mesh'] for t in tiles)),
                      'roles':dict(collections.Counter(t['role'].split('/')[0] for t in tiles))}))

if __name__=='__main__':main()
