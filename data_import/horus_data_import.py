import scipy.io
import os

# Class definition to hold radar volume data
class RadarVolume:
    def __init__(self, radar, lat, lon, elev_m, height_m, lambda_m, prf_hz, nyq_m_per_s,
                 datestr, time, vcp, el_deg, az_deg, aze_deg, bw_deg, sweep_el_deg,
                 sweep_az_deg, prod, radar_type, start_range_km):
        self.radar = radar
        self.lat = lat
        self.lon = lon
        self.elev_m = elev_m
        self.height_m = height_m
        self.lambda_m = lambda_m
        self.prf_hz = prf_hz
        self.nyq_m_per_s = nyq_m_per_s
        self.datestr = datestr
        self.time = time
        self.vcp = vcp
        self.el_deg = el_deg
        self.az_deg = az_deg
        self.aze_deg = aze_deg
        self.bw_deg = bw_deg
        self.sweep_el_deg = sweep_el_deg
        self.sweep_az_deg = sweep_az_deg
        self.prod = prod
        self.radar_type = radar_type
        self.start_range_km = start_range_km

    def __repr__(self):
        return f"RadarVolume({self.datestr}, {self.prod})"

# Function to load radar volume data from a MATLAB file and convert it into Python objects
def create_radar_volumes_from_mat(volume_data):
    volumes = []
    num_elements = volume_data.shape[1]  # Get the number of elements in the volume

    for i in range(num_elements):
        vol = volume_data[0, i]

        radar = vol['radar'][0]
        lat = vol['lat'][0]
        lon = vol['lon'][0]
        elev_m = vol['elev_m'][0]
        height_m = vol['height_m'][0]
        lambda_m = vol['lambda_m'][0]
        prf_hz = vol['prf_hz'][0]
        nyq_m_per_s = vol['nyq_m_per_s'][0]
        datestr = vol['datestr'][0]
        time = vol['time'][0]
        vcp = vol['vcp'][0]
        el_deg = vol['el_deg'][0]
        az_deg = vol['az_deg'][0]
        aze_deg = vol['aze_deg'][0]
        bw_deg = vol['bw_deg'][0]
        sweep_el_deg = vol['sweep_el_deg'][0]
        sweep_az_deg = vol['sweep_az_deg'][0]
        prod = vol['prod'][0]
        radar_type = vol['type'][0]
        start_range_km = vol['start_range_km'][0]

        # Create a RadarVolume instance and add it to the list
        radar_volume = RadarVolume(radar, lat, lon, elev_m, height_m, lambda_m, prf_hz, nyq_m_per_s,
                                   datestr, time, vcp, el_deg, az_deg, aze_deg, bw_deg, sweep_el_deg,
                                   sweep_az_deg, prod, radar_type, start_range_km)
        volumes.append(radar_volume)

    return volumes

# Define the parent folder that contains all the scan folders
parent_folder_path = r'C:\Users\till0017\Desktop\20240506'

# List all scan folders (scan_10, scan_11, scan_12, scan_13, etc.)
scan_folders = [f for f in os.listdir(parent_folder_path) if os.path.isdir(os.path.join(parent_folder_path, f)) and f.startswith('scan_')]

# Loop through each scan folder and process the MATLAB files inside it
for scan_folder in scan_folders:
    
    # Define the path to the MATLAB folder inside each scan folder
    matlab_folder_path = os.path.join(parent_folder_path, scan_folder, 'MATLAB')

    # Check if the MATLAB folder exists, if not, skip to the next scan folder
    if not os.path.exists(matlab_folder_path):
        print(f"\nSkipping {scan_folder}: No MATLAB folder found.")
        continue

    # List all .mat files in the MATLAB folder
    mat_files = [f for f in os.listdir(matlab_folder_path) if f.endswith('.mat')]

    # If no .mat files are found, skip the folder
    if not mat_files:
        print(f"\nNo .mat files found in {scan_folder}. Skipping.")
        continue

    # Loop through each .mat file and process it
    for mat_file in mat_files:
        
        full_path = os.path.join(matlab_folder_path, mat_file)
        
        # Load the .mat file
        try:
            mat_data = scipy.io.loadmat(full_path)
        except Exception as e:
            print(f"Error loading {mat_file} in {scan_folder}: {e}")
            continue

        # Extract the 'volume' structure from the .mat data
        try:
            volume_data = mat_data['volume']
        except KeyError:
            print(f"'volume' key not found in {mat_file}. Skipping.")
            continue

        # Convert the volume data into a list of RadarVolume objects
        radar_volumes = create_radar_volumes_from_mat(volume_data)

        # Display the extracted radar volumes
        print(f"\nProcessing {mat_file} in {scan_folder}:")
        for vol in radar_volumes:
            print(vol)

        # Example of accessing specific data from the first radar volume
        if radar_volumes:
            first_volume = radar_volumes[0]
            print(f"\nFirst volume from {mat_file} in {scan_folder}:")
            print(f"Radar: {first_volume.radar}")
            print(f"Latitude: {first_volume.lat}")
            print(f"Longitude: {first_volume.lon}")
            print(f"Reflectivity product: {first_volume.prod}")


