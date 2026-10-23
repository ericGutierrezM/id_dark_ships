"""
SAR & AIS Data Fusion
Cross-references physical SAR targets with broadcasted AIS pings 
to identify "Dark Vessels" (unmatched physical targets).

Author: Eric Gutiérrez.
October 2026.

AI Disclosure: AI has been used to assist in the generation of the following code.
"""

import pandas as pd
import numpy as np
import math

# 1. Configuration
SAR_TARGETS_CSV = "output/alboran_filtered_targets.csv" # Adjust path if yours is different
AIS_PINGS_CSV = "data/ais/alboran_gfw_ais.csv"
OUTPUT_DARK_SHIPS = "output/dark_vessels_final.csv"
OUTPUT_MATCHED_SHIPS = "output/matched_vessels.csv"

# Max distance to consider an AIS ping a "match" for a SAR target (in kilometers)
# 2km is standard for OSINT due to vessel speed between the top-of-hour AIS ping and the exact satellite minute.
MATCH_RADIUS_KM = 2.0 

def haversine(lat1, lon1, lat2, lon2):
    """Calculates the distance in km between two GPS points."""
    R = 6371.0 # Earth radius in km
    
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

print("Loading datasets...")
df_sar = pd.read_csv(SAR_TARGETS_CSV)
df_ais = pd.read_csv(AIS_PINGS_CSV)

print(f"Loaded {len(df_sar)} SAR targets and {len(df_ais)} AIS pings.")

dark_vessels = []
matched_vessels = []

print(f"Running spatial fusion (Match Radius: {MATCH_RADIUS_KM}km)...")

for index, sar in df_sar.iterrows():
    sar_lat = sar['latitude']
    sar_lon = sar['longitude']
    
    # Calculate distance to ALL 9,000 AIS pings
    # (Vectorized numpy calculation for blazing fast speed)
    lats = np.radians(df_ais['latitude'].values)
    lons = np.radians(df_ais['longitude'].values)
    sar_lat_rad = math.radians(sar_lat)
    sar_lon_rad = math.radians(sar_lon)
    
    dlons = lons - sar_lon_rad
    dlats = lats - sar_lat_rad
    
    a = np.sin(dlats/2)**2 + np.cos(sar_lat_rad) * np.cos(lats) * np.sin(dlons/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    distances = 6371.0 * c # Earth radius in km
    
    min_distance = np.min(distances)
    
    if min_distance <= MATCH_RADIUS_KM:
        # We found a match! Get the closest AIS vessel
        closest_ais_idx = np.argmin(distances)
        matched_vessel = df_ais.iloc[closest_ais_idx]
        
        sar_dict = sar.to_dict()
        sar_dict['ais_match_mmsi'] = matched_vessel['MMSI']
        sar_dict['ais_match_name'] = matched_vessel['vessel_name']
        sar_dict['match_distance_km'] = round(min_distance, 3)
        matched_vessels.append(sar_dict)
    else:
        # No AIS ping within 2km. THIS IS A DARK VESSEL.
        sar_dict = sar.to_dict()
        sar_dict['closest_ais_distance_km'] = round(min_distance, 3)
        dark_vessels.append(sar_dict)

# 3. Save the results
df_dark = pd.DataFrame(dark_vessels)
df_matched = pd.DataFrame(matched_vessels)

if not df_dark.empty:
    df_dark.to_csv(OUTPUT_DARK_SHIPS, index=False)
if not df_matched.empty:
    df_matched.to_csv(OUTPUT_MATCHED_SHIPS, index=False)

print("\n--- FUSION COMPLETE ---")
print(f"Physical SAR Targets: {len(df_sar)}")
print(f"Legitimate (Matched) Vessels: {len(df_matched)}")
print(f"DARK VESSELS DETECTED: {len(df_dark)}")
print(f"Results saved to {OUTPUT_DARK_SHIPS}")