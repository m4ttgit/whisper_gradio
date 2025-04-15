"""
Utility functions for the video transcription application.

This module provides helper functions for formatting timestamps,
generating SRT content, checking dependencies, and UI interactions.
"""

# Standard library imports
import datetime
import os
import shutil
import sys
import tkinter as tk
from tkinter import filedialog
from typing import Dict, Any


def format_timestamp(seconds: float) -> str:
    """Format seconds into SRT timestamp format HH:MM:SS,ms.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string in SRT format
        
    Raises:
        AssertionError: If seconds is negative
    """
    assert seconds >= 0, "non-negative timestamp expected"
    
    milliseconds = round(seconds * 1000.0)
    td = datetime.timedelta(milliseconds=milliseconds)
    
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def generate_srt_content(result: Dict[str, Any]) -> str:
    """Generate SRT content as a string from Whisper results.
    
    Args:
        result: Dictionary containing transcription results with segments
        
    Returns:
        String containing SRT formatted content
    """
    srt_content = []
    
    for i, segment in enumerate(result.get("segments", []), start=1):
        start_time = format_timestamp(segment["start"])
        end_time = format_timestamp(segment["end"])
        text = segment["text"].strip()
        
        srt_segment = f"{i}\n{start_time} --> {end_time}\n{text}\n"
        srt_content.append(srt_segment)
        
    return "\n".join(srt_content)


def check_yt_dlp() -> None:
    """Check if yt-dlp is installed and accessible.
    
    Exits the program if yt-dlp is not found.
    """
    if shutil.which("yt-dlp") is None:
        print("Error: yt-dlp command not found.")
        print("Please install it using 'pip install -U yt-dlp'")
        sys.exit(1)
        
    print("yt-dlp found.")


def select_directory(initial_dir: str = None) -> str:
    """Open directory picker dialog and return selected path.
    
    Args:
        initial_dir: Initial directory to show in the dialog
        
    Returns:
        Selected directory path or initial_dir if canceled
    """
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    
    directory = filedialog.askdirectory(initialdir=initial_dir or os.getcwd())
    
    return directory if directory else initial_dir or os.getcwd()
