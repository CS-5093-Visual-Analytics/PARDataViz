from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction, QActionGroup
from radar_volume import RadarVolume

class BaseCanvas(FigureCanvasQTAgg):
    """
    Provides a base canvas to be extended for plotting data in either Cartesian
    or Polar coordinates.
    """

    def __init__(self, parent=None, width=10, height=8, dpi=100, polar=True):
        fig = Figure(figsize=(width, height), dpi=dpi)
        if polar:
            self.axes = fig.add_subplot(111, polar=True)
        else:
            self.axes = fig.add_subplot(111)
        self.axes.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
        super().__init__(fig)

        # Group the product switching actions together to ensure mutual exclusivity
        self.action_group = QActionGroup(self)
        self.reflectivity_mode_action = QAction("Reflectivity", self, checkable=True)
        self.velocity_mode_action = QAction("Velocity", self, checkable=True)

        # Triggering each product mode action invokes the same slot with the corresponding product as the parameter
        self.reflectivity_mode_action.triggered.connect(lambda: self.set_product_display('reflectivity'))
        self.velocity_mode_action.triggered.connect(lambda: self.set_product_display('velocity'))

        self.action_group.addAction(self.reflectivity_mode_action)
        self.action_group.addAction(self.velocity_mode_action)
    
        # Show reflectivity by default
        self.reflectivity_mode_action.setChecked(True)
        self.set_product_display('reflectivity')

    def get_view_name(self):
        return "Base Canvas"

    def contextMenuEvent(self, event):
        context_menu = QMenu(self)

        # Sections (e.g. context_menu.addSection()) may be ignored depending on the
        # platform look and feel, so just add a disabled "action" and separator
        # to act as a label for a group of actions in the context menu.
        select_product_fake_action = QAction("Select Product", self)
        select_product_fake_action.setEnabled(False)
        context_menu.addAction(select_product_fake_action)
        context_menu.addSeparator()

        context_menu.addAction(self.reflectivity_mode_action)
        context_menu.addAction(self.velocity_mode_action)

        context_menu.exec(event.globalPos())
    
    def set_product_display(self, product):
        self.current_data_type = product
        self.update_view()

    def get_product_display(self):
        return self.current_data_type

    def update_view(self, radar_volume: RadarVolume):
        print(f"{self.get_view_name()} view product changed: {self.current_data_type}")
