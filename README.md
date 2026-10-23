# Dark Vessel Detection in the Alboran Sea

A scrollytelling intelligence page visualizing the detection of "dark" maritime vessels (ships intentionally disabling their Automatic Identification System (AIS) transponders) in the Alboran Sea during  two-day window in October 2026. 

**[View the Dashboard Here](https://ericgutierrezm.github.io/id_dark_ships/)**

## System Architecture

This project fuses orbital radar data with open-source telemetry to identify uncooperative physical targets.
* **SAR Acquisition:** Synthetic Aperture Radar (SAR) tiles pulled from the ESA Sentinel-1 satellite via the Copernicus API.
* **Target Extraction (AI):** SAR arrays processed through a custom-trained YOLOv8 neural network to isolate high-intensity metallic hull backscatter against sea-clutter. Image affine transform matrices map pixel detections to absolute GPS coordinates.
* **Kinematic Fusion:** Vectorized Haversine distance tracking cross-references static radar hits against dynamic AIS waypoints from the Global Fishing Watch database. Physical targets lacking an AIS broadcast within a 2.0 km radius are flagged.

## Technology Stack

* **Frontend:** Single-page HTML5/CSS3 application with a strict zero-border-radius, dark-mode aesthetic. 
* **Scrollytelling Engine:** Vanilla JavaScript Intersection Observers and CSS `position: sticky` for seamless slide wiping and hardware-accelerated rendering.
* **Interactive Mapping:** Leaflet.js utilizing the CARTO Dark Matter basemap to visualize verified telemetry versus potential dark targets.
* **Data Preprocessing:** Python, Pandas, and NumPy for spatial-temporal data fusion.

## Author
**Eric Gutiérrez**  
[Portfolio](https://ericgutierrezm.github.io/about_page/) | [LinkedIn](https://www.linkedin.com/in/eric-gutierrez-moreno/)