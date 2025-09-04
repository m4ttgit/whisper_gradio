import gradio as gr
from dotenv import load_dotenv
import os
import groq
import threading
import uuid
import time
from typing import Optional
from fastapi import Body, Form, File, UploadFile, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from typing import List


class TranscriptionRequest(BaseModel):
    url: Optional[str] = None
    dir: str = ""
    lang: str = "Auto Detect"
    model_choice: str = "Local Whisper"
    local_model: str = "medium"
    groq_model: str = "whisper-large-v3"
    translate: bool = False


class TranscriptionRequestWrapper(BaseModel):
    data: List[TranscriptionRequest]


from fastapi.middleware.cors import CORSMiddleware

# FastAPI app for custom endpoints
fastapi_app = FastAPI()

# Configure CORS
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@fastapi_app.post("/gradio/handle_transcription")
async def handle_transcription_json_api(
    request: TranscriptionRequestWrapper = Body(...),
):
    job_ids = []
    for req in request.data:
        job_id = str(uuid.uuid4())
        with job_store_lock:
            job_store[job_id] = {
                "status": "pending",
                "result": None,
                "created_at": time.time(),
            }
        # Only support URL-based jobs for JSON API (file upload not supported via JSON)
        file = None
        # Start background thread
        thread = threading.Thread(
            target=background_transcription_job,
            args=(
                job_id,
                req.url,
                file,
                req.dir,
                req.lang,
                req.model_choice,
                req.local_model,
                req.groq_model,
                req.translate,
            ),
            daemon=True,
        )
        thread.start()
        job_ids.append(job_id)
    return {"job_ids": job_ids}


@fastapi_app.get("/gradio/job_status")
async def job_status(job_id: str):
    with job_store_lock:
        job = job_store.get(job_id)
        if not job:
            return JSONResponse(status_code=404, content={"status": "not_found"})
        if job["status"] == "complete":
            return {"status": "complete", "result": job["result"]}
        elif job["status"] == "failed":
            return {"status": "failed", "result": job["result"]}
        else:
            return {"status": "pending"}


def submit_transcription_job_api(
    url: str = Form(None),
    file: UploadFile = File(None),
    dir: str = Form(""),
    lang: str = Form("Auto Detect"),
    model_choice: str = Form("Local Whisper"),
    local_model: str = Form("medium"),
    groq_model: str = Form("whisper-large-v3"),
    translate: str = Form("false"),
):
    job_id = str(uuid.uuid4())
    with job_store_lock:
        job_store[job_id] = {
            "status": "pending",
            "result": None,
            "created_at": time.time(),
        }
    # Convert translate to boolean
    translate_bool = translate.lower() == "true"
    # Start background thread
    thread = threading.Thread(
        target=background_transcription_job,
        args=(
            job_id,
            url,
            file,
            dir,
            lang,
            model_choice,
            local_model,
            groq_model,
            translate_bool,
        ),
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id}


from transcription import (
    load_whisper_model,
    load_groq_client,
    transcribe_local_video,
    transcribe_video_from_url,
    transcribe_with_groq,
    DEFAULT_OUTPUT_DIR,
)
from utils import select_directory

# Global job store
job_store = {}
job_store_lock = threading.Lock()

load_dotenv()
load_whisper_model()
load_groq_client()

LANGUAGES = {
    "auto": "Auto Detect",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ru": "Russian",
    "pt": "Portuguese",
    "it": "Italian",
    "hi": "Hindi",
    "ar": "Arabic",
    "bn": "Bengali",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "th": "Thai",
    "pl": "Polish",
    "uk": "Ukrainian",
    "ro": "Romanian",
    "nl": "Dutch",
    "sv": "Swedish",
    "fi": "Finnish",
    "no": "Norwegian",
    "da": "Danish",
    "cs": "Czech",
    "el": "Greek",
    "hu": "Hungarian",
    "id": "Indonesian",
    "ms": "Malay",
    "fa": "Persian",
    "sw": "Swahili",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "kn": "Kannada",
    "ml": "Malayalam",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "ur": "Urdu",
    "he": "Hebrew",
    "bg": "Bulgarian",
    "hr": "Croatian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "et": "Estonian",
    "is": "Icelandic",
    "af": "Afrikaans",
    "mk": "Macedonian",
    "ne": "Nepali",
    "si": "Sinhala",
    "my": "Burmese",
    "km": "Khmer",
    "lo": "Lao",
    "mn": "Mongolian",
    "am": "Amharic",
    "yo": "Yoruba",
    "ig": "Igbo",
    "zu": "Zulu",
}


def get_language_code(language_name):
    for code, name in LANGUAGES.items():
        if name == language_name:
            return code
    return "auto"


def handle_transcription(
    url, file, dir, lang, model_choice, local_model, groq_model, translate
):
    lang_code = get_language_code(lang)
    safe_title = "downloaded_video"
    video_title_from_url = None

    if file is not None:
        safe_title = "".join(
            c
            for c in os.path.splitext(os.path.basename(file.name))[0]
            if c.isalnum() or c in (" ", "-", "_")
        ).strip()
    elif url:
        safe_title = "downloaded_video"

    # Use user-specified dir if provided, else default
    if dir:
        output_dir = dir
    else:
        output_dir = os.path.join(DEFAULT_OUTPUT_DIR, safe_title)

    if model_choice == "Local Whisper":
        if file is not None:
            text, srt_path, text_path, video_path_out = transcribe_local_video(
                file.name, output_dir, lang_code
            )
            return text, srt_path, text_path, video_path_out
        else:
            text, srt_path, text_path, video_path_out = transcribe_video_from_url(
                url, output_dir, lang_code
            )
            return text, srt_path, text_path, video_path_out
    else:
        import transcription

        if transcription.GROQ_CLIENT is None:
            return (
                "Groq API key missing or invalid. Please enter a valid key and restart.",
                None,
                None,
                None,
            )
        try:
            if file is not None:
                video_path = file.name
                result = transcribe_with_groq(
                    video_path, lang_code, groq_model, translate
                )
                safe_title = "".join(
                    c
                    for c in os.path.splitext(os.path.basename(file.name))[0]
                    if c.isalnum() or c in (" ", "-", "_")
                ).strip()
                # Use user-specified dir if provided, else default
                if dir:
                    output_dir = dir
                else:
                    output_dir = os.path.join(DEFAULT_OUTPUT_DIR, safe_title)
                from transcription import save_output_files, generate_srt_content

                srt_content = generate_srt_content(result)
                video_path_out, text_path, srt_path = save_output_files(
                    output_dir, safe_title, result["text"], srt_content, video_path
                )
                return result["text"], srt_path, text_path, video_path_out
            else:
                import tempfile, yt_dlp, shutil

                temp_dir = tempfile.mkdtemp()
                video_path = None
                try:
                    # Attempt to download the best format first
                    try:
                        with yt_dlp.YoutubeDL(
                            {
                                "format": "best",
                                "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
                            }
                        ) as ydl:
                            info = ydl.extract_info(url, download=True)
                            video_path = os.path.join(temp_dir, os.listdir(temp_dir)[0])
                    except yt_dlp.utils.DownloadError as e:
                        print(
                            f"Warning: Downloading best format failed: {e}. Attempting fallback to format 234."
                        )
                        # Fallback to format 234 if best fails
                        try:
                            with yt_dlp.YoutubeDL(
                                {
                                    "format": "234",  # Audio-only format
                                    "outtmpl": os.path.join(
                                        temp_dir, "%(title)s.%(ext)s"
                                    ),
                                }
                            ) as ydl:
                                info = ydl.extract_info(url, download=True)
                                video_path = os.path.join(
                                    temp_dir, os.listdir(temp_dir)[0]
                                )
                        except Exception as fallback_e:
                            raise fallback_e  # Re-raise if fallback also fails

                    if video_path is None:
                        raise Exception(
                            "Failed to download video using both 'best' and '234' formats."
                        )

                    result = transcribe_with_groq(
                        video_path, lang_code, groq_model, translate
                    )
                    video_title_from_url = info.get("title", "")
                    safe_title_url = "".join(
                        c
                        for c in video_title_from_url
                        if c.isalnum() or c in (" ", "-", "_")
                    ).strip()
                    if not safe_title_url:
                        safe_title_url = "".join(
                            c
                            for c in os.path.splitext(os.path.basename(video_path))[0]
                            if c.isalnum() or c in (" ", "-", "_")
                        ).strip()
                    safe_title = safe_title_url
                    # Use user-specified dir if provided, else default
                    if dir:
                        output_dir = dir
                    else:
                        output_dir = os.path.join(DEFAULT_OUTPUT_DIR, safe_title)
                    from transcription import save_output_files, generate_srt_content

                    srt_content = generate_srt_content(result)
                    video_path_out, text_path, srt_path = save_output_files(
                        output_dir,
                        safe_title,
                        result["text"],
                        srt_content,
                        video_path,
                    )
                    return result["text"], srt_path, text_path, video_path_out
                finally:
                    if temp_dir and os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
        except Exception as e:
            return f"Error during Groq API processing: {e}", None, None, None


def background_transcription_job(
    job_id, url, file, dir, lang, model_choice, local_model, groq_model, translate
):
    try:
        result = handle_transcription(
            url, file, dir, lang, model_choice, local_model, groq_model, translate
        )
        if isinstance(result, tuple):
            text, srt_path, text_path, video_path_out = result
            result_data = {
                "text": text,
                "srt_path": srt_path,
                "text_path": text_path,
                "video_path_out": video_path_out,
            }
        else:
            # Handle error case where result is just an error message
            result_data = {"error": result}

        with job_store_lock:
            job_store[job_id]["status"] = "complete"
            job_store[job_id]["result"] = result_data
    except Exception as e:
        with job_store_lock:
            job_store[job_id]["status"] = "failed"
            job_store[job_id]["result"] = {"error": str(e)}


with gr.Blocks(title="Video Transcriber") as app:
    gr.Markdown("# Multi-Language Video Transcriber")
    gr.Markdown("Enter a video URL or upload a video file to transcribe it.")

    def reload_groq_env_and_client():
        from dotenv import load_dotenv as ld
        import transcription

        ld(override=True)
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            try:
                client = groq.Groq(api_key=api_key)
                client.models.list()
                transcription.GROQ_CLIENT = client
                print(f"Reloaded Groq API key starts with: {api_key[:6]}...")
            except Exception as e:
                transcription.GROQ_CLIENT = None
                print(f"Failed to reload Groq API key: {e}")
        else:
            transcription.GROQ_CLIENT = None
            print("No Groq API key found in .env after reload.")

    def update_groq_api_key_ui(method_choice, api_key):
        import transcription
        import os as pyos

        reload_groq_env_and_client()

        visible = method_choice == "Groq API"
        status = ""
        groq_model_visible = visible
        groq_translate_visible = visible
        local_whisper_visible = method_choice == "Local Whisper"

        env_api_key = pyos.getenv("GROQ_API_KEY")

        if visible:
            if env_api_key:
                try:
                    print(
                        f"DEBUG: Validating env API key starts with: {env_api_key[:6]}..."
                    )
                    client = groq.Groq(api_key=env_api_key)
                    client.models.list()
                    transcription.GROQ_CLIENT = client
                    status = "Groq API key loaded from environment."
                    # Hide API key input if env key is valid
                    visible = False
                except Exception as e:
                    transcription.GROQ_CLIENT = None
                    status = f"Invalid Groq API key in environment: {e}"
                    visible = True
            elif api_key:
                try:
                    print(
                        f"DEBUG: Validating entered API key starts with: {api_key[:6]}..."
                    )
                    client = groq.Groq(api_key=api_key)
                    client.models.list()
                    transcription.GROQ_CLIENT = client
                    status = "Groq API key set."
                except Exception as e:
                    transcription.GROQ_CLIENT = None
                    status = f"Invalid Groq API key: {e}"
            else:
                transcription.GROQ_CLIENT = None
                status = "Please enter your Groq API key."
        else:
            transcription.GROQ_CLIENT = None
            status = ""

        return (
            gr.update(visible=visible),  # API key textbox
            status,  # Status message
            gr.update(visible=groq_model_visible),  # Groq model dropdown
            gr.update(visible=groq_translate_visible),  # Translate checkbox
            gr.update(visible=local_whisper_visible),  # Local Whisper dropdown
        )

    with gr.Row():
        with gr.Column():
            model_choice = gr.Radio(
                ["Local Whisper", "Groq API"],
                value="Local Whisper",
                label="Transcription Method",
            )
            groq_api_key = gr.Textbox(
                label="Groq API Key",
                placeholder="Enter your Groq API key",
                type="password",
                visible=False,
            )
            groq_api_status = gr.Markdown("")

            local_whisper_model = gr.Dropdown(
                ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
                value="medium",
                label="Local Whisper Model",
                visible=True,
            )
            groq_model = gr.Dropdown(
                [
                    "whisper-large-v3",
                    "whisper-large-v3-turbo",
                    "distil-whisper-large-v3-en",
                ],
                value="whisper-large-v3",
                label="Groq API Model",
                visible=False,
            )
            groq_translate = gr.Checkbox(
                label="Translate to English",
                value=False,
                visible=False,
            )
        with gr.Column():
            with gr.Tab("URL Input"):
                url_input = gr.Textbox(label="Video URL")
            with gr.Tab("File Upload"):
                file_input = gr.File(
                    label="Upload Video", file_types=["video"], file_count="single"
                )
            output_dir = gr.Textbox(
                label="Output Directory",
                placeholder="Select output folder",
                value="",
                interactive=False,
            )
            select_btn = gr.Button("📂 Browse Output Directory")
            language_dropdown = gr.Dropdown(
                choices=list(LANGUAGES.values()),
                value="Auto Detect",
                label="Transcription Language",
            )
            transcribe_btn = gr.Button("🎯 Transcribe Video")

            transcription = gr.Textbox(label="Transcription", lines=15)
            srt_file = gr.File(label="Download SRT")
            text_file = gr.File(label="Download Text")
            video_file = gr.File(label="Download Video")

    model_choice.change(
        fn=update_groq_api_key_ui,
        inputs=[model_choice, groq_api_key],
        outputs=[
            groq_api_key,
            groq_api_status,
            groq_model,
            groq_translate,
            local_whisper_model,
        ],
    )
    groq_api_key.change(
        fn=update_groq_api_key_ui,
        inputs=[model_choice, groq_api_key],
        outputs=[
            groq_api_key,
            groq_api_status,
            groq_model,
            groq_translate,
            local_whisper_model,
        ],
    )

    select_btn.click(
        fn=lambda: select_directory(DEFAULT_OUTPUT_DIR), outputs=output_dir
    )

    # For Gradio UI, keep synchronous for now
    transcribe_btn.click(
        fn=handle_transcription,
        inputs=[
            url_input,
            file_input,
            output_dir,
            language_dropdown,
            model_choice,
            local_whisper_model,
            groq_model,
            groq_translate,
        ],
        outputs=[transcription, srt_file, text_file, video_file],
    )

# Mount FastAPI app for custom endpoints
import uvicorn


def run_app():
    gradio_server = threading.Thread(
        target=app.launch,
        kwargs={"server_name": "127.0.0.1", "server_port": 7860},
        daemon=True,
    )
    gradio_server.start()
    uvicorn.run(fastapi_app, host="127.0.0.1", port=7861)


if __name__ == "__main__":
    run_app()
