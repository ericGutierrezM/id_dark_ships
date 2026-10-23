"""
Train a YOLO model (using YOLOv8 as base model) with SAR
ship data.

Author: Eric Gutiérrez.
October 2026.

AI Disclosure: AI has been used to assist in the generation of the following code.
"""

from ultralytics import YOLO

# Initialize the base small model
model = YOLO("yolov8s.pt") 

# Provide the absolute path to your downloaded NDJSON file.
# The Ultralytics engine will parse this file, concurrently download the images 
# from the signed URLs, and automatically generate the necessary YAML and folders.
ndjson_path = "data/yolo_train_dataset/ssdd-sar-ship.ndjson"

print("Parsing NDJSON dataset and starting fine-tuning on Apple Silicon...")

results = model.train(
    data=ndjson_path,
    epochs=50,                  
    imgsz=800,                  
    batch=8,                   
    device="mps",               
    patience=10,                
    project="shadow_fleet",     
    name="sar_yolov8s_ssdd"     
)