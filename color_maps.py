import scipy.io as scio
from vispy.color import Colormap

class ColorMaps:
    """
    Reflectivity and Velocity Colormaps
    """
    def __init__(self, path_to_maps) -> None:
        self.path_to_maps = path_to_maps
        self.maps_mat = scio.loadmat(self.path_to_maps)

    def reflectivity(self):
        return Colormap(self.maps_mat['reflectivity'])
    
    def reflectivity_lims(self):
        return (-10, 70)

    def velocity(self):
        return Colormap(self.maps_mat['velocity'])
    
    def velocity_lims(self):
        return (-24, 24)
    
    