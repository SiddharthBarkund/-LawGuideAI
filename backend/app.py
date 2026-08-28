import os
import re
import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, File, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import (
    OCR_AVAILABLE,
    TESSERACT_INSTALLED,
    PYMUPDF_AVAILABLE,
    HF_MODEL_ID,
    logger
)
from .database import (
    save_document,
    get_document,
    delete_document,
    save_chat_message,
    get_chat_history,
    clear_chat_history,
    get_conversations_list,
    save_conversation
)
from .document_processor import extract_text_from_file
from .utils import detect_language, analyze_document_for_fraud
from .prompts import initialize_messages
from .rag_engine import build_or_load_data_index
from . import rag_engine
from . import ai_engine

# Initialize FastAPI App
app = FastAPI(title="Law Mitra AI Server", version="2.0.0")

# Setup CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Session Middleware (Compatible with client-side signed cookies)
app.add_middleware(
    SessionMiddleware, 
    secret_key="law_mitra_2026_secure_session_key"
)

# Setup Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded for IP: {request.client.host}")
    return JSONResponse(
        status_code=429,
        content={"response": "⏱️ Rate limit exceeded. Please wait a moment and try again."}
    )

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Build RAG search index on startup
build_or_load_data_index()

# ----------------------------------------------------------------------------------
# Request Schemas
# ----------------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str

# ----------------------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------------------

@app.get("/")
async def read_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(index_path):
        index_path = os.path.join(FRONTEND_DIR, "law_mitra.html")
    return FileResponse(index_path)


@app.get("/app.js")
async def read_js():
    return FileResponse(os.path.join(FRONTEND_DIR, "app.js"))


@app.get("/law_mitra.html")
async def read_law_mitra_html():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(index_path):
        index_path = os.path.join(FRONTEND_DIR, "law_mitra.html")
    return FileResponse(index_path)


@app.post("/upload")
@limiter.limit("5/minute")
async def upload_file(request: Request, file: UploadFile = File(...)):
    session = request.session
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    session_id = session["session_id"]

    try:
        ext = os.path.splitext(file.filename)[1].lower()
        allowed_extensions = [
            ".pdf",
            ".docx",
            ".txt",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".bmp",
        ]

        if ext not in allowed_extensions:
            if ext == ".doc":
                return JSONResponse(
                    status_code=400,
                    content={"error": "Old .doc format not supported. Please convert to .docx"}
                )
            return JSONResponse(
                status_code=400,
                content={"error": f"Unsupported file type: {ext}"}
            )

        upload_dir = os.path.join(os.getcwd(), "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        safe_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(upload_dir, safe_filename)

        # Write uploaded file asynchronously
        try:
            with open(file_path, "wb") as f:
                f.write(await file.read())
        except Exception as save_error:
            logger.error(f"File write error: {save_error}")
            return JSONResponse(
                status_code=500,
                content={"error": f"File save error: {str(save_error)}"}
            )

        try:
            text, error_msg = extract_text_from_file(file_path)

            try:
                os.remove(file_path)
            except Exception:
                pass

            if error_msg:
                return JSONResponse(status_code=400, content={"error": error_msg})

            if not text or not text.strip():
                return JSONResponse(status_code=400, content={"error": "No extractable text found in file"})

            fraud_warnings = analyze_document_for_fraud(text)

            # Persist upload in SQLite database
            save_document(session_id, file.filename, text, fraud_warnings)

            # Re-initialize session settings
            user_name = session.get("user_name")
            user_language = session.get("user_language", "english")
            
            # Save conversation metadata
            save_conversation(
                session_id, 
                user_name=user_name, 
                user_language=user_language, 
                preview=f"Uploaded: {file.filename}"
            )
            
            # Save upload event in chat logs
            save_chat_message(
                session_id, 
                "system", 
                f"📄 Document '{file.filename}' processed successfully."
            )

            logger.info(f"✅ Document stored in SQLite for session {session_id} ({len(text)} chars)")

            response_data = {
                "message": f"File '{file.filename}' processed successfully",
                "filename": file.filename,
                "text_length": len(text),
                "fraud_warnings": fraud_warnings,
            }

            return response_data

        except Exception as extract_error:
            try:
                os.remove(file_path)
            except Exception:
                pass
            logger.error(f"Extraction error: {extract_error}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Processing error: {str(extract_error)}"}
            )

    except Exception as e:
        logger.error(f"Upload execution error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Upload failed: {str(e)}"}
        )


@app.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request, chat_req: ChatRequest):
    session = request.session
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    session_id = session["session_id"]
    user_name = session.get("user_name")

    user_message = chat_req.message.strip()
    if not user_message:
        return JSONResponse(status_code=400, content={"response": "Please enter a message."})

    detected_language = detect_language(user_message)
    logger.info(f"🌐 Detected language for query: {detected_language}")

    if "user_language" not in session or detected_language != "mixed":
        session["user_language"] = detected_language
    user_language = session.get("user_language", "english")

    # 1. Save user query in chat logs
    save_chat_message(session_id, "user", user_message)

    # 2. Extract name identifiers
    name_match = re.search(
        r"(?:i am|my name is|maz nav|mi|माझे नाव|मी)\s+([a-zA-Zअ-ॲ]+)",
        user_message.lower(),
    )
    if name_match:
        detected_name = name_match.group(1).capitalize()
        ignored_words = ["looking", "searching", "asking", "law", "mitra", "bot", "ai", "आहे", "होते"]
        if detected_name.lower() not in ignored_words:
            session["user_name"] = detected_name
            save_conversation(session_id, user_name=detected_name, user_language=user_language)
            logger.info(f"✅ User identified name: {detected_name}")

    # 3. Retrieve Law context
    law_context = ""
    if rag_engine.law_search_engine:
        try:
            logger.info(f"🔍 Searching local laws for query: '{user_message}'")
            results = rag_engine.law_search_engine.search(user_message, top_n=3)
            if results:
                logger.info(f"   🎯 Found {len(results)} relevant law segments")
                law_context = "═══════════════════════════════════════════════════════════════\n🔴 LOCAL REFERENCED LAW CONTEXT (Indian Law PDFs)\n═══════════════════════════════════════════════════════════════\n"
                law_context += "Use the following legal sections from the official documents if they are relevant to the question. Always mention the source file name and page number when referencing them.\n\n"
                for r in results:
                    law_context += f"📖 Source: {r['source']} (Page {r['page']}) (Relevance Score: {r['score']:.2f})\nContent:\n{r['text']}\n\n"
                law_context += "═══════════════════════════════════════════════════════════════\n"
        except Exception as search_err:
            logger.error(f"⚠️ Law search failed: {search_err}")

    # 4. Generate prompts system instruction
    system_instruction = initialize_messages(
        session_id=session_id, user_name=user_name, user_language=user_language, law_context=law_context
    )

    # 5. Fetch persistent chat history logs from SQLite
    history = get_chat_history(session_id)

    # 6. SSE streaming generators logic
    def event_stream():
        accumulated_text = ""
        try:
            for chunk in ai_engine.generate_bot_response_stream(history, system_instruction):
                yield chunk
                accumulated_text += chunk
        finally:
            # Re-verify and save response in chat logs
            if accumulated_text:
                save_chat_message(session_id, "assistant", accumulated_text)
                # Save metadata update
                save_conversation(
                    session_id, 
                    user_name=session.get("user_name"), 
                    user_language=user_language, 
                    preview=user_message[:60]
                )

    return StreamingResponse(event_stream(), media_type="text/plain")


@app.post("/newchat")
async def new_chat(request: Request):
    try:
        session = request.session
        session_id = session.get("session_id")
        if session_id:
            clear_chat_history(session_id)
            logger.info(f"🧹 Chat cleared for session {session_id}")

        return {"response": "New chat started", "conversations": []}
    except Exception as e:
        logger.error(f"New chat error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to start new chat"})


@app.get("/conversations")
async def get_conversations(request: Request):
    session = request.session
    session_id = session.get("session_id")
    if not session_id:
        return {"conversations": []}

    history = get_chat_history(session_id)
    return {"conversations": history}


@app.get("/history")
async def get_history(request: Request):
    history_list = get_conversations_list()
    return {"history": history_list}


@app.post("/clear_document")
async def clear_document_route(request: Request):
    try:
        session = request.session
        session_id = session.get("session_id")
        if session_id:
            delete_document(session_id)
            logger.info(f"✅ Document deleted for session {session_id}")
        
        return {"message": "Document cleared successfully"}
    except Exception as e:
        logger.error(f"Clear document route error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to clear document"})


@app.get("/status")
async def get_status(request: Request):
    session = request.session
    session_id = session.get("session_id", "None")
    
    doc_data = get_document(session_id) if session_id else None
    has_document = doc_data is not None

    api_status = []
    if ai_engine.gemini_pro_available:
        model_name = getattr(ai_engine.gemini_client, "working_model", "gemini-2.5-flash")
        api_status.append(f"1st: Gemini ({model_name}) ⭐")
    if ai_engine.hf_available:
        api_status.append(f"2nd: Hugging Face ({HF_MODEL_ID}) ✅")
    if ai_engine.groq_available:
        api_status.append("3rd: Groq ⚡")

    if not api_status:
        api_status.append("⚠️ No APIs active")

    user_language = session.get("user_language", "english")
    language_display = {
        "marathi": "मराठी 🇮🇳",
        "hindi": "हिंदी 🇮🇳",
        "english": "English 🇬🇧",
        "mixed": "Mixed",
    }

    messages = get_chat_history(session_id) if session_id else []

    return {
        "status": "online",
        "ocr_available": OCR_AVAILABLE and TESSERACT_INSTALLED,
        "pymupdf_available": PYMUPDF_AVAILABLE,
        "session_id": session_id,
        "document_uploaded": has_document,
        "user_name": session.get("user_name", "Not set"),
        "user_language": language_display.get(user_language, "English"),
        "message_count": len(messages),
        "available_apis": api_status,
        "priority_order": "1st: Gemini → 2nd: Hugging Face → 3rd: Groq",
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn Server...")
    uvicorn.run("backend.app:app", host="0.0.0.0", port=5000, reload=True)

