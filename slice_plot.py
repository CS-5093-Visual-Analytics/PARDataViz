import scipy.io as scio
import numpy as np
import sys
import vispy.app
from vispy.scene import Label
from vispy.scene import SceneCanvas, PanZoomCamera, AxisWidget, ColorBarWidget
from vispy.scene.visuals import Image
from vispy.plot import Fig, PlotWidget
from vispy.color import Colormap
from vispy.visuals.transforms import STTransform, PolarTransform
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QDockWidget, QMenu
from PySide6.QtCore import Qt, Slot, QObject, Signal
from PySide6.QtGui import QAction, QActionGroup, QPaintEvent
from color_maps import ColorMaps
from radar_volume import RadarVolume
from dynamic_dock_widget import DynamicDockWidget

class SlicePlot(QObject):
    cmaps = ColorMaps('D:/cs5093/20240428/MATLAB Display Code/colormaps.mat')

    def __init__(self, id, parent=None, slice_type='ppi'):
        super().__init__(parent=parent)
        
        # Set this plot's id (used for window/dock-tab title)
        self.id = id

        # The type of data slice to display ('ppi'/'rhi')
        self.slice_type = slice_type

        # Current locations on the principle axes to slice the data.
        self.current_az = 0
        self.current_el = 0

        # Group the product switching actions together to ensure mutual exclusivity
        self.action_group = QActionGroup(self)
        self.reflectivity_mode_action = QAction("Reflectivity", self, checkable=True)
        self.velocity_mode_action = QAction("Velocity", self, checkable=True)
        self.phi_mode_action = QAction("Phi", self, checkable=True)
        self.rho_mode_action = QAction("Rho", self, checkable=True)
        self.width_mode_action = QAction("Width", self, checkable=True)
        self.zdr_mode_action = QAction("Zdr", self, checkable=True)

        # Triggering each product mode action invokes the same slot with the corresponding product as the parameter
        # Products: ['Z', 'V', 'W', 'D', 'P', 'R', 'S']
        self.reflectivity_mode_action.triggered.connect(lambda: self.set_product_display('Z'))
        self.velocity_mode_action.triggered.connect(lambda: self.set_product_display('V'))
        self.phi_mode_action.triggered.connect(lambda: self.set_product_display('P'))
        self.rho_mode_action.triggered.connect(lambda: self.set_product_display('R'))
        self.width_mode_action.triggered.connect(lambda: self.set_product_display('W'))
        self.zdr_mode_action.triggered.connect(lambda: self.set_product_display('D'))

        self.action_group.addAction(self.reflectivity_mode_action)
        self.action_group.addAction(self.velocity_mode_action)
        self.action_group.addAction(self.phi_mode_action)
        self.action_group.addAction(self.rho_mode_action)
        self.action_group.addAction(self.width_mode_action)
        self.action_group.addAction(self.zdr_mode_action)

        # Show reflectivity by default
        self.reflectivity_mode_action.setChecked(True)
        self.product_to_display = 'Z'
        self.cmap = self.cmaps.reflectivity()
        self.clim = (-10, 70)

        # Scene setup
        #
        # Grid layout:
        #
        # __|  - 0 -  |  - 1 -  |  - 2 -  |
        #   |                             |
        #  0|  ..........title........... |   
        #   |                             |
        # --| --------------------------- |
        #   |        |          |         |
        #  1| y_axis |   view   |  c_bar  |
        #   |        |          |         |
        # --| ------ | -------- | ------- |
        #   |        |          |         |
        #  2| (none) |  x_axis  |  (none) |
        #   |        |          |         |
        # --| ------ | -------- | ------- |
        #

        self.canvas = SceneCanvas(size=(10, 10))
        self.canvas.native.setContextMenuPolicy(Qt.CustomContextMenu)
        self.grid = self.canvas.central_widget.add_grid(spacing=1.0, margin=10.0)
        
        # Cell (0,0) - Title
        self.title = Label(
            f'RHI ({self.product_to_display})' if slice_type == 'rhi' else f'PPI ({self.product_to_display})', 
            color='white')
        self.title.margin = 10.0
        self.title.height_max = 40.0
        self.grid.add_widget(self.title, row=0, col=0, col_span=3)

        # Cell (1,0) - Y-Axis
        self.y_axis = AxisWidget(
            orientation="left", 
            axis_label="Meridonal Distance (km)" if self.slice_type == 'ppi' else "Height (km)",
            axis_font_size=8,
            axis_label_margin=75.0,
            tick_label_margin=15.0)
        self.y_axis.width_min = 80.0
        self.y_axis.width_max = 120.0
        self.grid.add_widget(self.y_axis, row=1, col=0)

        # Cell (1,1) - View
        self.view = self.grid.add_view(row=1, col=1, camera='panzoom')        
        self.view.camera.set_range((-5, 15), (-5, 15))
        self.image = Image(np.zeros((10, 10)), parent=self.view.scene, cmap=self.cmap, clim=self.clim, grid=(360, 360), method='subdivide', interpolation='nearest')

        # Cell (1,2) - Color Bar
        self.color_bar = ColorBarWidget(
            label="",
            clim=self.clim,
            cmap=self.cmap,
            orientation="right",
            border_width=1,
            label_color='white')
        
        # Figuring out how to set the font size on the color bar tick marks was insane
        for tick in self.color_bar.ticks:
            tick.font_size = 6
        self.color_bar.width_max = 120
        self.grid.add_widget(self.color_bar, row=1, col=2)

        # Cell (2,1) - X-Axis
        self.x_axis = AxisWidget(
            orientation="bottom", 
            axis_label="Zonal Distance (km)" if self.slice_type == 'ppi' else "Range (km)",
            axis_font_size=8,
            axis_label_margin=75.0,
            tick_label_margin=45.0)
        self.x_axis.height_min = 120.0
        self.x_axis.height_max = 160.0
        self.grid.add_widget(self.x_axis, row=2, col=1)

        self.y_axis.link_view(self.view)
        self.x_axis.link_view(self.view)

        # self.update_plot()

    def set_product_display(self, product):
        self.product_to_display = product

        # Set dock-tab/window title
        if self.slice_type == 'rhi':
            self.parent().setWindowTitle(f'View {self.id} - RHI ({product})')
            self.title.text = f'RHI ({product})'
        else:
            self.parent().setWindowTitle(f'View {self.id} - PPI ({product})')
            self.title.text = f'PPI ({product})'

        (cmap, clim) = self.cmaps.get_cmap_and_clims_for_product(self.product_to_display)
        self.cmap = cmap
        self.clim = clim

        # Update color bar
        self.color_bar.cmap = self.cmap
        self.color_bar.clim = self.clim

        # Image color setup (depends on displayed product)
        self.image.cmap = self.cmap
        self.image.clim = self.clim
        self.update_plot()

    def get_product_display(self):
        return self.product_to_display

    def on_dock_custom_context_menu_requested(self, pos):
        context_menu = QMenu()

        dummy_action = QAction("Select product:", self)
        dummy_action.setEnabled(False)
        context_menu.addAction(dummy_action)
        context_menu.addSeparator()

        context_menu.addAction(self.reflectivity_mode_action)
        context_menu.addAction(self.velocity_mode_action)
        context_menu.addAction(self.phi_mode_action)
        context_menu.addAction(self.rho_mode_action)
        context_menu.addAction(self.width_mode_action)
        context_menu.addAction(self.zdr_mode_action)

        parent: DynamicDockWidget = self.parent()
        if parent.isFloating():
            print("Floating")

        # Parent should be a dynamic dock widget
        context_menu.exec(self.parent().mapToGlobal(pos))        

    # Possible fix for dock removing/reparent issue: https://github.com/vispy/vispy/issues/2270
    def paintEvent(self, event: QPaintEvent) -> None:
        # force send paintevent
        self.canvas.native.paintEvent(event)
        return super().paintEvent(event)

    @Slot(RadarVolume)
    def on_radar_volume_updated(self, volume: RadarVolume):
        self.azimuths_rad = volume.azimuths_rad
        self.elevations_rad = volume.elevations_rad
        self.ranges_km = volume.ranges_km
        self.products = volume.products

        # Axes
        # self.x_axis = AxisWidget(orientation='bottom', axis_label="Range (km)")
        # self.x_axis.stretch = (1, 0.1)
        # self.grid.add_widget(self.x_axis, row=1, col=1)
        # self.x_axis.link_view(self.view)

        # Because we transform into polar coordinates
        # Width of the camera is range_start_km * 1000 / doppler_resolution + len(ranges)
        self.y_start = np.floor(volume.start_range_km / volume.doppler_resolution_km) 
        cam_width = self.y_start + len(self.ranges_km)
        
        # if self.slice_type == 'rhi':
        # self.view.camera.set_range((0, cam_width), (0, cam_width))
        # else:
            # self.view.camera.set_range((-cam_width, cam_width), (-cam_width, cam_width))
        
        # Calculate the radial extents of the slice
        if self.slice_type == 'rhi':
            self.radial_swath = volume.elevation_swath_rad
        else:
            self.radial_swath = volume.azimuth_swath_rad

        self.update_plot()

    @Slot(int, int)
    def on_az_el_index_selection_changed(self, el_idx, az_idx):
        self.current_az = az_idx
        self.current_el = el_idx
        self.update_plot()
        
    @Slot(int, int)
    def on_az_el_slice_hovered(self, el_idx, az_idx):
        self.current_az = az_idx
        self.current_el = el_idx
        self.update_plot()

    def update_plot(self):
        
        prod = self.products[self.product_to_display]
        if self.slice_type == 'rhi':
            # RHI: elevation x range
            slice = prod[:, self.current_az, :].T
        else:
            # PPI: azimuth x range.
            slice = prod[self.current_el, :, :].T

        self.image.set_data(slice)

        # Complicated method for transforming an image in cartesian coordinates into polar coordinates
        # Credit: https://stackoverflow.com/a/68390497/13542651

        # Compute the scaling factor to convert from pixel space into kilometers
        km_per_pixel = self.ranges_km[-1] / (self.y_start + len(self.ranges_km))
        scx = km_per_pixel
        scy = km_per_pixel
        xoff = 0
        yoff = 0

        ori0 = 0 # Side of the image to collapse at origin (0 for top/1 for bottom)
        loc0 = self.radial_swath if self.slice_type == 'ppi' else -self.elevations_rad[0] # Location of zero (0, 2* np.pi) clockwise
        dir0 = 1 # Direction cw/ccw -1, 1

        transform = (
            STTransform(scale=(scx, scy), translate=(xoff, yoff))

            *PolarTransform()

            # 1
            # pre scale image to work with polar transform
            # PolarTransform does not work without this
            # scale vertex coordinates to 2*pi
            *STTransform(scale=(self.radial_swath / self.image.size[0], 1.0))

            # 2
            # origin switch via translate.y, fix translate.x
            *STTransform(translate=(self.image.size[0] * (ori0 % 2) * 0.5,                                                                   
                                    -self.image.size[1] * (ori0 % 2)))

            # 3
            # location change via translate.x
            *STTransform(translate=(self.image.size[0] * (loc0), 0.0))

            # 4
            # direction switch via inverting scale.x
            * STTransform(scale=(-dir0 if self.slice_type == 'ppi' else dir0, 1.0))

            # 5
            # Shift the image up for the receive start (start_range_km * 1000 / doppler_resolution)
            *STTransform(translate=(0, self.y_start))
        )
        self.image.transform = transform

        self.grid.update()
