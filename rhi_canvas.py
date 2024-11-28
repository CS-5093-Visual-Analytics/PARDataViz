from PySide6.QtWidgets import QApplication, QToolTip
from PySide6.QtCore import Qt, Slot
from base_canvas import BaseCanvas
from color_maps import ColorMaps
from matplotlib.colors import Normalize
import numpy as np
from radar_volume import RadarVolume

class RHI_Canvas(BaseCanvas):
    def __init__(self, parent=None, width=10, height=8, dpi=100, polar=True):
        super().__init__(parent, width, height, dpi, polar)

        self.axes.set_theta_zero_location("E")
    
    def get_view_name(self):
        return "RHI"
    
    @Slot(RadarVolume)
    def update_view(self, radar_volume: RadarVolume):
        if radar_volume.reflectivity_data is None and self.velocity_data is None:
            print("No data available for RHI plot.")
            return

        # Select data, colormap, and normalization
        data = self.reflectivity_data if self.get_product_display() == "reflectivity" else self.velocity_data
        cmap = ColorMaps.reflectivity() if self.get_product_display() == 'reflectivity' else ColorMaps.velocity()
        norm = Normalize(vmin=-30, vmax=75) if self.get_product_display() == "reflectivity" else Normalize(vmin=-50, vmax=50)

        # Clear and reinitialize the figure and axes
        self.figure.clf()  # Clear entire figure, including any color bars
        self.axes = self.figure.add_subplot(111, polar=True)
        self.axes.set_theta_zero_location("E")
        self.axes.set_aspect('equal', adjustable='box')

        # Adjust layout to center the plot 
        self.figure.subplots_adjust(left=0.05, right=0.70)  # Adjust as needed

        # Set up data grid and plot data
        elevations = np.linspace(0, np.pi / 6, data.shape[0] + 1)
        ranges = np.linspace(self.radar_volume.start_range_km, 115, data.shape[1] + 1)
        # ranges = np.linspace(0, 100, data.shape[1] + 1)
        elevation_grid, range_grid = np.meshgrid(elevations, ranges)
        rhi_plot = self.axes.pcolormesh(elevation_grid, range_grid, data.T, cmap=cmap, norm=norm, shading='auto')

        # Create color bar
        self.rhi_colorbar = self.figure.colorbar(rhi_plot, ax=self.axes, orientation='vertical', pad=0.05)
        self.rhi_colorbar.set_label("Reflectivity (dBZ)" if self.get_product_display() == "reflectivity" else "Velocity (m/s)")

        # Set title and axes properties
        self.mpl_connect('motion_notify_event', self.on_rhi_hover)
        self.mpl_connect('motion_notify_event', self.on_rhi_hover)
        self.mpl_connect('axes_enter_event', self.on_axes_enter)
        self.mpl_connect('axes_leave_event', self.on_axes_leave)
        self.axes.set_title("RHI View - Reflectivity" if self.get_product_display() == "reflectivity" else "RHI View - Velocity")
        self.axes.set_thetamin(0)
        self.axes.set_thetamax(30)
        self.axes.set_ylim(self.radar_volume.start_range_km, 115)
        self.draw()

    def on_rhi_hover(self, event):
        if event.inaxes != self.rhi_canvas.axes:
            return

        # Get mouse coordinates (polar)
        r = event.ydata  # Distance from center
        theta = event.xdata  # Elevation angle in radians

        # Convert to degrees
        elev_deg = np.degrees(theta)

        
        data = self.reflectivity_data if self.get_product_display() == "reflectivity" else self.velocity_data
        if data is not None and r is not None:
            # Calculate indices for data lookup
            range_index = int(r * (data.shape[1] / 100))  # Assuming max range is 100 km
            elev_index = int((elev_deg / 30) * data.shape[0])  # Assuming elevation max is 30°

            if 0 <= range_index < data.shape[1] and 0 <= elev_index < data.shape[0]:
                value = data[elev_index, range_index]
                product = "Reflectivity (dBZ)" if self.get_product_display() == "reflectivity" else "Velocity (m/s)"

                
                QToolTip.showText(
                    event.guiEvent.globalPos(),
                    f"{product}: {value:.2f}\nRange: {r:.1f} km\nElevation: {elev_deg:.1f}°",
                    self
                )
    
    def on_axes_enter(self, event):
        if event.inaxes == self.axes:
            QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)

    def on_axes_leave(self, event):
        if event.inaxes == self.axes:
            QApplication.restoreOverrideCursor()