from PySide6.QtWidgets import QDockWidget
from PySide6.QtCore import Qt

class DynamicDockWidget(QDockWidget):
    """A dockable widget which removes itself from its parent's list of widgets."""
    def __init__(self, title, parent=None, plot_type='PPI'):
        # We have to be very careful with references here and not pass a parent
        # to the super-class. Otherwise, this object will have a lifetime of 
        # the entire QApplication. We want these "dynamic" objects to get
        # garbage collected after they are closed.
        super().__init__(title, parent)
        # self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.parent = parent
        self.plot_type = plot_type

    def get_plot_type(self):
        return self.plot_type

    def set_plot_type(self, type):
        self.plot_type = type

    def clean_up(self):
        """Disconnect signals and perform cleanup."""
        self.setParent(None)
        self.parent = None
        self.widget().deleteLater() # Ensure child widgets are deleted

    def closeEvent(self, event):
        """Handle close events by removing the dock widget from the parent's list."""
        if self.parent:
            if self.plot_type == 'PPI':
                self.parent.remove_ppi_view(self)
            elif self.plot_type == 'RHI':
                self.parent.remove_rhi_view(self)
        self.clean_up()
        super().closeEvent(event)

    def __del__(self):
        print(f'Dynamic {self.get_plot_type()} view docking widget destroyed.')
        # super().__del__(self)