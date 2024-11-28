from PySide6.QtCore import QObject, Signal, Slot
from scan_set import ScanSet
from scan import Scan

class Data_Manager(QObject):
    """
    
    """
    scan_selected = Signal(str)

    def __init__(self):
        pass
    
    @Slot(ScanSet)
    def on_scanset_load(self, scanset: ScanSet):
        print(f'Data manager now working with scanset "{scanset.get_name()}".')

    @Slot(str)
    def on_scan_selected(self, scan):
        print(f'Setting selected scan to "{scan}"')
