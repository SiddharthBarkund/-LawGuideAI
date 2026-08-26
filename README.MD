# ⚖️ LawGuideAI — Intelligent Indian Legal Assistant & Document Analyzer

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/Framework-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/AI-Google%20Gemini%202.5-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Google Gemini" />
  <img src="https://img.shields.io/badge/Backup%20AI-Groq%20⚡-F55036?style=for-the-badge&logo=groq&logoColor=white" alt="Groq" />
  <img src="https://img.shields.io/badge/Search-BM25%20RAG-orange?style=for-the-badge" alt="RAG" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
</p>

---

**LawGuideAI** is an advanced, production-ready AI Legal Assistant designed to provide instant, accessible, and structured legal guidance tailored to **Indian Law**. 

Equipped with a **RAG (Retrieval-Augmented Generation)** knowledge base, multi-model fallback orchestration (**Google Gemini 2.5 Flash**, **Groq**, and **Hugging Face**), multilingual conversation support (**English, Hindi, Marathi**), and an automated **Legal Document & Fraud Analyzer**, LawGuideAI bridges the gap between complex legal jargon and everyday citizens.

---

## 🌟 Key Features

### 🧠 1. Multi-Tier AI Engine & Auto-Failover
- **Primary Engine**: **Google Gemini 2.5 Flash / Pro** for high-accuracy legal analysis and contextual reasoning.
- **Secondary & Tertiary Fallbacks**: **Hugging Face Router** and **Groq (Qwen 27B / Llama 3)** ensure **zero downtime** even if API quotas or limits are reached.
- **Token Streaming**: Real-time response streaming via Server-Sent Events (SSE) for instant responses.

### 📖 2. Indian Legal RAG Knowledge Base
- **2,674+ Indexed Legal Chunks** powered by a custom **BM25 ranking algorithm**.
- Built-in coverage of major Indian statutes and acts:
  - 🏛️ **Bharatiya Nyaya Sanhita (BNS)**
  - 📜 **Constitution of India (Sanvidhan / संविधान)**
  - 💻 **Information Technology Act, 2000**
  - 🛡️ **Protection of Human Rights Act, 1993**
  - 🥗 **Food Safety and Standards Act, 2006**
- Injects verified citations and act references directly into conversational answers.

### 🌐 3. Native Multilingual Support
- Automatic language detection and natural responses in:
  - 🇬🇧 **English**
  - 🇮🇳 **Hindi (हिंदी)**
  - 🇮🇳 **Marathi (मराठी)**

### 📄 4. Document Processing & OCR
- Extract and examine documents from **PDF**, **DOCX**, **TXT**, and images (**PNG**, **JPG**, **JPEG**).
- Integrated **Tesseract OCR** and **PyMuPDF** engines for optical character recognition on scanned contracts and notices.

### 🚨 5. Legal Fraud & Risk Analysis
- Heuristic and pattern analysis detecting suspicious terms, unfair clauses, unauthorized penalties, and high-risk demand notices.

### 🎙️ 6. Modern Interactive UI
- Clean, responsive glassmorphism interface with dark-mode accents.
- Markdown rendering via Marked.js, voice input capability, and persistent session management with SQLite.

---

## 📁 Project Architecture

The repository is organized into a clean 3-tier modular structure:

```text
LawGuideAI/
├── backend/                  # Python FastAPI application & AI services
│   ├── __init__.py
│   ├── app.py                # Server entry point, rate limiting, and API routing
│   ├── ai_engine.py          # Gemini & Groq multi-model fallback engine
│   ├── config.py             # App environment configuration & logging
│   ├── database.py           # SQLite database layer for chat persistence
│   ├── document_processor.py # PDF / DOCX extraction & Tesseract OCR
│   ├── prompts.py            # Indian legal system prompts & templates
│   ├── rag_engine.py         # BM25 RAG legal knowledge retrieval
│   └── utils.py              # Multilingual detection & fraud heuristics
├── frontend/                 # Client UI
│   ├── index.html            # Main web interface
│   └── app.js                # Frontend client logic & SSE streaming
├── data/                     # Legal knowledge base & database
│   ├── data_index.json       # Pre-indexed BM25 law search chunks
│   ├── law_mitra.db          # SQLite database (auto-generated)
│   └── *.pdf                 # Legal PDFs and reference acts
├── uploads/                  # Temporary file upload directory
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
├── run.bat                   # 1-Click Windows launch script
└── start.bat                 # Quick launch shortcut
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python 3.10+** installed ([Download Python](https://www.python.org/downloads/))
- **Git** installed ([Download Git](https://git-scm.com/))
- *(Optional)* **Tesseract-OCR** for scanned image OCR ([Download Tesseract](https://github.com/UB-Mannheim/tesseract/wiki))

### 2. Clone the Repository
```bash
git clone https://github.com/SiddharthBarkund/-LawGuideAI.git
cd -LawGuideAI
```

### 3. Create a Virtual Environment & Install Dependencies
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the `.env.example` file to `.env`:
```bash
copy .env.example .env     # Windows
cp .env.example .env       # Linux/macOS
```
Open `.env` and add your API keys:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
HUGGINGFACE_API_KEY=your_hf_api_key_here
HF_MODEL_ID=meta-llama/Meta-Llama-3-8B-Instruct
```
> 💡 **Get Free Keys**:
> - [Google AI Studio (Gemini)](https://aistudio.google.com/)
> - [Groq Console](https://console.groq.com/)

---

## 💻 Running the Application

### Option A: 1-Click Launch (Windows)
Double-click **`run.bat`** or run:
```cmd
run.bat
```
*This automatically activates `.venv`, verifies Python, starts the server, and opens `http://localhost:5000` in your browser.*

### Option B: Manual Command Line
```bash
python -m backend.app
```
Then visit **`http://localhost:5000`** in your browser.

---

## 🔌 API Endpoints Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Serves the web interface (`frontend/index.html`) |
| `/app.js` | `GET` | Serves frontend client script |
| `/chat` | `POST` | Standard chat completion endpoint |
| `/chat/stream` | `POST` | Real-time Server-Sent Events (SSE) streaming chat |
| `/upload` | `POST` | Document upload & OCR analysis (PDF, DOCX, Images) |
| `/status` | `GET` | Real-time system health, active AI models, & OCR availability |
| `/conversations` | `GET` | Retrieve saved chat conversations |
| `/clear` | `POST` | Clear active conversation history |

---

## 🛠️ Tech Stack

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/), [SlowAPI](https://github.com/laurentS/slowapi) (Rate Limiting)
- **AI / LLM Orchestration**: [Google GenAI SDK](https://github.com/googleapis/python-genai), [Groq API](https://groq.com/), [OpenAI SDK](https://github.com/openai/openai-python), [Hugging Face](https://huggingface.co/)
- **Document & OCR Engines**: [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/), [PyPDF2](https://pypdf2.readthedocs.io/), [python-docx](https://python-docx.readthedocs.io/), [Pytesseract](https://pypi.org/project/pytesseract/), [Pillow](https://pillow.readthedocs.io/)
- **Database & Storage**: [SQLite3](https://www.sqlite.org/) with thread-safe session handling
- **Frontend**: Vanilla HTML5, Modern CSS3 (Glassmorphism), JavaScript (ES6+), [Marked.js](https://marked.js.org/), [Font Awesome](https://fontawesome.com/)

---

## 👨‍💻 Author

**Siddharth Barkund**
- 🎓 B.Tech in Artificial Intelligence & Machine Learning
- 💡 Passionate about Agentic AI, NLP, and Full-Stack Engineering
- 🌐 GitHub: [@SiddharthBarkund](https://github.com/SiddharthBarkund)

---

## ⭐ Support & Contributing

Contributions, issues, and feature requests are welcome!
- If you find this project helpful, please give it a **⭐ on GitHub**!
- Feel free to fork the repository and submit a Pull Request.

---

## ⚖️ Legal Disclaimer

> **IMPORTANT**: **LawGuideAI** is designed exclusively for educational, informational, and preliminary guidance purposes. It does **not** constitute legal advice and does not create an attorney-client relationship. Users should consult a qualified advocate or legal professional for formal legal proceedings or binding advice.