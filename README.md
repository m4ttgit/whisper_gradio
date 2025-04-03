# Video Transcriber (Cantonese)

A Python application that downloads videos from various sources (YouTube, Vimeo, etc.) and transcribes them to Cantonese text using OpenAI's Whisper model. The application provides both text transcription and SRT subtitle files.

## Features

- Downloads videos from various sources (YouTube, Vimeo, direct links)
- Transcribes audio to Cantonese text using Whisper
- Generates SRT subtitle files with timestamps
- User-friendly Gradio web interface
- Customizable output directory
- Supports multiple video formats
- Handles temporary files automatically
- Saves original video along with transcription

## Requirements

```
openai-whisper>=20231117
torch>=2.0.0
transformers>=4.30.0
gradio>=3.50.0
pysrt>=1.1.2
yt-dlp>=2023.3.4
librosa>=0.10.0
ffmpeg-python>=0.2.0
sentencepiece>=0.1.99
```

Additionally, you need FFmpeg installed on your system.

## Installation

1. Clone this repository
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
   python main.py
   ```

2. Access the web interface through your browser (typically at http://localhost:7860)

3. Enter a video URL in the input field

4. (Optional) Click "Browse Output Directory" to choose where to save the files

5. Click "Transcribe Video" to start the process

## Output Files

For each transcription, the following files are generated in the output directory:

- `{video_title}.mp4` - The downloaded video
- `{video_title}.srt` - Subtitle file with timestamps
- `{video_title}.txt` - Plain text transcription

## Model Information

The application uses the Whisper `medium` model by default. This provides a good balance between accuracy and performance. Other available model sizes include:
- tiny
- base
- small
- medium (default)
- large
- large-v2
- large-v3

## Notes

- The model is loaded when the application starts
- Files are automatically saved with the original video title (sanitized for filesystem compatibility)
- Temporary files are cleaned up automatically after processing
- For GPU acceleration, uncomment the CUDA line in `load_whisper_model()` if you have a compatible NVIDIA GPU

## Default Settings

- Model Size: medium
- Language: Chinese (optimized for Cantonese)
- Default Output Directory: `./outputs/`

These settings can be modified in the `main.py` file by adjusting the global variables at the top of the script.
