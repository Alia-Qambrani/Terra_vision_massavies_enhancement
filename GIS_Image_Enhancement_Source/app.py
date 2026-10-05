from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path

import rasterio
import streamlit as st

from processors.pipeline import EnhancementSettings, enhance_raster


st.set_page_config(page_title="TerraVision · Image Studio", page_icon="🗺️", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
 :root { --tv-ink:#142d2b; --tv-muted:#71817e; --tv-green:#08796b; --tv-border:#e3ebe8; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; color:var(--tv-ink); }
.stApp { background:#f5f8f7; }
[data-testid="stHeader"] { background:rgba(245,248,247,.88); }
[data-testid="stToolbar"] { right:1.5rem; }
[data-testid="stAppViewContainer"] .main .block-container { max-width:1280px; padding:2rem 2.4rem 5rem; }
section[data-testid="stSidebar"] { background:#fff; border-right:1px solid var(--tv-border); }
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 { font-family:Manrope,sans-serif; }
.hero { position:relative; overflow:hidden; padding:2rem 2.25rem; border-radius:22px; color:white;
  background:radial-gradient(ellipse at 85% 15%,rgba(93,211,177,.32),transparent 35%),linear-gradient(115deg,#102e2c 0%,#125b50 56%,#087f6e 100%);
  margin-bottom:1.7rem; box-shadow:0 16px 40px rgba(16,65,56,.13); }
.hero:after { content:""; position:absolute; width:290px;height:290px;right:8%;top:-210px;border:1px solid rgba(255,255,255,.15);border-radius:50%;box-shadow:0 0 0 28px rgba(255,255,255,.035),0 0 0 58px rgba(255,255,255,.025); }
.hero-top { display:flex; align-items:center; gap:.55rem; margin-bottom:1.05rem; color:#b9eee1; font-size:.75rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; }
.hero-mark { display:grid;place-items:center;width:25px;height:25px;border:1px solid #ffffff44;border-radius:8px;font-size:.9rem; }
.hero h1 { position:relative;z-index:1;font-family:Manrope,sans-serif;margin:0;font-size:clamp(1.8rem,3vw,2.5rem);letter-spacing:-.045em; }
.hero p { position:relative;z-index:1;max-width:620px;color:#d0e9e3;margin:.65rem 0 0;font-size:1rem;line-height:1.6; }
.hero-meta { position:relative;z-index:1;display:flex;gap:.55rem;flex-wrap:wrap;margin-top:1.25rem; }
.hero-meta span { border:1px solid #ffffff35;background:#ffffff0c;border-radius:30px;padding:.38rem .72rem;color:#e4f6f1;font-size:.73rem; }
[data-testid="stFileUploader"] { background:#fff; border:1px dashed #b9cec7;border-radius:16px;padding:.5rem; }
[data-testid="stFileUploader"] section { border:0 !important;background:transparent !important; }
[data-testid="stFileUploader"] button { border-radius:9px !important; }
[data-testid="stFileUploaderDropzoneInstructions"] small { color:#71817e; }
div[data-testid="stMetric"] { background:#fff;padding:1rem 1.1rem;border:1px solid var(--tv-border);border-radius:14px;box-shadow:0 4px 12px #173b3210; }
[data-testid="stMetricLabel"] { color:#71817e; }
[data-testid="stMetricValue"] { color:#173c35; }
div.stButton > button[kind="primary"], div.stDownloadButton > button { border:0;border-radius:11px;background:linear-gradient(110deg,#08796b,#0a8c78);box-shadow:0 7px 15px #08796b25;font-weight:700;min-height:2.8rem; }
div.stButton > button[kind="primary"]:hover, div.stDownloadButton > button:hover { background:#07685d;border-color:#07685d; }
div[data-testid="stExpander"] { background:white;border:1px solid var(--tv-border);border-radius:12px; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius:14px; }
.section-kicker { color:#738580;font-size:.72rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;margin:0 0 .2rem; }
.section-title { font-family:Manrope,sans-serif;font-weight:750;font-size:1.3rem;letter-spacing:-.025em;color:#193632;margin:0 0 .35rem; }
.section-note { color:#72817e;font-size:.9rem;margin:0 0 1rem; }
.workflow-card { min-height:145px;padding:1.05rem 1.1rem;border:1px solid var(--tv-border);border-radius:15px;background:#fff; }
.workflow-number { color:#0b8574;font-size:.72rem;font-weight:800;letter-spacing:.1em; }
.workflow-card strong { display:block;margin:.45rem 0 .3rem;color:#183a35;font-family:Manrope,sans-serif; }
.workflow-card p { margin:0;color:#71817e;font-size:.84rem;line-height:1.5; }
.result-row { padding:.7rem .85rem;border:1px solid var(--tv-border);background:#fff;border-radius:12px;margin:.35rem 0; }
@media(max-width:700px) { [data-testid="stAppViewContainer"] .main .block-container { padding:1.1rem 1rem 4rem; }.hero{padding:1.5rem;border-radius:17px;} }
</style>
<div class="hero"><div class="hero-top"><span class="hero-mark">✦</span> TERRAVISION · IMAGE STUDIO</div>
<h1>Bring your maps into focus.</h1>
<p>Enhance scanned maps and raster imagery with a carefully tuned image workflow. Process a single image or an entire batch, then export ready-to-use GeoTIFFs.</p>
<div class="hero-meta"><span>TIFF · JPG · PNG</span><span>Batch processing</span><span>GeoTIFF aware</span></div></div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<p class='section-kicker'>WORKSPACE</p><h3 style='font-family:Manrope;margin:.1rem 0 .2rem'>Enhancement settings</h3>", unsafe_allow_html=True)
    st.caption("Tune the processing profile. Defaults follow your supplied script.")
    tile_size = st.select_slider("Tile size", options=[256, 512, 1024, 2048], value=1024)
    sigmas = (
        st.number_input("Retinex sigma 1", min_value=1, max_value=500, value=15),
        st.number_input("Retinex sigma 2", min_value=1, max_value=1000, value=80),
        st.number_input("Retinex sigma 3", min_value=1, max_value=2000, value=250),
    )
    sharpen = st.slider("Sharpen amount", 0.0, 3.0, 1.3, 0.1)
    blur_sigma = st.slider("Blur sigma", 0.1, 5.0, 1.2, 0.1)
    saturation = st.slider("Saturation factor", 0.0, 2.0, 1.05, 0.05)
    denoise = st.slider("Denoising strength", 0, 20, 5)
    halo = st.slider("Tile overlap / halo", 32, 1024, 256, 32,
                     help="Extra context around tiles reduces visible processing seams.")
    compression = st.selectbox("TIFF compression", ["LZW", "DEFLATE", "None"], index=0)

uploads = st.file_uploader(
    "Add source images", type=["tif", "tiff", "jpg", "jpeg", "png"],
    accept_multiple_files=True,
    help="TIFF georeferencing is retained when present. JPG/PNG outputs are ordinary GeoTIFFs without CRS metadata."
)

if uploads:
    st.markdown(f"<p class='section-kicker'>INPUT QUEUE</p><p class='section-title'>{len(uploads)} image{'s' if len(uploads) != 1 else ''} ready to process</p>", unsafe_allow_html=True)
    with st.expander("Selected files", expanded=False):
        for file in uploads:
            st.write(f"• {file.name} · {file.size / 1024 / 1024:.1f} MB")

    left, right = st.columns([1, 1])
    with left:
        output_dir_text = st.text_input("Save outputs to", value=str(Path.cwd() / "output"),
                                        help="The app process must have permission to write to this folder.")
    with right:
        st.info("The download bundle is available even when the app is hosted remotely. Local folder saving writes on the machine running Streamlit.")

    run = st.button("✦   Enhance images", type="primary", use_container_width=True)
    if run:
        output_dir = Path(output_dir_text).expanduser()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            settings = EnhancementSettings(
                tile_size=int(tile_size), sigmas=tuple(float(s) for s in sigmas),
                sharpen_amount=float(sharpen), blur_sigma=float(blur_sigma),
                saturation_factor=float(saturation), denoise_strength=int(denoise),
                halo=int(halo), compression=None if compression == "None" else compression.lower(),
            )
            progress = st.progress(0, text="Preparing batch…")
            results: list[Path] = []
            failures: list[tuple[str, str]] = []
            status = st.empty()
            for index, uploaded in enumerate(uploads):
                name = Path(uploaded.name).stem
                destination = output_dir / f"{name}_MSR.tif"
                # Avoid overwriting a prior result when filenames repeat.
                suffix = 2
                while destination.exists():
                    destination = output_dir / f"{name}_MSR_{suffix}.tif"
                    suffix += 1
                status.write(f"Processing **{uploaded.name}**…")
                try:
                    with tempfile.NamedTemporaryFile(suffix=Path(uploaded.name).suffix, delete=False) as source_file:
                        source_file.write(uploaded.getvalue())
                        source_path = Path(source_file.name)
                    try:
                        with rasterio.open(source_path) as source:
                            dimensions = f"{source.width:,} × {source.height:,} · {source.count} band(s)"
                        enhance_raster(source_path, destination, settings,
                                      progress_callback=lambda done, total, name=uploaded.name, i=index:
                                      progress.progress((i + done / total) / len(uploads),
                                                        text=f"{name}: tile {done}/{total}"))
                        results.append(destination)
                        st.success(f"{uploaded.name} → {destination.name} ({dimensions})")
                    finally:
                        source_path.unlink(missing_ok=True)
                except Exception as exc:
                    failures.append((uploaded.name, str(exc)))
                    st.error(f"Could not process {uploaded.name}: {exc}")
                progress.progress((index + 1) / len(uploads), text=f"Finished {index + 1}/{len(uploads)} images")
            status.empty()
            st.session_state["enhancement_results"] = [str(p) for p in results]
            st.session_state["enhancement_failures"] = failures
            if results:
                st.success(f"Completed {len(results)} of {len(uploads)} image(s). Output: {output_dir}")
            if failures:
                st.warning(f"{len(failures)} image(s) could not be processed.")
        except Exception as exc:
            st.error(f"Unable to prepare output folder: {exc}")

results = [Path(p) for p in st.session_state.get("enhancement_results", []) if Path(p).exists()]
if results:
    st.markdown("<p class='section-kicker'>EXPORTS</p><p class='section-title'>Your enhanced images</p><p class='section-note'>GeoTIFF files are saved to your chosen folder and ready to download.</p>", unsafe_allow_html=True)
    for result in results:
        with rasterio.open(result) as dataset:
            cols = st.columns([3, 1, 1, 1.5])
            cols[0].markdown(f"**{result.name}**")
            cols[1].caption(f"{dataset.width:,} × {dataset.height:,}")
            cols[2].caption(f"CRS: {dataset.crs or 'not set'}")
        cols[3].download_button("⬇ Download TIFF", data=result.read_bytes(),
                                file_name=result.name, mime="image/tiff",
                                key=f"download-{result.name}", use_container_width=True)
    if len(results) > 1:
        bundle = io.BytesIO()
        with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in results:
                archive.write(path, path.name)
        st.download_button("⬇  Download all images as ZIP", bundle.getvalue(), "enhanced_images.zip",
                           "application/zip", type="primary", use_container_width=True)
elif st.session_state.get("enhancement_failures"):
    st.warning("No output files are available yet. Review the processing errors above, correct the issue, then run enhancement again.")
else:
    st.markdown("<p class='section-kicker'>HOW IT WORKS</p><p class='section-title'>A simple workflow</p><p class='section-note'>Everything you need to go from source image to an enhanced raster.</p>", unsafe_allow_html=True)
    a, b, c = st.columns(3)
    a.markdown("<div class='workflow-card'><span class='workflow-number'>01 · SELECT</span><strong>Bring in your imagery</strong><p>Upload one image or a batch of TIFF, JPG, or PNG files.</p></div>", unsafe_allow_html=True)
    b.markdown("<div class='workflow-card'><span class='workflow-number'>02 · REFINE</span><strong>Set your enhancement</strong><p>Adjust Retinex scales, denoising, sharpening, and color.</p></div>", unsafe_allow_html=True)
    c.markdown("<div class='workflow-card'><span class='workflow-number'>03 · EXPORT</span><strong>Use it in your GIS</strong><p>Download RGB TIFFs with source georeferencing retained when available.</p></div>", unsafe_allow_html=True)

st.caption("For non-georeferenced JPEG/PNG inputs, the generated TIFF has no CRS or map transform. Input TIFFs with fewer than three bands are converted to RGB using available bands.")
