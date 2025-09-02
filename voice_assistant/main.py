from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from asr import transcribe_audio
from llm import conv_manager
from tts import synthesize_speech

from router import try_route_llm_function_call, maybe_call_by_rules

app = FastAPI(title="Week6 Voice Agent with Function Calling", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat/")
async def chat_endpoint(file: UploadFile = File(...)):
    """
    Compatible with Week 3 frontend example:
    - Frontend uploads audio file to /chat/
    - Backend returns audio/wav, frontend plays directly
    """
    audio_bytes = await file.read()

    try:
        # 1) ASR
        user_text = await run_in_threadpool(transcribe_audio, audio_bytes)
        print(f"[ASR output] User said: {user_text}")  # Print recognized content
        
        # 2) LLM generates normally first (could be natural language or JSON function call)
        llm_raw = await run_in_threadpool(conv_manager.generate_response, user_text)
        print(f"[DEBUG] LLM generated reply: {llm_raw}")
        
        # 3) Routing:
        #    3.1 Priority: if llm_raw is {"function":..., "arguments":{...}} → parse and execute tool
        #    3.2 Otherwise: fallback by rules (math expressions / arXiv keywords etc.) to try triggering tools
        routed = try_route_llm_function_call(llm_raw)
        if routed is None:
            tool_hit = maybe_call_by_rules(user_text)
            reply_text = tool_hit if tool_hit is not None else llm_raw
        else:
            reply_text = routed

        # 4) Fallback: give understandable prompt when text is empty
        if not reply_text or not reply_text.strip():
            reply_text = "I didn't catch that. Could you please repeat?"
            print("[DEBUG] Empty reply after routing; used fallback.")

        print(f"[LLM/TOOLS output] Bot said: {reply_text}")
        
        # 5) TTS synthesis and return audio
        audio_path = await run_in_threadpool(synthesize_speech, reply_text)
        print(f"[TTS output] Audio file ready: {audio_path}")

        return FileResponse(audio_path, media_type="audio/wav", filename="reply.wav")

    except Exception as e:
        import traceback;traceback.print_exc()
        # To prevent frontend from crashing, return JSON error (could also return an "sorry" audio)
        return JSONResponse(status_code=500, content={"error": str(e)})

# === Endpoint for "homework log/debugging": returns JSON (text + optional audio URL) ===

from fastapi import Request
from urllib.parse import quote

@app.post("/chat_debug")
async def chat_debug_endpoint(request: Request, file: UploadFile = File(...)):
    """
    For Week 6 homework "test log" output:
    - Returns request_text / llm_raw / final_text
    - Also provides an audio download URL (browser can play directly)
    """
    audio_bytes = await file.read()
    

    try:
        # 1) ASR
        user_text = await run_in_threadpool(transcribe_audio, audio_bytes)
        print("[ASR output]", repr(user_text))

        # 2) LLM   
        llm_raw = await run_in_threadpool(conv_manager.generate_response, user_text)
        print("[LLM raw]", repr(llm_raw)) 

        # 3) Routing
        routed = try_route_llm_function_call(llm_raw)
        if routed is None:
            tool_hit = maybe_call_by_rules(user_text)
            final_text = tool_hit if tool_hit is not None else llm_raw
        else:
            final_text = routed

        if not final_text or not final_text.strip():
            final_text = "I didn't catch that. Could you please repeat?"
        print("[FINAL]", repr(final_text))

        # 4) TTS
        audio_path = await run_in_threadpool(synthesize_speech, final_text)
        print("[TTS] file:", audio_path) 

         # ✅ 关键：对 Windows 本地路径做 URL 编码，并用 url_for 生成完整可点链接
        encoded = quote(audio_path, safe="")  # 把 C:\... 转成 C%3A%5C...
        audio_url = str(request.url_for("get_audio")) + f"?path={encoded}"

        return {
            "request_text": user_text,
            "llm_raw": llm_raw,
            "final_text": final_text,
            "audio_url": audio_url
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

# === Provide audio file reading (to work with audio_url returned by /chat_debug) ===
@app.get("/audio", name="get_audio")
def get_audio(path: str):
    return FileResponse(path, media_type="audio/wav", filename="reply.wav")