#!/usr/bin/env python3
"""
Simple test script to verify YouTube download functionality
"""
import os
import tempfile
import yt_dlp

def test_youtube_download(url):
    """Test YouTube download with minimal configuration"""
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Minimal configuration that should work
        ydl_opts = {
            'format': 'best[height<=720]/best',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
        print(f"Testing download from: {url}")
        print(f"Temp directory: {temp_dir}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Unknown')
                print(f"SUCCESS: Downloaded '{title}'")
                
                # List downloaded files
                files = os.listdir(temp_dir)
                print(f"Downloaded files: {files}")
                return True
                
            except Exception as e:
                print(f"FAILED: {e}")
                return False
                
    finally:
        # Clean up
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    # Test with a simple YouTube URL
    test_url = "https://www.youtube.com/watch?v=w6Ro4hmVMYk"
    test_youtube_download(test_url)