"""QR code rendering — shared by Memory Video & Web View."""
from __future__ import annotations

import io

import qrcode
from qrcode.image.pil import PilImage


def make_qr_png(data: str, size: int = 480) -> bytes:
    """Render `data` as a PNG QR code at roughly `size` px square."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(data or "")
    qr.make(fit=True)
    img = qr.make_image(image_factory=PilImage, fill_color="black",
                        back_color="white")
    pil = img.get_image()  # PIL.Image
    pil = pil.resize((size, size))
    buf = io.BytesIO()
    pil.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
