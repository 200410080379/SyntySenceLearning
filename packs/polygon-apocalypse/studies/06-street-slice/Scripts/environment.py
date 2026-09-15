"""Independent lighting, copied from the validated earlier study recipe."""
import unreal

def _spawn(actors, actor_class, label, location, rotation=None, folder='00_Environment'):
    actor = actors.spawn_actor_from_class(actor_class, unreal.Vector(*location),
                                         unreal.Rotator(**(rotation or {'pitch': 0, 'yaw': 0, 'roll': 0})))
    if not actor:
        raise RuntimeError('Could not create actor: ' + label)
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    return actor


def _environment(actors, cube, sky_class):
    sun = _spawn(actors, unreal.DirectionalLight, 'Town_Sun', [0, 0, 5000],
                 {'pitch': -43, 'yaw': -38, 'roll': 0})
    sun.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun.light_component.set_intensity(3.2)
    sun.light_component.set_light_color(unreal.LinearColor(r=1, g=.91, b=.77, a=1))
    sky = _spawn(actors, unreal.SkyLight, 'Town_Skylight', [0, 0, 3000])
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property('source_type', unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sky.light_component.set_editor_property('cubemap', cube)
    sky.light_component.set_intensity(.65)
    sky.light_component.set_light_color(unreal.LinearColor(r=.72, g=.85, b=1, a=1))
    sphere = _spawn(actors, sky_class, 'Town_Sky', [0, 0, 0])
    sphere.set_editor_property('Directional light actor', sun)
    sphere.set_editor_property('Cloud opacity', 1.1)
    sphere.set_editor_property('Sun brightness', 18.0)
    sphere.call_method('UpdateSunDirection')
    fog = _spawn(actors, unreal.ExponentialHeightFog, 'Town_DistantHaze', [0, 0, 400])
    component = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    component.set_editor_property('fog_density', .006)
    component.set_editor_property('fog_height_falloff', .22)
    component.set_editor_property('start_distance', 6500.0)
    component.set_editor_property('fog_max_opacity', .25)
    component.set_fog_inscattering_color(unreal.LinearColor(r=.30, g=.35, b=.33, a=1))
    post = _spawn(actors, unreal.PostProcessVolume, 'Town_Grade', [0, 0, 0])
    post.set_editor_property('unbound', True)
    settings = post.get_editor_property('settings')
    parameters = {
        'color_saturation': unreal.Vector4(x=.90, y=.91, z=.91, w=1),
        'color_contrast': unreal.Vector4(x=1.07, y=1.07, z=1.07, w=1),
        'ambient_occlusion_intensity': .9,
        'ambient_occlusion_radius': 80.0,
        'bloom_intensity': .12,
        'vignette_intensity': .15,
    }
    for key, value in parameters.items():
        settings.set_editor_property('override_' + key, True)
        settings.set_editor_property(key, value)
    post.set_editor_property('settings', settings)


