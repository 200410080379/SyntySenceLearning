import json, math
from pathlib import Path
import unreal

def clamp(x): return max(0.,min(1.,x))
def smooth(x):
    x=clamp(x)
    return x*x*(3-2*x)
def rect_dist(x,y,b):
    x0,y0,x1,y1=b
    return math.hypot(max(x0-x,0,x-x1),max(y0-y,0,y-y1))
PADS=[[-820,-6500,820,6500],[500,-2650,3850,-100],[-2500,-1100,-600,1800],[500,-100,2700,1900],[2300,-600,3850,1700]]
def height(x,y):
    d=min(rect_dist(x,y,b) for b in PADS)
    a=smooth(d/750)
    hills=28+24*math.sin(x/580)*math.cos(y/670)+16*math.sin((x+y)/310)
    hills+=150*math.exp(-((x+4200)**2+(y-3600)**2)/1600**2)
    hills+=210*math.exp(-((x-4500)**2+(y-4600)**2)/1900**2)
    return round((24.21875+a*hills)*128/100)*100/128
def dirt_weight(x,y):
    road=1-smooth((abs(x)-700)/650)
    yard=max(1-smooth(rect_dist(x,y,b)/280) for b in PADS[1:])
    patch=.5+.25*math.sin(x/260+y/450)+.25*math.sin(x/410-y/230)
    return clamp(max(road*.92,yard*.78)+.12*patch)

def main():
    root=Path(unreal.Paths.project_dir()).resolve()/'Learning/SyntySenceLearning/polygon-apocalypse/06-street-slice'
    root.mkdir(parents=True,exist_ok=True)
    w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert w.get_path_name()=='/Game/SyntySenceLearning/PolygonApocalypse/StreetSlice/L_StreetSlice.L_StreetSlice'
    land=next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if isinstance(a,unreal.Landscape))
    assert len(land.get_components_by_class(unreal.LandscapeComponent))==4
    mat=unreal.load_asset('/Game/SyntySenceLearning/PolygonApocalypse/StreetSlice/Materials/M_StreetLandscape')
    assert mat, 'Run build_scene.main(prepare) before native Landscape creation'
    assert list(land.get_actor_location().to_tuple())==[-6300.,-6300.,0.]
    assert list(land.get_actor_scale3d().to_tuple())==[100.,100.,100.]
    targets=land.get_editor_property('target_layers')
    for name in ['Base','Dirt','Grass_02']:
        layer=unreal.load_asset('/Game/Synty/PolygonGeneric/LandscapeMaterial/Material_Lay_Wood/'+name+'_LayerInfo')
        assert layer
        targets[unreal.Name(name)].set_editor_property('layer_info_obj',layer)
    land.set_editor_property('landscape_material',mat,notify_mode=unreal.PropertyAccessChangeNotifyMode.ALWAYS)
    rt=unreal.RenderingLibrary.create_render_target2d(w,127,127,unreal.TextureRenderTargetFormat.RTF_RGBA32F)
    result={}
    for channel in ['height','Base','Dirt','Grass_02']:
        canvas,size,context=unreal.RenderingLibrary.begin_draw_canvas_to_render_target(w,rt)
        for j in range(127):
            y=-6300+j*100
            for i in range(127):
                x=-6300+i*100
                if channel=='height': value=32768+height(x,y)*128/100
                elif channel=='Base': value=0
                elif channel=='Dirt': value=dirt_weight(x,y)
                else: value=1-dirt_weight(x,y)
                canvas.draw_texture(None,unreal.Vector2D(i,j),unreal.Vector2D(1,1),unreal.Vector2D(0,0),unreal.Vector2D(1,1),unreal.LinearColor(value,value,value,1),unreal.BlendMode.BLEND_OPAQUE)
        unreal.RenderingLibrary.end_draw_canvas_to_render_target(w,context)
        if channel=='height': ok=land.landscape_import_heightmap_from_render_target(rt,False,0)
        else: ok=land.landscape_import_weightmap_from_render_target(rt,channel,0)
        result[channel]=ok
        print(channel,ok)
        if not ok: raise RuntimeError('Landscape import failed '+channel)
    land.set_folder_path('00_Terrain')
    result.update({'resolution':[127,127],'components':4,'location':[-6300,-6300,0],'scale':[100,100,100],'height_range':[min(height(-6300+i*100,-6300+j*100) for i in range(127) for j in range(127)),max(height(-6300+i*100,-6300+j*100) for i in range(127) for j in range(127))]})
    (root/'TerrainBuild.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__': main()
