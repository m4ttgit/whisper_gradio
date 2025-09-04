# Troubleshooting Guide

## YouTube Download Issues (403 Forbidden)

If you're getting 403 Forbidden errors when trying to download YouTube videos, try these solutions:

### Quick Fix
1. Run the fix script:
   ```bash
   python fix_youtube.py
   ```

### Manual Steps

1. **Update yt-dlp to the latest version:**
   ```bash
   pip install --upgrade yt-dlp
   ```

2. **Test with a simple video:**
   ```bash
   python test_download.py
   ```

3. **Check FFmpeg installation:**
   ```bash
   ffmpeg -version
   ```

### Alternative Solutions

1. **Try different video URLs:**
   - Some videos may be geo-blocked or private
   - Try with public, non-restricted videos

2. **Use audio-only mode:**
   - The app will automatically fallback to audio-only if video download fails

3. **Upload video files directly:**
   - Use the file upload option instead of URL download

## Groq API Issues

If you see "Invalid API Key" errors:

1. **Get a valid Groq API key:**
   - Visit https://console.groq.com/
   - Create an account and generate an API key

2. **Update your .env file:**
   ```
   GROQ_API_KEY=your-actual-api-key-here
   ```

3. **Restart the application:**
   ```bash
   python main.py
   ```

## Common Issues

### FFmpeg Not Found
- **Windows:** Download from https://ffmpeg.org/download.html
- **Or use chocolatey:** `choco install ffmpeg`

### Model Loading Issues
- Ensure you have enough disk space (models can be several GB)
- Check internet connection for initial model download

### Permission Errors
- Run as administrator if needed
- Check file permissions in the output directory

## Getting Help

If issues persist:
1. Check the console output for detailed error messages
2. Try with different video URLs
3. Ensure all dependencies are installed: `pip install -r requirements.txt`