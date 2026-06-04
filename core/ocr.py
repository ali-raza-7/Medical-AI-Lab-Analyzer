import io
import asyncio
import logging
from PIL import Image
import pytesseract
from fastapi import UploadFile

logger = logging.getLogger(__name__)

# psm 6: treat image as a single uniform block of text — best for lab report layouts.
# psm 4: single column of text with varying sizes — good fallback for single-page reports.
# oem 3: use LSTM neural net engine for highest accuracy.
_TESS_CONFIG = "--psm 6 --oem 3"

async def extract_text(file: UploadFile) -> str:
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    raw_text = await asyncio.to_thread(pytesseract.image_to_string, image, config=_TESS_CONFIG)

    # Log raw OCR output for debugging
    logger.info("[ocr] raw text extracted (%d chars)", len(raw_text))
    logger.debug("[ocr] RAW OUTPUT:\n%s\n[ocr] END RAW OUTPUT", raw_text)

    return raw_text
