import os
import logging
from dotenv import load_dotenv

# Base project directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
env_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=env_path)

# Configure logging system
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(BASE_DIR, "law_mitra.log"), encoding="utf-8")
    ]
)
logger = logging.getLogger("law_mitra")
logger.info("Configuration loaded, logger initialized")

# Retrieve API keys from environment
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "")
HF_MODEL_ID = os.environ.get("HF_MODEL_ID", "meta-llama/Meta-Llama-3-8B-Instruct")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# ----------------------------------------------------------------------------------
# Library availability checks & setup
# ----------------------------------------------------------------------------------
GOOGLE_GENAI_AVAILABLE = False
try:
    from google import genai
    from google.genai import types
    GOOGLE_GENAI_AVAILABLE = True
    logger.info("✅ Google GenAI SDK imported successfully")
except ImportError:
    logger.warning("❌ Google GenAI SDK not installed. Run: pip install google-genai")

OCR_AVAILABLE = False
TESSERACT_INSTALLED = False
PYMUPDF_AVAILABLE = False

# pytesseract setup
try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageOps
    OCR_AVAILABLE = True

    if os.name == "nt":
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                TESSERACT_INSTALLED = True
                logger.info(f"✅ Tesseract engine found: {path}")
                break

        if not TESSERACT_INSTALLED:
            try:
                pytesseract.get_tesseract_version()
                TESSERACT_INSTALLED = True
                logger.info("✅ Tesseract found in system PATH")
            except Exception:
                logger.warning("⚠️ Tesseract engine not found. OCR will be unavailable.")
    else:
        try:
            pytesseract.get_tesseract_version()
            TESSERACT_INSTALLED = True
            logger.info("✅ Tesseract available")
        except Exception:
            logger.warning("⚠️ Tesseract engine not installed.")
except ImportError:
    logger.warning("⚠️ pytesseract or Pillow PIL not installed.")

# PyMuPDF setup
try:
    import fitz
    PYMUPDF_AVAILABLE = True
    logger.info("✅ PyMuPDF available")
except ImportError:
    logger.warning("⚠️ PyMuPDF not installed.")
