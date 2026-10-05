# GIS Image Enhancement App

A local Streamlit application for batch enhancing TIFF, JPG/JPEG, and PNG images and exporting three-band RGB TIFFs. Georeferencing and raster metadata are retained for georeferenced TIFF inputs.

## Run

```powershell
cd GIS_Image_Enhancement_App
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

The local Streamlit config disables usage-stat collection so the app does not need to write a user configuration file outside this project.

Open the local URL printed by Streamlit, upload one or more images, tune settings, and select an output directory. Use the download button for one TIFF or a ZIP for a batch.

## Processing

The default pipeline follows the supplied script: colored non-local means denoising, Multi-Scale Retinex, per-channel 1st/99th percentile normalization, bilateral filtering, unsharp masking, and HSV saturation adjustment. It processes tiles with a configurable halo and uses a dataset-wide sample to scale non-8-bit data consistently across tiles. GeoTIFF CRS, transform, dimensions, and other compatible metadata are copied from the source.

JPG/PNG inputs have no geospatial reference, so their output TIFFs do not acquire a CRS or map transform. Inputs with one or two bands are expanded to RGB; inputs with three or more bands use the first three bands as RGB.

## Project layout

```text
GIS_Image_Enhancement_App/
├── app.py
├── processors/
│   ├── __init__.py
│   ├── msr.py
│   └── pipeline.py
├── requirements.txt
└── README.md
```
