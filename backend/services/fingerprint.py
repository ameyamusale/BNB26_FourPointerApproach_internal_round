"""Image perceptual fingerprint for transformation-aware evidence.

This is a compact pHash-style fingerprint. It is deliberately treated as
supporting evidence: a close fingerprint does not prove authorship by itself.
"""
from __future__ import annotations

import io
import math
from typing import Optional

from PIL import Image, ImageOps

from models.artifact import ArtifactType

IMPLEMENTED = True


def _dct_2d(values, n=32):
    # First 8x8 DCT coefficients. Pure Python keeps the MVP dependency-light.
    result = [[0.0] * 8 for _ in range(8)]
    for u in range(8):
        for v in range(8):
            total = 0.0
            for x in range(n):
                for y in range(n):
                    total += values[x][y] * math.cos((2 * x + 1) * u * math.pi / (2 * n)) * math.cos((2 * y + 1) * v * math.pi / (2 * n))
            au = 1 / math.sqrt(n) if u == 0 else math.sqrt(2 / n)
            av = 1 / math.sqrt(n) if v == 0 else math.sqrt(2 / n)
            result[u][v] = au * av * total
    return result


def compute_robust_fingerprint(data: bytes, artifact_type: ArtifactType = ArtifactType.IMAGE) -> Optional[str]:
    if artifact_type != ArtifactType.IMAGE:
        return None
    try:
        with Image.open(io.BytesIO(data)) as source:
            image = ImageOps.exif_transpose(source).convert("L").resize((32, 32), Image.Resampling.LANCZOS)
            pixels = [[image.getpixel((x, y)) for y in range(32)] for x in range(32)]
        dct = _dct_2d(pixels)
        low = [dct[u][v] for u in range(8) for v in range(8) if not (u == 0 and v == 0)]
        median = sorted(low)[len(low) // 2]
        bits = ["1" if value > median else "0" for value in low]
        return f"phash:{int(''.join(bits), 2):016x}"
    except Exception:
        return None


def fingerprint_distance(first: Optional[str], second: Optional[str]) -> Optional[int]:
    if not first or not second or not first.startswith("phash:") or not second.startswith("phash:"):
        return None
    try:
        return (int(first.split(":", 1)[1], 16) ^ int(second.split(":", 1)[1], 16)).bit_count()
    except Exception:
        return None
