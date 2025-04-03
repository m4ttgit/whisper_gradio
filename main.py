import gradio as gr
import whisper
import yt_dlp
import os
import tempfile
import datetime
import shutil  # For removing temporary directories
from pathlib import Path

# --- Global Variables ---
WHISPER_MODEL = None
MODEL_SIZE = "medium"  # Choose: tiny, base, small, medium, large, large-v2, large-v3
LANGUAGE_CODE = "zh"  # Chinese (will work for Cantonese)
DEFAULT_OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")

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
        start_time = format_timestamp(segment["start"])
        end_time = format_timestamp(segment["end"])
        text = segment["text"].strip()
        srt_content.append(f"{i}")
        srt_content.append(f"{start_time} --> {end_time}")
        srt_content.append(f"{text}\n")  # Add extra newline
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

def save_output_files(output_dir: str, video_name: str, transcription_text: str, srt_content: str, source_video_path: str):
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
    text_path.write_text(transcription_text, encoding='utf-8')
    srt_path.write_text(srt_content, encoding='utf-8')
    
    return str(video_path), str(text_path), str(srt_path)

def transcribe_video_from_url(url: str, output_dir: str = DEFAULT_OUTPUT_DIR):
    """Downloads video, transcribes, and saves all files to the specified directory."""
    if not WHISPER_MODEL:
        print("Error: Whisper model not loaded.")
        return "Error: Whisper model not loaded.", None, None

    if not url:
        return "Please enter a video URL.", None, None

    if not output_dir:
        return "Please select an output directory.", None, None

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
            video_title = info_dict.get('title', None)
            downloaded_files = os.listdir(temp_dir)
            if not downloaded_files:
                raise FileNotFoundError("No file found after download.")
            temp_video_path = os.path.join(temp_dir, downloaded_files[0])
            print(f"Video downloaded successfully to: {temp_video_path}")

        # Transcribe using Whisper
        print("Starting transcription...")
        result = WHISPER_MODEL.transcribe(
            temp_video_path, language=LANGUAGE_CODE, verbose=True, fp16=False
        )
        print("Transcription complete.")

        # Generate outputs
        transcription_text = result["text"]
        srt_content = generate_srt_content(result)

        # Save all files to the user-selected directory
        safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).strip()
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
    root.attributes('-topmost', True)  # Bring dialog to front
    directory = filedialog.askdirectory(initialdir=DEFAULT_OUTPUT_DIR)
    return directory if directory else DEFAULT_OUTPUT_DIR

# --- Launch the App ---
if __name__ == "__main__":
    # Initialize default output directory
    Path(DEFAULT_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    # Create the Gradio interface using Blocks
    with gr.Blocks(title="Video Transcriber (Cantonese)") as app:
        gr.Markdown(f"# Video Transcriber (Cantonese)")
        gr.Markdown(f"Enter a video URL to download and transcribe it into Cantonese text and SRT format using the local Whisper '{MODEL_SIZE}' model.")
        
        with gr.Row():
            with gr.Column():
                url_input = gr.Textbox(
                    label="Video URL",
                    placeholder="Enter URL (e.g., YouTube, Vimeo, direct link)...",
                    lines=1
                )
                output_dir = gr.Textbox(
                    label="Output Directory",
                    placeholder="Select output folder using the button below",
                    value=DEFAULT_OUTPUT_DIR,
                    interactive=False
                )
                select_btn = gr.Button("📂 Browse Output Directory", variant="primary")
                
                # Add transcribe button
                transcribe_btn = gr.Button("🎯 Transcribe Video", variant="primary", size="large")
                
                # Outputs
                transcription = gr.Textbox(label="Transcription", lines=15)
                srt_file = gr.File(label="Download SRT")
                text_file = gr.File(label="Download Text")
                
        # Add helpful notes
        gr.Markdown("""
        ### Notes:
        - Files will be saved with the original video title
        - Each transcription creates three files:
          - Video file (.mp4)
          - Subtitles file (.srt)
          - Text transcription (.txt)
        - Use the Browse button to choose where to save your files
        """)
        
        # Wire up the events
        select_btn.click(fn=select_directory, outputs=output_dir)
        transcribe_btn.click(
            fn=transcribe_video_from_url,
            inputs=[url_input, output_dir],
            outputs=[transcription, srt_file, text_file]
        )
    
    # Launch with all output directories allowed
    app.launch(allowed_paths=[DEFAULT_OUTPUT_DIR])
