import os
import sys
import numpy as np
import scipy.io
import matplotlib
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from datetime import datetime

matplotlib.use('QtAgg')

from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                               QHBoxLayout, QWidget, QFileDialog, QLabel, QListWidget)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, Signal, QObject, QTimer

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Reflectivity and Velocity Colormaps
reflectivity_cmap = mcolors.LinearSegmentedColormap.from_list(
    "reflectivity", ["purple", "blue", "green", "yellow", "orange", "red"]
)
velocity_cmap = mcolors.LinearSegmentedColormap.from_list(
    "velocity", ["blue", "lightblue", "lightgreen", "darkgreen", "white", 
                 "darkred", "red", "pink", "orange"]
)

class RadarVolume:
    def __init__(self, radar, lat, lon, elev_m, height_m, lambda_m, prf_hz, nyq_m_per_s,
                 datestr, time, vcp, el_deg, az_deg, aze_deg, bw_deg, sweep_el_deg,
                 sweep_az_deg, prod, radar_type, start_range_km):
        self.radar = radar
        self.lat = lat
        self.lon = lon
        self.elev_m = elev_m
        self.height_m = height_m
        self.lambda_m = lambda_m
        self.prf_hz = prf_hz
        self.nyq_m_per_s = nyq_m_per_s
        self.datestr = datestr
        self.time = time
        self.vcp = vcp
        self.el_deg = el_deg
        self.az_deg = az_deg
        self.aze_deg = aze_deg
        self.bw_deg = bw_deg
        self.sweep_el_deg = sweep_el_deg
        self.sweep_az_deg = sweep_az_deg
        self.prod = prod
        self.radar_type = radar_type
        self.start_range_km = start_range_km

    def __repr__(self):
        return f"RadarVolume({self.datestr}, {self.prod})"


def create_radar_volumes_from_mat(file_path):
    mat_data = scipy.io.loadmat(file_path)
    
    if 'volume' not in mat_data:
        print("No 'volume' key found in the .mat file. Please check the data structure.")
        return None, None, None
    
    volume_data = mat_data['volume']
    
    if volume_data.shape[1] > 0:
        first_volume = volume_data[0, 0]
        
        if 'prod' in first_volume.dtype.names:
            prod_data = first_volume['prod'][0]
            
            reflectivity_data = None
            velocity_data = None
            for entry in prod_data:
                if entry[0] == 'Z':  # Reflectivity
                    reflectivity_data = entry[3]
                    print("Reflectivity data shape:", reflectivity_data.shape)
                elif entry[0] == 'V':  # Velocity
                    velocity_data = entry[3]
                    print("Velocity data shape:", velocity_data.shape)
            
            radar_volume = RadarVolume(
                radar=first_volume['radar'][0] if 'radar' in first_volume.dtype.names else None,
                lat=first_volume['lat'][0] if 'lat' in first_volume.dtype.names else None,
                lon=first_volume['lon'][0] if 'lon' in first_volume.dtype.names else None,
                elev_m=first_volume['elev_m'][0] if 'elev_m' in first_volume.dtype.names else None,
                height_m=first_volume['height_m'][0] if 'height_m' in first_volume.dtype.names else None,
                lambda_m=first_volume['lambda_m'][0] if 'lambda_m' in first_volume.dtype.names else None,
                prf_hz=first_volume['prf_hz'][0] if 'prf_hz' in first_volume.dtype.names else None,
                nyq_m_per_s=first_volume['nyq_m_per_s'][0] if 'nyq_m_per_s' in first_volume.dtype.names else None,
                datestr=first_volume['datestr'][0] if 'datestr' in first_volume.dtype.names else None,
                time=first_volume['time'][0] if 'time' in first_volume.dtype.names else None,
                vcp=first_volume['vcp'][0] if 'vcp' in first_volume.dtype.names else None,
                el_deg=first_volume['el_deg'][0] if 'el_deg' in first_volume.dtype.names else None,
                az_deg=first_volume['az_deg'][0] if 'az_deg' in first_volume.dtype.names else None,
                aze_deg=first_volume['aze_deg'][0] if 'aze_deg' in first_volume.dtype.names else None,
                bw_deg=first_volume['bw_deg'][0] if 'bw_deg' in first_volume.dtype.names else None,
                sweep_el_deg=first_volume['sweep_el_deg'][0] if 'sweep_el_deg' in first_volume.dtype.names else None,
                sweep_az_deg=first_volume['sweep_az_deg'][0] if 'sweep_az_deg' in first_volume.dtype.names else None,
                prod=reflectivity_data,
                radar_type=first_volume['type'][0] if 'type' in first_volume.dtype.names else None,
                start_range_km=first_volume['start_range_km'][0] if 'start_range_km' in first_volume.dtype.names else None
            )
            return radar_volume, reflectivity_data, velocity_data
    
    print("No data found in volume.")
    return None, None, None


class Controller(QObject):
    matFileSelected = Signal(str)


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=10, height=8, dpi=100, polar=False):
        fig = Figure(figsize=(width, height), dpi=dpi)
        if polar:
            self.axes = fig.add_subplot(111, polar=True)
        else:
            self.axes = fig.add_subplot(111)
        self.axes.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
        super().__init__(fig)


class RadarDataUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PAR Radar Data Viewer")
        self.setGeometry(100, 100, 1600, 900)
        self.showMaximized()

        main_layout = QHBoxLayout()
        self.controller = Controller()

        # Layouts and widgets for the file selector
        self.raster_selector_layout = QVBoxLayout()
        self.raster_selector_layout.setAlignment(Qt.AlignTop)

        self.scan_folder_list = QListWidget()
        self.scan_folder_list.itemClicked.connect(self.load_mat_files_in_folder)
        self.raster_selector_layout.addWidget(self.scan_folder_list)

        self.mat_file_list = QListWidget()
        self.mat_file_list.itemClicked.connect(self.load_selected_mat_file)
        self.raster_selector_layout.addWidget(self.mat_file_list)

        self.load_button = QPushButton("Load Scan(s)")
        self.load_button.clicked.connect(self.load_scan_folders)
        self.raster_selector_layout.addWidget(self.load_button)

        # Layout and widgets for visualization
        self.visualization_layout = QVBoxLayout()

        # PPI Canvas
        self.ppi_canvas = MplCanvas(self, width=10, height=8, dpi=100, polar=True)
        self.ppi_canvas.axes.set_theta_zero_location("N")
        self.ppi_label = QLabel("PPI View", self)
        self.ppi_label.setStyleSheet("font-weight: bold; border: 1px solid black; padding: 5px;")
        self.visualization_layout.addWidget(self.ppi_label)
        self.visualization_layout.addWidget(self.ppi_canvas)

        # Buttons for Reflectivity and Velocity
        self.ppi_button_layout = QHBoxLayout()
        self.ppi_reflectivity_button = QPushButton("Reflectivity")
        self.ppi_reflectivity_button.clicked.connect(lambda: self.set_ppi_data_type("reflectivity"))
        self.ppi_velocity_button = QPushButton("Velocity")
        self.ppi_velocity_button.clicked.connect(lambda: self.set_ppi_data_type("velocity"))
        self.ppi_button_layout.addWidget(self.ppi_reflectivity_button)
        self.ppi_button_layout.addWidget(self.ppi_velocity_button)
        self.visualization_layout.addLayout(self.ppi_button_layout)

        # RHI Canvas
        self.rhi_canvas = MplCanvas(self, width=10, height=8, dpi=100, polar=True)
        self.rhi_canvas.axes.set_theta_zero_location("E")
        self.rhi_label = QLabel("RHI View", self)
        self.rhi_label.setStyleSheet("font-weight: bold; border: 1px solid black; padding: 5px;")
        self.visualization_layout.addWidget(self.rhi_label)
        self.visualization_layout.addWidget(self.rhi_canvas)

        # RHI Buttons
        self.rhi_button_layout = QHBoxLayout()
        self.rhi_reflectivity_button = QPushButton("Reflectivity")
        self.rhi_reflectivity_button.clicked.connect(lambda: self.set_rhi_data_type("reflectivity"))
        self.rhi_velocity_button = QPushButton("Velocity")
        self.rhi_velocity_button.clicked.connect(lambda: self.set_rhi_data_type("velocity"))
        self.rhi_button_layout.addWidget(self.rhi_reflectivity_button)
        self.rhi_button_layout.addWidget(self.rhi_velocity_button)
        self.visualization_layout.addLayout(self.rhi_button_layout)

        # Timeline controls
        self.timeline_button_layout = QHBoxLayout()
        self.back_button = QPushButton()
        self.back_button.setIcon(QIcon.fromTheme("media-skip-backward"))
        self.back_button.clicked.connect(self.back)
        self.timeline_button_layout.addWidget(self.back_button)

        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon.fromTheme("media-playback-start"))
        self.play_button.clicked.connect(self.toggle_play_pause)
        self.timeline_button_layout.addWidget(self.play_button)

        self.forward_button = QPushButton()
        self.forward_button.setIcon(QIcon.fromTheme("media-skip-forward"))
        self.forward_button.clicked.connect(self.forward)
        self.timeline_button_layout.addWidget(self.forward_button)

        self.visualization_layout.addLayout(self.timeline_button_layout)
        self.timeline_label = QLabel("Selected Time:")
        self.visualization_layout.addWidget(self.timeline_label)

        # Set up the layout
        main_layout.addLayout(self.raster_selector_layout, 1)
        main_layout.addLayout(self.visualization_layout, 3)

        central_widget = QWidget(self)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.controller.matFileSelected.connect(self.display_data_from_mat_file)

        
        self.base_folder_path = None
        self.scan_times = []
        self.current_scan_index = 0

        self.current_ppi_data_type = "reflectivity"
        self.current_rhi_data_type = "velocity"
        self.reflectivity_data = None
        self.velocity_data = None

        
        self.play_timer = QTimer()
        self.play_timer.timeout.connect(self.forward)  

    def set_ppi_data_type(self, data_type):
        self.current_ppi_data_type = data_type
        self.update_ppi_view()

    def set_rhi_data_type(self, data_type):
        self.current_rhi_data_type = data_type
        self.update_rhi_view()

    def load_scan_folders(self):
        self.base_folder_path = QFileDialog.getExistingDirectory(self, "Select Base Folder", os.path.expanduser("~"))
        if self.base_folder_path:
            self.scan_folder_list.clear()
            self.scan_times.clear()

            scan_folders = [f for f in os.listdir(self.base_folder_path) if os.path.isdir(os.path.join(self.base_folder_path, f)) and f.startswith('scan_')]
            for scan_folder in scan_folders:
                self.scan_folder_list.addItem(scan_folder)

    def load_mat_files_in_folder(self, item):
        folder_name = item.text()
        matlab_folder_path = os.path.join(self.base_folder_path, folder_name, 'MATLAB')

        if os.path.exists(matlab_folder_path):
            self.mat_file_list.clear()
            mat_files = [f for f in os.listdir(matlab_folder_path) if f.endswith('.mat')]

            self.scan_times.clear()
            for mat_file in mat_files:
                timestamp_str = self.extract_timestamp_from_filename(mat_file)
                if timestamp_str:
                    self.scan_times.append((timestamp_str, os.path.join(matlab_folder_path, mat_file)))
                    self.mat_file_list.addItem(mat_file)

    def load_selected_mat_file(self, item):
        folder_item = self.scan_folder_list.currentItem()
        if folder_item:
            folder_name = folder_item.text()
            full_path = os.path.join(self.base_folder_path, folder_name, 'MATLAB', item.text())
            self.controller.matFileSelected.emit(full_path)

    def display_data_from_mat_file(self, file_path):
        radar_volume, reflectivity_data, velocity_data = create_radar_volumes_from_mat(file_path)
        self.reflectivity_data = reflectivity_data
        self.velocity_data = velocity_data

        self.update_ppi_view()
        self.update_rhi_view()

    def update_ppi_view(self):
        if self.reflectivity_data is None and self.velocity_data is None:
            print("No data available for PPI plot.")
            return

        # Select data, colormap, and normalization
        data = self.reflectivity_data if self.current_ppi_data_type == "reflectivity" else self.velocity_data
        cmap = reflectivity_cmap if self.current_ppi_data_type == "reflectivity" else velocity_cmap
        norm = mcolors.Normalize(vmin=-30, vmax=75) if self.current_ppi_data_type == "reflectivity" else mcolors.Normalize(vmin=-50, vmax=50)

        # Clear and reinitialize the figure and axes
        self.ppi_canvas.figure.clf()  # Clear entire figure, including any color bars
        self.ppi_canvas.axes = self.ppi_canvas.figure.add_subplot(111, polar=True)
        self.ppi_canvas.axes.set_theta_zero_location("N")
        self.ppi_canvas.axes.set_aspect('equal', adjustable='box')

       
        self.ppi_canvas.figure.subplots_adjust(left=0.05, right=0.70)  # Adjust as needed

        # Set up data grid and plot data
        azimuths = np.linspace(-np.pi / 6, np.pi / 6, data.shape[1] + 1)
        ranges = np.linspace(0, 100, data.shape[0] + 1)
        azimuth_grid, range_grid = np.meshgrid(azimuths, ranges)
        ppi_plot = self.ppi_canvas.axes.pcolormesh(azimuth_grid, range_grid, data, cmap=cmap, norm=norm, shading='auto')

        # Create color bar
        self.ppi_colorbar = self.ppi_canvas.figure.colorbar(ppi_plot, ax=self.ppi_canvas.axes, orientation='vertical', pad=0.05)
        self.ppi_colorbar.set_label("Reflectivity (dBZ)" if self.current_ppi_data_type == "reflectivity" else "Velocity (m/s)")

        # Set title and axes properties
        self.ppi_canvas.axes.set_title("PPI View - Reflectivity" if self.current_ppi_data_type == "reflectivity" else "PPI View - Velocity")
        self.ppi_canvas.axes.set_thetamin(-30)
        self.ppi_canvas.axes.set_thetamax(30)
        self.ppi_canvas.axes.set_ylim(0, 100)
        self.ppi_canvas.draw()

    def update_rhi_view(self):
        if self.reflectivity_data is None and self.velocity_data is None:
            print("No data available for RHI plot.")
            return

        # Select data, colormap, and normalization
        data = self.reflectivity_data if self.current_rhi_data_type == "reflectivity" else self.velocity_data
        cmap = reflectivity_cmap if self.current_rhi_data_type == "reflectivity" else velocity_cmap
        norm = mcolors.Normalize(vmin=-30, vmax=75) if self.current_rhi_data_type == "reflectivity" else mcolors.Normalize(vmin=-50, vmax=50)

        # Clear and reinitialize the figure and axes
        self.rhi_canvas.figure.clf()  # Clear entire figure, including any color bars
        self.rhi_canvas.axes = self.rhi_canvas.figure.add_subplot(111, polar=True)
        self.rhi_canvas.axes.set_theta_zero_location("E")
        self.rhi_canvas.axes.set_aspect('equal', adjustable='box')

        # Adjust layout to center the plot 
        self.rhi_canvas.figure.subplots_adjust(left=0.05, right=0.70)  # Adjust as needed

        # Set up data grid and plot data
        elevations = np.linspace(0, np.pi / 6, data.shape[0] + 1)
        ranges = np.linspace(0, 100, data.shape[1] + 1)
        elevation_grid, range_grid = np.meshgrid(elevations, ranges)
        rhi_plot = self.rhi_canvas.axes.pcolormesh(elevation_grid, range_grid, data.T, cmap=cmap, norm=norm, shading='auto')

        # Create color bar
        self.rhi_colorbar = self.rhi_canvas.figure.colorbar(rhi_plot, ax=self.rhi_canvas.axes, orientation='vertical', pad=0.05)
        self.rhi_colorbar.set_label("Reflectivity (dBZ)" if self.current_rhi_data_type == "reflectivity" else "Velocity (m/s)")

        # Set title and axes properties
        self.rhi_canvas.axes.set_title("RHI View - Reflectivity" if self.current_rhi_data_type == "reflectivity" else "RHI View - Velocity")
        self.rhi_canvas.axes.set_thetamin(0)
        self.rhi_canvas.axes.set_thetamax(30)
        self.rhi_canvas.axes.set_ylim(0, 100)
        self.rhi_canvas.draw()

    def back(self):
        if not self.scan_times:
            return
        self.current_scan_index = (self.current_scan_index - 1) % len(self.scan_times)
        self.update_scan_from_index()

    def forward(self):
        if not self.scan_times:
            return
        self.current_scan_index = (self.current_scan_index + 1) % len(self.scan_times)
        self.update_scan_from_index()

    def toggle_play_pause(self):
        if not self.scan_times:
            return
        if self.play_timer.isActive():
            self.play_timer.stop()
            self.play_button.setIcon(QIcon.fromTheme("media-playback-start")) 
        else:
            self.play_timer.start(1000)  # Start timer with 1-second intervals
            self.play_button.setIcon(QIcon.fromTheme("media-playback-pause"))  

    def update_scan_from_index(self):
        if not self.scan_times:
            return
        timestamp_str, file_path = self.scan_times[self.current_scan_index]
        formatted_time = self.format_timestamp(timestamp_str)
        self.timeline_label.setText(f"Selected Time: {formatted_time}")
        self.controller.matFileSelected.emit(file_path)

    def extract_timestamp_from_filename(self, filename):
        try:
            timestamp_str = filename.split('_')[1] + filename.split('_')[2][:6]
            return timestamp_str
        except IndexError:
            return None

    def format_timestamp(self, timestamp_str):
        try:
            parsed_time = datetime.strptime(timestamp_str, "%d%m%y%H%M%S")
            if parsed_time.year == 2007:
                parsed_time = parsed_time.replace(year=2024)
            return parsed_time.strftime("%m/%d/%Y %H:%M:%S")
        except ValueError:
            return timestamp_str


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RadarDataUI()
    window.show()
    sys.exit(app.exec())
