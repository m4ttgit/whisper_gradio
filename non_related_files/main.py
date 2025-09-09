import gradio as gr
from dotenv import load_dotenv
import os
import groq
import threading
import uuid
import time
import json
import socket
from typing import Optional
from fastapi import Body, Form, File, UploadFile, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from typing import List


def find_available_port(start_port=7860):
    """Find an available port starting from start_port"""
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                port += 1
                if port > 65535:
                    raise OSError("No available ports found")


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
        job_store.set_job(job_id, {
            "status": "pending",
            "result": None,
            "created_at": time.time(),
            "progress": 0,
            "last_checkpoint": None,
        })
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
    job = job_store.get_job(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"status": "not_found"})
    if job["status"] == "complete":
        return {"status": "complete", "result": job["result"], "progress": job.get("progress", 0)}
    elif job["status"] == "failed":
        return {"status": "failed", "result": job["result"]}
    else:
        return {"status": "pending", "progress": job.get("progress", 0)}


@fastapi_app.post("/gradio/resume_job")
async def resume_job(request: Request):
    """Resume an interrupted job"""
    try:
        # Try to get job_id from query parameters first
        job_id = request.query_params.get("job_id")

        # If not in query params, try to get from JSON body
        if not job_id:
            body = await request.json()
            job_id = body.get("job_id")

        if not job_id:
            return JSONResponse(
                status_code=422,
                content={"error": "job_id is required"}
            )

        job = job_store.get_job(job_id)
        if not job:
            return JSONResponse(status_code=404, content={"status": "not_found"})

        if job["status"] in ["complete", "failed"]:
            return {"status": "already_finished", "job_status": job["status"]}

        # Mark job as resuming
        if job_store.resume_job(job_id):
            print(f"Starting resume thread for job {job_id}")
            # Start background thread to actually resume the job
            thread = threading.Thread(
                target=resume_background_job,
                args=(job_id,),
                daemon=True,
            )
            thread.start()
            print(f"Resume thread started for job {job_id}")
            return {"status": "resumed", "job_id": job_id}
        else:
            return JSONResponse(status_code=400, content={"status": "cannot_resume"})

    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid request: {str(e)}"}
        )


@fastapi_app.get("/gradio/incomplete_jobs")
async def get_incomplete_jobs():
    """Get list of incomplete jobs"""
    incomplete_jobs = job_store.get_incomplete_jobs()
    return {"incomplete_jobs": list(incomplete_jobs.keys()), "count": len(incomplete_jobs)}


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
    job_store.set_job(job_id, {
        "status": "pending",
        "result": None,
        "created_at": time.time(),
        "progress": 0,
        "last_checkpoint": None,
    })
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

# Persistent Job Storage
class PersistentJobStore:
    def __init__(self, storage_file="job_store.json"):
        self.storage_file = storage_file
        self.jobs = {}
        self.lock = threading.Lock()
        self.load_jobs()

    def load_jobs(self):
        """Load jobs from persistent storage"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    self.jobs = json.load(f)
                print(f"Loaded {len(self.jobs)} jobs from persistent storage")
        except Exception as e:
            print(f"Error loading jobs from storage: {e}")
            self.jobs = {}

    def save_jobs(self):
        """Save jobs to persistent storage"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.jobs, f, indent=2)
        except Exception as e:
            print(f"Error saving jobs to storage: {e}")

    def get_job(self, job_id):
        with self.lock:
            return self.jobs.get(job_id)

    def set_job(self, job_id, job_data):
        with self.lock:
            self.jobs[job_id] = job_data
            self.save_jobs()

    def delete_job(self, job_id):
        with self.lock:
            if job_id in self.jobs:
                del self.jobs[job_id]
                self.save_jobs()

    def get_all_jobs(self):
        with self.lock:
            return self.jobs.copy()

    def get_incomplete_jobs(self):
        """Get jobs that are not complete or failed"""
        with self.lock:
            return {job_id: job for job_id, job in self.jobs.items()
                    if job.get("status") not in ["complete", "failed"]}

    def resume_job(self, job_id):
        """Mark a job for resumption"""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                if job["status"] not in ["complete", "failed"]:
                    self.jobs[job_id] = {
                        **job,
                        "status": "resuming",
                        "resumed_at": time.time(),
                    }
                    self.save_jobs()
                    return True
        return False

# Global job store
job_store = PersistentJobStore()

load_dotenv()
load_whisper_model()
load_groq_client()

# Check for incomplete jobs on startup
def check_incomplete_jobs():
    """Check for incomplete jobs and log them"""
    incomplete_jobs = job_store.get_incomplete_jobs()
    if incomplete_jobs:
        print(f"Found {len(incomplete_jobs)} incomplete jobs:")
        for job_id, job in incomplete_jobs.items():
            print(f"  Job {job_id}: {job.get('status', 'unknown')} (progress: {job.get('progress', 0)}%)")
    else:
        print("No incomplete jobs found.")

check_incomplete_jobs()

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
    url, file, dir, lang, model_choice, local_model, groq_model, translate, job_id=None
):
    def update_progress(progress):
        if job_id:
            job_data = job_store.get_job(job_id)
            if job_data:
                job_store.set_job(job_id, {
                    **job_data,
                    "progress": progress,
                    "last_checkpoint": time.time(),
                })

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
                    video_path, lang_code, groq_model, translate, update_progress
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
                import tempfile, shutil, subprocess

                temp_dir = tempfile.mkdtemp()
                video_path = None
                try:
                    # Use subprocess to run yt-dlp command directly with enhanced options to bypass 403 errors
                    command = [
                        "yt-dlp",
                        "--continue",  # Enable download resume
                        "--no-part",   # Don't use .part files for resume
                        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "--referer", "https://www.youtube.com/",
                        "--add-header", "Accept-Language:en-US,en;q=0.9",
                        "--add-header", "Accept:text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "--add-header", "DNT:1",
                        "--add-header", "Upgrade-Insecure-Requests:1",
                        "--no-check-certificates",
                        "--extractor-retries", "10",
                        "--retries", "10",
                        "--fragment-retries", "10",
                        "--skip-unavailable-fragments",
                        "--keep-fragments",
                        "--geo-bypass",
                        "--no-playlist",
                        "--no-warnings",
                        "--sleep-requests", "1",
                        "--min-sleep-interval", "1",
                        "--max-sleep-interval", "5",
                        "--force-ipv4",
                        "--http-chunk-size", "1048576",
                        "--buffer-size", "16M",
                        "--concurrent-fragments", "1",
                        "-f", "best[ext=mp4][height<=720]/best[height<=720]/18/mp4",  # Multiple format fallbacks
                        "-o", os.path.join(temp_dir, "%(title)s.%(ext)s"),
                        url,
                    ]

                    # Try with cookies first, then fallback without cookies
                    cookie_file_path = os.getenv("YT_DLP_COOKIE_FILE")
                    base_command = command.copy()

                    success = False
                    attempts = [
                        ("with cookies", lambda: base_command + (["--cookies", cookie_file_path] if cookie_file_path and os.path.exists(cookie_file_path) else [])),
                        ("without cookies", lambda: base_command),
                        ("aggressive mode", lambda: base_command + ["--force-generic-extractor", "--no-cache-dir", "--rm-cache-dir"]),
                        ("no fragments", lambda: [arg for arg in base_command if arg not in ["--keep-fragments", "--concurrent-fragments", "1"]] + ["--no-part"]),
                        ("different format", lambda: base_command + ["-f", "18/best[height<=480]/best"])
                    ]

                    for attempt_name, get_command in attempts:
                        if success:
                            break

                        command = get_command()
                        print(f"Trying {attempt_name}...")
                        print(f"Executing yt-dlp command: {' '.join(command)}")
                        process = subprocess.run(command, capture_output=True, text=True, cwd=temp_dir)

                        if process.returncode == 0:
                            print(f"SUCCESS: Download successful using {attempt_name}")
                            success = True
                        else:
                            print(f"FAILED {attempt_name}: Exit code {process.returncode}")
                            print(f"STDERR: {process.stderr}")
                            print(f"STDOUT: {process.stdout}")
                            if attempt_name == "with cookies" and cookie_file_path:
                                print(f"Warning: Cookie file {cookie_file_path} may be invalid or outdated")
                            if "403" in process.stderr or "Forbidden" in process.stderr:
                                print(f"403 Forbidden error detected in {attempt_name}")

                    if not success:
                        raise Exception(f"yt-dlp download failed after all attempts. Last error: {process.stderr}")

                    print(f"yt-dlp command output:\n{process.stdout}")

                    # Find the downloaded file (should be mp4 for format 234)
                    downloaded_files = os.listdir(temp_dir)
                    downloaded_file = next((f for f in downloaded_files if f.endswith(".mp4")), None)
                    if downloaded_file is None:
                         raise Exception("Failed to find downloaded mp4 file.")
                    video_path = os.path.join(temp_dir, downloaded_file)

                    # Get video title from yt-dlp info (can parse stdout or re-run info extraction)
                    # For simplicity, let's try to get it from stdout or use a default
                    video_title_from_url = "downloaded_video" # Default title
                    # A more robust way would be to run yt-dlp --print title <url> separately

                    safe_title = "".join(
                        c
                        for c in video_title_from_url
                        if c.isalnum() or c in (" ", "-", "_")
                    ).strip()
                    if not safe_title:
                         safe_title = "downloaded_video"

                    result = transcribe_with_groq(
                        video_path, lang_code, groq_model, translate, update_progress
                    )

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
        # Store original parameters for resume capability
        job_store.set_job(job_id, {
            **job_store.get_job(job_id),
            "params": {
                "url": url,
                "file": file.name if file else None,
                "dir": dir,
                "lang": lang,
                "model_choice": model_choice,
                "local_model": local_model,
                "groq_model": groq_model,
                "translate": translate,
            }
        })

        # Update progress to downloading
        job_store.set_job(job_id, {
            **job_store.get_job(job_id),
            "status": "downloading",
            "progress": 10,
        })

        result = handle_transcription(
            url, file, dir, lang, model_choice, local_model, groq_model, translate, job_id
        )

        # Update progress to transcribing
        job_store.set_job(job_id, {
            **job_store.get_job(job_id),
            "status": "transcribing",
            "progress": 50,
        })

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

        # Update progress to complete
        job_store.set_job(job_id, {
            **job_store.get_job(job_id),
            "status": "complete",
            "result": result_data,
            "progress": 100,
            "last_checkpoint": time.time(),
        })
    except Exception as e:
        job_store.set_job(job_id, {
            **job_store.get_job(job_id),
            "status": "failed",
            "result": {"error": str(e)},
        })


def resume_background_job(job_id):
    """Resume a background job from stored parameters"""
    print(f"Resume background job started for {job_id}")
    try:
        job = job_store.get_job(job_id)
        if not job:
            print(f"Job {job_id} not found")
            return

        # Check if parameters are stored (for jobs created after resume feature)
        if "params" not in job:
            print(f"No stored parameters for job {job_id} (created before resume feature)")
            print("Marking job as non-resumable")

            # For jobs without stored parameters, we can't resume them
            # Mark as failed with explanation
            job_store.set_job(job_id, {
                **job,
                "status": "failed",
                "result": {
                    "error": "This job was created before the resume feature was implemented. "
                           "Cannot resume jobs without stored parameters. "
                           "Please restart the transcription for this content."
                },
            })
            return

        params = job["params"]
        print(f"Resuming job {job_id} with parameters: {params}")

        # Update status to indicate resumption
        job_store.set_job(job_id, {
            **job,
            "status": "resuming",
            "progress": job.get("progress", 0),
        })

        # Reconstruct file object if it was a file upload
        file = None
        if params.get("file"):
            # For file uploads, we can't easily reconstruct the file object
            # This is a limitation - file uploads can't be resumed
            print(f"Warning: Cannot resume file upload job {job_id}")
            job_store.set_job(job_id, {
                **job,
                "status": "failed",
                "result": {"error": "File upload jobs cannot be resumed"},
            })
            return

        # Resume the transcription
        result = handle_transcription(
            params.get("url"),
            file,
            params.get("dir"),
            params.get("lang"),
            params.get("model_choice"),
            params.get("local_model"),
            params.get("groq_model"),
            params.get("translate"),
            job_id
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
            result_data = {"error": result}

        job_store.set_job(job_id, {
            **job_store.get_job(job_id),
            "status": "complete",
            "result": result_data,
            "progress": 100,
            "last_checkpoint": time.time(),
        })

    except Exception as e:
        print(f"Error resuming job {job_id}: {str(e)}")
        job_store.set_job(job_id, {
            **job_store.get_job(job_id),
            "status": "failed",
            "result": {"error": f"Resume failed: {str(e)}"},
        })


with gr.Blocks(title="Video Transcriber") as app:
    gr.Markdown("# Multi-Language Video Transcriber")
    gr.Markdown("Enter a video URL or upload a video file to transcribe it.")

    # Incomplete Jobs Section
    with gr.Accordion("Resume Incomplete Jobs", open=False):
        incomplete_jobs_display = gr.JSON(label="Incomplete Jobs")
        refresh_jobs_btn = gr.Button("🔄 Refresh Jobs")
        resume_job_input = gr.Textbox(label="Job ID to Resume", placeholder="Enter job ID from above")
        resume_job_btn = gr.Button("▶️ Resume Job")
        resume_status = gr.Markdown("")

        def refresh_incomplete_jobs():
            incomplete_jobs = job_store.get_incomplete_jobs()
            return incomplete_jobs

        def resume_job_ui(job_id):
            if not job_id.strip():
                return "Please enter a job ID"

            try:
                import requests
                response = requests.post(f"http://localhost:7861/gradio/resume_job", json={"job_id": job_id})
                if response.status_code == 200:
                    return f"✅ Job {job_id} resumed successfully"
                else:
                    return f"❌ Failed to resume job: {response.text}"
            except Exception as e:
                return f"❌ Error resuming job: {str(e)}"

        refresh_jobs_btn.click(
            fn=refresh_incomplete_jobs,
            outputs=incomplete_jobs_display
        )

        resume_job_btn.click(
            fn=resume_job_ui,
            inputs=resume_job_input,
            outputs=resume_status
        )

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
import argparse


import os

def run_app(server_port, api_port):
    # Find available ports starting from specified ports
    gradio_port = find_available_port(server_port)
    api_port = find_available_port(api_port)

    print(f"Using Gradio port: {gradio_port}")
    print(f"Using API port: {api_port}")

    # Set Gradio port range to allow finding available ports
    os.environ["GRADIO_SERVER_PORT_RANGE"] = f"{server_port}-{server_port + 100}"

    gradio_server = threading.Thread(
        target=app.launch,
        kwargs={"server_name": "127.0.0.1", "server_port": gradio_port},
        daemon=True,
    )
    gradio_server.start()
    try:
        uvicorn.run(fastapi_app, host="127.0.0.1", port=api_port)
    except Exception as e:
        print(f"Failed to start FastAPI server on port {api_port}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--server_port", type=int, default=7860, help="Gradio server port"
    )
    parser.add_argument(
        "--api_port", type=int, default=7861, help="FastAPI server port"
    )
    args = parser.parse_args()
    run_app(args.server_port, args.api_port)
