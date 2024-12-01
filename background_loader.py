from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtWidgets import QApplication, QWidget
from radar_volume import RadarVolume
import threading

class VolumeLoaderTask(QRunnable):
    """
    QRunnable task for concurrent loading of volume data files.
    """
    def __init__(self, filename, callback):
        super().__init__()
        self.filename = filename
        self.callback = callback

    def run(self):
        # Load the volume and invoke the callback
        r_volume = RadarVolume.build_radar_volume_from_matlab_file(self.filename)
        self.callback(r_volume)

class BackgroundLoader(QObject):
    """
    Background loader class. Can be used to submit volume file loading tasks to
    a thread pool. The thread pool saves on the cost of starting and stopping
    QThreads all the time.
    """
    # Signal emitted when a volume is loaded
    volume_loaded = Signal(RadarVolume)

    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool.globalInstance()

    def load_volume(self, filename):
        # Create a new VolumeLoaderTask for the file
        task = VolumeLoaderTask(filename, self._on_volume_loaded)
        self.thread_pool.start(task)
    
    @Slot(RadarVolume)
    def _on_volume_loaded(self, r_volume: RadarVolume):
        self.volume_loaded.emit(r_volume)


# Test code:
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle("Test Background Loader")

    def on_volume_loaded(volume):
        if volume is not None:
            print(f"Volume loaded: {volume.filename} {volume.products['Z'].shape}")
        else:
            print("Failed to load volume.")

    # Create the background loader
    loader = BackgroundLoader()
    loader.volume_loaded.connect(on_volume_loaded)

    file_name = 'D:/cs5093/20240428/Scan 12/MATLAB/HRUS_240428_020051000_100.mat'
    # Queue up some loading tasks
    loader.load_volume(file_name)
    loader.load_volume(file_name)
    loader.load_volume(file_name)
    loader.load_volume(file_name)
    loader.load_volume("file5.dat")

    # Start the application event loop
    window.show()
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        pass