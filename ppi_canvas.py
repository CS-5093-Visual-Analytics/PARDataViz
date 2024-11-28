from PySide6.QtCore import Slot
from base_canvas import BaseCanvas
from color_maps import ColorMaps
from matplotlib.colors import Normalize
import numpy as np
from radar_volume import RadarVolume

class PPI_Canvas(BaseCanvas):
    def __init__(self, parent=None, width=10, height=8, dpi=100, polar=True):
        super().__init__(parent, width, height, dpi, polar)

        self.axes.set_theta_zero_location("N")

    def get_view_name(self):
        return "PPI"

    @Slot(RadarVolume)
    def update_view(self, radar_volume: RadarVolume):
        if self.reflectivity_data is None and self.velocity_data is None:
            print("No data available for PPI plot.")
            return

        # Select data, colormap, and normalization
        data = self.reflectivity_data if self.get_product_display() == "reflectivity" else self.velocity_data
        cmap = ColorMaps.reflectivity() if self.get_product_display() == "reflectivity" else ColorMaps.velocity()
        norm = Normalize(vmin=-30, vmax=75) if self.get_product_display() == "reflectivity" else Normalize(vmin=-50, vmax=50)

        # Clear and reinitialize the figure and axes
        self.figure.clf()  # Clear entire figure, including any color bars
        self.axes = self.figure.add_subplot(111, polar=True)
        self.axes.set_theta_zero_location("N")
        self.axes.set_aspect('equal', adjustable='box')

        self.figure.subplots_adjust(left=0.05, right=0.70)  # Adjust as needed

        # Set up data grid and plot data
        azimuths = np.linspace(-np.pi / 6, np.pi / 6, data.shape[1] + 1)
        ranges = np.linspace(self.radar_volume.start_range_km, 115, data.shape[0] + 1)
        azimuth_grid, range_grid = np.meshgrid(azimuths, ranges)
        ppi_plot = self.axes.pcolormesh(azimuth_grid, range_grid, data, cmap=cmap, norm=norm, shading='auto')

        # Create color bar
        self.ppi_colorbar = self.figure.colorbar(ppi_plot, ax=self.axes, orientation='vertical', pad=0.05)
        self.ppi_colorbar.set_label("Reflectivity (dBZ)" if self.get_product_display() == "reflectivity" else "Velocity (m/s)")

        # Set title and axes properties
        self.mpl_connect('motion_notify_event', self.on_ppi_hover)
        self.mpl_connect('motion_notify_event', self.on_ppi_hover)
        self.mpl_connect('axes_enter_event', self.on_axes_enter)
        self.mpl_connect('axes_leave_event', self.on_axes_leave)
        self.axes.set_title("PPI View - Reflectivity" if self.get_product_display() == "reflectivity" else "PPI View - Velocity")
        self.axes.set_thetamin(-30)
        self.axes.set_thetamax(30)
        self.axes.set_ylim(self.radar_volume.start_range_km, 115)
        self.draw()

    def on_ppi_hover(self, event):
        if event.inaxes != self.ppi_canvas.axes:
            return

        # Get mouse coordinates (polar)
        r = event.ydata  # Distance from center
        theta = event.xdata  # Angle in radians

        # Convert to degrees
        angle_deg = np.degrees(theta)
        if angle_deg < -30 or angle_deg > 30:  # Limit hover to the plotted azimuth range
            return

        # Adjust angle to 0°-60° scale
        angle_deg += 30  # Shift range from [-30°, 30°] to [0°, 60°]

       
        data = self.reflectivity_data if self.current_ppi_data_type == "reflectivity" else self.velocity_data
        if data is not None and r is not None:
            # Calculate indices for data lookup
            range_index = int(r * (data.shape[0] / 100))  # Scale radial distance to data rows
            azimuth_index = int((angle_deg / 60) * data.shape[1])  # Scale angle to data columns

            # Validate indices
            if 0 <= range_index < data.shape[0] and 0 <= azimuth_index < data.shape[1]:
                value = data[range_index, azimuth_index]
                product = "Reflectivity (dBZ)" if self.current_ppi_data_type == "reflectivity" else "Velocity (m/s)"

                
                QToolTip.showText(
                    event.guiEvent.globalPos(),
                    f"{product}: {value:.2f}\nRange: {r:.1f} km\nAngle: {angle_deg - 30:.1f}°",
                    self
                )