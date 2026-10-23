"""
Batch Inference & Georeferencing Script (Alboran Sea Grid)
Runs YOLOv8 SAR ship detection on a folder of tiled Sentinel-1 TIFFs
and converts pixel bounding boxes to real-world GPS coordinates.

Author: Eric Gutiérrez.
October 2026.

AI Disclosure: AI has been used to assist in the generation of the following code.
"""

import os
import re
import rasterio
from rasterio.warp import transform
import numpy as np
from ultralytics import YOLO
import pandas as pd

# 1. Configuration
MODEL_PATH = "output/yolo/shadow_fleet/sar_yolov8s_ssdd-10/weights/best.pt"
TILES_DIR = "data/sentinel1/alboran_tiles"
OUTPUT_CSV = "output/alboran_physical_targets_oct2026.csv"

# 2. Load Model
print(f"Loading YOLO model from {MODEL_PATH}...")
model = YOLO(MODEL_PATH)

# 3. SAR Normalization Function
def normalize_sar(band, vmin=-25, vmax=0):
    """Converts linear power to dB, safely handles NaNs, and normalizes to uint8."""
    # Convert NaNs to a tiny positive float to avoid log10 math domain errors
    band_clean = np.nan_to_num(band, nan=1e-10)
    # Clip zero/negative values before logarithm
    band_db = 10.0 * np.log10(np.clip(band_clean, 1e-10, None))
    clipped = np.clip(band_db, vmin, vmax)
    # Scale to 0-255
    norm = ((clipped - vmin) / (vmax - vmin)) * 255.0
    return norm.astype(np.uint8)

# 4. Process the Grid
detections = []
tile_files = [f for f in os.listdir(TILES_DIR) if f.endswith(".tiff")]

print(f"Starting batch inference on {len(tile_files)} tiles...")

for filename in tile_files:
    filepath = os.path.join(TILES_DIR, filename)
    
    # Extract date from filename (e.g., tile_c3_r5_2026-10-15.tiff)
    match = re.search(r"tile_c(\d+)_r(\d+)_(\d{4}-\d{2}-\d{2})", filename)
    if not match:
        continue
    
    col, row, date = int(match.group(1)), int(match.group(2)), match.group(3)
    
    # Read the TIFF and Extract GeoTransform
    with rasterio.open(filepath) as src:
        vv = src.read(1)
        # Skip completely empty tiles (if the satellite swath missed this grid square entirely)
        if np.max(vv) == 0:
            continue
            
        affine_transform = src.transform
        src_crs = src.crs

    # Construct Pseudo-RGB (Grayscale stack for YOLO)
    vv_u8 = normalize_sar(vv, vmin=-20, vmax=0)
    sar_rgb = np.dstack((vv_u8, vv_u8, vv_u8))
    
    # Run YOLOv8 Inference
    # verbose=False keeps the terminal clean during the batch loop
    results = model.predict(source=sar_rgb, imgsz=1024, conf=0.35, device="mps", verbose=False)
    
    # Georeference Detections
    boxes = results[0].boxes
    for box in boxes:
        # Bounding box in pixels
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
        conf = float(box.conf[0])
        
        # Calculate center point in pixel space
        center_x = (x1 + x2) / 2.0
        center_y = (y1 + y2) / 2.0
        
        # Convert pixel coordinates to dataset projected coordinates
        proj_x, proj_y = rasterio.transform.xy(affine_transform, center_y, center_x)
        
        # Reproject projected coordinates to WGS84 GPS (Lat, Lon)
        lon, lat = transform(src_crs, "EPSG:4326", [proj_x], [proj_y])
        
        detections.append({
            "date": date,
            "tile": f"c{col}_r{row}",
            "confidence": round(conf, 3),
            "pixel_bbox": [round(float(v), 1) for v in [x1, y1, x2, y2]],
            "longitude": round(lon[0], 6),
            "latitude": round(lat[0], 6)
        })
        
    print(f"Processed {filename} -> Found {len(boxes)} targets")

# 5. Export Master CSV
df = pd.DataFrame(detections)
os.makedirs("output", exist_ok=True)
df.to_csv(OUTPUT_CSV, index=False)

print(f"\nBatch processing complete!")
print(f"Total physical targets detected across the Alboran Sea: {len(df)}")
print(f"Results saved to {OUTPUT_CSV}")