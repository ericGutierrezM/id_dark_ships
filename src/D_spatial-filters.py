"""
Spatial Filtering Script
Strips coastal radar artifacts and permanent marine infrastructure 
from raw YOLOv8 SAR detections.

Author: Eric Gutiérrez.
October 2026.

AI Disclosure: AI has been used to assist in the generation of the following code.
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import osmnx as ox
import warnings

# Suppress OSMNx warnings for cleaner terminal output
warnings.filterwarnings("ignore")

# 1. Load the Raw Detections
INPUT_CSV = "output/alboran_physical_targets_oct2026.csv"
OUTPUT_CSV = "output/alboran_filtered_targets.csv"

print("Loading raw YOLO detections...")
df = pd.read_csv(INPUT_CSV)

# Convert coordinates into a GeoDataFrame 
# EPSG:4326 is standard GPS Lat/Lon
gdf_targets = gpd.GeoDataFrame(
    df, 
    geometry=gpd.points_from_xy(df.longitude, df.latitude), 
    crs="EPSG:4326"
)

# Reproject to EPSG:3857 (Web Mercator) so we can measure distance in real meters
gdf_targets = gdf_targets.to_crs("EPSG:3857")


# 2. Apply The Coastal Buffer (Filter 1)
print("Applying 100m Coastal Buffer...")
# Load the 10m Natural Earth Land Shapefile
land_path = "data/shapefiles/ne_10m_land/ne_10m_land.shp" 
land_gdf = gpd.read_file(land_path).to_crs("EPSG:3857")

# Merge all global landmasses into one giant polygon, then expand it 100 meters into the ocean
buffered_land = land_gdf.geometry.buffer(100).unary_union

# Keep only the targets that DO NOT intersect the buffered land
starting_count = len(gdf_targets)
gdf_targets = gdf_targets[~gdf_targets.geometry.intersects(buffered_land)]
print(f"Removed {starting_count - len(gdf_targets)} coastal radar artifacts.")


# 3. Apply The Infrastructure Mask (Filter 2)
print("Querying OpenStreetMap for permanent marine infrastructure...")

# Configure OSMnx to use multiple endpoint mirrors to prevent 502 Timeouts
ox.settings.overpass_endpoint = [
    "https://overpass-api.de/api",
    "https://overpass.kumi.systems/api",
    "https://maps.mail.ru/osm/tools/overpass/api"
]
# Increase the timeout allowance
ox.settings.timeout = 180 

north, south, east, west = 36.75, 35.60, -1.20, -5.35

infra_tags = {
    "man_made": "offshore_platform",
    "seamark:type": True,
    "landuse": "aquaculture"
}

try:
    # Attempt to pull the infrastructure data
    infra_gdf = ox.features_from_bbox(bbox=(north, south, east, west), tags=infra_tags)
    
    if not infra_gdf.empty:
        infra_gdf = infra_gdf.to_crs("EPSG:3857")
        print(f"Found {len(infra_gdf)} infrastructure objects in the Alboran Sea.")

        # Draw a 200-meter radius around every piece of infrastructure
        buffered_infra = infra_gdf.geometry.buffer(200).unary_union

        # Filter out targets
        pre_infra_count = len(gdf_targets)
        gdf_targets = gdf_targets[~gdf_targets.geometry.intersects(buffered_infra)]
        print(f"Removed {pre_infra_count - len(gdf_targets)} infrastructure false-positives.")
    else:
        print("No infrastructure found in this bounding box.")

except Exception as e:
    print(f"\nWarning: OSM Overpass query failed. Error: {e}")
    print("Proceeding without the infrastructure mask. You may have a few buoy false-positives.")

# 4. Export the Cleaned Dataset
print("\nExporting cleaned anomalies...")
# Project back to standard GPS coordinates
gdf_targets = gdf_targets.to_crs("EPSG:4326")

# Drop the geometry column to save as a clean CSV
final_df = gdf_targets.drop(columns=['geometry'])
final_df.to_csv(OUTPUT_CSV, index=False)

print(f"Filtering complete! You have {len(final_df)} highly verified targets remaining.")
print(f"Saved to {OUTPUT_CSV}")