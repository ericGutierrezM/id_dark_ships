"""
Global Fishing Watch API Extraction (v3 API)
Pulls historical AIS vessel presence for the Alboran Sea.

Author: Eric Gutiérrez.
October 2026.

AI Disclosure: AI has been used to assist in the generation of the following code.
"""

import requests
import time
import pandas as pd
import json
import zipfile
import io

# 1. Configuration
with open("confidential/confidential/global_fishing_watch_token.txt", "r") as f:
    GFW_API_TOKEN = f.read().strip()

OUTPUT_CSV = "data/ais/alboran_gfw_ais.csv"

# Target Date (must be YYYY-MM-DD format)
TARGET_DATE = "2026-10-03"

HEADERS = {
    "Authorization": f"Bearer {GFW_API_TOKEN}",
    "Content-Type": "application/json"
}

# 2. Define ONLY the Geometry for the Body Payload
geometry_payload = {
    "geojson": {
        "type": "Polygon",
        "coordinates": [[
            [-5.35, 35.60],
            [-1.20, 35.60],
            [-1.20, 36.75],
            [-5.35, 36.75],
            [-5.35, 35.60] 
        ]]
    }
}

print(f"Requesting AIS Presence Report for {TARGET_DATE}...")

base_url = "https://gateway.api.globalfishingwatch.org/v3/4wings/report"
query_string = (
    f"?spatial-resolution=HIGH"
    f"&temporal-resolution=HOURLY"
    f"&datasets[0]=public-global-presence:latest"
    f"&date-range=2026-10-03,2026-10-04"
    f"&format=CSV"
)
submit_url = base_url + query_string

try:
    response = requests.post(submit_url, headers=HEADERS, json=geometry_payload)
    
    if response.status_code == 422:
        print(f"Server rejected the payload:\n{json.dumps(response.json(), indent=2)}")
        exit()
        
    response.raise_for_status()
    
    # 4. Smart Response Handling
    content_type = response.headers.get('Content-Type', '')
    
    # SCENARIO A: The API returned a ZIP archive
    if 'zip' in content_type.lower():
        print("\nSuccess! The API returned a compressed ZIP. Extracting in memory...")
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            # Find the CSV file inside the zip
            csv_filename = [name for name in z.namelist() if name.endswith('.csv')][0]
            print(f"Found {csv_filename} inside archive. Saving to disk...")
            with z.open(csv_filename) as zf, open(OUTPUT_CSV, 'wb') as f:
                f.write(zf.read())
                
    # SCENARIO B: The API returned the CSV directly
    elif 'csv' in content_type.lower() or response.text.startswith('Time'):
        print("\nSuccess! The API returned the CSV directly.")
        with open(OUTPUT_CSV, "wb") as f:
            f.write(response.content)
            
    # SCENARIO C: The API returned a JSON with a Job ID (Needs Polling)
    elif 'json' in content_type.lower():
        report_info = response.json()
        report_id = report_info.get("id")
        print(f"Report Job Queued. ID: {report_id}")
        # (Polling logic omitted here for brevity since it returned a ZIP for you)
        print("Polling currently not implemented for JSON responses. Please run again.")
        exit()
            
    else:
        print(f"Unexpected response format: {content_type}")
        exit()

except requests.exceptions.RequestException as e:
    print(f"API Request Failed: {e}")
    exit()

# 5. Format the Data for our Fusion Script
print("\nFormatting data for Fusion Pipeline...")
df = pd.read_csv(OUTPUT_CSV)

# GFW CSVs usually use these column names
df = df.rename(columns={
    "Time": "timestamp",
    "Lat": "latitude",
    "Lon": "longitude"
})

if 'mmsi' not in df.columns and 'Vessel IDs' in df.columns:
    df['mmsi'] = df['Vessel IDs'] 

if 'vessel_name' not in df.columns:
    df['vessel_name'] = "GFW_VESSEL"

df.to_csv(OUTPUT_CSV, index=False)
print(f"Extraction Complete! Saved {len(df)} AIS pings to {OUTPUT_CSV}")