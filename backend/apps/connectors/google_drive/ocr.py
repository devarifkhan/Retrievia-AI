from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)


def pdf_to_text_via_ocr(pdf_data: bytes) -> str:
    """
    Convert scanned PDF bytes to text using pytesseract.
    Falls back to empty string on failure.
    Requires: poppler-utils (pdftoppm) and tesseract installed in the system.
    """
    try:
        import pytesseract
        from PIL import Image
        import subprocess
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "input.pdf")
            with open(pdf_path, "wb") as f:
                f.write(pdf_data)

            # Convert PDF pages to PNG images
            subprocess.run(
                ["pdftoppm", "-png", "-r", "200", pdf_path, os.path.join(tmpdir, "page")],
                check=True,
                capture_output=True,
            )

            # OCR each page
            texts = []
            for filename in sorted(os.listdir(tmpdir)):
                if filename.startswith("page") and filename.endswith(".png"):
                    img = Image.open(os.path.join(tmpdir, filename))
                    text = pytesseract.image_to_string(img, lang="eng")
                    if text.strip():
                        texts.append(text.strip())

            return "\n\n".join(texts)

    except Exception as exc:
        logger.warning("OCR failed: %s", exc)
        return ""
