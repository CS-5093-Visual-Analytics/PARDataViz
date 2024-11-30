import scipy.io as scio
import numpy as np
import sys
import vispy.app
from vispy.scene import SceneCanvas, PanZoomCamera, AxisWidget
from vispy.scene.visuals import Image
from vispy.plot import Fig, PlotWidget
from vispy.color import Colormap
from vispy.visuals.transforms import STTransform, PolarTransform
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QDockWidget, QMenu
from PySide6.QtCore import Qt, Slot, QObject, Signal, QPoint
from color_maps import ColorMaps
from radar_volume import RadarVolume


class SlicePlot(QObject):
    cmaps = ColorMaps('D:/cs5093/20240428/MATLAB Display Code/colormaps.mat')

    def __init__(self, parent=None, slice_type='ppi'):
        super().__init__(parent=parent)
        
        # The type of data slice to display ('ppi'/'rhi')
        self.slice_type = slice_type

        # Current locations on the principle axes to slice the data.
        self.current_az = 0
        self.current_el = 0

        # Color Setup (depends on displayed product)
        self.product_to_display = 'Z'
        self.cmap = SlicePlot.cmaps.reflectivity()

        # Scene setup
        self.canvas = SPSceneCanvas(parent=self, size=(10, 10))
        self.canvas.native.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.grid = self.canvas.central_widget.add_grid(spacing=0)
        # self.view = self.grid.add_view(row=0, col=1, camera='panzoom')
        self.view = self.canvas.central_widget.add_view(camera='panzoom')
        self.image = Image(np.zeros((10, 10)), parent=self.view.scene, cmap=self.cmap, clim=(-10, 70), grid=(1, 360), method='subdivide')
        
        # self.update_plot()

    
    def on_canvas_right_clicked(self, event):
        # Right-click
        if event.button == 2:
            print("Right-click caught in SceneCanvas.")
            # Mark the event as handled
            event.handled = True
            self.show_context_menu(event)

    def show_context_menu(self, event):
        menu = QMenu()
        menu.addAction("Option 1", lambda: print("Option 1 Clicked"))
        menu.addAction("Option 2", lambda: print("Option 2 Clicked"))

        pos = self.canvas.native.mapToGlobal(QPoint(event.pos[0], event.pos[1]))
        print(event.pos)
        print(pos)
        menu.exec(pos)

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
        self.view.camera.set_range((0, cam_width), (0, cam_width))
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
        scx = 1
        scy = 1
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

        self.canvas.update()

class SPSceneCanvas(SceneCanvas):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unfreeze()
        self.parent = parent
        if self.parent is not None:
            self.events.mouse_press.connect(self.on_mouse_press)
            self.events.mouse_move.connect(self.on_mouse_move)
            self.events.mouse_release.connect(self.on_mouse_release)
        self.freeze()
    
    def on_mouse_press(self, event):
        if event.button == 2:
            modifiers = event.modifiers
            if modifiers and 'Alt' in modifiers:
                event.handled = True
                if self.parent:
                    self.parent.view.camera.interactive = False
                    self.parent.on_canvas_right_clicked(event)
            return
    
    def on_mouse_move(self, event):
        if event.button == 2:  # Right-click
            modifiers = event.modifiers
            # Only suppress if Alt is pressed
            if modifiers and 'Alt' in modifiers:
                event.handled = True

    def on_mouse_release(self, event):
        self.parent.view.camera.interactive = True
        if event.button == 2:  # Right-click
            modifiers = event.modifiers
            # Only suppress if Alt is pressed
            if modifiers and 'Alt' in modifiers:
                event.handled = True
