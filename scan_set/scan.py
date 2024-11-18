from pathlib import Path

class Scan(object):
    # def __init__(self, scan_name: str, rel_dir: Path) -> None:
    def __init__(self, scan_name: str) -> None:
        self.name = scan_name
        # self.rel_dir = rel_dir
        self.scan_files = []
    
    def get_name(self) -> str:
        return self.name
    
    def set_name(self, name: str) -> None:
        self.name = name
    
    # def get_rel_dir(self) -> Path:
    #     return self.rel_dir

    def get_scan_files(self) -> list[Path]:
        return self.scan_files