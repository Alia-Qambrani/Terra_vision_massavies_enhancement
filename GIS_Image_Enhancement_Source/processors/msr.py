from __future__ import annotations

import cv2
import numpy as np


def multi_scale_retinex(image: np.ndarray, sigmas: tuple[float, ...]) -> np.ndarray:
    """Compute MSR for an RGB uint8 tile and return a float32 response."""
    if not sigmas or any(sigma <= 0 for sigma in sigmas):
        raise ValueError("Retinex sigmas must all be positive.")
    values = image.astype(np.float32) + 1.0
    response = np.zeros_like(values, dtype=np.float32)
    for sigma in sigmas:
        blurred = cv2.GaussianBlur(values, (0, 0), float(sigma))
        response += np.log(values) - np.log(blurred + 1.0)
    return response / len(sigmas)


def normalize_retinex(response: np.ndarray) -> np.ndarray:
    """Percentile-normalize each RGB channel safely to uint8."""
    output = np.empty(response.shape, dtype=np.uint8)
    for channel_index in range(3):
        channel = response[:, :, channel_index]
        low, high = np.percentile(channel, (1, 99))
        if not np.isfinite(low) or not np.isfinite(high) or high <= low:
            output[:, :, channel_index] = 0
            continue
        scaled = (np.clip(channel, low, high) - low) * (255.0 / (high - low))
        output[:, :, channel_index] = np.rint(scaled).astype(np.uint8)
    return output
