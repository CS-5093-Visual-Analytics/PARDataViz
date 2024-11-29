import scipy.io as scio
import numpy as np
import sys
import matplotlib
matplotlib.use('QtAgg')

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QDockWidget
from PySide6.QtCore import Qt, Slot
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.projections.polar import PolarAxes
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from color_maps import ColorMaps
from matplotlib.colors import Normalize
from volume_slice_selector import VolumeSliceSelector

mat_file = 'D:/cs5093/20240428/Scan 12/MATLAB/HRUS_240428_020033000_100.mat'

# Load the data, collapse unit dimensions (no 1x1 ndarrays)
data = scio.loadmat(mat_file, squeeze_me=True)

print(data.keys())
# dict_keys(['__header__', '__version__', '__globals__', 'volume', '__function_workspace__'])

print(f'Volume shape: {data["volume"].shape}')
print(f'Volume ndim: {data["volume"].ndim}')

volume = data['volume']

# Extract the azimuth metadata
azimuths = [(az * np.pi / 180.0) for az in volume[0]['az_deg']]

# Extract the elevation metadata
print(volume[0]['sweep_el_deg'])
elevations = [(entry['sweep_el_deg'] * np.pi / 180.0) for entry in volume]

# Extract the product metadata
products = [entry['type'] for entry in volume[0]['prod']]

# Extraxt the range metadata
start_range_km = volume[0]['start_range_km']
doppler_range = volume[0]['prod'][0]['dr']
num_ranges = volume[0]['prod'][0]['data'].shape[0]
ranges = [(start_range_km + (doppler_range * i) / 1000.0) for i in range(num_ranges)]

vol_prod_dict = {}
for product in products:
    # Initialize the 3-D block of data for the current product (el x az x range)
    if product == 'R':
        vol_prod_dict[product] = np.zeros((len(elevations), len(azimuths), len(ranges)), dtype=complex)
    else:
        vol_prod_dict[product] = np.zeros((len(elevations), len(azimuths), len(ranges)))

    # Transform the source data into the 3-D block for the current product.
    vol = vol_prod_dict[product]
    prod_idx = products.index(product)
    for el_idx in range(len(elevations)):
        prods = volume[el_idx]['prod']
        if product == 'Z':
            vol[el_idx, :, :] = np.nan_to_num(prods[prod_idx]['data'].T, nan=0.0)
        else:
            vol[el_idx, :, :] = prods[prod_idx]['data'].T

# Print metadata shapes for verification
print("Num products: ", len(products))                # 9
print("Num elevations: ", len(elevations))            # 20
print("Num azimuths: ", len(azimuths))                # 44
print("Num ranges: ", len(ranges))                    # 1822
print("Volume shape:", vol_prod_dict['Z'].shape)      # (20, 44, 1822)

print(f'Range start: {ranges[0]}, range end: {ranges[-1]}')

# Reflectivity
vol = vol_prod_dict['Z']
# PPI
el_idx = 0

ppi_slice = vol[el_idx, :, :]
print(f'PPI slice shape {ppi_slice.shape}')

# RHI
az_idx = len(azimuths) // 2
rhi_slice = vol[:, az_idx, :]
print(f'RHI slice shape {rhi_slice.shape}')

class SlicePlotCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, slice_type='ppi'):
        fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
        super().__init__(fig)
        self.ax : PolarAxes = ax
        
        # The type of data slice to display ('ppi'/'rhi')
        self.slice_type = slice_type

        if self.slice_type == 'rhi':
            self.ax.set_theta_zero_location('E')
        else:
            self.ax.set_theta_zero_location('N', offset=-12.5)
            self.ax.set_theta_direction('clockwise')

        # Radar Volume information
        self.azimuths = azimuths
        self.elevations = elevations
        self.ranges = ranges
        self.vol_prod_dict = vol_prod_dict

        # Color Setup (depends on displayed product)
        self.cmap = ColorMaps.reflectivity()
        self.norm = Normalize(vmin=-10, vmax=70)
        
        # Current locations on the principle axes to slice the data.
        self.current_az = len(azimuths) // 2
        eid = elevations.index(2.25 * np.pi / 180) or None
        self.current_el = eid if eid is not None else 0

        self.update_plot()

    def set_color_map(self, color_map = ColorMaps.reflectivity()):
        self.cmap = color_map

    @Slot(int, int)
    def on_az_el_index_selection_changed(self, el_idx, az_idx):
        self.current_az = az_idx
        self.current_el = el_idx
        self.update_plot()

    def update_plot(self):
        ax = self.ax
        if self.slice_type == 'rhi':
            ax.set_title("RHI Plot")
            ax.set_xlabel("Range (km)")
            # ax.set_ylabel("Height (km)")
        else:
            ax.set_title("PPI Plot")
            ax.set_xlabel("Range (km)")
            # ax.set_ylabel("Height (km)")
        
        # Example product reflectivity
        vol = self.vol_prod_dict['Z']
        
        # Extract a 2D slice from the 3D data
        if self.slice_type == 'rhi':
            slice = vol[:-1, self.current_az, :-1]
            p_grid, r_grid = np.meshgrid(elevations, ranges)
        else:
            slice = vol[self.current_el, :-1, :-1]
            p_grid, r_grid = np.meshgrid(azimuths, ranges)
        
        # Plot the data
        self.ax.pcolormesh(p_grid, r_grid, slice.T, cmap=self.cmap, norm=self.norm, shading='flat')

        # Set the axis limits for RHI
        self.ax.set_rlim(0, ranges[-1])

        if self.slice_type == 'rhi':
            self.ax.set_thetalim(elevations[0], elevations[-1])
        else:
            self.ax.set_thetalim(azimuths[0], azimuths[-1])
        self.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Plotting RHI Data")

    widget = QWidget()
    layout = QHBoxLayout(widget)

    ppi_canvas = SlicePlotCanvas()
    layout.addWidget(ppi_canvas)

    rhi_canvas = SlicePlotCanvas(slice_type='rhi')
    layout.addWidget(rhi_canvas)

    dockable_vss = QDockWidget("Volume Slice Selector", window)
    window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dockable_vss)
    volume_slice_selector = VolumeSliceSelector()
    volume_slice_selector.on_grid_updated(len(elevations), len(azimuths), 20, 20, 10)
    volume_slice_selector.selection_changed.connect(ppi_canvas.on_az_el_index_selection_changed)
    volume_slice_selector.selection_changed.connect(rhi_canvas.on_az_el_index_selection_changed)
    dockable_vss.setWidget(volume_slice_selector)

    window.setDockNestingEnabled(True)
    window.setCentralWidget(widget)

    window.show()
    sys.exit(app.exec())
