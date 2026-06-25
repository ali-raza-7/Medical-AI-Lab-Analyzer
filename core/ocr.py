import io
import asyncio
import logging
from PIL import Image, ImageOps, ImageFile
ImageFile.MAX_IMAGE_PIXELS = 100_000_000
import pytesseract
from fastapi import UploadFile

try:
    import fitz
except ImportError:
    fitz = None

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

logger = logging.getLogger(__name__)

_TESS_CONFIG = "--psm 6 --oem 3"


def _open_image(content: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(content))
    return ImageOps.exif_transpose(img) or img


def _extract_pdf_text(content: bytes) -> str:
    if fitz is None:
        raise ImportError("pymupdf is required for PDF processing (pip install pymupdf)")
    doc = fitz.open(stream=content, filetype="pdf")
    all_text_parts = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        page_text = page.get_text()
        if page_text.strip():
            all_text_parts.append(page_text)
        for img_index in range(len(page.get_images())):
            xref = page.get_images()[img_index][0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            try:
                img = _open_image(image_bytes)
                ocr_text = pytesseract.image_to_string(img, config=_TESS_CONFIG)
                if ocr_text.strip():
                    all_text_parts.append(ocr_text)
            except Exception:
                continue
    doc.close()
    return "\n".join(all_text_parts)


async def extract_text(file: UploadFile) -> str:
    contents = await file.read()
    return await extract_text_from_bytes_async(contents)


async def extract_text_from_bytes_async(content: bytes) -> str:
    if content[:4] == b"%PDF":
        if fitz is None:
            raise ImportError("pymupdf required for PDF processing")
        return await asyncio.to_thread(_extract_pdf_text, content)
    image = _open_image(content)
    raw_text = await asyncio.to_thread(pytesseract.image_to_string, image, config=_TESS_CONFIG)
    logger.info("[ocr] raw text extracted (%d chars)", len(raw_text))
    logger.debug("[ocr] RAW OUTPUT:\n%s\n[ocr] END RAW OUTPUT", raw_text)
    return raw_text


def extract_text_sync(content: bytes) -> str:
    if content[:4] == b"%PDF":
        if fitz is None:
            raise ImportError("pymupdf required for PDF processing")
        return _extract_pdf_text(content)
    image = _open_image(content)
    raw_text = pytesseract.image_to_string(image, config=_TESS_CONFIG)
    logger.info("[ocr] sync raw text extracted (%d chars)", len(raw_text))
    return raw_text
