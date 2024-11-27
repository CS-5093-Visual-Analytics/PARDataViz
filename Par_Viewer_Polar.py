import os
import sys
import numpy as np
import scipy.io
import matplotlib
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from pathlib import Path
from datetime import datetime

matplotlib.use('QtAgg')

from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QDockWidget, QSizeGrip,
                               QHBoxLayout, QWidget, QFileDialog, QLabel, QListWidget, QToolTip, QSlider)
from PySide6.QtGui import QIcon, QAction, QActionGroup
from PySide6.QtCore import Qt, Signal, QObject, QTimer

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ppi_canvas import PPI_Canvas
from rhi_canvas import RHI_Canvas
from data_manager import Data_Manager
from scan_set import ScanSet
from scanset_builder import ScansetBuilder
from volume_slice_selector import VolumeSliceSelector
from dynamic_dock_widget import DynamicDockWidget
import gc

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


# class MplCanvas(FigureCanvas):
#     def __init__(self, parent=None, width=10, height=8, dpi=100, polar=False):
#         fig = Figure(figsize=(width, height), dpi=dpi)
#         if polar:
#             self.axes = fig.add_subplot(111, polar=True)
#         else:
#             self.axes = fig.add_subplot(111)
#         self.axes.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
#         super().__init__(fig)


class RadarDataUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PAR Radar Data Viewer")
        self.setGeometry(100, 100, 1600, 900)
        

        # Initialize attributes
        self.scan_times = []  
        self.current_scan_index = 0  
        self.current_ppi_data_type = "reflectivity"  
        self.current_rhi_data_type = "velocity"  
        self.reflectivity_data = None  
        self.velocity_data = None  
        self.base_folder_path = None  

        # Timer for playback
        self.play_timer = QTimer()
        self.play_timer.timeout.connect(self.forward)

        # Main layout
        main_layout = QHBoxLayout()
        self.controller = Controller()
        self.data_manager = Data_Manager()
        
        # Menu bar and related actions
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        
        new_scanset_action = QAction("New scanset...", self, shortcut="Ctrl+N")
        new_scanset_action.triggered.connect(self.show_scanset_builder)
        file_menu.addAction(new_scanset_action)

        load_scanset_action = QAction("Load scanset...", self, shortcut="Ctrl+O")
        load_scanset_action.triggered.connect(self.load_scanset)
        file_menu.addAction(load_scanset_action)

        exit_action = QAction("Exit", self, shortcut="Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        self.view_menu = menu_bar.addMenu("View")
        
        new_ppi_view_action = QAction("New PPI View...", self)
        new_ppi_view_action.triggered.connect(self.create_new_ppi_view)
        self.view_menu.addAction(new_ppi_view_action)

        new_rhi_view_action = QAction("New RHI View...", self)
        new_rhi_view_action.triggered.connect(self.create_new_rhi_view)
        self.view_menu.addAction(new_rhi_view_action)

        # Sections (e.g. context_menu.addSection()) may be ignored depending on the
        # platform look and feel, so just add a disabled "action" and separator
        # to act as a label for a group of actions in the menu.
        # view_menu.addSection("Toggle Views")
        self.toggle_views_action = QAction("Toggle Views", self)
        self.toggle_views_action.setEnabled(False)
        self.view_menu.addAction(self.toggle_views_action)
        self.view_menu.addSeparator()

        # Status bar
        self.statusBar()

        # Timeline slider
        # self.timeline_slider = QSlider(Qt.Horizontal)
        # self.timeline_slider.setRange(0, 0)  # Initial range with no data
        # self.timeline_slider.setSingleStep(1)
        # self.timeline_slider.setPageStep(1)
        # self.timeline_slider.valueChanged.connect(self.scrub_through_data)
        # self.timeline_slider.setTickPosition(QSlider.TicksBelow)
        # self.timeline_slider.setTickInterval(1)
        # self.timeline_slider.setEnabled(False)  # Disabled until data is loaded

        # Layouts and widgets for the file selector
        # self.raster_selector_layout = QVBoxLayout()
        # self.raster_selector_layout.setAlignment(Qt.AlignTop)

        # self.scan_folder_list = QListWidget()
        # self.scan_folder_list.itemClicked.connect(self.load_mat_files_in_folder)
        # self.raster_selector_layout.addWidget(self.scan_folder_list)

        # self.mat_file_list = QListWidget()
        # self.mat_file_list.itemClicked.connect(self.load_selected_mat_file)
        # self.raster_selector_layout.addWidget(self.mat_file_list)

        # self.load_button = QPushButton("Load Scan(s)")
        # self.load_button.clicked.connect(self.load_scan_folders)
        # self.raster_selector_layout.addWidget(self.load_button)

        # Get wild with docking
        self.setDockNestingEnabled(True)

        # Scanset Builder
        self.dockable_ssb = QDockWidget("Scan Set Builder", self)
        # self.dockable_ssb.setFloating(True) # Start as a floating window
        # self.dockable_ssb.hide() # Don't show up at startup
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockable_ssb)
        self.view_menu.addAction(self.dockable_ssb.toggleViewAction())

        self.scanset_builder = ScansetBuilder()
        self.dockable_ssb.setWidget(self.scanset_builder)

        # Volume Slice Selector (separate but dockable dialog)
        self.dockable_vss = QDockWidget("Volume Slice Selector", self)
        self.dockable_vss.setFloating(True) # Start as a floating window
        self.dockable_vss.hide() # Don't show up at startup
        self.view_menu.addAction(self.dockable_vss.toggleViewAction())

        self.volume_slice_selector = VolumeSliceSelector()
        self.volume_slice_selector.update_grid(1, 1, 20, 20, 10)
        self.dockable_vss.setWidget(self.volume_slice_selector)
        
        # This is a bit of a hack to create a known position in the menu
        # before which we can insert new dynamic views.
        self.dummy_view_action = QAction("Dummy View Action", self)
        self.dummy_view_action.setEnabled(False)
        self.dummy_view_action.setVisible(False)
        self.view_menu.addAction(self.dummy_view_action)
        
        self.rhi_views = []
        self.rhi_view_actions = {}
        self.rhi_view_count = 0
        self.ppi_views = []
        self.ppi_view_actions = {}
        self.ppi_view_count = 0

        # Initial PPI Canvas
        initial_ppi = self.create_new_ppi_view()
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, initial_ppi)

        # Initial RHI Canvas
        initial_rhi = self.create_new_rhi_view()
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, initial_rhi)

        # 
        # self.dockable_ppi = QDockWidget("PPI View", self)
        # self.ppi_canvas = PPI_Canvas(self)
        # self.dockable_ppi.setWidget(self.ppi_canvas)
        # self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockable_ppi)
        # self.view_menu.addAction(self.dockable_ppi.toggleViewAction())

        # # RHI Canvas
        # self.dockable_rhi = QDockWidget("RHI View", self)
        # self.rhi_canvas = RHI_Canvas(self)
        # self.dockable_rhi.setWidget(self.rhi_canvas)
        # self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dockable_rhi)
        # self.view_menu.addAction(self.dockable_rhi.toggleViewAction())

        # Timeline controls
        # self.timeline_button_layout = QHBoxLayout()
        # self.back_button = QPushButton()
        # self.back_button.setIcon(QIcon.fromTheme("media-skip-backward"))
        # self.back_button.clicked.connect(self.back)
        # self.timeline_button_layout.addWidget(self.back_button)

        # self.play_button = QPushButton()
        # self.play_button.setIcon(QIcon.fromTheme("media-playback-start"))
        # self.play_button.clicked.connect(self.toggle_play_pause)
        # self.timeline_button_layout.addWidget(self.play_button)

        # self.forward_button = QPushButton()
        # self.forward_button.setIcon(QIcon.fromTheme("media-skip-forward"))
        # self.forward_button.clicked.connect(self.forward)
        # self.timeline_button_layout.addWidget(self.forward_button)

        # Add the slider to the timeline layout
        # self.timeline_button_layout.addWidget(self.timeline_slider)

        # self.visualization_layout.addLayout(self.timeline_button_layout)
        # self.timeline_label = QLabel("Selected Time:")
        # self.visualization_layout.addWidget(self.timeline_label)

        # Set up the layout
        # main_layout.addLayout(self.raster_selector_layout, 1)
        # main_layout.addLayout(self.visualization_layout, 3)

        # central_widget = QWidget(self)
        # central_widget.setLayout(main_layout)
        # self.setCentralWidget(central_widget)

        # Connect the controller signal
        self.controller.matFileSelected.connect(self.display_data_from_mat_file)

        self.showMaximized()
        self.statusBar().showMessage("Ready to rock. 🎸")
        

    def closeEvent(self, event):
        """Ensure the viewer quits when the main window is closed. This is necessary
        because a QApplication will continue running as long as at least one
        top-level widget is still visible. This behavior is undesireable. The 
        user shouldn't have to close all windows before exiting."""
        QApplication.instance().quit()

    def create_new_ppi_view(self):
        self.ppi_view_count = self.ppi_view_count + 1
        view_title = f'PPI View {self.ppi_view_count}'
        dock_widget = DynamicDockWidget(view_title, self, plot_type='PPI')
        dock_widget.setFloating(True) # Start as a floating window
        dock_widget.show()

        ppi_canvas = PPI_Canvas(dock_widget)
        # TODO: Hook up signals and slots for a new PPI view
        dock_widget.setWidget(ppi_canvas)

        toggle_view_action = dock_widget.toggleViewAction()
        # toggle_view_action.setChecked(True)
        self.view_menu.insertAction(self.dummy_view_action, toggle_view_action)
        # Add an entry in the widget -> action mapping
        self.ppi_view_actions[dock_widget] = toggle_view_action

        self.ppi_views.append(dock_widget)
        return dock_widget

    def remove_ppi_view(self, dock_widget):
        if dock_widget in self.ppi_views:
            self.ppi_views.remove(dock_widget)

        # Use the mapping between widget -> action to easily remove the view action
        if dock_widget in self.ppi_view_actions:
            action = self.ppi_view_actions.pop(dock_widget)
            self.view_menu.removeAction(action)


    def create_new_rhi_view(self):
        self.rhi_view_count = self.rhi_view_count + 1
        view_title = f'RHI View {self.rhi_view_count}'
        dock_widget = DynamicDockWidget(view_title, self, plot_type='RHI')
        dock_widget.setFloating(True) # Start as a floating window
        dock_widget.show()
        
        rhi_canvas = RHI_Canvas(dock_widget)
        
        # TODO: Hook up signals and slots for a new RHI view
        
        dock_widget.setWidget(rhi_canvas)
        
        toggle_view_action = dock_widget.toggleViewAction()
        # toggle_view_action.setChecked(True)
        self.view_menu.insertAction(self.dummy_view_action, toggle_view_action)
        # Add an entry in the widget -> action mapping
        self.rhi_view_actions[dock_widget] = toggle_view_action

        self.rhi_views.append(dock_widget)
        return dock_widget

    def remove_rhi_view(self, dock_widget):
        if dock_widget in self.rhi_views:
            self.rhi_views.remove(dock_widget)

        # Use the mapping between widget -> action to easily remove the view action
        if dock_widget in self.rhi_view_actions:
            action = self.rhi_view_actions.pop(dock_widget)
            self.view_menu.removeAction(action)
        
    def show_scanset_builder(self):
        self.dockable_ssb.setVisible(True)
        self.scanset_builder.new_scanset()

    def load_scanset(self):
        (filename, selected_filter) = QFileDialog.getOpenFileName(self, "Load scanset...", os.path.expanduser("~"), "JSON files (*.json)")
        if filename:
            self.scanset = ScanSet.load_scanset(Path(filename))
            self.statusBar().showMessage(f'Loaded scanset "{self.scanset.get_name()}" ✔️')

# OLD STUFF



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
            
            # Enable and update the slider range based on loaded scans
            if self.scan_times:
                self.timeline_slider.setRange(0, len(self.scan_times) - 1)
                self.timeline_slider.setEnabled(True)
            else:
                self.timeline_slider.setEnabled(False)

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
        self.radar_volume = radar_volume

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
        ranges = np.linspace(self.radar_volume.start_range_km, 115, data.shape[0] + 1)
        azimuth_grid, range_grid = np.meshgrid(azimuths, ranges)
        ppi_plot = self.ppi_canvas.axes.pcolormesh(azimuth_grid, range_grid, data, cmap=cmap, norm=norm, shading='auto')

        # Create color bar
        self.ppi_colorbar = self.ppi_canvas.figure.colorbar(ppi_plot, ax=self.ppi_canvas.axes, orientation='vertical', pad=0.05)
        self.ppi_colorbar.set_label("Reflectivity (dBZ)" if self.current_ppi_data_type == "reflectivity" else "Velocity (m/s)")

        # Set title and axes properties
        self.ppi_canvas.mpl_connect('motion_notify_event', self.on_ppi_hover)
        self.ppi_canvas.mpl_connect('motion_notify_event', self.on_ppi_hover)
        self.ppi_canvas.mpl_connect('axes_enter_event', self.on_axes_enter)
        self.ppi_canvas.mpl_connect('axes_leave_event', self.on_axes_leave)
        self.ppi_canvas.axes.set_title("PPI View - Reflectivity" if self.current_ppi_data_type == "reflectivity" else "PPI View - Velocity")
        self.ppi_canvas.axes.set_thetamin(-30)
        self.ppi_canvas.axes.set_thetamax(30)
        self.ppi_canvas.axes.set_ylim(self.radar_volume.start_range_km, 115)
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
        ranges = np.linspace(self.radar_volume.start_range_km, 115, data.shape[1] + 1)
        # ranges = np.linspace(0, 100, data.shape[1] + 1)
        elevation_grid, range_grid = np.meshgrid(elevations, ranges)
        rhi_plot = self.rhi_canvas.axes.pcolormesh(elevation_grid, range_grid, data.T, cmap=cmap, norm=norm, shading='auto')

        # Create color bar
        self.rhi_colorbar = self.rhi_canvas.figure.colorbar(rhi_plot, ax=self.rhi_canvas.axes, orientation='vertical', pad=0.05)
        self.rhi_colorbar.set_label("Reflectivity (dBZ)" if self.current_rhi_data_type == "reflectivity" else "Velocity (m/s)")

        # Set title and axes properties
        self.rhi_canvas.mpl_connect('motion_notify_event', self.on_rhi_hover)
        self.rhi_canvas.mpl_connect('motion_notify_event', self.on_rhi_hover)
        self.rhi_canvas.mpl_connect('axes_enter_event', self.on_axes_enter)
        self.rhi_canvas.mpl_connect('axes_leave_event', self.on_axes_leave)
        self.rhi_canvas.axes.set_title("RHI View - Reflectivity" if self.current_rhi_data_type == "reflectivity" else "RHI View - Velocity")
        self.rhi_canvas.axes.set_thetamin(0)
        self.rhi_canvas.axes.set_thetamax(30)
        self.rhi_canvas.axes.set_ylim(self.radar_volume.start_range_km, 115)
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
        
        # Update slider position (prevent recursive updates)
        self.timeline_slider.blockSignals(True)
        self.timeline_slider.setValue(self.current_scan_index)
        self.timeline_slider.blockSignals(False)

        # Extract and display data
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


    def on_rhi_hover(self, event):
        if event.inaxes != self.rhi_canvas.axes:
            return

        # Get mouse coordinates (polar)
        r = event.ydata  # Distance from center
        theta = event.xdata  # Elevation angle in radians

        # Convert to degrees
        elev_deg = np.degrees(theta)

        
        data = self.reflectivity_data if self.current_rhi_data_type == "reflectivity" else self.velocity_data
        if data is not None and r is not None:
            # Calculate indices for data lookup
            range_index = int(r * (data.shape[1] / 100))  # Assuming max range is 100 km
            elev_index = int((elev_deg / 30) * data.shape[0])  # Assuming elevation max is 30°

            if 0 <= range_index < data.shape[1] and 0 <= elev_index < data.shape[0]:
                value = data[elev_index, range_index]
                product = "Reflectivity (dBZ)" if self.current_rhi_data_type == "reflectivity" else "Velocity (m/s)"

                
                QToolTip.showText(
                    event.guiEvent.globalPos(),
                    f"{product}: {value:.2f}\nRange: {r:.1f} km\nElevation: {elev_deg:.1f}°",
                    self
                )
    
    def on_axes_enter(self, event):
        if event.inaxes in [self.ppi_canvas.axes, self.rhi_canvas.axes]:
            QApplication.setOverrideCursor(Qt.CrossCursor)

    def on_axes_leave(self, event):
        if event.inaxes in [self.ppi_canvas.axes, self.rhi_canvas.axes]:
            QApplication.restoreOverrideCursor()

    def scrub_through_data(self, value):
        if not self.scan_times:
            return

        # Update current scan index and trigger data update
        self.current_scan_index = value
        self.update_scan_from_index()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RadarDataUI()
    window.show()

    # # Force garbage collection periodically to test
    # def force_gc():
    #     print("\nForcing garbage collection...")
    #     gc.collect()
    #     for obj in gc.garbage:
    #         print(f"Uncollectable: {obj}")

    # # Create a timer to periodically force garbage collection
    # from PySide6.QtCore import QTimer
    # gc_timer = QTimer()
    # gc_timer.timeout.connect(force_gc)
    # gc_timer.start(5000)  # Run every 5 seconds

    sys.exit(app.exec())