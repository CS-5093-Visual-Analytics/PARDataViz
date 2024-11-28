from matplotlib.colors import LinearSegmentedColormap

class ColorMaps:
    """
    Reflectivity and Velocity Colormaps
    """

    @staticmethod
    def reflectivity():        
        return LinearSegmentedColormap.from_list("reflectivity", ["purple", "blue", "green", "yellow", "orange", "red"])

    @staticmethod
    def velocity():
        return LinearSegmentedColormap.from_list("velocity", ["blue", "lightblue", "lightgreen", "darkgreen", "white", "darkred", "red", "pink", "orange"])

    