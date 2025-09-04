import os
import tempfile
import yt_dlp

def test_download():
    temp_dir = tempfile.mkdtemp()
    
    ydl_opts = {
        'format': 'best[height<=720]/best',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'quiet': True,
    }
    
    url = "https://www.youtube.com/watch?v=w6Ro4hmVMYk"
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            files = os.listdir(temp_dir)
            print(f"SUCCESS: Downloaded {len(files)} file(s)")
            return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    test_download()