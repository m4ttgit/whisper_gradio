"""
Transcription module for video and audio processing.

This module provides functions for transcribing audio and video files
using either local Whisper models or the Groq API.
"""

# Standard library imports
import os
import shutil
import json
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, Any, Tuple, Optional, List, Union

# Third-party imports
import whisper
import groq
from dotenv import load_dotenv

# Local imports
from utils import format_timestamp, generate_srt_content

# Initialize environment
load_dotenv()

# Global variables
GROQ_CLIENT = None
WHISPER_MODEL = None
MODEL_SIZE = "medium"
DEFAULT_OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")


def load_groq_client() -> Optional[groq.Groq]:
    """Initialize the Groq client with API key from environment.
    
    Returns:
        Initialized Groq client or None if initialization fails
    """
    global GROQ_CLIENT
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("Groq API key not found. Continuing with local Whisper only.")
        return None
    
    try:
        client = groq.Groq(api_key=api_key)
        client.models.list()  # Test the connection
        GROQ_CLIENT = client
        return client
    except Exception as e:
        print(f"Groq API key validation failed: {e}")
        print("Continuing with local Whisper only.")
        return None


def load_whisper_model() -> None:
    """Load the Whisper model into memory."""
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        print(f"Loading Whisper model: {MODEL_SIZE}...")
        WHISPER_MODEL = whisper.load_model(MODEL_SIZE)
        print("Whisper model loaded.")


def save_output_files(
    output_dir: str, 
    video_name: str, 
    transcription_text: str, 
    srt_content: str, 
    source_video_path: str
) -> Tuple[str, str, str]:
    """Save transcription outputs to files.
    
    Args:
        output_dir: Directory to save files
        video_name: Base name for output files
        transcription_text: Plain text transcription
        srt_content: SRT formatted content
        source_video_path: Path to source video file
        
    Returns:
        Tuple of (video path, text path, srt path)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    video_path = output_path / f"{video_name}.mp4"
    text_path = output_path / f"{video_name}.txt"
    srt_path = output_path / f"{video_name}.srt"

    shutil.copy2(source_video_path, str(video_path))
    text_path.write_text(transcription_text.strip(), encoding="utf-8")
    srt_path.write_text(srt_content, encoding="utf-8")

    return str(video_path), str(text_path), str(srt_path)


def transcribe_local_video(
    video_path: str, 
    output_dir: str = DEFAULT_OUTPUT_DIR, 
    language: str = "auto"
) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """Transcribe a local video file using Whisper.
    
    Args:
        video_path: Path to the video file
        output_dir: Directory to save output files
        language: Language code or 'auto' for auto-detection
        
    Returns:
        Tuple of (transcription text, srt path, text path, video path)
    """
    if not WHISPER_MODEL:
        print("Error: Whisper model not loaded.")
        return "Error: Whisper model not loaded.", None, None, None

    if not video_path or not os.path.exists(video_path):
        return "Invalid video file path.", None, None, None

    video_title = Path(video_path).stem
    
    # Set language parameter for Whisper
    whisper_language = None if language == "auto" else language
    
    # Transcribe with Whisper
    result = WHISPER_MODEL.transcribe(
        video_path, language=whisper_language, verbose=True, fp16=False
    )

    transcription_text = result["text"]
    srt_content = generate_srt_content(result)

    # Create safe filename
    safe_title = "".join(
        c for c in video_title if c.isalnum() or c in (" ", "-", "_")
    ).strip()

    # Use current directory if output_dir not provided
    if not output_dir:
        output_dir = os.getcwd()

    # Save output files
    video_path_out, text_path, srt_path = save_output_files(
        output_dir, safe_title, transcription_text, srt_content, video_path
    )

    return transcription_text, srt_path, text_path, str(video_path_out)


def transcribe_video_from_url(
    url: str, 
    output_dir: str = DEFAULT_OUTPUT_DIR, 
    language: str = "auto"
) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """Download and transcribe a video from URL using Whisper.
    
    Args:
        url: URL of the video
        output_dir: Directory to save output files
        language: Language code or 'auto' for auto-detection
        
    Returns:
        Tuple of (transcription text, srt path, text path, video path)
    """
    import tempfile
    import yt_dlp

    if not WHISPER_MODEL:
        print("Error: Whisper model not loaded.")
        return "Error: Whisper model not loaded.", None, None, None

    if not url:
        return "Please enter a video URL.", None, None, None

    temp_dir = tempfile.mkdtemp()
    try:
        # Download video using yt-dlp
        ydl_opts = {
            "format": "best",
            "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
            "quiet": False,
            "progress": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get("title", "downloaded_video")
            downloaded_files = os.listdir(temp_dir)
            
            if not downloaded_files:
                raise FileNotFoundError("No file found after download.")
                
            temp_video_path = os.path.join(temp_dir, downloaded_files[0])

        # Set language parameter for Whisper
        whisper_language = None if language == "auto" else language
        
        # Transcribe with Whisper
        result = WHISPER_MODEL.transcribe(
            temp_video_path, language=whisper_language, verbose=True, fp16=False
        )

        transcription_text = result["text"]
        srt_content = generate_srt_content(result)

        # Create safe filename
        safe_title = "".join(
            c for c in video_title if c.isalnum() or c in (" ", "-", "_")
        ).strip()

        # Use current directory if output_dir not provided
        if not output_dir:
            output_dir = os.getcwd()

        # Save output files
        video_path_out, text_path, srt_path = save_output_files(
            output_dir, safe_title, transcription_text, srt_content, temp_video_path
        )

        return transcription_text, srt_path, text_path, str(video_path_out)

    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


def transcribe_with_groq(
    audio_path: str, 
    language: str = "auto", 
    model: str = "whisper-large-v3-turbo", 
    translate: bool = False
) -> Dict[str, Any]:
    """Transcribe audio using Groq API.
    
    Args:
        audio_path: Path to the audio/video file
        language: Language code or 'auto' for auto-detection
        model: Groq model to use
        translate: Whether to translate to English
        
    Returns:
        Dictionary with transcription results
        
    Raises:
        RuntimeError: If Groq client is not initialized or other errors occur
    """
    print("DEBUG: Inside transcribe_with_groq, GROQ_CLIENT:", GROQ_CLIENT)

    if GROQ_CLIENT is None:
        raise RuntimeError("Groq client not initialized. Please check your API key.")

    # Create temporary FLAC file for processing
    temp_flac = NamedTemporaryFile(suffix=".flac", delete=False)
    try:
        # Convert audio to FLAC format using ffmpeg
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

        # Read the FLAC file
        with open(temp_flac.name, "rb") as audio_file:
            file_content = audio_file.read()

        # Process with Groq API
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

        # Parse response
        response_dict = json.loads(response)
        transcription_text = response_dict.get("text", "").strip()
        segments = response_dict.get("segments", [])

        return {"text": transcription_text, "segments": segments}

    finally:
        # Clean up temporary file
        if temp_flac and os.path.exists(temp_flac.name):
            os.unlink(temp_flac.name)
