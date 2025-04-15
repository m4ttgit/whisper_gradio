"""
Video Transcription Application with Gradio UI and FastAPI backend.

This module provides a web interface for transcribing videos using either
local Whisper models or the Groq API. It supports both file uploads and URL inputs.
"""

# Standard library imports
import os
import threading
import time
import uuid
import tempfile
import shutil
from typing import Dict, Any, Tuple, Optional, List, Union

# Third-party imports
import gradio as gr
import groq
import uvicorn
import yt_dlp
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, File, UploadFile, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Local imports
from transcription import (
    load_whisper_model,
    load_groq_client,
    transcribe_local_video,
    transcribe_video_from_url,
    transcribe_with_groq,
    save_output_files,
    generate_srt_content,
    DEFAULT_OUTPUT_DIR,
)
from utils import select_directory

# Initialize global variables
load_dotenv()
load_whisper_model()
load_groq_client()

# Global job store for async processing
job_store: Dict[str, Dict[str, Any]] = {}
job_store_lock = threading.Lock()

# FastAPI app for custom endpoints
fastapi_app = FastAPI()

# Language mapping dictionary
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


def get_language_code(language_name: str) -> str:
    """Convert language name to language code.
    
    Args:
        language_name: The full name of the language
        
    Returns:
        The language code or 'auto' if not found
    """
    for code, name in LANGUAGES.items():
        if name == language_name:
            return code
    return "auto"


def get_safe_title(file_path: Optional[str] = None, url_title: Optional[str] = None) -> str:
    """Generate a safe filename from a file path or URL title.
    
    Args:
        file_path: Path to the file
        url_title: Title extracted from URL
        
    Returns:
        A sanitized string safe for filenames
    """
    if file_path:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        return "".join(
            c for c in base_name if c.isalnum() or c in (" ", "-", "_")
        ).strip()
    elif url_title:
        return "".join(
            c for c in url_title if c.isalnum() or c in (" ", "-", "_")
        ).strip()
    return "downloaded_video"


def get_output_directory(user_dir: str, safe_title: str) -> str:
    """Determine the output directory for transcription files.
    
    Args:
        user_dir: User-specified directory
        safe_title: Safe title for subdirectory
        
    Returns:
        Path to the output directory
    """
    if user_dir:
        return os.path.join(user_dir, safe_title) if not os.path.isabs(safe_title) else user_dir
    return os.path.join(DEFAULT_OUTPUT_DIR, safe_title)


def handle_transcription(
    url: Optional[str],
    file: Optional[Any],
    dir: str,
    lang: str,
    model_choice: str,
    local_model: str,
    groq_model: str,
    translate: bool
) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """Handle video transcription using either local Whisper or Groq API.
    
    Args:
        url: URL of the video to transcribe
        file: Uploaded file object
        dir: Output directory
        lang: Language for transcription
        model_choice: 'Local Whisper' or 'Groq API'
        local_model: Local Whisper model size
        groq_model: Groq API model name
        translate: Whether to translate to English
        
    Returns:
        Tuple of (transcription text, SRT file path, text file path, video file path)
    """
    lang_code = get_language_code(lang)
    
    # Determine safe title and output directory
    if file is not None:
        safe_title = get_safe_title(file_path=file.name)
    elif url:
        safe_title = "downloaded_video"
    else:
        return "No input provided. Please upload a file or enter a URL.", None, None, None
    
    output_dir = get_output_directory(dir, safe_title)
    
    # Process with Local Whisper
    if model_choice == "Local Whisper":
        if file is not None:
            return transcribe_local_video(file.name, output_dir, lang_code)
        else:
            return transcribe_video_from_url(url, output_dir, lang_code)
    
    # Process with Groq API
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
            # Process local file with Groq
            video_path = file.name
            result = transcribe_with_groq(video_path, lang_code, groq_model, translate)
            safe_title = get_safe_title(file_path=file.name)
            output_dir = get_output_directory(dir, safe_title)
            
            srt_content = generate_srt_content(result)
            video_path_out, text_path, srt_path = save_output_files(
                output_dir, safe_title, result["text"], srt_content, video_path
            )
            return result["text"], srt_path, text_path, video_path_out
        else:
            # Process URL with Groq
            temp_dir = tempfile.mkdtemp()
            try:
                with yt_dlp.YoutubeDL({
                    "format": "best",
                    "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
                }) as ydl:
                    info = ydl.extract_info(url, download=True)
                    video_path = os.path.join(temp_dir, os.listdir(temp_dir)[0])
                    result = transcribe_with_groq(video_path, lang_code, groq_model, translate)
                    
                    video_title = info.get("title", "")
                    safe_title = get_safe_title(url_title=video_title) or get_safe_title(file_path=video_path)
                    output_dir = get_output_directory(dir, safe_title)
                    
                    srt_content = generate_srt_content(result)
                    video_path_out, text_path, srt_path = save_output_files(
                        output_dir, safe_title, result["text"], srt_content, video_path
                    )
                    return result["text"], srt_path, text_path, video_path_out
            finally:
                shutil.rmtree(temp_dir)
    except Exception as e:
        return f"Error during Groq API processing: {e}", None, None, None


def background_transcription_job(
    job_id: str,
    url: Optional[str],
    file: Optional[Any],
    dir: str,
    lang: str,
    model_choice: str,
    local_model: str,
    groq_model: str,
    translate: bool
) -> None:
    """Process transcription in a background thread.
    
    Args:
        job_id: Unique ID for the job
        url: URL of the video to transcribe
        file: Uploaded file object
        dir: Output directory
        lang: Language for transcription
        model_choice: 'Local Whisper' or 'Groq API'
        local_model: Local Whisper model size
        groq_model: Groq API model name
        translate: Whether to translate to English
    """
    try:
        # Use the same transcription logic but store results differently
        text, srt_path, text_path, video_path_out = handle_transcription(
            url, file, dir, lang, model_choice, local_model, groq_model, translate
        )
        
        result = {
            "text": text,
            "srt_path": srt_path,
            "text_path": text_path,
            "video_path_out": video_path_out,
        }
        
        # If there was an error, the text will contain the error message
        if text.startswith("Error") or text.startswith("Groq API key missing"):
            result = {"error": text}
            with job_store_lock:
                job_store[job_id]["status"] = "failed"
                job_store[job_id]["result"] = result
        else:
            with job_store_lock:
                job_store[job_id]["status"] = "complete"
                job_store[job_id]["result"] = result
    except Exception as e:
        with job_store_lock:
            job_store[job_id]["status"] = "failed"
            job_store[job_id]["result"] = {"error": str(e)}


class TranscriptionJobRequest(BaseModel):
    """Request model for JSON-based transcription job API."""
    url: Optional[str] = None
    file: Optional[str] = None  # Not supported for file upload, but included for compatibility
    dir: str = ""
    lang: str = "Auto Detect"
    model_choice: str = "Local Whisper"
    local_model: str = "medium"
    groq_model: str = "whisper-large-v3"
    translate: bool = False


@fastapi_app.post("/gradio_api/api/handle_transcription")
async def submit_transcription_job_api(
    url: str = Form(None),
    file: UploadFile = File(None),
    dir: str = Form(""),
    lang: str = Form("Auto Detect"),
    model_choice: str = Form("Local Whisper"),
    local_model: str = Form("medium"),
    groq_model: str = Form("whisper-large-v3"),
    translate: str = Form("false"),
):
    """API endpoint for form-based transcription job submission.
    
    Returns:
        Dict with job_id for tracking the job status
    """
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


@fastapi_app.post("/gradio_api/api/handle_transcription_json")
async def handle_transcription_json_api(data: TranscriptionJobRequest = Body(...)):
    """API endpoint for JSON-based transcription job submission.
    
    Returns:
        Dict with job_id for tracking the job status
    """
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
            data.url,
            file,
            data.dir,
            data.lang,
            data.model_choice,
            data.local_model,
            data.groq_model,
            data.translate,
        ),
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id}


@fastapi_app.get("/gradio_api/api/job_status")
async def job_status(job_id: str):
    """API endpoint to check the status of a transcription job.
    
    Args:
        job_id: The ID of the job to check
        
    Returns:
        Dict with job status and result if complete
    """
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


def reload_groq_env_and_client():
    """Reload the Groq API key from .env and initialize the client."""
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


def update_groq_api_key_ui(method_choice: str, api_key: str):
    """Update the UI based on the selected transcription method and API key.
    
    Args:
        method_choice: 'Local Whisper' or 'Groq API'
        api_key: User-provided Groq API key
        
    Returns:
        Tuple of UI updates
    """
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
                print(f"DEBUG: Validating env API key starts with: {env_api_key[:6]}...")
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
                print(f"DEBUG: Validating entered API key starts with: {api_key[:6]}...")
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


# Define the Gradio UI
with gr.Blocks(title="Video Transcriber") as app:
    gr.Markdown("# Multi-Language Video Transcriber")
    gr.Markdown("Enter a video URL or upload a video file to transcribe it.")

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

            transcription_output = gr.Textbox(label="Transcription", lines=15)
            srt_file = gr.File(label="Download SRT")
            text_file = gr.File(label="Download Text")
            video_file = gr.File(label="Download Video")

    # Set up event handlers
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
        outputs=[transcription_output, srt_file, text_file, video_file],
    )


def run_app():
    """Run both Gradio and FastAPI servers."""
    gradio_server = threading.Thread(
        target=app.launch,
        kwargs={"server_name": "127.0.0.1", "server_port": 7860},
        daemon=True,
    )
    gradio_server.start()
    uvicorn.run(fastapi_app, host="127.0.0.1", port=7861)


if __name__ == "__main__":
    run_app()
