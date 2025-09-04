#!/usr/bin/env python3
"""
Fix script for YouTube download issues
"""
import subprocess
import sys
import os

def update_ytdlp():
    """Update yt-dlp to the latest version"""
    print("Updating yt-dlp to the latest version...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
        print("✓ yt-dlp updated successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to update yt-dlp: {e}")
        return False

def test_download():
    """Test download functionality"""
    print("\nTesting YouTube download...")
    try:
        from test_download import test_youtube_download
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll - should always be available
        success = test_youtube_download(url)
        if success:
            print("✓ YouTube download test passed")
        else:
            print("✗ YouTube download test failed")
        return success
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False

def check_ffmpeg():
    """Check if FFmpeg is available"""
    print("\nChecking FFmpeg availability...")
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("✓ FFmpeg is available")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ FFmpeg not found. Please install FFmpeg:")
        print("  - Windows: Download from https://ffmpeg.org/download.html")
        print("  - Or use chocolatey: choco install ffmpeg")
        return False

def main():
    print("YouTube Download Fix Script")
    print("=" * 30)
    
    # Check FFmpeg first
    ffmpeg_ok = check_ffmpeg()
    
    # Update yt-dlp
    ytdlp_ok = update_ytdlp()
    
    # Test download
    if ytdlp_ok:
        test_ok = test_download()
    else:
        test_ok = False
    
    print("\n" + "=" * 30)
    print("Summary:")
    print(f"FFmpeg: {'✓' if ffmpeg_ok else '✗'}")
    print(f"yt-dlp update: {'✓' if ytdlp_ok else '✗'}")
    print(f"Download test: {'✓' if test_ok else '✗'}")
    
    if all([ffmpeg_ok, ytdlp_ok, test_ok]):
        print("\n🎉 All checks passed! YouTube downloads should work now.")
    else:
        print("\n⚠️  Some issues remain. Check the errors above.")

if __name__ == "__main__":
    main()