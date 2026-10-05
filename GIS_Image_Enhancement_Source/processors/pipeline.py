from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
import rasterio
from rasterio.windows import Window

from processors.msr import multi_scale_retinex, normalize_retinex


@dataclass(frozen=True)
class EnhancementSettings:
    tile_size: int = 1024
    sigmas: tuple[float, ...] = (15.0, 80.0, 250.0)
    sharpen_amount: float = 1.3
    blur_sigma: float = 1.2
    saturation_factor: float = 1.05
    denoise_strength: int = 5
    halo: int = 256
    compression: str | None = "lzw"


def _rgb_window(src: rasterio.io.DatasetReader, window: Window,
                ranges: tuple[tuple[float, float], ...]) -> np.ndarray:
    if src.count >= 3:
        indexes = [1, 2, 3]
    elif src.count == 2:
        indexes = [1, 2, 2]
    else:
        indexes = [1, 1, 1]
    raw = src.read(indexes=indexes, window=window, masked=True)
    image = np.moveaxis(raw.filled(0), 0, -1).astype(np.float32)
    for channel in range(3):
        low, high = ranges[channel]
        if high > low:
            image[:, :, channel] = (image[:, :, channel] - low) * (255.0 / (high - low))
        else:
            image[:, :, channel] = 0
    return np.clip(image, 0, 255).astype(np.uint8)


def _sample_ranges(src: rasterio.io.DatasetReader) -> tuple[tuple[float, float], ...]:
    """Use a downsampled, dataset-wide sample to avoid tile-by-tile input stretching."""
    indexes = [1, 2, 3] if src.count >= 3 else ([1, 2, 2] if src.count == 2 else [1, 1, 1])
    out_h = min(src.height, 2048)
    out_w = min(src.width, 2048)
    sampled = src.read(indexes=indexes, out_shape=(3, out_h, out_w), masked=True)
    ranges: list[tuple[float, float]] = []
    for band in sampled:
        values = band.compressed().astype(np.float32)
        values = values[np.isfinite(values)]
        if values.size == 0:
            ranges.append((0.0, 1.0))
        elif np.issubdtype(src.dtypes[0], np.integer) and src.dtypes[0] == "uint8":
            ranges.append((0.0, 255.0))
        else:
            low, high = np.percentile(values, (2, 98))
            ranges.append((float(low), float(high)))
    return tuple(ranges)


def _enhance_rgb(image: np.ndarray, settings: EnhancementSettings) -> np.ndarray:
    working = image
    if settings.denoise_strength > 0:
        working = cv2.fastNlMeansDenoisingColored(
            working, None, settings.denoise_strength, settings.denoise_strength, 7, 21
        )
    enhanced = normalize_retinex(multi_scale_retinex(working, settings.sigmas))
    enhanced = cv2.bilateralFilter(enhanced, 5, 30, 30)
    blurred = cv2.GaussianBlur(enhanced, (0, 0), settings.blur_sigma)
    sharpened = cv2.addWeighted(enhanced, 1 + settings.sharpen_amount,
                                blurred, -settings.sharpen_amount, 0)
    hsv = cv2.cvtColor(sharpened, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * settings.saturation_factor, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)


def enhance_raster(input_path: str | Path, output_path: str | Path,
                   settings: EnhancementSettings,
                   progress_callback: Callable[[int, int], None] | None = None) -> None:
    """Enhance an image into a 3-band uint8 GeoTIFF using haloed tiles."""
    if settings.tile_size < 1 or settings.halo < 0:
        raise ValueError("Tile size must be positive and halo cannot be negative.")
    input_path, output_path = Path(input_path), Path(output_path)
    with rasterio.open(input_path) as src:
        if src.count < 1:
            raise ValueError("The image contains no readable bands.")
        ranges = _sample_ranges(src)
        profile = src.profile.copy()
        profile.update(driver="GTiff", dtype="uint8", count=3, photometric="RGB",
                       BIGTIFF="IF_SAFER", tiled=True, blockxsize=256, blockysize=256)
        # A source nodata value may be out of range after conversion to uint8.
        profile.pop("nodata", None)
        if settings.compression:
            profile["compress"] = settings.compression
        else:
            profile.pop("compress", None)
        total = ((src.width + settings.tile_size - 1) // settings.tile_size) * ((src.height + settings.tile_size - 1) // settings.tile_size)
        done = 0
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(output_path, "w", **profile) as dst:
            for y in range(0, src.height, settings.tile_size):
                for x in range(0, src.width, settings.tile_size):
                    core_w = min(settings.tile_size, src.width - x)
                    core_h = min(settings.tile_size, src.height - y)
                    left, top = max(0, x - settings.halo), max(0, y - settings.halo)
                    right, bottom = min(src.width, x + core_w + settings.halo), min(src.height, y + core_h + settings.halo)
                    expanded = Window(left, top, right - left, bottom - top)
                    tile = _rgb_window(src, expanded, ranges)
                    processed = _enhance_rgb(tile, settings)
                    crop_x, crop_y = x - left, y - top
                    core = processed[crop_y:crop_y + core_h, crop_x:crop_x + core_w]
                    dst.write(np.moveaxis(core, -1, 0), window=Window(x, y, core_w, core_h))
                    done += 1
                    if progress_callback:
                        progress_callback(done, total)
