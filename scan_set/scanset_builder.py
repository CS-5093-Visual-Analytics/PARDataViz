import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QDialog, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QListWidget, QListWidgetItem, QFrame, QStatusBar
from PySide6.QtGui import QValidator
from scan_set import ScanSet
from scan import Scan

class ScansetDirValidator(QValidator):
    def __init__(self):
        super().__init__()

    def validate(arg1, arg2):
        return Invalid

class ScansetBuilder(QDialog):
    """
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scanset Builder")
        self.setSizeGripEnabled(True)
        
        self.last_selected_base_dir = os.path.expanduser("~")

        self.scanset = ScanSet("Scanset", Path(self.last_selected_base_dir))

        layout = QVBoxLayout()
        # self.label = QLabel("Scanset Builder")
        # layout.addWidget(self.label)
        
        # Label for scanset name editor field
        self.scanset_name_editor_label = QLabel("Scanset Name:")
        layout.addWidget(self.scanset_name_editor_label)

        # Scanset name editor field
        self.scanset_name_editor = QLineEdit()
        self.scanset_name_editor.setPlaceholderText("Enter a name for the scanset...")
        self.scanset_name_editor.textChanged.connect(self.scanset_editor_text_changed)
        layout.addWidget(self.scanset_name_editor)

        # Label for scanset directory
        self.scanset_dir_label = QLabel("Base directory:")
        layout.addWidget(self.scanset_dir_label)

        # Scanset dir editor field
        self.scanset_dir_editor = QLineEdit()
        self.scanset_dir_editor.setPlaceholderText("Base directory for the scanset...")
        self.scanset_dir_editor
        layout.addWidget(self.scanset_dir_editor)

        self.scanset_dir_browse_button = QPushButton("Browse...")
        self.scanset_dir_browse_button.clicked.connect(self.scanset_editor_base_dir_browse_clicked)
        layout.addWidget(self.scanset_dir_browse_button)

        # List of scans in this scanset
        self.scanset_scanslist_label = QLabel("Scans:")
        layout.addWidget(self.scanset_scanslist_label)

        self.scanset_scanslist = QListWidget()
        self.scanset_scanslist.itemClicked.connect(self.scanset_scanslist_item_clicked)
        self.scanset_scanslist.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        layout.addWidget(self.scanset_scanslist)

        # Add scan button
        self.add_scan_button = QPushButton("Add Scan")
        self.add_scan_button.clicked.connect(self.scanset_editor_add_scan_clicked)
        layout.addWidget(self.add_scan_button)

        # Remove scan button
        self.remove_scan_button = QPushButton("Remove Scan")
        self.remove_scan_button.clicked.connect(self.scanset_editor_remove_scan_clicked)
        layout.addWidget(self.remove_scan_button)

        self.scan_hrule = QFrame()
        self.scan_hrule.setFrameShape(QFrame.Shape.HLine)
        self.scan_hrule.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(self.scan_hrule)

        self.selected_scan_label = QLabel("Selected Scan")
        self.selected_scan_label.setEnabled(False)
        layout.addWidget(self.selected_scan_label)

        self.selected_scan_name_editor = QLineEdit()
        self.selected_scan_name_editor.setEnabled(False)
        self.selected_scan_name_editor.textChanged.connect(self.selected_scan_name_editor_text_changed)
        layout.addWidget(self.selected_scan_name_editor)

        self.selected_scan_files_list = QListWidget()
        self.selected_scan_files_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.selected_scan_files_list.setEnabled(False)
        layout.addWidget(self.selected_scan_files_list)

        self.selected_scan_add_files_button = QPushButton("Add scan files...")
        self.selected_scan_add_files_button.setEnabled(False)
        self.selected_scan_add_files_button.clicked.connect(self.scanset_editor_add_scan_files_clicked)
        layout.addWidget(self.selected_scan_add_files_button)

        self.selected_scan_remove_files_button = QPushButton("Remove selected scan files")
        self.selected_scan_remove_files_button.setEnabled(False)
        self.selected_scan_remove_files_button.clicked.connect(self.scanset_editor_remove_scan_files_clicked)
        layout.addWidget(self.selected_scan_remove_files_button)

        self.setLayout(layout)
        
    def scanset_editor_text_changed(self, text):
        # Programmatic change of the text
        # print(f'{text}')
        self.scanset.set_name(text)

    def scanset_editor_base_dir_browse_clicked(self):
        dir = QFileDialog.getExistingDirectory(self, "Select Scanset Base Folder...", self.last_selected_base_dir)
        if dir:
            self.last_selected_base_dir = dir
            self.scanset_dir_editor.setText(dir)

    def scanset_scanslist_item_clicked(self, item):
        # Filter for the selected scan
        self.selected_scan = next(scan for scan in self.scanset.get_scans() if scan.get_name() == item.text())
        
        # Enable the label for the selected scan editor area
        self.selected_scan_label.setEnabled(True)

        # Enable the line editor for the selected scan name
        self.selected_scan_name_editor.setEnabled(True)
        self.selected_scan_name_editor.setText(self.selected_scan.get_name())
        
        # Enable and populate the selected scan's files list
        self.selected_scan_files_list.setEnabled(True)
        self.selected_scan_files_list.clear()
        for scan_file in self.selected_scan.get_scan_files():
            self.selected_scan_files_list.addItem(f'{scan_file}')
        
        # Enable the add and remove scan files buttons
        self.selected_scan_add_files_button.setEnabled(True)
        self.selected_scan_remove_files_button.setEnabled(True)

    def scanset_editor_add_scan_clicked(self):
        num_scans = len(self.scanset.get_scans())
        new_scan_name = f'Scan {num_scans + 1}'
        item = QListWidgetItem(new_scan_name, self.scanset_scanslist)
        self.scanset_scanslist.addItem(item)
        
        # TODO change relpath from base dir
        self.scanset.get_scans().append(Scan(new_scan_name, self.last_selected_base_dir))
        self.scanset.get_scans().append(Scan(new_scan_name))

    def scanset_editor_remove_scan_clicked(self):
        if len(self.scanset_scanslist.selectedItems()) > 0:
            selected_scan = self.scanset_scanslist.selectedItems()[0]

            scanset_scan = next(scan for scan in self.scanset.get_scans() if scan.get_name() == selected_scan.text())
            self.scanset.get_scans().remove(scanset_scan)
            self.scanset_scanslist.takeItem(self.scanset_scanslist.row(selected_scan))

        # The currently selected scan has been removed from the scan list, reset the scan files editor
        self.reset_selected_scan_file_list()

    def scanset_editor_add_scan_files_clicked(self):
        (filenames, selected_filter) = QFileDialog.getOpenFileNames(self, "Select Scan Files...", self.last_selected_base_dir, filter="MATLAB files (*.mat)")
        for filename in filenames:
            self.selected_scan.get_scan_files().append(Path(filename))
            self.selected_scan_files_list.addItem(filename)

    def scanset_editor_remove_scan_files_clicked(self):
        removals = []
        for item in self.selected_scan_files_list.selectedItems():
            print(item.text())
            removals.append((next(file for file in self.selected_scan.get_scan_files() if file == Path(item.text())), item))
        
        for file, item in removals:
            self.selected_scan.get_scan_files().remove(file)
            self.selected_scan_files_list.takeItem(self.selected_scan_files_list.row(item))
    
    def reset_selected_scan_file_list(self):
        self.selected_scan_label.setEnabled(False)
        self.selected_scan_name_editor.setEnabled(False)
        self.selected_scan_files_list.setEnabled(False)
        self.selected_scan_add_files_button.setEnabled(False)
        self.selected_scan_remove_files_button.setEnabled(False)

    def selected_scan_name_editor_text_changed(self, text):
        self.selected_scan.set_name(text)
        self.scanset_scanslist.selectedItems()[0].setText(text)

class StandaloneScansetBuilder(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Standalone Scanset Builder")
        # self.setGeometry(0, 0, 600, 300)
        self.button = QPushButton("Create Scanset Builder")
        self.button.clicked.connect(self.show_scanset_builder)
        self.setCentralWidget(self.button)

    def show_scanset_builder(self, checked):
        self.scanset_builder = ScansetBuilder()
        self.scanset_builder.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StandaloneScansetBuilder()
    window.show()
    sys.exit(app.exec())