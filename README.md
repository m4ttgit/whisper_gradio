# Video Transcriber (Whisper via Local & Groq API)

A Python application that downloads videos from various sources (YouTube, Vimeo, etc.) and transcribes them using OpenAI's Whisper model. It supports both local processing and transcription via the Groq API for faster performance. The application provides text transcription and SRT subtitle files.

## Features

- Downloads videos from various sources (YouTube, Vimeo, direct links)
- Transcribes audio using Whisper (supports local processing or Groq API)
- Generates SRT subtitle files with timestamps
- User-friendly Gradio web interface
- Customizable output directory
- Supports multiple video formats
- Handles temporary files automatically
- Saves original video along with transcription
- Configuration via `.env` file for API keys

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

Additionally, you need [FFmpeg](https://ffmpeg.org/download.html) installed on your system and available in your PATH.

## Installation

1.  Clone this repository:
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
2.  Create a `.env` file by copying the example:
    ```bash
    copy .env.example .env
    ```
    (Use `cp .env.example .env` on Linux/macOS)
3.  Edit the `.env` file and add your Groq API key:
    ```
    GROQ_API_KEY=your_actual_groq_api_key
    ```
4.  Install the required packages:
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

## Configuration

-   **API Keys**: The application requires API keys for certain services (like Groq). These should be stored in a `.env` file in the project root. Create this file by copying `.env.example` and filling in your keys.
-   **Local Model**: If using local transcription, the Whisper model size can be configured in `main.py`. The default is `medium`.

## Notes

- The application can utilize either local Whisper processing or the Groq API for transcription, potentially configurable in the interface or code.
- Files are automatically saved with the original video title (sanitized for filesystem compatibility).
- Temporary files are cleaned up automatically after processing.
- For local GPU acceleration, ensure you have a compatible NVIDIA GPU and necessary drivers/CUDA toolkit installed. Relevant settings might be in `transcription.py` or `utils.py`.

## Default Settings

- Default Output Directory: `./outputs/`
- Local Model Size (if used): `medium` (configurable in code)
- API Provider (if used): Groq (requires API key in `.env`)

Check `main.py` or related configuration files for specific default parameters.
