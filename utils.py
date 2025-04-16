import datetime
import os
import tkinter as tk
from tkinter import filedialog
import shutil

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
    for i, segment in enumerate(result.get("segments", []), start=1):
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
