import gradio as gr
import whisper
import yt_dlp
import os
import tempfile
import datetime
import shutil  # For removing temporary directories
from pathlib import Path
from dotenv import load_dotenv
import groq
import json # Import json for parsing

# Load environment variables
load_dotenv()


def validate_groq_api_key():
    """Validate the Groq API key and provide clear error message"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print(
            "\nGroq API key not found. To enable Groq API features:"
            "\n1. Create a .env file in the project directory"
            "\n2. Add the line: GROQ_API_KEY=your-api-key-here"
            "\n3. Replace 'your-api-key-here' with your actual Groq API key"
            "\n4. Restart the application"
            "\n\nContinuing with local Whisper only..."
        )
        return None

    # Test the API key by creating a client
    try:
        client = groq.Groq(api_key=api_key)
        # Try a simple API call to validate the key
        client.models.list()
        return client
    except Exception as e:
        print(f"\nGroq API key validation failed: {str(e)}")
        print("Please check your API key and ensure it is valid.")
        print("Continuing with local Whisper only...\n")
        return None


# --- Global Variables ---
GROQ_CLIENT = validate_groq_api_key()
WHISPER_MODEL = None
MODEL_SIZE = "medium"  # Choose: tiny, base, small, medium, large, large-v2, large-v3
DEFAULT_OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")

# Language options for the dropdown
LANGUAGES = {
    "auto": "Auto Detect",
    "af": "Afrikaans",
    "ar": "Arabic",
    "hy": "Armenian",
    "az": "Azerbaijani",
    "be": "Belarusian",
    "bs": "Bosnian",
    "bg": "Bulgarian",
    "ca": "Catalan",
    "zh": "Chinese",
    "hr": "Croatian",
    "cs": "Czech",
    "da": "Danish",
    "nl": "Dutch",
    "en": "English",
    "et": "Estonian",
    "fi": "Finnish",
    "fr": "French",
    "gl": "Galician",
    "de": "German",
    "el": "Greek",
    "he": "Hebrew",
    "hi": "Hindi",
    "hu": "Hungarian",
    "is": "Icelandic",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "kn": "Kannada",
    "kk": "Kazakh",
    "ko": "Korean",
    "lv": "Latvian",
    "lt": "Lithuanian",
    "mk": "Macedonian",
    "ms": "Malay",
    "mr": "Marathi",
    "mi": "Maori",
    "ne": "Nepali",
    "no": "Norwegian",
    "fa": "Persian",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sr": "Serbian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "es": "Spanish",
    "sw": "Swahili",
    "sv": "Swedish",
    "tl": "Tagalog",
    "ta": "Tamil",
    "th": "Thai",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "vi": "Vietnamese",
    "cy": "Welsh",
}

# --- Helper Functions ---


def format_timestamp(seconds: float) -> str:
    """Formats seconds into SRT timestamp format HH:MM:SS,ms"""
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)
    td = datetime.timedelta(milliseconds=milliseconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def generate_srt_content(result: dict) -> str:
    """Generates SRT content as a string from Whisper results."""
    srt_content = []
    for i, segment in enumerate(result["segments"], start=1):
        # Format timestamps
        start_time = format_timestamp(segment["start"])
        end_time = format_timestamp(segment["end"])
        # Clean text and ensure proper line breaks
        text = segment["text"].strip()
        # Build SRT segment with exact formatting
        srt_segment = f"{i}\n{start_time} --> {end_time}\n{text}\n"
        srt_content.append(srt_segment)

    # Join with newline to match reference format
    return "\n".join(srt_content)


def load_whisper_model():
    """Loads the Whisper model into the global variable if not already loaded."""
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        print(f"Loading Whisper model: {MODEL_SIZE}...")
        try:
            # Add device="cuda" if you have a compatible NVIDIA GPU and installed PyTorch with CUDA
            # WHISPER_MODEL = whisper.load_model(MODEL_SIZE, device="cuda")
            WHISPER_MODEL = whisper.load_model(MODEL_SIZE)
            print("Whisper model loaded successfully.")
        except Exception as e:
            print(f"Error loading Whisper model: {e}")
            raise RuntimeError(
                f"Failed to load Whisper model '{MODEL_SIZE}'. Please check installation and resources."
            ) from e


def save_output_files(
    output_dir: str,
    video_name: str,
    transcription_text: str,
    srt_content: str,
    source_video_path: str,
):
    """Save output files to the specified directory and return their paths."""
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create paths for output files using video name
    video_path = output_path / f"{video_name}.mp4"
    text_path = output_path / f"{video_name}.txt"
    srt_path = output_path / f"{video_name}.srt"

    # Save files
    shutil.copy2(source_video_path, str(video_path))
    # Save plain text without any formatting
    text_path.write_text(transcription_text.strip(), encoding="utf-8")
    srt_path.write_text(srt_content, encoding="utf-8")

    return str(video_path), str(text_path), str(srt_path)


def transcribe_local_video(
    video_path: str, output_dir: str = DEFAULT_OUTPUT_DIR, language: str = "auto"
):
    """Transcribes a local video file and saves outputs to the specified directory."""
    if not WHISPER_MODEL:
        print("Error: Whisper model not loaded.")
        return "Error: Whisper model not loaded.", None, None

    if not video_path or not os.path.exists(video_path):
        return "Invalid video file path.", None, None

    print(f"Processing local video: {video_path}")
    try:
        # Get video title from filename
        video_title = Path(video_path).stem
        using_default = not output_dir or output_dir == DEFAULT_OUTPUT_DIR

        # Transcribe using Whisper
        print("Starting transcription...")
        whisper_language = None if language == "auto" else language
        result = WHISPER_MODEL.transcribe(
            video_path, language=whisper_language, verbose=True, fp16=False
        )
        print("Transcription complete.")

        # Generate outputs
        transcription_text = result["text"]
        srt_content = generate_srt_content(result)

        # Create safe title for directory name
        safe_title = "".join(
            c for c in video_title if c.isalnum() or c in (" ", "-", "_")
        ).strip()

        # If using default directory, create a subdirectory with the video title
        if using_default:
            output_dir = os.path.join(DEFAULT_OUTPUT_DIR, safe_title)
            print(f"Created output directory based on video title: {output_dir}")

        # Save all files
        video_path_out, text_path, srt_path = save_output_files(
            output_dir, safe_title, transcription_text, srt_content, video_path
        )
        print(f"Files saved in: {output_dir}")

        return transcription_text, srt_path, text_path

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback

        traceback.print_exc()
        return f"An unexpected error occurred during processing: {e}", None, None


def transcribe_video_from_url(
    url: str, output_dir: str = DEFAULT_OUTPUT_DIR, language: str = "auto"
):
    """Downloads video, transcribes, and saves all files to the specified directory."""
    if not WHISPER_MODEL:
        print("Error: Whisper model not loaded.")
        return "Error: Whisper model not loaded.", None, None

    if not url:
        return "Please enter a video URL.", None, None

    # Replace empty or default output directory with video-title based directory
    using_default = not output_dir or output_dir == DEFAULT_OUTPUT_DIR

    print(f"Processing URL: {url}")
    temp_dir = None
    temp_video_path = None

    try:
        # Create temporary directory for download
        temp_dir = tempfile.mkdtemp()
        print(f"Created temporary directory: {temp_dir}")

        # Download video
        print("Starting video download...")
        ydl_opts = {
            "format": "best",
            "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
            "quiet": False,
            "progress": True,
        }

        video_title = None
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_title = info_dict.get("title", None)
            downloaded_files = os.listdir(temp_dir)
            if not downloaded_files:
                raise FileNotFoundError("No file found after download.")
            temp_video_path = os.path.join(temp_dir, downloaded_files[0])
            print(f"Video downloaded successfully to: {temp_video_path}")

        # Transcribe using Whisper
        print("Starting transcription...")
        # Set language to None for auto-detection
        whisper_language = None if language == "auto" else language
        result = WHISPER_MODEL.transcribe(
            temp_video_path, language=whisper_language, verbose=True, fp16=False
        )
        print("Transcription complete.")

        # Generate outputs
        transcription_text = result["text"]
        srt_content = generate_srt_content(result)

        # Create safe title for directory name
        safe_title = "".join(
            c for c in video_title if c.isalnum() or c in (" ", "-", "_")
        ).strip()

        # If using default directory, create a subdirectory with the video title
        if using_default:
            output_dir = os.path.join(DEFAULT_OUTPUT_DIR, safe_title)
            print(f"Created output directory based on video title: {output_dir}")

        # Save all files
        video_path, text_path, srt_path = save_output_files(
            output_dir, safe_title, transcription_text, srt_content, temp_video_path
        )
        print(f"Files saved in: {output_dir}")

        # All files are saved in the selected directory
        return transcription_text, srt_path, text_path

    except yt_dlp.utils.DownloadError as e:
        print(f"Error downloading video: {e}")
        return f"Error downloading video: {e}", None, None
    except FileNotFoundError as e:
        print(f"Error finding downloaded file: {e}")
        return f"Error finding downloaded file: {e}", None, None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback

        traceback.print_exc()
        return f"An unexpected error occurred during processing: {e}", None, None
    finally:
        # Cleanup temporary files
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print(f"Removed temporary directory: {temp_dir}")
            except OSError as e:
                print(f"Error removing temporary directory {temp_dir}: {e}")


# --- Load Model on Startup ---
load_whisper_model()


def select_directory():
    """Open directory picker dialog and return selected path."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.attributes("-topmost", True)  # Bring dialog to front
    directory = filedialog.askdirectory(initialdir=DEFAULT_OUTPUT_DIR)
    return directory if directory else DEFAULT_OUTPUT_DIR


# --- Launch the App ---
if __name__ == "__main__":
    # Initialize default output directory
    Path(DEFAULT_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    # Create the Gradio interface using Blocks
    with gr.Blocks(title="Video Transcriber") as app:
        gr.Markdown(f"# Multi-Language Video Transcriber")
        gr.Markdown(
            f"Enter a video URL or drag & drop a video file to transcribe it. Choose between local Whisper model or Groq API for transcription."
        )

        with gr.Row():
            with gr.Column(scale=1):
                model_choice = gr.Radio(
                    choices=["Local Whisper", "Groq API"],
                    value="Local Whisper",
                    label="Transcription Method",
                    info="Choose between local Whisper model or Groq API",
                )

                # Add API key input for Groq
                groq_api_key = gr.Textbox(
                    label="Groq API Key",
                    placeholder="Enter your Groq API key here",
                    type="password",
                    visible=False,
                    info="Required for Groq API. Leave empty to use key from .env file",
                )

                def validate_and_update_groq_client(api_key):
                    """Validate API key and update global client"""
                    global GROQ_CLIENT
                    if not api_key:
                        return gr.update(value="Local Whisper")
                    try:
                        client = groq.Groq(api_key=api_key)
                        # Test the key
                        client.models.list()
                        GROQ_CLIENT = client
                        return gr.update(), gr.update(
                            value="✅ API key validated successfully!"
                        )
                    except Exception as e:
                        GROQ_CLIENT = None
                        # Move error handling inside the except block
                        error_type = (
                            "invalid_api_key"
                            if "invalid_api_key" in str(e).lower()
                            else "connection"
                        )
                        if error_type == "invalid_api_key":
                            error_msg = "❌ Invalid API key: Please check your API key and try again"
                        else:
                            error_msg = f"❌ Connection error: {str(e)}\nPlease check your internet connection and try again"
                        return gr.update(value="Local Whisper"), gr.update(
                            value=error_msg, visible=True
                        )

                def update_api_key_visibility(choice):
                    """Show/hide API key input and status based on model choice"""
                    is_groq = choice == "Groq API"
                    needs_key = is_groq and GROQ_CLIENT is None

                    key_visible = needs_key
                    status_visible = needs_key or (is_groq and GROQ_CLIENT is not None)
                    status_value = (
                        "✅ Using configured API key"
                        if is_groq and GROQ_CLIENT is not None
                        else ""
                    )

                    return gr.update(visible=key_visible), gr.update(
                        visible=status_visible, value=status_value
                    )

                # Local Whisper model choices
                local_whisper_model = gr.Dropdown(
                    choices=[
                        "tiny",
                        "base",
                        "small",
                        "medium",
                        "large",
                        "large-v2",
                        "large-v3",
                    ],
                    value=MODEL_SIZE,
                    label="Local Whisper Model",
                    visible=True,
                    info="Select local Whisper model for transcription",
                )

                # Groq API model choices
                groq_model = gr.Dropdown(
                    choices=[
                        "whisper-large-v3",  # Full Whisper model
                        "whisper-large-v3-turbo",  # Pruned model for speed
                        "distil-whisper-large-v3-en",  # English-only model
                    ],
                    value="whisper-large-v3",
                    label="Groq API Model",
                    visible=False,
                    info="""
                    • whisper-large-v3: Best accuracy, multilingual (recommended)
                    • whisper-large-v3-turbo: Faster, multilingual (216x realtime)
                    • distil-whisper-large-v3-en: Fastest, English-only (250x realtime)
                    
                    Translation is only available with whisper-large-v3
                    """,
                )

                # Add translation option for Groq API
                groq_translate = gr.Checkbox(
                    label="Translate to English",
                    value=False,
                    visible=False,
                    info="Use Groq's translation endpoint to translate audio directly to English",
                )

                def update_model_visibility(choice):
                    if choice == "Local Whisper":
                        return [
                            gr.update(visible=True),  # local_whisper_model
                            gr.update(visible=False),  # groq_model
                            gr.update(visible=False),  # groq_translate
                            gr.update(visible=False),  # groq_api_key
                        ]
                    else:
                        api_key_visible = GROQ_CLIENT is None
                        return [
                            gr.update(visible=False),  # local_whisper_model
                            gr.update(visible=True),  # groq_model
                            gr.update(visible=True),  # groq_translate
                            gr.update(visible=api_key_visible),  # groq_api_key
                        ]

                def update_model_on_translate(translate_enabled):
                    """Update the model when translation is enabled/disabled"""
                    if translate_enabled:
                        return gr.update(value="whisper-large-v3", interactive=False)
                    else:
                        return gr.update(interactive=True)

                # Update visibility when model choice changes
                model_choice.change(
                    fn=update_model_visibility,
                    inputs=[model_choice],
                    outputs=[
                        local_whisper_model,
                        groq_model,
                        groq_translate,
                        groq_api_key,
                    ],
                )

                # Add status message for API key validation
                api_status = gr.Textbox(
                    label="API Status", interactive=False, visible=False
                )

                # Validate API key when entered
                groq_api_key.change(
                    fn=validate_and_update_groq_client,
                    inputs=[groq_api_key],
                    outputs=[model_choice, api_status],
                )

                # Update status message and API key visibility when model choice changes
                model_choice.change(
                    fn=update_api_key_visibility,
                    inputs=[model_choice],
                    outputs=[groq_api_key, api_status],
                )

                groq_translate.change(
                    fn=update_model_on_translate,
                    inputs=[groq_translate],
                    outputs=[groq_model],
                )
            with gr.Column():
                with gr.Tab("URL Input"):
                    url_input = gr.Textbox(
                        label="Video URL",
                        placeholder="Enter URL (e.g., YouTube, Vimeo, direct link)...",
                        lines=1,
                    )

                with gr.Tab("File Upload"):
                    file_input = gr.File(
                        label="Upload Video", file_types=["video"], file_count="single"
                    )
                output_dir = gr.Textbox(
                    label="Output Directory",
                    placeholder="Select output folder using the button below",
                    value=DEFAULT_OUTPUT_DIR,
                    interactive=False,
                )
                select_btn = gr.Button("📂 Browse Output Directory", variant="primary")

                # Add language dropdown
                language_dropdown = gr.Dropdown(
                    choices=list(LANGUAGES.values()),
                    value="Auto Detect",
                    label="Transcription Language",
                    info="Select target language or Auto Detect",
                )

                # Add transcribe button
                transcribe_btn = gr.Button(
                    "🎯 Transcribe Video", variant="primary", size="large"
                )

                # Outputs
                transcription = gr.Textbox(label="Transcription", lines=15)
                srt_file = gr.File(label="Download SRT")
                text_file = gr.File(label="Download Text")

        # Add helpful notes
        gr.Markdown(
            """
        ### Notes:
        - By default, files are saved in a folder named after the video
        - Each transcription creates three files:
          - Video file (.mp4)
          - Subtitles file (.srt)
          - Text transcription (.txt)
        - Use the Browse button to choose a specific output folder, or let the app organize files automatically
        """
        )

        # Wire up the events
        select_btn.click(fn=select_directory, outputs=output_dir)

        def get_language_code(language_name):
            # Find the language code for the selected language name
            for code, name in LANGUAGES.items():
                if name == language_name:
                    return code
            return "auto"  # Default to auto if not found

        def transcribe_with_groq(
            audio_path: str,
            language: str = "auto",
            model: str = "whisper-large-v3-turbo",
            translate: bool = False,
        ) -> dict:
            """Transcribe or translate audio using Groq's API."""
            try:
                # Convert audio to FLAC with proper specs
                import subprocess
                from tempfile import NamedTemporaryFile

                temp_flac = None
                try:
                    # Convert to FLAC with proper specs
                    temp_flac = NamedTemporaryFile(suffix=".flac", delete=False)
                    # Convert to FLAC with proper specs and suppress output
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-i",
                            audio_path,
                            "-ar",
                            "16000",  # 16kHz sample rate
                            "-ac",
                            "1",  # Mono audio
                            "-map",
                            "0:a",  # Only audio track
                            "-c:a",
                            "flac",  # FLAC codec
                            "-y",  # Overwrite without asking
                            "-loglevel",
                            "error",  # Suppress output
                            temp_flac.name,
                        ],
                        check=True,
                        capture_output=True,
                    )

                    # Close the temporary file to ensure it's written
                    temp_flac.close()

                    # Process the audio file with proper file handle management
                    with open(temp_flac.name, "rb") as audio_file:
                        # Read the file content once
                        file_content = audio_file.read()

                    # Use the appropriate endpoint based on translate flag
                    if translate:
                        # Check if translation is supported by the selected model
                        if model != "whisper-large-v3":
                            raise RuntimeError(
                                "Translation is only supported with the whisper-large-v3 model. The model has been automatically selected for you."
                            )

                        # Use translations endpoint
                        response = GROQ_CLIENT.audio.translations.create(
                            file=("audio.flac", file_content),
                            model="whisper-large-v3",  # Always use full model for translation
                            response_format="verbose_json",
                            temperature=0.0,
                        ).model_dump_json() # Use model_dump_json instead of json
                    else:
                        # Use transcriptions endpoint
                        response = GROQ_CLIENT.audio.transcriptions.create(
                            file=("audio.flac", file_content),
                            model=model,
                            language=None if language == "auto" else language,
                            response_format="verbose_json",
                            timestamp_granularities=["segment"],
                            temperature=0.0,
                        ).model_dump_json() # Use model_dump_json instead of json

                    # Extract text and segments
                    # Need to parse the JSON string returned by model_dump_json
                    response_dict = json.loads(response)

                    if isinstance(response_dict, dict):
                        transcription_text = response_dict.get("text", "").strip()
                        segments = []

                        # Process segments while preserving original text and timing
                        for segment in response_dict.get("segments", []):
                            if (
                                isinstance(segment, dict)
                                and segment.get("text", "").strip()
                            ):
                                segments.append(
                                    {
                                        "start": float(segment.get("start", 0)),
                                        "end": float(segment.get("end", 0)),
                                        "text": segment.get("text", "").strip(),
                                    }
                                )
                    else:
                        # Handle case where response might not be a dict after parsing
                        transcription_text = str(response_dict).strip()
                        segments = [
                            {
                                "start": 0,
                                "end": len(transcription_text.split()) * 0.3,
                                "text": transcription_text,
                            }
                        ]

                    result = {"text": transcription_text, "segments": segments}
                    return result
                finally:
                    # Clean up temporary file
                    if temp_flac and os.path.exists(temp_flac.name):
                        os.unlink(temp_flac.name)
            except Exception as e:
                raise RuntimeError(f"Groq API transcription failed: {str(e)}")

        def handle_transcription(
            url, file, dir, lang, model_choice, local_model, groq_model, translate
        ):
            if not file and not url:
                return (
                    "Please provide either a video URL or upload a video file.",
                    None,
                    None,
                )

            try:
                # Get language code
                lang_code = get_language_code(lang)

                if model_choice == "Local Whisper":
                    global WHISPER_MODEL, MODEL_SIZE
                    # Update WHISPER_MODEL if model selection changed
                    if local_model != MODEL_SIZE:
                        MODEL_SIZE = local_model
                        WHISPER_MODEL = None
                        load_whisper_model()

                    if file is not None:
                        return transcribe_local_video(file.name, dir, lang_code)
                    else:
                        return transcribe_video_from_url(url, dir, lang_code)
                else:
                    # Check if Groq client is available
                    if GROQ_CLIENT is None:
                        return (
                            "Error: Groq API is not configured. Please check your API key configuration.",
                            None,
                            None,
                        )

                    # Using Groq API
                    try:
                        if file is not None:
                            # Get safe file name for output
                            video_path = file.name
                            video_title = Path(file.name).stem

                            # Process with Groq
                            result = transcribe_with_groq(
                                video_path, lang_code, groq_model, translate
                            )
                        else:
                            # Download video and use Groq API
                            temp_dir = tempfile.mkdtemp()
                            try:
                                with yt_dlp.YoutubeDL(
                                    {
                                        "format": "best",  # Get best quality for consistent output
                                        "outtmpl": os.path.join(
                                            temp_dir, "%(title)s.%(ext)s"
                                        ),
                                    }
                                ) as ydl:
                                    info = ydl.extract_info(url, download=True)
                                    video_title = info.get("title", "downloaded_video")
                                    downloaded_files = os.listdir(temp_dir)
                                    if not downloaded_files:
                                        raise FileNotFoundError(
                                            "No file found after download."
                                        )
                                    video_path = os.path.join(
                                        temp_dir, downloaded_files[0]
                                    )

                                    # Process with Groq
                                    result = transcribe_with_groq(
                                        video_path, lang_code, groq_model, translate
                                    )

                                    # Create safe title for directory name
                                    safe_title = "".join(
                                        c
                                        for c in video_title
                                        if c.isalnum() or c in (" ", "-", "_")
                                    ).strip()

                                    # If using default directory, create a subdirectory with the video title
                                    if not dir or dir == DEFAULT_OUTPUT_DIR:
                                        dir = os.path.join(
                                            DEFAULT_OUTPUT_DIR, safe_title
                                        )

                                    # Save files using the same function as local Whisper
                                    video_path_out, text_path, srt_path = (
                                        save_output_files(
                                            dir,
                                            safe_title,
                                            result["text"],
                                            generate_srt_content(result),
                                            video_path,
                                        )
                                    )

                                    return result["text"], srt_path, text_path
                            finally:
                                if temp_dir and os.path.exists(temp_dir):
                                    shutil.rmtree(temp_dir)

                        # For file uploads, use the same format
                        safe_title = "".join(
                            c
                            for c in video_title
                            if c.isalnum() or c in (" ", "-", "_")
                        ).strip()
                        if not dir or dir == DEFAULT_OUTPUT_DIR:
                            dir = os.path.join(DEFAULT_OUTPUT_DIR, safe_title)

                        # Save files using the same function as local Whisper
                        _, text_path, srt_path = save_output_files(
                            dir,
                            safe_title,
                            result["text"],
                            generate_srt_content(result),
                            video_path,
                        )

                        return result["text"], srt_path, text_path

                    except Exception as e:
                        print(f"Error processing with Groq API: {str(e)}")
                        import traceback

                        traceback.print_exc()
                        return f"Error during Groq API processing: {str(e)}", None, None
            except Exception as e:
                return f"Error during transcription: {str(e)}", None, None

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
            outputs=[transcription, srt_file, text_file],
        )

    # Launch with all output directories allowed
    app.launch(allowed_paths=[DEFAULT_OUTPUT_DIR])
