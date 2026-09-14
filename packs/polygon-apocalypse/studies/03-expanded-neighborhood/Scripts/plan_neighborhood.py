"""Author a 200 x 160 m ground study with staggered T junctions and four parcels."""
import collections
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ENV='/Game/PolygonApocalypse/Meshes/Environments/'
LEVEL='/Game/SyntySenceLearning/PolygonApocalypse/ExpandedNeighborhood/L_ExpandedNeighborhood'
BLOCKS=[
    (2,24,2,13,'SW_GasAndShops','Gas station and small shops',115,60),
    (27,37,2,13,'SE_ServiceCourt','Service yard and small commercial plot',55,60),
    (2,12,16,29,'NW_Diner','Diner and frontage parking',55,70),
    (15,37,16,29,'NE_Motel','Motel court and rear building strip',115,70)]

def main():
    nx,ny=40,32
    roads={}
    for j in range(ny):
        for i in range(nx):
            h='MainStreet' if j in (14,15) else 'BoundaryStreet' if j in (0,1,30,31) else None
            v='BoundaryStreet' if i in (0,1,38,39) else 'NorthLocalStreet' if i in (13,14) and j>=16 else 'SouthLocalStreet' if i in (25,26) and j<=13 else None
            if h or v:roads[i,j]=(h,v)
    # Crossings are set back from the curved corners; each has two lowered ends.
    crossings={(i,j):('horizontal',0 if i==10 else 180) for i in (10,29) for j in (14,15)}
    crossings.update({(i,j):('vertical',180 if j==18 else 0) for j,cols in [(18,(13,14)),(11,(25,26))] for i in cols})
    pedestrian={(10,13):90,(10,16):270,(29,13):90,(29,16):270,
                (12,18):0,(15,18):180,(24,11):0,(27,11):180}
    vehicle={(5,13):90,(8,13):90,(20,2):270,(24,6):0,
             (33,13):90,(37,5):0,(6,16):270,
             (15,23):180,(37,23):0}
    parking={}
    for x,ys,yaw in [(4,range(5,11),0),(22,range(8,12),180),
                     (29,range(4,7),0),(4,range(18,23),0),
                     (9,range(18,23),180),(19,range(19,25),0),
                     (33,range(19,25),180)]:
        for k,y in enumerate(ys):parking[x,y]=(k%2+1,yaw)
    tiles=[]
    for j in range(ny):
        for i in range(nx):
            yaw=0;name='SM_Env_Road_Bare_01';role='Road/Junction'
            if (i,j) in roads:
                h,v=roads[i,j]
                # Entire 10 m main-street width is clear at each T junction.
                main_t=j in (14,15) and i in (12,13,14,15,24,25,26,27)
                top_t=j in (30,31) and i in (12,13,14,15)
                bottom_t=j in (0,1) and i in (24,25,26,27)
                side_t=i in (0,1,38,39) and j in (13,14,15,16)
                if h and not v and not (main_t or top_t or bottom_t):
                    name='SM_Env_Road_01';yaw=180 if j in (0,14,30) else 0;role='Road/'+h
                elif v and not h and not side_t:
                    # Short access streets are unmarked; their role differs from the through street.
                    role='Road/'+v
                    if v=='BoundaryStreet':name='SM_Env_Road_01';yaw=90 if i in (0,38) else 270
                if (i,j) in crossings:
                    axis,side=crossings[i,j];name='SM_Env_Road_Crossing_01'
                    yaw=(90 if side==0 else 270) if axis=='horizontal' else side
                    role='Road/Crosswalk'
            else:
                lo,hi,bot,top,block,_,_,_=next(b for b in BLOCKS if b[0]<=i<=b[1] and b[2]<=j<=b[3])
                xs=-1 if i==lo else 1 if i==hi else 0
                ys=-1 if j==bot else 1 if j==top else 0
                if xs and ys:
                    name='SM_Env_Sidewalk_Corner_01'
                    yaw={(1,1):0,(-1,1):90,(-1,-1):180,(1,-1):270}[xs,ys]
                    role=block+'/Corner'
                elif xs or ys:
                    name='SM_Env_Sidewalk_Panel_01' if (i+2*j)%5==0 else 'SM_Env_Sidewalk_Straight_01'
                    yaw=0 if xs==1 else 180 if xs==-1 else 90 if ys==1 else 270
                    role=block+'/Sidewalk'
                else:
                    # Asphalt yards and discrete concrete pads give each parcel a readable structure.
                    paved=False;role=block+'/Forecourt'
                    if block=='SW_GasAndShops':
                        paved=(5<=i<=10 and 3<=j<=5) or (14<=i<=21 and 5<=j<=9)
                        if j==3 and i>=13:role=block+'/RearServiceLane_5m'
                        elif i<=12:role=block+'/GasForecourt'
                    elif block=='SE_ServiceCourt':paved=30<=i<=35 and 7<=j<=11
                    elif block=='NW_Diner':paved=4<=i<=10 and 24<=j<=28
                    elif block=='NE_Motel':
                        paved=(17<=i<=35 and 26<=j<=28) or (23<=i<=28 and 19<=j<=23)
                        if j==17:role=block+'/FrontCirculation'
                    if paved:
                        name='SM_Env_Sidewalk_01';yaw=0;role=block+'/BuildingOrPedestrianReserve'
                    if (i,j) in parking:
                        number,yaw=parking[i,j];name='SM_Env_Road_Parking_%02d'%number;role=block+'/ParkingBays'
                if (i,j) in vehicle:
                    name='SM_Env_Sidewalk_Dip_01';yaw=vehicle[i,j];role=block+'/VehicleAccess'
                if (i,j) in pedestrian:
                    name='SM_Env_Sidewalk_Dip_01';yaw=pedestrian[i,j];role=block+'/PedestrianAccess'
            angle=math.radians(yaw);cx=-10000+(i+.5)*500;cy=-8000+(j+.5)*500
            location=[round(cx+250*math.cos(angle)-250*math.sin(angle),5),
                      round(cy+250*math.sin(angle)+250*math.cos(angle),5),0]
            tiles.append({'i':i,'j':j,'name':name,'mesh':ENV+name+'.'+name,'yaw':yaw,'location':location,'scale':[1,1,1],'role':role})
    plan={'map':LEVEL,'grid_size':[nx,ny],'cell_size_cm':500,'origin_cm':[-10000,-8000],
          'surface_size_m':[200,160],'road_width_m':10,'tiles':tiles,
          'blocks':[{'id':b[4],'purpose':b[5],'cell_bounds':list(b[:4]),'size_m':list(b[6:])} for b in BLOCKS],
          'design':{'main_street':'East-west continuous street, 10 m modular width',
                    'local_junctions':'Two opposing T junctions offset by 60 m along the through street',
                    'vehicle_accesses':len(vehicle),'pedestrian_accesses':len(pedestrian),
                    'crossings':4,'ground_only':True,
                    'reserved_pads':'Surface zoning only; building fit and foundations are not yet validated',
                    'road_scale':'Uses the pack\'s existing 5 m half-road modules; not a regulatory road-width claim'},
          'notes':['One source surface mesh per 5 m cell; no underlay or scaled ground modules.',
                   'Road edges at the study boundary are future extension ports, not finished city limits.',
                   'Parking is a visual layout sample; vehicle swept paths and navigation are not tested.']}
    (ROOT/'Data').mkdir(parents=True,exist_ok=True)
    (ROOT/'Data/Layout.json').write_bytes((json.dumps(plan,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({'tiles':len(tiles),'mesh_types':len(set(t['mesh'] for t in tiles)),
                      'roles':dict(collections.Counter(t['role'].split('/')[0] for t in tiles))}))

if __name__=='__main__':main()
