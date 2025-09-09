import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
import time
import whisper
import groq
import json
import hashlib

from utils import format_timestamp, generate_srt_content

load_dotenv()

GROQ_CLIENT = None
WHISPER_MODEL = None
DEFAULT_OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")
CACHE_DIR = os.path.join(os.getcwd(), "cache")


def load_groq_client():
    global GROQ_CLIENT
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Groq API key not found. Continuing with local Whisper only.")
        return None
    try:
        client = groq.Groq(api_key=api_key)
        client.models.list()
        GROQ_CLIENT = client
        return client
    except Exception as e:
        print(f"Groq API key validation failed: {e}")
        print("Continuing with local Whisper only.")
        return None


def load_whisper_model(model_name="medium"):
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        print(f"Loading Whisper model: {model_name}...")
        WHISPER_MODEL = whisper.load_model(model_name)
        print("Whisper model loaded.")


def get_cache_key(audio_path, language, model, translate=False):
    """Generate a unique cache key for transcription results"""
    content = f"{audio_path}:{language}:{model}:{translate}"
    return hashlib.md5(content.encode()).hexdigest()


def save_to_cache(cache_key, result):
    """Save transcription result to cache"""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
        with open(cache_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Saved result to cache: {cache_key}")
    except Exception as e:
        print(f"Error saving to cache: {e}")


def load_from_cache(cache_key):
    """Load transcription result from cache"""
    try:
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                result = json.load(f)
            print(f"Loaded result from cache: {cache_key}")
            return result
    except Exception as e:
        print(f"Error loading from cache: {e}")
    return None


def save_output_files(
    output_dir, video_name, transcription_text, srt_content, source_video_path
):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    video_path = output_path / f"{video_name}.mp4"
    text_path = output_path / f"{video_name}.txt"
    srt_path = output_path / f"{video_name}.srt"

    retries = 3
    for attempt in range(retries):
        try:
            shutil.copy2(source_video_path, str(video_path))
            print(f"Video saved to {video_path}")
            break  # If successful, break out of the retry loop
        except PermissionError as e:
            if attempt < retries - 1:  # If not the last attempt
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in 1 second...")
                time.sleep(1)  # Wait for 1 second before retrying
            else:  # If it's the last attempt, raise the exception
                print(f"Failed to copy video after {retries} attempts.")
                raise  # Re-raise the exception to be caught by the caller

    text_path.write_text(transcription_text.strip(), encoding="utf-8")
    srt_path.write_text(srt_content, encoding="utf-8")

    return str(video_path), str(text_path), str(srt_path)


def transcribe_local_video(video_path, output_dir=DEFAULT_OUTPUT_DIR, language="auto", model_name="medium"):
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        load_whisper_model(model_name)
    if not WHISPER_MODEL:
        print("Error: Whisper model not loaded.")
        return "Error: Whisper model not loaded.", None, None

    if not video_path or not os.path.exists(video_path):
        return "Invalid video file path.", None, None

    video_title = Path(video_path).stem
    using_default = not output_dir or output_dir == DEFAULT_OUTPUT_DIR

    whisper_language = None if language == "auto" else language
    result = WHISPER_MODEL.transcribe(
        video_path, language=whisper_language, verbose=True, fp16=False
    )

    transcription_text = result["text"]
    srt_content = generate_srt_content(result)

    safe_title = "".join(
        c for c in video_title if c.isalnum() or c in (" ", "-", "_")
    ).strip()

    # If output_dir is not provided, use cwd, else use as-is (no subfolder)
    if not output_dir:
        output_dir = os.getcwd()

    video_path_out, text_path, srt_path = save_output_files(
        output_dir, safe_title, transcription_text, srt_content, video_path
    )

    return transcription_text, srt_path, text_path, str(video_path_out)


def transcribe_video_from_url(url, output_dir=DEFAULT_OUTPUT_DIR, language="auto", model_name="medium"):
    import tempfile
    import yt_dlp
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        load_whisper_model(model_name)
    if not WHISPER_MODEL:
        print("Error: Whisper model not loaded.")
        return "Error: Whisper model not loaded.", None, None

    if not url:
        return "Please enter a video URL.", None, None

    temp_dir = tempfile.mkdtemp()
    try:
        # Modern yt-dlp configuration with updated strategies and resume support
        base_opts = {
            "format": "best[height<=720]/best",
            "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "extractaudio": False,
            "audioformat": "mp3",
            "embed_subs": False,
            "writesubtitles": False,
            "writeautomaticsub": False,
            "continue_dl": True,  # Enable download resume
            "no_part": True,      # Don't use .part files
        }

        success = False
        temp_video_path = None
        video_title = "downloaded_video"

        # Try different strategies with latest yt-dlp features
        strategies = [
            # Strategy 1: Basic with updated user agent
            {
                "name": "basic_updated",
                "opts": {**base_opts, "http_headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}}
            },
            # Strategy 2: Use different format with fallback
            {
                "name": "format_fallback", 
                "opts": {**base_opts, "format": "worst[height>=360]/worst"}
            },
            # Strategy 3: Audio-only as last resort
            {
                "name": "audio_only",
                "opts": {**base_opts, "format": "bestaudio/best"}
            }
        ]

        for strategy in strategies:
            if success:
                break
                
            print(f"Trying {strategy['name']} strategy...")
            try:
                with yt_dlp.YoutubeDL(strategy['opts']) as ydl:
                    info = ydl.extract_info(url, download=True)
                    video_title = info.get("title", "downloaded_video")
                    
                    # Find downloaded file
                    downloaded_files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
                    if downloaded_files:
                        temp_video_path = os.path.join(temp_dir, downloaded_files[0])
                        print(f"SUCCESS: Downloaded using {strategy['name']} strategy")
                        success = True
                        
            except Exception as e:
                print(f"FAILED {strategy['name']}: {str(e)[:100]}...")
                continue

        if not success:
            return "Failed to download video. The video may be private, geo-blocked, or temporarily unavailable. Try updating yt-dlp with: pip install --upgrade yt-dlp", None, None, None

        # Verify the downloaded file exists and is valid
        if not temp_video_path or not os.path.exists(temp_video_path):
            return "Download appeared successful but video file not found.", None, None, None
            
        file_size = os.path.getsize(temp_video_path)
        if file_size < 1024:  # Less than 1KB is likely an error
            return "Downloaded file is too small, likely corrupted.", None, None, None
            
        safe_filename = ''.join(c for c in os.path.basename(temp_video_path) if ord(c) < 128)
        print(f"Downloaded video: {safe_filename} ({file_size} bytes)")

        whisper_language = None if language == "auto" else language
        result = WHISPER_MODEL.transcribe(
            temp_video_path, language=whisper_language, verbose=True, fp16=False
        )

        transcription_text = result["text"]
        srt_content = generate_srt_content(result)

        safe_title = "".join(
            c for c in video_title if c.isalnum() or c in (" ", "-", "_")
        ).strip()

        if not output_dir:
            output_dir = os.getcwd()

        video_path_out, text_path, srt_path = save_output_files(
            output_dir, safe_title, transcription_text, srt_content, temp_video_path
        )

        return transcription_text, srt_path, text_path, str(video_path_out)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def transcribe_with_groq(
    audio_path, language="auto", model="whisper-large-v3-turbo", translate=False, progress_callback=None
):
    import subprocess
    from tempfile import NamedTemporaryFile

    print("DEBUG: Inside transcribe_with_groq, GROQ_CLIENT:", GROQ_CLIENT)

    if GROQ_CLIENT is None:
        raise RuntimeError("Groq client not initialized. Please check your API key.")

    # Check cache first
    cache_key = get_cache_key(audio_path, language, model, translate)
    cached_result = load_from_cache(cache_key)
    if cached_result:
        if progress_callback:
            progress_callback(90)  # Skip to end if cached
        return cached_result

    temp_flac = NamedTemporaryFile(suffix=".flac", delete=False)
    try:
        if progress_callback:
            progress_callback(60)  # Audio conversion started

        subprocess.run(
            [
                "ffmpeg",
                "-i",
                audio_path,
                "-ar",
                "16000",
                "-ac",
                "1",
                "-map",
                "0:a",
                "-c:a",
                "flac",
                "-y",
                "-loglevel",
                "error",
                temp_flac.name,
            ],
            check=True,
            capture_output=True,
        )
        temp_flac.close()

        if progress_callback:
            progress_callback(70)  # Audio conversion complete

        with open(temp_flac.name, "rb") as audio_file:
            file_content = audio_file.read()

        if translate:
            if model != "whisper-large-v3":
                raise RuntimeError(
                    "Translation only supported with whisper-large-v3 model."
                )
            response = GROQ_CLIENT.audio.translations.create(
                file=("audio.flac", file_content),
                model="whisper-large-v3",
                response_format="verbose_json",
                temperature=0.0,
            ).model_dump_json()
        else:
            response = GROQ_CLIENT.audio.transcriptions.create(
                file=("audio.flac", file_content),
                model=model,
                language=None if language == "auto" else language,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
                temperature=0.0,
            ).model_dump_json()

        if progress_callback:
            progress_callback(80)  # Transcription API call started

        response_dict = json.loads(response)
        transcription_text = response_dict.get("text", "").strip()
        segments = response_dict.get("segments", [])

        if progress_callback:
            progress_callback(90)  # Transcription complete

        result = {"text": transcription_text, "segments": segments}

        # Save to cache
        save_to_cache(cache_key, result)

        return result

    finally:
        if temp_flac and os.path.exists(temp_flac.name):
            os.unlink(temp_flac.name)
            os.unlink(temp_flac.name)
