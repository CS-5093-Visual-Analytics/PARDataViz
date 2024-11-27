from PySide6.QtCore import QObject, Signal, Slot

class Data_Manager(QObject):
    """
    
    """
    def __init__(self):
        pass
    
    selectedScanChanged = Signal(str)

    @Slot(str)
    def setSelectedScan(self, scan):
        print(f'Setting selected scan to "{scan}"')
