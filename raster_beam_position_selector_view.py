import os
import numpy as np
import gzip
from PyQt5.QtWidgets import QApplication, QMainWindow, QGridLayout, QWidget, QPushButton, QListWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


def load_radar_data_from_file(file_path):
    with gzip.open(file_path, 'rb') as f:
        data = f.read()  
    beam_positions = np.random.rand(10, 10) 
    return beam_positions


def load_all_radar_data(folder_path):
    radar_data = {}
    for filename in os.listdir(folder_path):
        if filename.endswith('.gz'):
            file_path = os.path.join(folder_path, filename)
            radar_data[filename] = load_radar_data_from_file(file_path)
    return radar_data


class RadarFileSelector(QWidget):
    def __init__(self, radar_data, file_selected_callback):
        super().__init__()
        self.radar_data = radar_data
        self.file_selected_callback = file_selected_callback
        self.initUI()
    
    def initUI(self):
        self.layout = QVBoxLayout()
        self.file_list = QListWidget()
        for filename in self.radar_data.keys():
            self.file_list.addItem(filename)
        self.file_list.clicked.connect(self.on_file_selected)
        self.layout.addWidget(self.file_list)
        self.setLayout(self.layout)
    
    def on_file_selected(self, index):
        filename = self.file_list.item(index.row()).text()
        beam_positions = self.radar_data[filename]
        self.file_selected_callback(filename, beam_positions)


class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure()
        self.ax = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)

    def plot_data(self, data, title=""):
        self.ax.clear()
        self.ax.imshow(data, aspect='auto', cmap='viridis')
        self.ax.set_title(title)
        self.draw()


class RasterBeamSelector(QWidget):
    def __init__(self, beam_positions, update_callback):
        super().__init__()
        self.layout = QGridLayout()
        self.beam_positions = beam_positions
        self.update_callback = update_callback
        self.buttons = [] 
        self.initUI()
    
    def initUI(self):
        for i in range(self.beam_positions.shape[0]):
            row_buttons = []
            for j in range(self.beam_positions.shape[1]):
                button = QPushButton(f'{i},{j}')
                button.clicked.connect(lambda _, x=i, y=j: self.on_button_clicked(x, y))
                self.layout.addWidget(button, i, j)
                row_buttons.append(button)
            self.buttons.append(row_buttons)
        self.setLayout(self.layout)

    def on_button_clicked(self, x, y):
        
        self.update_callback(x, y)
        self.highlight_row_and_column(x, y)

    def highlight_row_and_column(self, x, y):

        for i, row in enumerate(self.buttons):
            for j, button in enumerate(row):
                if i == x or j == y:  
                    button.setStyleSheet("background-color: yellow")
                else:  
                    button.setStyleSheet("")


class MainWindow(QMainWindow):
    def __init__(self, radar_data):
        super().__init__()
        self.setWindowTitle("PAR Radar Data Viewer")
        
        self.radar_data = radar_data
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        
        self.file_selector = RadarFileSelector(radar_data, self.load_raster_view)
        self.main_layout.addWidget(self.file_selector)
        
        self.ppi_canvas = PlotCanvas(self)
        self.rhi_canvas = PlotCanvas(self)
        self.main_layout.addWidget(self.ppi_canvas)
        self.main_layout.addWidget(self.rhi_canvas)
        
        self.raster_view = RasterBeamSelector(np.zeros((10, 10)), self.update_views)  
        self.main_layout.addWidget(self.raster_view)
        
        self.setCentralWidget(self.central_widget)

    def load_raster_view(self, filename, beam_positions):
        self.main_layout.removeWidget(self.raster_view)
        self.raster_view.deleteLater()
        self.raster_view = RasterBeamSelector(beam_positions, self.update_views)
        self.main_layout.addWidget(self.raster_view)
        print(f"Loaded raster view for file: {filename}")

    def update_views(self, x, y):
        print(f"Updating views for beam position ({x}, {y})")
        
        ppi_data = np.random.rand(100, 100)  
        rhi_data = np.random.rand(100, 100) 
        
        self.ppi_canvas.plot_data(ppi_data, title=f"PPI View - Position ({x},{y})")
        self.rhi_canvas.plot_data(rhi_data, title=f"RHI View - Position ({x},{y})")

if __name__ == '__main__':
    folder_path = '/Users/ravisribhashyam/downloads/20240506'
    radar_data = load_all_radar_data(folder_path)
    
    app = QApplication([])
    main_window = MainWindow(radar_data)
    main_window.show()
    app.exec_()
