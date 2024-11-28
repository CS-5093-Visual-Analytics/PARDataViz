import scipy.io as scio

class RadarVolume(object):
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
    
    @staticmethod
    def create_radar_volumes_from_mat(file_path):
        mat_data = scio.loadmat(file_path)
        
        if 'volume' not in mat_data:
            print("No 'volume' key found in the .mat file. Please check the data structure.")
            return None, None, None
        
        volume_data = mat_data['volume']
        
        if volume_data.shape[1] > 0:
            first_volume = volume_data[0, 0]
            
            if 'prod' in first_volume.dtype.names:
                prod_data = first_volume['prod'][0]
                
                reflectivity_data = None
                velocity_data = None
                for entry in prod_data:
                    if entry[0] == 'Z':  # Reflectivity
                        reflectivity_data = entry[3]
                        print("Reflectivity data shape:", reflectivity_data.shape)
                    elif entry[0] == 'V':  # Velocity
                        velocity_data = entry[3]
                        print("Velocity data shape:", velocity_data.shape)
                
                radar_volume = RadarVolume(
                    radar=first_volume['radar'][0] if 'radar' in first_volume.dtype.names else None,
                    lat=first_volume['lat'][0] if 'lat' in first_volume.dtype.names else None,
                    lon=first_volume['lon'][0] if 'lon' in first_volume.dtype.names else None,
                    elev_m=first_volume['elev_m'][0] if 'elev_m' in first_volume.dtype.names else None,
                    height_m=first_volume['height_m'][0] if 'height_m' in first_volume.dtype.names else None,
                    lambda_m=first_volume['lambda_m'][0] if 'lambda_m' in first_volume.dtype.names else None,
                    prf_hz=first_volume['prf_hz'][0] if 'prf_hz' in first_volume.dtype.names else None,
                    nyq_m_per_s=first_volume['nyq_m_per_s'][0] if 'nyq_m_per_s' in first_volume.dtype.names else None,
                    datestr=first_volume['datestr'][0] if 'datestr' in first_volume.dtype.names else None,
                    time=first_volume['time'][0] if 'time' in first_volume.dtype.names else None,
                    vcp=first_volume['vcp'][0] if 'vcp' in first_volume.dtype.names else None,
                    el_deg=first_volume['el_deg'][0] if 'el_deg' in first_volume.dtype.names else None,
                    az_deg=first_volume['az_deg'][0] if 'az_deg' in first_volume.dtype.names else None,
                    aze_deg=first_volume['aze_deg'][0] if 'aze_deg' in first_volume.dtype.names else None,
                    bw_deg=first_volume['bw_deg'][0] if 'bw_deg' in first_volume.dtype.names else None,
                    sweep_el_deg=first_volume['sweep_el_deg'][0] if 'sweep_el_deg' in first_volume.dtype.names else None,
                    sweep_az_deg=first_volume['sweep_az_deg'][0] if 'sweep_az_deg' in first_volume.dtype.names else None,
                    prod=reflectivity_data,
                    radar_type=first_volume['type'][0] if 'type' in first_volume.dtype.names else None,
                    start_range_km=first_volume['start_range_km'][0] if 'start_range_km' in first_volume.dtype.names else None
                )
                return radar_volume, reflectivity_data, velocity_data
        
        print("No data found in volume.")
        return None, None, None