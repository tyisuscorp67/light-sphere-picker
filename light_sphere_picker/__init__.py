from krita import DockWidgetFactory, DockWidgetFactoryBase, Krita
from .light_sphere_docker import LightSpherePickerDocker

instance = Krita.instance()
dock_factory = DockWidgetFactory(
    "light_sphere_picker",
    DockWidgetFactoryBase.DockRight,
    LightSpherePickerDocker,
)
instance.addDockWidgetFactory(dock_factory)
