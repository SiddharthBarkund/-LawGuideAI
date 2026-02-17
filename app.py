import os
import re
import uuid
import requests
from datetime import datetime
from flask import Flask, request, jsonify, send_file, session
from flask_cors import CORS
from openai import OpenAI
from PyPDF2 import PdfReader
from docx import Document

# ==================================================================================
# 1. GOOGLE GENAI - PRIMARY MODEL (Gemini 1.5 Pro)
# ==================================================================================
try:
    from google import genai
    from google.genai import types
    GOOGLE_GENAI_AVAILABLE = True
    print("✅ New Google GenAI SDK imported")
except ImportError:
    print("❌ Please install: pip install google-genai")
    GOOGLE_GENAI_AVAILABLE = False

# ==================================================================================
# 2. OCR & DEPENDENCY INITIALIZATION
# ==================================================================================
OCR_AVAILABLE = False
TESSERACT_INSTALLED = False
PYMUPDF_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageOps
    OCR_AVAILABLE = True
    
    if os.name == 'nt':
        tesseract_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]
        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                TESSERACT_INSTALLED = True
                print(f"✅ Tesseract found: {path}")
                break
        
        if not TESSERACT_INSTALLED:
            try:
                pytesseract.get_tesseract_version()
                TESSERACT_INSTALLED = True
                print("✅ Tesseract found in PATH")
            except:
                print("⚠️ Tesseract not found")
    else:
        try:
            pytesseract.get_tesseract_version()
            TESSERACT_INSTALLED = True
            print("✅ Tesseract available")
        except:
            print("⚠️ Tesseract not installed")
            
except ImportError:
    print("⚠️ pytesseract/PIL not installed")

try:
    import fitz
    PYMUPDF_AVAILABLE = True
    print("✅ PyMuPDF available")
except ImportError:
    print("⚠️ PyMuPDF not installed")

# ==================================================================================
# 3. FLASK APPLICATION SETUP
# ==================================================================================
app = Flask(__name__)
app.secret_key = 'law_mitra_2026_secure_session_key'
CORS(app, supports_credentials=True)

DOCUMENT_STORE = {}

# ==================================================================================
# 4. API CONFIGURATION - THREE PRIORITY SYSTEM
# ==================================================================================

# ════════════════════════════════════════════════════════════════════════════════
# PASTE YOUR API KEYS HERE (येथे तुमची API keys paste करा)
# ════════════════════════════════════════════════════════════════════════════════

# PRIMARY: Google Gemini 1.5 Pro (REQUIRED - मुख्य आणि सर्वात शक्तिशाली)
GOOGLE_API_KEY = ""

# SECONDARY: Hugging Face Inference API (OPTIONAL - पर्यायी)
# NOTE: Replace the placeholder below with your real Hugging Face API key and desired model ID
HUGGINGFACE_API_KEY = ""
HF_MODEL_ID = "meta-llama/Meta-Llama-3-8B-Instruct"

# THIRD: Groq (FREE & FAST - विनामूल्य आणि जलद)
GROQ_API_KEY = ""

# ════════════════════════════════════════════════════════════════════════════════

# ==================================================================================
# Configure Google Gemini 1.5 Pro (PRIMARY - 1st Priority)
# ==================================================================================
gemini_client = None
gemini_pro_available = False

if GOOGLE_GENAI_AVAILABLE:
    if GOOGLE_API_KEY and GOOGLE_API_KEY != "PASTE_YOUR_GEMINI_KEY_HERE":
        try:
            gemini_client = genai.Client(api_key=GOOGLE_API_KEY.strip())
            
            try:
                print("🔍 Auto-detecting available Gemini models...")
                models_list = gemini_client.models.list()
                
                preferred_models = [
                    'models/gemini-2.5-flash',
                    'models/gemini-2.5-pro',
                    'models/gemini-2.0-flash',
                    'models/gemini-exp-1206',
                    'models/gemini-flash-latest',
                    'models/gemini-pro-latest'
                ]
                
                working_model = None
                gemini_quota_exceeded = False

                for pref_model in preferred_models:
                    try:
                        print(f"🧪 Testing: {pref_model}")
                        test_response = gemini_client.models.generate_content(
                            model=pref_model,
                            contents='Test'
                        )
                        working_model = pref_model
                        gemini_pro_available = True
                        gemini_client.working_model = working_model
                        print(f"✅ 1st PRIORITY: Google Gemini ({working_model}) - ACTIVE")
                        break
                    except Exception as e:
                        error_str = str(e)
                        if "429" in error_str or "quota" in error_str.lower() or "RESOURCE_EXHAUSTED" in error_str:
                            print(f"⚠️ Gemini Quota Exceeded. Will use OpenRouter/Groq.")
                            gemini_quota_exceeded = True
                            break
                        print(f"   ❌ Failed: {error_str[:80]}")
                        continue
                
                if not working_model and not gemini_quota_exceeded:
                    for model in models_list:
                        if 'gemini' in model.name.lower():
                            try:
                                print(f"🧪 Testing: {model.name}")
                                test_response = gemini_client.models.generate_content(
                                    model=model.name,
                                    contents='Test'
                                )
                                working_model = model.name
                                gemini_pro_available = True
                                gemini_client.working_model = working_model
                                print(f"✅ 1st PRIORITY: Google Gemini ({working_model}) - ACTIVE")
                                break
                            except Exception as e:
                                error_str = str(e)
                                if "429" in error_str or "quota" in error_str.lower():
                                    gemini_quota_exceeded = True
                                    break
                                continue
                
                if not working_model:
                    if gemini_quota_exceeded:
                        print("⚠️ Gemini quota exhausted - will use backup APIs")
                    else:
                        print("⚠️ No working Gemini model found")
                    gemini_pro_available = False
                    
            except Exception as e:
                print(f"⚠️ Gemini auto-detection failed: {e}")
                gemini_pro_available = False
                
        except Exception as e:
            print(f"⚠️ Google Gemini setup failed: {e}")
            gemini_client = None
    else:
        print("⚠️ Gemini API key not set")
else:
    print("⚠️ Install: pip install google-genai")

# ==================================================================================
# Configure Hugging Face (SECONDARY - 2nd Priority)
# ==================================================================================
hf_available = False

if HUGGINGFACE_API_KEY and HUGGINGFACE_API_KEY != "PASTE_YOUR_HF_API_KEY_HERE":
    try:
        print("🧪 Testing Hugging Face connection (router API)...")
        test_resp = requests.post(
            f"https://router.huggingface.co/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {HUGGINGFACE_API_KEY.strip()}",
                "Content-Type": "application/json"
            },
            json={
                "model": HF_MODEL_ID,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 8
            },
            timeout=20
        )
        if test_resp.ok:
            hf_available = True
            print(f"✅ 2nd PRIORITY: Hugging Face - ACTIVE ({HF_MODEL_ID})")
        else:
            print(f"⚠️ Hugging Face test failed: {test_resp.status_code} {test_resp.text[:120]}")
    except Exception as e:
        print(f"⚠️ Hugging Face setup failed: {e}")
else:
    print("⚠️ Hugging Face not configured (Optional)")

# ==================================================================================
# Configure Groq (THIRD - 3rd Priority) - FREE, FAST & RELIABLE
# ==================================================================================
groq_client = None
groq_available = False

if GROQ_API_KEY and GROQ_API_KEY != "PASTE_YOUR_GROQ_KEY_HERE":
    try:
        groq_client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=GROQ_API_KEY.strip()
        )
        
        # Test Groq connection
        try:
            print("🧪 Testing Groq connection...")
            test_response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10,
                timeout=15
            )
            groq_available = True
            print("✅ 3rd PRIORITY: Groq - ACTIVE")
        except Exception as test_error:
            print(f"⚠️ Groq test failed: {test_error}")
            groq_available = False
            
    except Exception as e:
        print(f"⚠️ Groq setup failed: {e}")
        groq_client = None
else:
    print("⚠️ Groq not configured (Optional)")

# ==================================================================================
# 5. DOCUMENT TEXT EXTRACTION
# ==================================================================================
def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == '.pdf':
            try:
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                if not text.strip():
                    if OCR_AVAILABLE and TESSERACT_INSTALLED and PYMUPDF_AVAILABLE:
                        print("📄 PDF appears scanned. Attempting OCR...")
                        doc = fitz.open(file_path)
                        ocr_text = ""
                        for page_num, page in enumerate(doc):
                            try:
                                pix = page.get_pixmap(dpi=300)
                                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                img = ImageOps.grayscale(img)
                                img = ImageEnhance.Contrast(img).enhance(2.5)
                                img = ImageEnhance.Sharpness(img).enhance(2.0)
                                
                                try:
                                    page_text = pytesseract.image_to_string(img, lang='eng+mar', config='--psm 6')
                                except:
                                    page_text = pytesseract.image_to_string(img, lang='eng', config='--psm 6')
                                
                                ocr_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                            except Exception as page_error:
                                print(f"OCR failed for page {page_num + 1}: {page_error}")
                                continue
                        
                        if ocr_text.strip():
                            text = ocr_text
                            print(f"✅ OCR extracted {len(text)} characters")
                    else:
                        missing = []
                        if not OCR_AVAILABLE: missing.append("pytesseract/PIL")
                        if not TESSERACT_INSTALLED: missing.append("Tesseract Engine")
                        if not PYMUPDF_AVAILABLE: missing.append("PyMuPDF")
                        return None, f"Cannot perform OCR. Missing: {', '.join(missing)}"
                
                if not text.strip():
                    return None, "PDF appears empty"
                
                return text, None
                
            except Exception as e:
                return None, f"PDF reading error: {str(e)}"
        
        elif ext == '.docx':
            try:
                doc = Document(file_path)
                text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
                
                if not text.strip():
                    return None, "DOCX file is empty"
                
                return text, None
            except Exception as e:
                return None, f"DOCX reading error: {str(e)}"
        
        elif ext == '.txt':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                if not text.strip():
                    return None, "Text file is empty"
                
                return text, None
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        text = f.read()
                    return text, None
                except Exception as e:
                    return None, f"Text file encoding error: {str(e)}"
            except Exception as e:
                return None, f"Text file error: {str(e)}"
        
        elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
            if not OCR_AVAILABLE:
                return None, "OCR libraries not installed"
            
            if not TESSERACT_INSTALLED:
                return None, "Tesseract OCR not installed"
            
            try:
                img = Image.open(file_path)
                
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                try:
                    img = ImageOps.grayscale(img)
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(2.5)
                    enhancer = ImageEnhance.Sharpness(img)
                    img = enhancer.enhance(2.0)
                    print("✅ Image preprocessing complete")
                except Exception as prep_error:
                    print(f"⚠️ Image preprocessing failed: {prep_error}")
                
                try:
                    text = pytesseract.image_to_string(img, lang='eng+mar', config='--psm 6')
                    print(f"✅ OCR (eng+mar) extracted {len(text)} characters")
                except:
                    print("⚠️ Bilingual OCR failed, falling back to English")
                    text = pytesseract.image_to_string(img, lang='eng', config='--psm 6')
                    print(f"✅ OCR (eng) extracted {len(text)} characters")
                
                if not text.strip():
                    return None, "No readable text found in image"
                
                print(f"📝 OCR Preview: {text[:200]}...")
                
                return text, None
                
            except pytesseract.TesseractNotFoundError:
                return None, "Tesseract OCR not found in system"
            except Exception as e:
                return None, f"Image OCR error: {str(e)}"
        
        else:
            return None, f"Unsupported file type: {ext}"
    
    except Exception as e:
        return None, f"File processing error: {str(e)}"

# ==================================================================================
# 6. LANGUAGE DETECTION
# ==================================================================================
def detect_language(text):
    marathi_chars = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    total_chars = len([c for c in text if c.isalpha()])
    
    if total_chars == 0:
        return 'english'
    
    devanagari_percentage = (marathi_chars / total_chars) * 100 if total_chars > 0 else 0
    
    marathi_words = ['आहे', 'होते', 'काय', 'कसे', 'कोण', 'कुठे', 'केव्हा', 'मला', 'तुम्हाला', 'माहिती', 'सांगा', 'कृपया']
    marathi_word_count = sum(1 for word in marathi_words if word in text)
    
    hindi_words = ['है', 'हैं', 'था', 'थे', 'क्या', 'कैसे', 'कौन', 'कहाँ', 'कब', 'मुझे', 'आपको', 'बताइए', 'कृपया']
    hindi_word_count = sum(1 for word in hindi_words if word in text)
    
    if devanagari_percentage > 50:
        if marathi_word_count > hindi_word_count:
            return 'marathi'
        elif hindi_word_count > marathi_word_count:
            return 'hindi'
        else:
            return 'marathi'
    elif devanagari_percentage > 10:
        return 'mixed'
    else:
        return 'english'

# ==================================================================================
# 7. FRAUD DETECTION ANALYZER
# ==================================================================================
def analyze_document_for_fraud(text):
    warnings = []
    
    dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text)
    if len(set(dates)) > 1:
        warnings.append("⚠️ Multiple different dates found")
    
    names = re.findall(r'\b[A-Z][a-z]{2,15}\s[A-Z][a-z]{2,15}\b', text)
    for name in names:
        if re.search(r'(.)\1{2,}', name):
            warnings.append(f"⚠️ Suspicious name pattern: '{name}'")
    
    legal_keywords = ['signature', 'seal', 'stamp', 'authorized', 'certified']
    found_keywords = [kw for kw in legal_keywords if kw.lower() in text.lower()]
    if len(found_keywords) < 2:
        warnings.append("⚠️ Document may be missing official stamps/signatures")
    
    if text.count('  ') > len(text) / 50:
        warnings.append("⚠️ Unusual spacing detected")
    
    return warnings

# ==================================================================================
# 7.5. ULTRA LOCK PROMPT
# ==================================================================================
ULTRA_LOCK_SUPER_PROMPT = """
You are LAW MITRA, an AI assistant for Indian law.
Follow these CRITICAL BEHAVIOUR RULES:

1) QUESTION TYPE DETECTION
- First, understand what kind of question it is:
  • If it is an MCQ: Answer ONLY with
    - "Correct Option: <A/B/C/D/etc>"
    - One short explanation in 3–5 lines.
  • If it is a simple question: Give 3–6 short bullet points only.
  • If it is a case-based / scenario question: Give brief step-by-step reasoning.

2) FORMAT FLEXIBILITY
- Do NOT force a fixed template like "What is it / Main Points / Summary" every time.
- Choose a natural, simple format based on the question type.

3) LENGTH & CLARITY
- Default limit: keep answers under 120 words, unless user clearly asks for more detail.
- Use very simple English, short sentences, and no heavy legal jargon.

4) ACCURACY PRIORITY
- Accuracy is ALWAYS more important than style.
- If you are unsure, think carefully and avoid guessing.
- Before final answer, internally verify Indian legal age rules (for example, marriage age is 21 for males, not 18) and avoid assumption errors.

5) CONTENT LIMITS
- Mention Articles, Sections, or case laws ONLY if absolutely necessary for understanding.
- Do not give long theoretical analysis unless the user clearly asks for detailed explanation.

Respond based on the detected question type in the most helpful and concise way.
"""

# ==================================================================================
# 8. SYSTEM PROMPT BUILDER
# ==================================================================================
def initialize_messages(session_id=None, user_name=None, user_language='english'):
    doc_text = ""
    fraud_warnings = []
    has_document = False
    
    if session_id and session_id in DOCUMENT_STORE:
        doc_data = DOCUMENT_STORE[session_id]
        doc_text = doc_data.get('text', '')
        fraud_warnings = doc_data.get('fraud_warnings', [])
        has_document = True
        print(f"🔍 System prompt building WITH document ({len(doc_text)} chars)")
    else:
        print(f"🔍 System prompt building WITHOUT document")
    
    language_instructions = {
        'marathi': "तुम्हाला संपूर्ण उत्तर **फक्त मराठीत** द्यावे लागेल (कायदेशीर शब्द वगळता)",
        'hindi': "आपको पूरा जवाब **केवल हिंदी में** देना है (कानूनी शब्दों को छोड़कर)",
        'english': "You MUST respond completely in English",
        'mixed': "तुम्ही मुख्यतः मराठीत उत्तर द्या, आवश्यक असल्यास इंग्रजी वापरा"
    }
    
    current_language_instruction = language_instructions.get(user_language, language_instructions['english'])
    
    if has_document:
        system_content = f"""{ULTRA_LOCK_SUPER_PROMPT}

**YOUR IDENTITY:**
- Your name: Law Mitra (लॉ मित्र)
- User's name: {user_name if user_name else "User"}

**LANGUAGE RULE:**
{current_language_instruction}

═══════════════════════════════════════════════════════════════
🔴 DOCUMENT MODE - ACTIVE
═══════════════════════════════════════════════════════════════

A legal document has been uploaded.

**IMPORTANT BEHAVIOR RULES (STRICTLY FOLLOW THIS):**

1. **Use document context ONLY if:**
   - The user question is DIRECTLY related to the uploaded document.
   - The retrieved document content is relevant.

2. **If the user question is UNRELATED to the document:**
   - **IGNORE the document completely.**
   - Do NOT say "information not found in document".
   - Simply answer the question using general Indian legal knowledge.

3. **When using the document:**
   - Quote relevant parts if helpful.
   - Mention "According to the uploaded document..."

4. **FRAUD CHECK:**
   - Perform fraud checks (dates, names, stamps) ONLY if relevant to the user request.

**FRAUD CHECK RESULTS:**
{chr(10).join(fraud_warnings) if fraud_warnings else "✅ No obvious fraud indicators detected"}

═══════════════════════════════════════════════════════════════
📄 DOCUMENT CONTENT
═══════════════════════════════════════════════════════════════

{doc_text[:45000]}

═══════════════════════════════════════════════════════════════
END OF DOCUMENT
═══════════════════════════════════════════════════════════════
"""
    
    else:
        system_content = f"""{ULTRA_LOCK_SUPER_PROMPT}

**YOUR IDENTITY:**
- Your name: Law Mitra (लॉ मित्र)
- User's name: {user_name if user_name else "User"}

**LANGUAGE RULE:**
{current_language_instruction}

═══════════════════════════════════════════════════════════════
🟡 CONSULTATION MODE - ACTIVE (No Document)
═══════════════════════════════════════════════════════════════
"""
    
    return system_content

# ==================================================================================
# 9. FLASK ROUTES
# ==================================================================================

@app.route('/')
def index():
    return send_file('law_mitra.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        ext = os.path.splitext(file.filename)[1].lower()
        allowed_extensions = ['.pdf', '.docx', '.txt', '.png', '.jpg', '.jpeg', '.gif', '.bmp']
        
        if ext not in allowed_extensions:
            if ext == '.doc':
                return jsonify({"error": "Old .doc format not supported. Please convert to .docx"}), 400
            return jsonify({"error": f"Unsupported file type: {ext}"}), 400
        
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        session_id = session['session_id']
        
        upload_dir = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        safe_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(upload_dir, safe_filename)
        
        try:
            file.save(file_path)
        except Exception as save_error:
            return jsonify({"error": f"File save error: {str(save_error)}"}), 500
        
        try:
            text, error_msg = extract_text_from_file(file_path)
            
            try:
                os.remove(file_path)
            except:
                pass
            
            if error_msg:
                return jsonify({"error": error_msg}), 400
            
            if not text or not text.strip():
                return jsonify({"error": "No extractable text found in file"}), 400
            
            fraud_warnings = analyze_document_for_fraud(text)
            
            DOCUMENT_STORE[session_id] = {
                'text': text,
                'filename': file.filename,
                'upload_time': datetime.now().isoformat(),
                'fraud_warnings': fraud_warnings
            }
            
            user_name = session.get('user_name')
            user_language = session.get('user_language', 'english')
            session['messages'] = []
            session['system_instruction'] = initialize_messages(
                session_id=session_id, 
                user_name=user_name,
                user_language=user_language
            )
            session.modified = True
            
            print(f"✅ Document stored for session {session_id} ({len(text)} chars)")
            
            response_data = {
                "message": f"File '{file.filename}' processed successfully",
                "filename": file.filename,
                "text_length": len(text),
                "fraud_warnings": fraud_warnings
            }
            
            return jsonify(response_data)
            
        except Exception as extract_error:
            try:
                os.remove(file_path)
            except:
                pass
            
            print(f"Extraction error: {str(extract_error)}")
            import traceback
            traceback.print_exc()
            
            return jsonify({"error": f"Processing error: {str(extract_error)}"}), 500
            
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

@app.route('/chat', methods=['POST'])
def chat():
    # ═══════════════════════════════════════════════════════════════════
    # CRITICAL FIX: Declare global variables at the start
    # ═══════════════════════════════════════════════════════════════════
    global gemini_pro_available, hf_available, groq_available

    try:
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        session_id = session['session_id']
        user_name = session.get('user_name')
        
        has_document = session_id in DOCUMENT_STORE
        print(f"📊 Session ID: {session_id}")
        print(f"📄 Document available: {has_document}")
        
        data = request.json
        user_message = data.get("message", "").strip()
        
        if not user_message:
            return jsonify({"response": "Please enter a message."}), 400
        
        detected_language = detect_language(user_message)
        print(f"🌐 Detected Language: {detected_language}")
        
        if 'user_language' not in session or detected_language != 'mixed':
            session['user_language'] = detected_language
        
        user_language = session.get('user_language', 'english')
        
        session['system_instruction'] = initialize_messages(
            session_id=session_id, 
            user_name=user_name,
            user_language=user_language
        )
        
        if 'messages' not in session:
            session['messages'] = []
        
        name_match = re.search(r"(?:i am|my name is|maz nav|mi|माझे नाव|मी)\s+([a-zA-Zअ-ॲ]+)", user_message.lower())
        if name_match:
            detected_name = name_match.group(1).capitalize()
            ignored_words = ['looking', 'searching', 'asking', 'law', 'mitra', 'bot', 'ai', 'आहे', 'होते']
            
            if detected_name.lower() not in ignored_words:
                session['user_name'] = detected_name
                session.modified = True
                print(f"✅ User identified: {detected_name}")
        
        session['messages'].append({"role": "user", "content": user_message})
        
        if 'conversation_history' not in session:
            session['conversation_history'] = []
        
        history_entry = {
            'id': str(uuid.uuid4()),
            'question': user_message,
            'timestamp': datetime.now().isoformat(),
            'preview': user_message[:60] + '...' if len(user_message) > 60 else user_message,
            'language': detected_language
        }
        
        session['conversation_history'].insert(0, history_entry)
        
        if len(session['conversation_history']) > 100:
            session['conversation_history'] = session['conversation_history'][:100]
        
        bot_response = None
        used_model = None
        
        # ═══════════════════════════════════════════════════════════════════
        # TRY 1ST PRIORITY: GEMINI
        # ═══════════════════════════════════════════════════════════════════
        if gemini_client and gemini_pro_available and not bot_response:
            try:
                print("🌟 Attempting 1st PRIORITY: Gemini...")
                
                system_instruction = session.get('system_instruction', '')
                conversation_text = system_instruction + "\n\n"
                
                for msg in session['messages']:
                    if msg['role'] == 'user':
                        conversation_text += f"User: {msg['content']}\n\n"
                    elif msg['role'] == 'assistant':
                        conversation_text += f"Assistant: {msg['content']}\n\n"
                
                model_name = getattr(gemini_client, 'working_model', 'gemini-1.5-pro')
                
                response = gemini_client.models.generate_content(
                    model=model_name,
                    contents=conversation_text
                )
                bot_response = response.text
                used_model = f"1st PRIORITY: Gemini ({model_name}) ⭐"
                print(f"✅ SUCCESS: Response from {model_name}")
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower() or "RESOURCE_EXHAUSTED" in error_str:
                    print(f"⚠️ Gemini quota exceeded, switching to backup...")
                    gemini_pro_available = False
                else:
                    print(f"⚠️ 1st Priority failed: {e}")
        
        # ═══════════════════════════════════════════════════════════════════
        # TRY 2ND PRIORITY: HUGGING FACE INFERENCE API
        # ═══════════════════════════════════════════════════════════════════
        if hf_available and not bot_response:
            try:
                print("🟡 Attempting 2nd PRIORITY: Hugging Face (router)...")
                
                # Build OpenAI-style messages for HF router
                hf_messages = [{"role": "system", "content": session.get('system_instruction', '')}]
                for msg in session['messages']:
                    if msg['role'] in ('user', 'assistant'):
                        hf_messages.append({"role": msg['role'], "content": msg['content']})
                
                hf_resp = requests.post(
                    "https://router.huggingface.co/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {HUGGINGFACE_API_KEY.strip()}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": HF_MODEL_ID,
                        "messages": hf_messages,
                        "max_tokens": 800,
                        "temperature": 0.3
                    },
                    timeout=60
                )
                
                if hf_resp.ok:
                    data = hf_resp.json()
                    generated = None
                    if isinstance(data, dict):
                        choices = data.get("choices") or []
                        if choices:
                            msg = choices[0].get("message") or {}
                            generated = msg.get("content")
                    
                    if not generated:
                        generated = str(data)
                    
                    bot_response = generated.strip()
                    used_model = f"2nd PRIORITY: Hugging Face ({HF_MODEL_ID})"
                    print("✅ SUCCESS: Hugging Face router response")
                else:
                    print(f"⚠️ Hugging Face router error: {hf_resp.status_code} {hf_resp.text[:200]}")
            except Exception as e:
                print(f"⚠️ 2nd Priority (Hugging Face) failed: {e}")
        
        # ═══════════════════════════════════════════════════════════════════
        # TRY 3RD PRIORITY: GROQ (FREE & FAST)
        # ═══════════════════════════════════════════════════════════════════
        if groq_client and groq_available and not bot_response:
            try:
                print("🔵 Attempting 3rd PRIORITY: Groq...")
                
                openai_messages = [
                    {"role": "system", "content": session.get('system_instruction', '')}
                ] + session['messages']
                
                # Try multiple Groq models
                groq_models = [
                    "llama-3.3-70b-versatile",
                    "llama-3.1-70b-versatile",
                    "mixtral-8x7b-32768"
                ]
                
                for gmodel in groq_models:
                    try:
                        print(f"   🔹 Trying Groq: {gmodel}")
                        completion = groq_client.chat.completions.create(
                            model=gmodel,
                            messages=openai_messages,
                            temperature=0.3,
                            max_tokens=3000
                        )
                        bot_response = completion.choices[0].message.content
                        used_model = f"3rd PRIORITY: Groq ({gmodel})"
                        print(f"✅ SUCCESS: Groq {gmodel}")
                        break
                    except:
                        continue
                
            except Exception as e:
                print(f"⚠️ 3rd Priority failed: {e}")
        
        # ═══════════════════════════════════════════════════════════════════
        # IF ALL FAIL
        # ═══════════════════════════════════════════════════════════════════
        if not bot_response:
            error_msg = """⚠️ सर्व AI models सध्या उपलब्ध नाहीत.

**कारणे:**
• Gemini: Quota संपला
• OpenRouter: Rate limit/Connection issue
• Groq: Server busy

**उपाय:**
1. थोडा वेळ (5-10 मिनिटे) थांबा
2. नवीन **Groq API key** घ्या (विनामूल्य): https://console.groq.com/keys
3. Backend file मध्ये GROQ_API_KEY update करा
4. Server restart करा

**Groq सर्वोत्तम आहे:**
- 100% विनामूल्य
- खूप जलद
- No quota issues"""
            
            return jsonify({"response": error_msg}), 503
        
        session['messages'].append({"role": "assistant", "content": bot_response})
        
        if len(session['messages']) > 100:
            session['messages'] = session['messages'][-99:]
        
        session.modified = True
        
        print(f"✅ Response from: {used_model}")
        
        return jsonify({"response": bot_response})
            
    except Exception as e:
        print(f"❌ Chat error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"response": "⚠️ Server error. Please refresh and try again."}), 500

@app.route('/newchat', methods=['POST'])
def new_chat():
    try:
        session_id = session.get('session_id')
        user_name = session.get('user_name')
        user_language = session.get('user_language', 'english')
        
        session['messages'] = []
        session['system_instruction'] = initialize_messages(
            session_id=session_id, 
            user_name=user_name,
            user_language=user_language
        )
        session.modified = True
        
        return jsonify({
            "response": "New chat started",
            "conversations": []
        })
        
    except Exception as e:
        print(f"New chat error: {e}")
        return jsonify({"error": "Failed to start new chat"}), 500

@app.route('/conversations', methods=['GET'])
def get_conversations():
    if 'messages' not in session:
        return jsonify({"conversations": []})
    
    conversations = session['messages']
    return jsonify({"conversations": conversations})

@app.route('/history', methods=['GET'])
def get_history():
    if 'conversation_history' not in session:
        session['conversation_history'] = []
    
    return jsonify({"history": session['conversation_history']})

@app.route('/clear_document', methods=['POST'])
def clear_document():
    try:
        session_id = session.get('session_id')
        
        if session_id and session_id in DOCUMENT_STORE:
            del DOCUMENT_STORE[session_id]
            print(f"✅ Document cleared for session {session_id}")
        
        user_name = session.get('user_name')
        user_language = session.get('user_language', 'english')
        session['messages'] = []
        session['system_instruction'] = initialize_messages(
            session_id=session_id, 
            user_name=user_name,
            user_language=user_language
        )
        session.modified = True
        
        return jsonify({"message": "Document cleared successfully"})
        
    except Exception as e:
        print(f"Clear document error: {e}")
        return jsonify({"error": "Failed to clear document"}), 500

@app.route('/status', methods=['GET'])
def status():
    session_id = session.get('session_id', 'None')
    has_document = session_id in DOCUMENT_STORE if session_id else False
    
    api_status = []
    if gemini_pro_available:
        model_name = getattr(gemini_client, 'working_model', 'gemini-1.5-pro')
        api_status.append(f"1st: Gemini ({model_name}) ⭐")
    if hf_available:
        api_status.append(f"2nd: Hugging Face ({HF_MODEL_ID}) ✅")
    if groq_available:
        api_status.append("3rd: Groq ⚡")
    
    if not api_status:
        api_status.append("⚠️ No APIs active")
    
    user_language = session.get('user_language', 'english')
    language_display = {
        'marathi': 'मराठी 🇮🇳',
        'hindi': 'हिंदी 🇮🇳',
        'english': 'English 🇬🇧',
        'mixed': 'Mixed'
    }
    
    return jsonify({
        "status": "online",
        "ocr_available": OCR_AVAILABLE and TESSERACT_INSTALLED,
        "pymupdf_available": PYMUPDF_AVAILABLE,
        "session_id": session_id,
        "document_uploaded": has_document,
        "user_name": session.get('user_name', 'Not set'),
        "user_language": language_display.get(user_language, 'English'),
        "message_count": len(session.get('messages', [])),
        "available_apis": api_status,
        "priority_order": "1st: Gemini → 2nd: Hugging Face → 3rd: Groq"
    })

# ==================================================================================
# 10. APPLICATION ENTRY POINT
# ==================================================================================
if __name__ == '__main__':
    print("=" * 80)
    print("🚀 LAW MITRA - FIXED WITH GROQ (FREE & FAST)")
    print("=" * 80)
    print(f"✅ Server starting on: http://localhost:5000")
    print("=" * 80)
    
    app.run(debug=True, port=5000, host='0.0.0.0')

