"""AI-style photo ranker for Memory Box (no external API needed).

Uses Pillow + statistics to score each uploaded photo on:
  • Sharpness  (variance of edge-filtered image — blurry → low)
  • Exposure   (avoids too dark / blown out)
  • Composition (resolution + color variance)

Returns the top-N indices in original upload order so the downstream
collage / video module can pick the strongest 6-9 photos for the
3 collage sets (2-3 each) the manager asked for.
"""
from __future__ import annotations

import base64
import io
from typing import List, Tuple

from PIL import Image, ImageFilter, ImageStat


def _strip_data_url(b64: str) -> bytes:
    if not b64:
        return b""
    if "," in b64 and b64.startswith("data:"):
        b64 = b64.split(",", 1)[1]
    try:
        return base64.b64decode(b64)
    except Exception:
        return b""


def _score_image(im: Image.Image) -> float:
    """Higher = better. Combines sharpness, exposure & composition."""
    try:
        # Down-sample for fast stats (max edge 512 px)
        w, h = im.size
        if max(w, h) > 512:
            scale = 512 / max(w, h)
            im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        gray = im.convert("L")

        # 1) Sharpness: variance of edges (Laplacian-ish)
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edges)
        sharpness = edge_stat.stddev[0]  # 0–127 typical

        # 2) Exposure: prefer brightness 80–180
        mean_b = ImageStat.Stat(gray).mean[0]
        # Triangular sweet-spot scoring around 130
        exp_score = max(0.0, 1.0 - abs(mean_b - 130) / 130)

        # 3) Color variance — washed-out / monochrome → low
        rgb = im.convert("RGB")
        cstat = ImageStat.Stat(rgb)
        color_var = sum(cstat.stddev) / 3.0  # 0–100+

        # 4) Resolution bonus (cap at 1024px on longest edge)
        res_bonus = min(1.0, max(w, h) / 1024)

        # Weighted blend → 0-100ish
        score = (
            sharpness * 0.45
            + exp_score * 50 * 0.20
            + color_var * 0.25
            + res_bonus * 30 * 0.10
        )
        return float(score)
    except Exception:
        return 0.0


def rank_photos(b64_photos: List[str], top_n: int = 9) -> Tuple[List[int], List[float]]:
    """Score every photo and return (top_indices_in_score_order, scores_aligned_to_input).

    Args:
        b64_photos:  list of data-url or raw base64 strings
        top_n:       maximum photos to return (default 9 → fits 3 collages of 2-3)

    Returns:
        indices:  list of original indices, best first, len ≤ top_n
        scores:   list of per-input scores in original order (for debug/UI)
    """
    scores: List[float] = []
    for b64 in b64_photos:
        raw = _strip_data_url(b64)
        if not raw:
            scores.append(0.0)
            continue
        try:
            im = Image.open(io.BytesIO(raw))
            im.load()
            scores.append(_score_image(im))
        except Exception:
            scores.append(0.0)

    # Rank by score desc, keeping original index
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    top = ranked[:top_n]
    return top, scores


def split_into_collage_sets(top_indices: List[int]) -> List[List[int]]:
    """Split a ranked list of up to 9 indices into exactly 3 collage sets
    of 2-3 photos each, alternating best→3rd-best→6th, etc. so each set has
    a strong hero photo."""
    n = len(top_indices)
    if n == 0:
        return [[], [], []]
    if n <= 3:
        return [top_indices, [], []]
    if n <= 6:
        # 3 + 3 layout
        half = (n + 1) // 2
        return [top_indices[:half], top_indices[half:], []]
    # n = 7..9 → 3-3-3 / 3-3-2 / 3-2-2
    sizes = [3, 3, 3] if n >= 9 else ([3, 3, 2] if n == 8 else [3, 2, 2])
    out, idx = [], 0
    for sz in sizes:
        out.append(top_indices[idx:idx + sz])
        idx += sz
    return out
