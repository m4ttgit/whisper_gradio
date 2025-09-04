import datetime
import os
import tkinter as tk
from tkinter import filedialog
import shutil
import datetime
import time
from pathlib import Path

def format_timestamp(seconds: float) -> str:
    """Formats seconds into SRT timestamp format HH:MM:SS,ms"""
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)
    td = datetime.timedelta(milliseconds=milliseconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def generate_srt_content(segments) -> str:
    """Generates SRT content as a string from Whisper results."""
    srt_content = ""
    if isinstance(segments, list):
        for i, segment in enumerate(segments, start=1):
            start_time = format_timestamp(segment["start"])
            end_time = format_timestamp(segment["end"])
            text = segment["text"].strip()
            srt_content += f"{i}\n{start_time} --> {end_time}\n{text}\n\n"
        return srt_content
    srt_content = []
    for i, segment in enumerate(segments.get("segments", []), start=1):
        start_time = format_timestamp(segment["start"])
        end_time = format_timestamp(segment["end"])
        text = segment["text"].strip()
        srt_segment = f"{i}\n{start_time} --> {end_time}\n{text}\n"
        srt_content.append(srt_segment)
    return "\n".join(srt_content)

def check_yt_dlp():
    """Checks if yt-dlp is installed and accessible."""
    if shutil.which("yt-dlp") is None:
        print("Error: yt-dlp command not found.")
        print("Please install it using 'pip install -U yt-dlp'")
        import sys; sys.exit(1)
    print("yt-dlp found.")

def select_directory(initial_dir=None):
    """Open directory picker dialog and return selected path."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    directory = filedialog.askdirectory(initialdir=initial_dir or os.getcwd())
    return directory if directory else initial_dir or os.getcwd()


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
