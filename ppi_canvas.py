from base_canvas import BaseCanvas

class PPI_Canvas(BaseCanvas):
    def __init__(self, parent=None, width=10, height=8, dpi=100, polar=True):
        super().__init__(parent, width, height, dpi, polar)

        self.axes.set_theta_zero_location("N")

    def get_view_name(self):
        return "PPI"
