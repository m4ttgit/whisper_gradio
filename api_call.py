import requests
import time
import os
import json

# CONFIGURABLE PARAMETERS
API_BASE = "http://127.0.0.1:7860/gradio_api/api"
TRANSCRIBE_ENDPOINT = f"{API_BASE}/handle_transcription"
JOB_STATUS_ENDPOINT = f"{API_BASE}/job_status"
POLL_INTERVAL = 10  # seconds

def submit_transcription_job(youtube_url, file_path, lang="Auto Detect", model_choice="Local Whisper", local_model="medium", groq_model="whisper-large-v3", translate=False):
    # Prepare data for POST
    data_dict = {
        "url": youtube_url,
        "dir": "",
        "lang": lang,
        "model_choice": model_choice,
        "local_model": local_model,
        "groq_model": groq_model,
        "translate": str(translate).lower()
    }
    data = {"data": json.dumps(data_dict)}
    files = None
    if file_path:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "video/mp4")}
            response = requests.post(TRANSCRIBE_ENDPOINT, data=data, files=files)
    else:
        response = requests.post(TRANSCRIBE_ENDPOINT, data=data)
    response.raise_for_status()
    result = response.json()
    job_id = result.get("job_id")
    if not job_id:
        raise Exception(f"No job_id returned: {result}")
    print(f"Job submitted. Job ID: {job_id}")
    return job_id

def poll_job_status(job_id):
    while True:
        try:
            response = requests.get(JOB_STATUS_ENDPOINT, params={"job_id": job_id})
            response.raise_for_status()
            result = response.json()
            status = result.get("status")
            if status == "complete":
                print("Transcription complete. Result:")
                print(result.get("result"))
                return result.get("result")
            elif status == "failed":
                print("Transcription failed.")
                print(result)
                return None
            else:
                print(f"Job status: {status}. Polling again in {POLL_INTERVAL} seconds...")
        except Exception as e:
            print(f"Error polling job status: {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    # Example usage
    YOUTUBE_URL = "https://www.youtube.com/shorts/7cfoMtZ7VKQ"
    FILE_PATH = r"D:\Projects\whisper_gradio\outputs\信仰有問題 預告EP8雷競業博士基督徒一定要參與事奉未信者可否參與信仰有問題 事奉 基督徒\信仰有問題 預告EP8雷競業博士基督徒一定要參與事奉未信者可否參與信仰有問題 事奉 基督徒.mp4"

    try:
        job_id = submit_transcription_job(YOUTUBE_URL, FILE_PATH)
        poll_job_status(job_id)
    except Exception as e:
        print("Error in transcription workflow:", e)

# TODO: 
# - Ensure your backend supports job submission and polling as described.
# - If not, backend changes are required.
# - Adjust endpoint URLs and parameters as needed to match your API.
