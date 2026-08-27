import requests
from openai import OpenAI
from .config import (
    GOOGLE_API_KEY,
    HUGGINGFACE_API_KEY,
    HF_MODEL_ID,
    GROQ_API_KEY,
    GOOGLE_GENAI_AVAILABLE,
    logger
)

if GOOGLE_GENAI_AVAILABLE:
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        pass

# Global engine status states
gemini_client = None
gemini_pro_available = False
hf_available = False
groq_client = None
groq_available = False

def initialize_ai_clients():
    global gemini_client, gemini_pro_available, hf_available, groq_client, groq_available

    # 1. Google Gemini SDK Setup
    if GOOGLE_GENAI_AVAILABLE:
        if GOOGLE_API_KEY and GOOGLE_API_KEY != "PASTE_YOUR_GEMINI_KEY_HERE":
            try:
                gemini_client = genai.Client(api_key=GOOGLE_API_KEY.strip())
                raw_models = [m.name.replace("models/", "") for m in gemini_client.models.list()]
                preferred_models = [
                    "gemini-2.5-flash",
                    "gemini-2.5-pro",
                    "gemini-flash-latest",
                    "gemini-pro-latest",
                ]
                models_to_test = [m for m in preferred_models if m in raw_models]
                if not models_to_test:
                    models_to_test = [m for m in raw_models if "gemini" in m.lower() and "tts" not in m.lower()]

                working_model = None
                gemini_quota_exceeded = False

                for pref_model in models_to_test:
                    try:
                        logger.info(f"🧪 Testing: {pref_model}")
                        test_response = gemini_client.models.generate_content(
                            model=pref_model, contents="Test"
                        )
                        working_model = pref_model
                        gemini_pro_available = True
                        gemini_client.working_model = working_model
                        logger.info(f"✅ 1st PRIORITY: Google Gemini ({working_model}) - ACTIVE")
                        break
                    except Exception as e:
                        error_str = str(e)
                        if (
                            "429" in error_str
                            or "quota" in error_str.lower()
                            or "RESOURCE_EXHAUSTED" in error_str
                        ):
                            logger.warning("⚠️ Gemini Quota Exceeded. Will use backup APIs.")
                            gemini_quota_exceeded = True
                            break
                        logger.warning(f"   ❌ Failed: {error_str[:80]}")
                        continue


                if not working_model:
                    if gemini_quota_exceeded:
                        logger.warning("⚠️ Gemini quota exhausted - will use backup APIs")
                    else:
                        logger.warning("⚠️ No working Gemini model found")
                    gemini_pro_available = False

            except Exception as e:
                logger.error(f"⚠️ Google Gemini setup failed: {e}")
                gemini_client = None
                gemini_pro_available = False
        else:
            logger.warning("⚠️ Gemini API key not set")
    else:
        logger.warning("⚠️ Install: pip install google-genai")

    # 2. Hugging Face Router Setup
    if HUGGINGFACE_API_KEY and HUGGINGFACE_API_KEY != "PASTE_YOUR_HF_API_KEY_HERE":
        try:
            logger.info("🧪 Testing Hugging Face connection (router API)...")
            test_resp = requests.post(
                "https://router.huggingface.co/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {HUGGINGFACE_API_KEY.strip()}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": HF_MODEL_ID,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 8,
                },
                timeout=20,
            )
            if test_resp.ok:
                hf_available = True
                logger.info(f"✅ 2nd PRIORITY: Hugging Face - ACTIVE ({HF_MODEL_ID})")
            else:
                logger.warning(f"⚠️ Hugging Face test failed: {test_resp.status_code} {test_resp.text[:120]}")
        except Exception as e:
            logger.error(f"⚠️ Hugging Face setup failed: {e}")
    else:
        logger.info("⚠️ Hugging Face not configured (Optional)")

    # 3. Groq Setup
    if GROQ_API_KEY and GROQ_API_KEY != "PASTE_YOUR_GROQ_KEY_HERE":
        try:
            groq_client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=GROQ_API_KEY.strip()
            )
            logger.info("🧪 Testing Groq connection...")
            
            preferred_groq_models = [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "qwen/qwen3.6-27b",
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
                "llama3-70b-8192",
                "llama3-8b-8192",
                "mixtral-8x7b-32768",
            ]
            
            working_groq_model = None
            try:
                available_models = [m.id for m in groq_client.models.list().data]
                # Try preferred models in order
                for pm in preferred_groq_models:
                    if pm in available_models:
                        working_groq_model = pm
                        break
                if not working_groq_model and available_models:
                    # Pick first non-whisper, non-guard model
                    for am in available_models:
                        if "whisper" not in am.lower() and "guard" not in am.lower():
                            working_groq_model = am
                            break
            except Exception:
                pass

            if not working_groq_model:
                working_groq_model = preferred_groq_models[0]

            test_response = groq_client.chat.completions.create(
                model=working_groq_model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10,
                timeout=15,
            )
            groq_client.working_model = working_groq_model
            groq_available = True
            logger.info(f"✅ 3rd PRIORITY: Groq ({working_groq_model}) - ACTIVE")
        except Exception as test_error:
            logger.warning(f"⚠️ Groq test failed: {test_error}")
            groq_available = False
            groq_client = None
    else:
        logger.info("⚠️ Groq not configured (Optional)")

# Automatically initialize on import
initialize_ai_clients()

# ----------------------------------------------------------------------------------
# Summarization Helpers
# ----------------------------------------------------------------------------------
def summarize_history(messages):
    """
    Summarizes all but the last 4 messages in history to keep token counts small.
    """
    if len(messages) <= 6:
        return messages

    to_summarize = messages[:-4]
    to_keep = messages[-4:]

    # Parse existing system summaries if any
    summary_prefix = ""
    if to_summarize[0]["role"] == "system" and "Summary of previous conversation" in to_summarize[0]["content"]:
        summary_prefix = to_summarize[0]["content"] + "\n\n"
        to_summarize = to_summarize[1:]

    # Concatenate message logs for summarization
    text_to_summarize = summary_prefix
    for msg in to_summarize:
        role_name = "User" if msg["role"] == "user" else "Assistant"
        text_to_summarize += f"{role_name}: {msg['content']}\n\n"

    logger.info("⚡ Active history size exceeded threshold. Running summarizer...")
    
    summary_prompt = (
        "Summarize the following Indian legal consultation history between a user and an AI assistant in under 150 words. "
        "Highlight the primary legal query, key details shared by the user, and previous advice given by the assistant:\n\n"
        f"{text_to_summarize}"
    )

    summary_text = None

    # Call Gemini first
    if gemini_client and gemini_pro_available:
        try:
            model_name = getattr(gemini_client, "working_model", "gemini-1.5-pro")
            response = gemini_client.models.generate_content(
                model=model_name, contents=summary_prompt
            )
            summary_text = response.text
        except Exception as e:
            logger.error(f"Summarization failed with Gemini: {e}")

    # Fallback to Groq
    if not summary_text and groq_client and groq_available:
        try:
            groq_model = getattr(groq_client, "working_model", "qwen/qwen3.6-27b")
            completion = groq_client.chat.completions.create(
                model=groq_model,
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=300,
            )
            summary_text = completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Summarization failed with Groq: {e}")

    if summary_text:
        logger.info(f"✅ Conversation summarized successfully: {len(summary_text)} chars")
        return [
            {"role": "system", "content": f"Summary of previous conversation:\n{summary_text.strip()}"}
        ] + to_keep
    
    logger.warning("⚠️ Summarization failed across all endpoints. Using raw history logs.")
    return messages

# ----------------------------------------------------------------------------------
# LLM Response Generation (Standard Call)
# ----------------------------------------------------------------------------------
def generate_bot_response(messages, system_instruction):
    global gemini_pro_available, hf_available, groq_available, gemini_client, groq_client

    # Apply history summarization before making calls
    messages = summarize_history(messages)

    bot_response = None
    used_model = None

    # TRY GEMINI
    if gemini_client and gemini_pro_available and not bot_response:
        try:
            logger.info("🌟 Attempting 1st PRIORITY: Gemini...")
            conversation_text = system_instruction + "\n\n"

            for msg in messages:
                role_name = "User" if msg["role"] == "user" else "Assistant"
                conversation_text += f"{role_name}: {msg['content']}\n\n"

            model_name = getattr(gemini_client, "working_model", "gemini-2.5-flash")
            response = gemini_client.models.generate_content(
                model=model_name, contents=conversation_text
            )
            bot_response = response.text
            used_model = f"1st PRIORITY: Gemini ({model_name}) ⭐"
            logger.info(f"✅ SUCCESS: Response from {model_name}")

        except Exception as e:
            error_str = str(e)
            if (
                "429" in error_str
                or "quota" in error_str.lower()
                or "RESOURCE_EXHAUSTED" in error_str
            ):
                logger.warning("⚠️ Gemini quota exceeded, switching to backup...")
                gemini_pro_available = False
            else:
                logger.error(f"⚠️ 1st Priority failed: {e}")

    # TRY HUGGING FACE
    if hf_available and not bot_response:
        try:
            logger.info("🟡 Attempting 2nd PRIORITY: Hugging Face (router)...")
            hf_messages = [
                {"role": "system", "content": system_instruction}
            ]
            for msg in messages:
                if msg["role"] in ("user", "assistant", "system"):
                    hf_messages.append(
                        {"role": msg["role"], "content": msg["content"]}
                    )

            hf_resp = requests.post(
                "https://router.huggingface.co/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {HUGGINGFACE_API_KEY.strip()}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": HF_MODEL_ID,
                    "messages": hf_messages,
                    "max_tokens": 800,
                    "temperature": 0.3,
                },
                timeout=60,
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
                logger.info("✅ SUCCESS: Hugging Face router response")
            else:
                logger.warning(f"⚠️ Hugging Face router error: {hf_resp.status_code} {hf_resp.text[:200]}")
        except Exception as e:
            logger.error(f"⚠️ 2nd Priority (Hugging Face) failed: {e}")

    # TRY GROQ
    if groq_client and groq_available and not bot_response:
        try:
            logger.info("🔵 Attempting 3rd PRIORITY: Groq...")
            openai_messages = [
                {"role": "system", "content": system_instruction}
            ]
            for m in messages:
                role = m["role"]
                if role not in ("system", "user", "assistant"):
                    role = "user"
                openai_messages.append({"role": role, "content": m["content"]})

            detected_model = getattr(groq_client, "working_model", "qwen/qwen3.6-27b")
            groq_models = [detected_model, "llama-3.3-70b-versatile", "llama-3.1-8b-instant", "qwen/qwen3.6-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama3-70b-8192", "mixtral-8x7b-32768"]
            # Deduplicate while preserving order
            groq_models = list(dict.fromkeys(groq_models))

            for gmodel in groq_models:
                try:
                    logger.info(f"   🔹 Trying Groq: {gmodel}")
                    completion = groq_client.chat.completions.create(
                        model=gmodel,
                        messages=openai_messages,
                        temperature=0.3,
                        max_tokens=3000,
                    )
                    bot_response = completion.choices[0].message.content
                    used_model = f"3rd PRIORITY: Groq ({gmodel})"
                    logger.info(f"✅ SUCCESS: Groq {gmodel}")
                    break
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"⚠️ 3rd Priority failed: {e}")

    return bot_response, used_model

# ----------------------------------------------------------------------------------
# LLM Response Generation (Event Streaming Call)
# ----------------------------------------------------------------------------------
def generate_bot_response_stream(messages, system_instruction):
    """
    Generates streaming responses yielding raw text chunks directly.
    """
    global gemini_pro_available, hf_available, groq_available, gemini_client, groq_client

    # Apply summarization checks
    messages = summarize_history(messages)

    # 1. Gemini Streaming
    if gemini_client and gemini_pro_available:
        try:
            logger.info("🌟 Attempting 1st PRIORITY: Gemini (Streaming)...")
            conversation_text = system_instruction + "\n\n"
            for msg in messages:
                role_name = "User" if msg["role"] == "user" else "Assistant"
                conversation_text += f"{role_name}: {msg['content']}\n\n"

            model_name = getattr(gemini_client, "working_model", "gemini-2.5-flash")
            response_stream = gemini_client.models.generate_content_stream(
                model=model_name, contents=conversation_text
            )
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
            return
        except Exception as e:
            logger.error(f"⚠️ Gemini streaming failed: {e}")
            if "429" in str(e) or "quota" in str(e).lower() or "RESOURCE_EXHAUSTED" in str(e):
                gemini_pro_available = False

    # 2. Groq Streaming
    if groq_client and groq_available:
        try:
            logger.info("🔵 Attempting 3rd PRIORITY: Groq (Streaming)...")
            openai_messages = [
                {"role": "system", "content": system_instruction}
            ]
            for m in messages:
                role = m["role"]
                if role not in ("system", "user", "assistant"):
                    role = "user"
                openai_messages.append({"role": role, "content": m["content"]})

            detected_model = getattr(groq_client, "working_model", "qwen/qwen3.6-27b")
            groq_models = [detected_model, "llama-3.3-70b-versatile", "llama-3.1-8b-instant", "qwen/qwen3.6-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama3-70b-8192", "mixtral-8x7b-32768"]
            groq_models = list(dict.fromkeys(groq_models))

            for gmodel in groq_models:
                try:
                    logger.info(f"   🔹 Trying Groq stream: {gmodel}")
                    completion_stream = groq_client.chat.completions.create(
                        model=gmodel,
                        messages=openai_messages,
                        temperature=0.3,
                        max_tokens=3000,
                        stream=True
                    )
                    for chunk in completion_stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                    return
                except Exception as inner_e:
                    logger.warning(f"Failed Groq stream {gmodel}: {inner_e}")
                    continue
        except Exception as e:
            logger.error(f"⚠️ Groq streaming failed: {e}")

    # Fallback to standard HTTP generation if both fail (yield as stream)
    fallback_response, fallback_model = generate_bot_response(messages, system_instruction)
    if fallback_response:
        logger.info(f"✅ Fallback to synchronous generation: {fallback_model}")
        yield fallback_response
    else:
        err_msg = "⚠️ AI server is busy or API limits exceeded. Please wait a few minutes and try again."
        yield err_msg
