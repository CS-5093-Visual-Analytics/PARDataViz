import os
import sys
import random
import numpy as np
import matplotlib
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from pathlib import Path
from datetime import datetime
from radar_volume import RadarVolume

matplotlib.use('QtAgg')

from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QDockWidget, QSizeGrip,
                               QHBoxLayout, QWidget, QFileDialog, QLabel, QListWidget, QToolTip, QSlider)
from PySide6.QtGui import QIcon, QAction, QActionGroup
from PySide6.QtCore import Qt, Signal, Slot, QObject, QTimer

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ppi_canvas import PPI_Canvas
from rhi_canvas import RHI_Canvas
from data_manager import Data_Manager
from scan_set import ScanSet
from scanset_builder import ScansetBuilder
from volume_slice_selector import VolumeSliceSelector
from dynamic_dock_widget import DynamicDockWidget
from timeline_controls import TimelineControls
from color_maps import ColorMaps

class Controller(QObject):
    mat_file_selected = Signal(str)

class RadarDataUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PAR Radar Data Viewer")
        
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

        # TODO: Backing data!!!
        self.controller = Controller()
        self.data_manager = Data_Manager()
        self.data_manager.scan_times_changed.connect(self.on_scan_times_changed)

        # Menu bar and related actions
        menu_bar = self.menuBar()
        self.file_menu = menu_bar.addMenu("File")
        
        new_scanset_action = QAction("New scanset...", self, shortcut="Ctrl+N")
        new_scanset_action.triggered.connect(self.new_scanset)
        self.file_menu.addAction(new_scanset_action)

        load_scanset_action = QAction("Load scanset...", self, shortcut="Ctrl+O")
        load_scanset_action.triggered.connect(self.load_scanset)
        self.file_menu.addAction(load_scanset_action)

        exit_action = QAction("Exit", self, shortcut="Ctrl+Q")
        exit_action.triggered.connect(self.close)
        self.file_menu.addAction(exit_action)

        self.view_menu = menu_bar.addMenu("View")
        
        new_ppi_view_action = QAction("New PPI View...", self)
        new_ppi_view_action.triggered.connect(lambda: self.create_new_ppi_view(True))
        self.view_menu.addAction(new_ppi_view_action)

        new_rhi_view_action = QAction("New RHI View...", self)
        new_rhi_view_action.triggered.connect(lambda: self.create_new_rhi_view(True))
        self.view_menu.addAction(new_rhi_view_action)

        # Sections (e.g. context_menu.addSection()) may be ignored depending on the
        # platform look and feel, so just add a disabled "action" and separator
        # to act as a label for a group of actions in the menu.
        # view_menu.addSection("Toggle Views")
        self.toggle_views_action = QAction("Toggle Views", self)
        self.toggle_views_action.setEnabled(False)
        self.view_menu.addAction(self.toggle_views_action)
        self.view_menu.addSeparator()

        # Get wild with docking
        self.setDockNestingEnabled(True)

        # Scanset Builder
        self.dockable_ssb = QDockWidget("Scan Set Builder", self)
        # self.dockable_ssb.setFloating(True) # Start as a floating window
        self.dockable_ssb.hide() # Don't show up at startup
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockable_ssb)
        self.view_menu.addAction(self.dockable_ssb.toggleViewAction())

        self.scanset_builder = ScansetBuilder()
        self.scanset_builder.status_updated.connect(self.on_status_updated)
        self.scanset_builder.scanset_loaded.connect(self.data_manager.on_scanset_load)
        self.dockable_ssb.setWidget(self.scanset_builder)

        # Volume Slice Selector (separate but dockable dialog)
        self.dockable_vss = QDockWidget("Volume Slice Selector", self)
        self.dockable_vss.setFloating(True) # Start as a floating window
        self.dockable_vss.hide() # Don't show up at startup
        self.view_menu.addAction(self.dockable_vss.toggleViewAction())

        self.volume_slice_selector = VolumeSliceSelector()
        self.volume_slice_selector.on_grid_updated(1, 1, 20, 20, 10)
        self.dockable_vss.setWidget(self.volume_slice_selector)
        
        # Timeline controls    
        self.dockable_timec = QDockWidget("Timeline Controls", self)
        self.dockable_timec.hide()
        self.timeline_controls = TimelineControls()
        self.dockable_timec.setWidget(self.timeline_controls)
        self.view_menu.addAction(self.dockable_timec.toggleViewAction())
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dockable_timec)

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
        initial_ppi = self.create_new_ppi_view(False)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, initial_ppi)

        # Initial RHI Canvas
        initial_rhi = self.create_new_rhi_view(False)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, initial_rhi)

        # TODO: BACKING DATA
        # Connect the controller signal
        self.controller.mat_file_selected.connect(self.display_data_from_mat_file)

        self.happy_messages = ['Jolly good.', 'Happy hunting.', 'Best of luck.', 'I\'m rooting for you.']
        self.ready_status_widget = QLabel('Ready to rock. 🎸 v0.1')
        self.show()
        self.statusBar().addPermanentWidget(self.ready_status_widget)
        self.statusBar().showMessage(f'PAR Data Visualizer initialized! {random.choice(self.happy_messages)}')
        
    def closeEvent(self, event):
        """Ensure the viewer quits when the main window is closed. This is necessary
        because a QApplication will continue running as long as at least one
        top-level widget is still visible. This behavior is undesireable. The 
        user shouldn't have to close all windows before exiting."""
        QApplication.instance().quit()

    def create_new_ppi_view(self, floating):
        self.ppi_view_count = self.ppi_view_count + 1
        view_title = f'PPI View {self.ppi_view_count}'
        dock_widget = DynamicDockWidget(view_title, self, plot_type='PPI')
        
        if floating:
            dock_widget.setFloating(floating) # Start as a floating window
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
        self.statusBar().showMessage('Dynamic PPI view created.')
        return dock_widget

    def remove_ppi_view(self, dock_widget):
        if dock_widget in self.ppi_views:
            self.ppi_views.remove(dock_widget)

        # Use the mapping between widget -> action to easily remove the view action
        if dock_widget in self.ppi_view_actions:
            action = self.ppi_view_actions.pop(dock_widget)
            self.view_menu.removeAction(action)
        
        self.statusBar().showMessage('Dynamic PPI view closed.')

    def create_new_rhi_view(self, floating):
        self.rhi_view_count = self.rhi_view_count + 1
        view_title = f'RHI View {self.rhi_view_count}'
        dock_widget = DynamicDockWidget(view_title, self, plot_type='RHI')

        if floating:
            dock_widget.setFloating(floating) # Start as a floating window
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
        self.statusBar().showMessage('Dynamic RHI view created.')
        return dock_widget

    def remove_rhi_view(self, dock_widget):
        if dock_widget in self.rhi_views:
            self.rhi_views.remove(dock_widget)

        # Use the mapping between widget -> action to easily remove the view action
        if dock_widget in self.rhi_view_actions:
            action = self.rhi_view_actions.pop(dock_widget)
            self.view_menu.removeAction(action)

        self.statusBar().showMessage('Dynamic RHI view closed.')
        
    def new_scanset(self):
        self.dockable_ssb.setVisible(True)
        self.scanset = ScanSet("New scanset", base_dir=Path(os.path.expanduser("~")))
        self.scanset_builder.on_scanset_loaded(self.scanset)

    def load_scanset(self):
        (filename, selected_filter) = QFileDialog.getOpenFileName(self, "Load scanset...", os.path.expanduser("~"), "JSON files (*.json)")
        if filename:
            self.scanset = ScanSet.load_scanset(Path(filename))
            self.scanset_builder.on_scanset_loaded(self.scanset)
            self.statusBar().showMessage(f'Loaded scanset "{self.scanset.get_name()}" ✔️')

    @Slot(str)
    def on_status_updated(self, status: str):
        self.statusBar().showMessage(status)

    @Slot(int)
    def on_scan_times_changed(self, num_times: int):
        self.timeline_controls.on_scan_times_changed(num_times)
        self.dockable_timec.show()

# OLD STUFF



    def set_ppi_data_type(self, data_type):
        self.current_ppi_data_type = data_type
        self.update_ppi_view()

    def set_rhi_data_type(self, data_type):
        self.current_rhi_data_type = data_type
        self.update_rhi_view()

  
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
            self.controller.mat_file_selected.emit(full_path)

    def display_data_from_mat_file(self, file_path):
        radar_volume, reflectivity_data, velocity_data = RadarVolume.create_radar_volumes_from_mat(file_path)
        self.reflectivity_data = reflectivity_data
        self.velocity_data = velocity_data
        self.radar_volume = radar_volume

        self.update_ppi_view()
        self.update_rhi_view()

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
        self.controller.mat_file_selected.emit(file_path)

    

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
