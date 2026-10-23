"""
This code implements a Tiling System to retrieve high-resolution (10m/px) 
Sentinel-1 SAR imagery for the entire Alboran Sea for October 15-17 2026.

Author: Eric Gutiérrez.
October 2026.

AI Disclosure: AI has been used to assist in the generation of the following code.
"""

import requests
import json
import os
import numpy as np
from datetime import datetime

# 1. Authentication
with open("confidential/client_id.txt", "r") as f:
    SH_CLIENT_ID = f.read().strip()
with open("confidential/client_secret.txt", "r") as f:
    SH_CLIENT_SECRET = f.read().strip()

SH_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
SH_CATALOG_URL = "https://sh.dataspace.copernicus.eu/catalog/v1/search"
SH_PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

def get_token():
    payload = {"grant_type": "client_credentials", "client_id": SH_CLIENT_ID, "client_secret": SH_CLIENT_SECRET}
    response = requests.post(SH_TOKEN_URL, data=payload)
    response.raise_for_status()
    return response.json().get("access_token")

token = get_token()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 2. Define the Macro-Region (The Alboran Sea)
MACRO_MIN_LON, MACRO_MAX_LON = -5.35, -1.20
MACRO_MIN_LAT, MACRO_MAX_LAT = 35.60, 36.75
TILE_STEP = 0.25 # Degrees (~27km)

start_date = "2026-10-01T00:00:00Z"
end_date = "2026-10-17T23:59:59Z"

os.makedirs("data/sentinel1/alboran_tiles", exist_ok=True)

# 3. The Evalscript (with dataMask to handle swath edges)
evalscript = """
//VERSION=3
function setup() {
  return {
    input: ["VV", "VH", "dataMask"],
    output: { id: "default", bands: 2, sampleType: "FLOAT32" }
  };
}
function evaluatePixel(sample) {
  if (sample.dataMask === 0) {
    return [0.0, 0.0];
  }
  return [sample.VV, sample.VH];
}
"""

# 4. Generate the Grid
lons = np.arange(MACRO_MIN_LON, MACRO_MAX_LON, TILE_STEP)
lats = np.arange(MACRO_MIN_LAT, MACRO_MAX_LAT, TILE_STEP)

total_tiles = len(lons) * len(lats)
print(f"Generated a grid of {total_tiles} tiles across the Alboran Sea.")

# 5. Iterate through the grid
tile_counter = 0
for col, lon in enumerate(lons):
    for row, lat in enumerate(lats):
        tile_counter += 1
        
        # Calculate bounding box for this specific tile
        tile_bbox = [
            round(lon, 4), 
            round(lat, 4), 
            round(lon + TILE_STEP, 4), 
            round(lat + TILE_STEP, 4)
        ]
        
        print(f"\n--- Processing Tile {tile_counter}/{total_tiles} (Col {col}, Row {row}) ---")
        
        # Check Catalog API for this specific tile
        catalog_payload = {
            "bbox": tile_bbox,
            "datetime": f"{start_date}/{end_date}",
            "collections": ["sentinel-1-grd"],
            "limit": 50,
        }
        
        catalog_response = requests.post(SH_CATALOG_URL, headers=headers, json=catalog_payload)
        features = catalog_response.json().get("features", [])
        
        # Extract unique dates this specific tile was photographed
        valid_dates = sorted(list(set([
            datetime.strptime(f["properties"]["datetime"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
            for f in features
        ])))
        
        if not valid_dates:
            print("No satellite passes covered this tile recently. Skipping.")
            continue
            
        # LIVE SNAPSHOT LOGIC: Only take the absolute most recent pass
        latest_date = valid_dates[-1]
        print(f"Latest pass for this tile is {latest_date}. Downloading snapshot...")
        
        filepath = f"data/sentinel1/alboran_tiles/tile_c{col}_r{row}_{latest_date}.tiff"
        
        if os.path.exists(filepath):
            print(f"Already exists: {filepath}")
            continue
                
        process_payload = {
            "input": {
                "bounds": {
                    "bbox": tile_bbox,
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
                },
                "data": [{
                    "type": "sentinel-1-grd",
                    "dataFilter": {
                        "timeRange": {"from": f"{latest_date}T00:00:00Z", "to": f"{latest_date}T23:59:59Z"},
                        "acquisitionMode": "IW",
                        "polarization": "DV"
                    },
                    "processing": {"backCoeff": "GAMMA0_TERRAIN", "orthorectify": True}
                    }]
                },
            "output": {
                    "width": 2500,
                    "height": 2500,
                    "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}]
                },
                "evalscript": evalscript
        }
            
        resp = requests.post(SH_PROCESS_URL, headers=headers, json=process_payload)
        if resp.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(resp.content)
            print(f"Saved: {filepath}")
        else:
            print(f"API Error for {latest_date}: {resp.status_code}")