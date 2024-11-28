from PySide6.QtCore import QObject, Signal, Slot
from scan_set import ScanSet
from scan import Scan
from pathlib import Path

class Data_Manager(QObject):
    """
    
    """
    scan_selected = Signal(str)
    scan_times_changed = Signal(int)

    def __init__(self):
        super().__init__()
        self.selected_scan = None
        self.scan_times = []
        self.mat_files = []
        self.current_index = 0

    @Slot(ScanSet)
    def on_scanset_load(self, scanset: ScanSet):
        print(f'Data manager now working with scanset "{scanset.get_name()}".')
        self.scanset = scanset
        if len(self.scanset.get_scans()) > 0:
            self.on_scan_selected(self.scanset.get_scans()[0])

    @Slot(str)
    def on_scan_selected(self, scan: Scan):
        print(f'Setting selected scan to "{scan.get_name()}"')
        self.selected_scan = scan
        self.initialize_data_buffer()
    
    def initialize_data_buffer(self):
        if self.selected_scan is not None:
            self.mat_files.clear()
            self.scan_times.clear()

            # Working from the base directory for the scanset
            base_dir = self.scanset.get_base_dir()
            # Loop over all the files in the current scan
            for filename in self.selected_scan.get_scan_files():
                
                # Extract the time for each scan file
                timestamp = self.extract_timestamp_from_filename(filename)

                if timestamp is not None:
                    mat_file = base_dir / Path(filename)

                    self.scan_times.append((timestamp, mat_file))
                    self.mat_files.append(mat_file)
                    self.current_index = 0
                    
            if len(self.scan_times) > 0:
                self.scan_times_changed.emit(len(self.scan_times))

    def extract_timestamp_from_filename(self, filename):
        try:
            timestamp_str = filename.split('_')[1] + filename.split('_')[2][:6]
            return timestamp_str
        except IndexError:
            return None