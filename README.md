# Video Transcriber (Cantonese)

A Python application that downloads videos from various sources (YouTube, Vimeo, etc.) and transcribes them using either local Whisper model or Groq API. The application provides both text transcription and SRT subtitle files.

## Features

- Downloads videos from various sources (YouTube, Vimeo, direct links)
- Multiple transcription options:
  - Local Whisper model for offline processing
  - Groq API for cloud-based transcription with translation capability
- Supports multiple languages with auto-detection
- Generates SRT subtitle files with timestamps
- User-friendly Gradio web interface with FastAPI backend
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
groq>=0.4.0
python-dotenv>=1.0.0
```

Additionally, you need:
- FFmpeg installed on your system
- Groq API key (optional, for using Groq API features)

## Installation

1. Clone this repository
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) For Groq API:
   - Copy `.env.example` to `.env`
   - Add your Groq API key to `.env`:
     ```
     GROQ_API_KEY=your-api-key-here
     ```

## Usage

1. Run the application:
   ```bash
   python main.py
   ```

2. Access the web interface through your browser:
   - Gradio UI: http://localhost:7860
   - FastAPI endpoints: http://localhost:7861

3. Choose transcription method:
   - Local Whisper: Uses local CPU/GPU for processing
   - Groq API: Cloud-based processing with additional features

4. Input options:
   - Enter a video URL
   - Upload a video file

5. Configure settings:
   - Select language or use auto-detection
   - Choose model size/version
   - Enable translation (Groq API only)
   - (Optional) Select output directory

6. Click "Transcribe Video" to start the process

## Output Files

For each transcription, the following files are generated in the output directory:

- `{video_title}.mp4` - The downloaded video
- `{video_title}.srt` - Subtitle file with timestamps
- `{video_title}.txt` - Plain text transcription

## Model Information

### Local Whisper Models
The application uses the Whisper `medium` model by default for local processing. Available model sizes:
- tiny
- base
- small
- medium (default)
- large
- large-v2
- large-v3

### Groq API Models
When using Groq API, the following models are available:
- whisper-large-v3 (default)
- whisper-large-v3-turbo
- distil-whisper-large-v3-en

Groq API features:
- Faster processing times compared to local models
- Optional translation to English
- Optimized for English transcription with distil model

## Notes

- The model is loaded when the application starts
- Files are automatically saved with the original video title (sanitized for filesystem compatibility)
- Temporary files are cleaned up automatically after processing
- For GPU acceleration, uncomment the CUDA line in `load_whisper_model()` if you have a compatible NVIDIA GPU

## Default Settings

- Local Whisper:
  - Model Size: medium
  - Language: Auto Detect
  - Default Output Directory: `./outputs/`

- Groq API:
  - Model: whisper-large-v3
  - Translation: Disabled by default
  - Language: Auto Detect

These settings can be modified through the web interface or by adjusting the global variables in `main.py`.
