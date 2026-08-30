import os
from PyPDF2 import PdfReader
from docx import Document
from .config import OCR_AVAILABLE, TESSERACT_INSTALLED, PYMUPDF_AVAILABLE, logger

# Try importing OCR and PDF libraries if they are available
if OCR_AVAILABLE:
    try:
        import pytesseract
        from PIL import Image, ImageOps, ImageEnhance
    except ImportError:
        pass

if PYMUPDF_AVAILABLE:
    try:
        import fitz
    except ImportError:
        pass

def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == ".pdf":
            try:
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

                if not text.strip():
                    if OCR_AVAILABLE and TESSERACT_INSTALLED and PYMUPDF_AVAILABLE:
                        logger.info("📄 PDF appears scanned. Attempting OCR...")
                        doc = fitz.open(file_path)
                        ocr_text = ""
                        for page_num, page in enumerate(doc):
                            try:
                                pix = page.get_pixmap(dpi=300)
                                img = Image.frombytes(
                                    "RGB", [pix.width, pix.height], pix.samples
                                )
                                img = ImageOps.grayscale(img)
                                img = ImageEnhance.Contrast(img).enhance(2.5)
                                img = ImageEnhance.Sharpness(img).enhance(2.0)

                                try:
                                    page_text = pytesseract.image_to_string(
                                        img, lang="eng+mar", config="--psm 6"
                                    )
                                except Exception:
                                    page_text = pytesseract.image_to_string(
                                        img, lang="eng", config="--psm 6"
                                    )

                                ocr_text += (
                                    f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                                )
                            except Exception as page_error:
                                logger.error(
                                    f"OCR failed for page {page_num + 1}: {page_error}"
                                )
                                continue

                        if ocr_text.strip():
                            text = ocr_text
                            logger.info(f"✅ OCR extracted {len(text)} characters")
                    else:
                        missing = []
                        if not OCR_AVAILABLE:
                            missing.append("pytesseract/PIL")
                        if not TESSERACT_INSTALLED:
                            missing.append("Tesseract Engine")
                        if not PYMUPDF_AVAILABLE:
                            missing.append("PyMuPDF")
                        return (
                            None,
                            f"Cannot perform OCR. Missing: {', '.join(missing)}",
                        )

                if not text.strip():
                    return None, "PDF appears empty"

                return text, None

            except Exception as e:
                return None, f"PDF reading error: {str(e)}"

        elif ext == ".docx":
            try:
                doc = Document(file_path)
                text = "\n".join(
                    [para.text for para in doc.paragraphs if para.text.strip()]
                )

                if not text.strip():
                    return None, "DOCX file is empty"

                return text, None
            except Exception as e:
                return None, f"DOCX reading error: {str(e)}"

        elif ext == ".txt":
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()

                if not text.strip():
                    return None, "Text file is empty"

                return text, None
            except UnicodeDecodeError:
                try:
                    with open(file_path, "r", encoding="latin-1") as f:
                        text = f.read()
                    return text, None
                except Exception as e:
                    return None, f"Text file encoding error: {str(e)}"
            except Exception as e:
                return None, f"Text file error: {str(e)}"

        elif ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
            if not OCR_AVAILABLE:
                return None, "OCR libraries not installed"

            if not TESSERACT_INSTALLED:
                return None, "Tesseract OCR not installed"

            try:
                img = Image.open(file_path)

                if img.mode != "RGB":
                    img = img.convert("RGB")

                try:
                    img = ImageOps.grayscale(img)
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(2.5)
                    enhancer = ImageEnhance.Sharpness(img)
                    img = enhancer.enhance(2.0)
                    logger.info("✅ Image preprocessing complete")
                except Exception as prep_error:
                    logger.warning(f"⚠️ Image preprocessing failed: {prep_error}")

                try:
                    text = pytesseract.image_to_string(
                        img, lang="eng+mar", config="--psm 6"
                    )
                    logger.info(f"✅ OCR (eng+mar) extracted {len(text)} characters")
                except Exception:
                    logger.warning("⚠️ Bilingual OCR failed, falling back to English")
                    text = pytesseract.image_to_string(
                        img, lang="eng", config="--psm 6"
                    )
                    logger.info(f"✅ OCR (eng) extracted {len(text)} characters")

                if not text.strip():
                    return None, "No readable text found in image"

                logger.info(f"📝 OCR Preview: {text[:200]}...")

                return text, None

            except pytesseract.TesseractNotFoundError:
                return None, "Tesseract OCR not found in system"
            except Exception as e:
                return None, f"Image OCR error: {str(e)}"

        else:
            return None, f"Unsupported file type: {ext}"

    except Exception as e:
        return None, f"File processing error: {str(e)}"
