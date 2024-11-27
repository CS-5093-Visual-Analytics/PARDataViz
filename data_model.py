import argparse
from pathlib import Path

class DataModel(object):
    def __init__(self, scans_dir: Path) -> None:
        self.scans_dir = scans_dir
        self.scan_files = []
        self.selected_scan = None
        self.selected_vol = None

    def do(self):
        print(f'{self.scans_dir}')
        folders = set()
        for matfile in self.scans_dir.glob('**/*.mat'):
            folders.add(matfile.parent)

        for unique_folder in folders:
            print(f'{unique_folder}')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dir', type=Path, help='The directory containing scan directories.')
    args = parser.parse_args()

    model = DataModel(args.dir)
    model.do()
    print('Hello, data loader.')

if __name__ == '__main__':
    main()
