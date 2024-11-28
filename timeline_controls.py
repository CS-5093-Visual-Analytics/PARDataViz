from PySide6.QtWidgets import QApplication, QWidget, QSlider, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, QSize, Slot
from PySide6.QtGui import QIcon

class TimelineControls(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.timeline_button_layout = QHBoxLayout()
        
        # Add a vertical spacer to push content to the bottom
        self.main_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Timeline controls
        self.back_button = QPushButton()
        self.back_button.setIcon(QIcon.fromTheme("media-skip-backward"))
        # self.back_button.clicked.connect(self.back)
        self.timeline_button_layout.addWidget(self.back_button)

        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon.fromTheme("media-playback-start"))
        # self.play_button.clicked.connect(self.toggle_play_pause)
        self.timeline_button_layout.addWidget(self.play_button)

        self.forward_button = QPushButton()
        self.forward_button.setIcon(QIcon.fromTheme("media-skip-forward"))
        # self.forward_button.clicked.connect(self.forward)
        self.timeline_button_layout.addWidget(self.forward_button)

        self.timeline_button_layout.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        # Timeline slider
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setRange(0, 100)  # Initial range for testing
        self.timeline_slider.setSingleStep(1)
        self.timeline_slider.setPageStep(1)
        self.timeline_slider.valueChanged.connect(self.scrub_through_data)
        self.timeline_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.timeline_slider.setTickInterval(1)
        self.timeline_slider.setTracking(False) # Don't emit an updated value until the user stops dragging the slider.
        # self.timeline_slider.setEnabled(False)  # Disabled until data is loaded
        self.timeline_slider.valueChanged.connect(self.slider_updated)

        # Add the slider to the timeline layout
        self.timeline_button_layout.addWidget(self.timeline_slider)
        self.main_layout.addLayout(self.timeline_button_layout)

        self.timeline_label = QLabel("Selected Time:")
        self.main_layout.addWidget(self.timeline_label)
    
    def slider_updated(self, int):
        print(f"Slider value {int}")
    
    @Slot(int)
    def on_scan_times_changed(self, num_times: int):
        self.timeline_slider.setValue(0)
        self.scan_times = num_times
        self.timeline_slider.setRange(0, num_times - 1)

    def scrub_through_data(self, value):
        if not self.scan_times:
            return

        # Update current scan index and trigger data update
        self.current_scan_index = value
        self.update_scan_from_index()

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

def main():
    """Test the TimelineControls widget."""
    import sys
    app = QApplication(sys.argv)

    timeline_controls = TimelineControls()    
    timeline_controls.setWindowTitle("TimelineControls Test")
    timeline_controls.resize(800, 100)
    timeline_controls.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()