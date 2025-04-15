"""
Client script to interact with the transcription API.

This script submits a transcription job (either via URL or file upload)
to the FastAPI backend and polls for the job status until completion or failure.
"""

import requests
import time
import os
import json
from typing import Optional, Dict, Any

# --- Configuration ---
API_BASE_URL = "http://127.0.0.1:7861"  # Updated port for FastAPI
# Ensure this matches the endpoint prefix and function name in main.py
TRANSCRIBE_ENDPOINT = f"{API_BASE_URL}/gradio_api/api/handle_transcription"
JOB_STATUS_ENDPOINT = f"{API_BASE_URL}/gradio_api/api/job_status"
POLL_INTERVAL_SECONDS = 10  # Time between status checks

# --- Functions ---

def submit_transcription_job(
    youtube_url: Optional[str] = None,
    file_path: Optional[str] = None,
    lang: str = "Auto Detect",
    model_choice: str = "Local Whisper",
    local_model: str = "medium",
    groq_model: str = "whisper-large-v3",
    translate: bool = False
) -> Optional[str]:
    """Submits a transcription job to the API.

    Args:
        youtube_url: URL of the YouTube video (optional).
        file_path: Path to the local video file (optional).
        lang: Language for transcription.
        model_choice: Transcription method ('Local Whisper' or 'Groq API').
        local_model: Model size for Local Whisper.
        groq_model: Model name for Groq API.
        translate: Whether to translate the output to English.

    Returns:
        The job ID if submission is successful, otherwise None.

    Raises:
        ValueError: If neither youtube_url nor file_path is provided.
        requests.exceptions.RequestException: For network or HTTP errors.
        Exception: For other errors like missing job_id.
    """
    if not youtube_url and not file_path:
        raise ValueError("Either youtube_url or file_path must be provided.")
    if youtube_url and file_path:
        print("Warning: Both URL and file path provided. Using file path.")
        youtube_url = None # Prioritize file path if both given

    # Prepare form data for POST request
    # FastAPI expects individual form fields, not a nested JSON blob
    form_data = {
        "url": youtube_url or "", # Send empty string if None
        "dir": "",
        "lang": lang,
        "model_choice": model_choice,
        "local_model": local_model,
        "groq_model": groq_model,
        "translate": str(translate).lower() # Send as string 'true' or 'false'
    }

    files = None
    request_kwargs = {"data": form_data}

    if file_path:
        if not os.path.exists(file_path):
            print(f"Error: File not found at {file_path}")
            return None
        # Prepare file for upload
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "video/mp4")}
        request_kwargs["files"] = files
        # Remove URL from form data if file is present
        request_kwargs["data"]["url"] = ""


    print(f"Submitting job to {TRANSCRIBE_ENDPOINT}...")
    try:
        response = requests.post(TRANSCRIBE_ENDPOINT, **request_kwargs)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        result = response.json()

        job_id = result.get("job_id")
        if not job_id:
            raise Exception(f"API did not return a job_id. Response: {result}")

        print(f"Job submitted successfully. Job ID: {job_id}")
        return job_id

    except requests.exceptions.RequestException as e:
        print(f"Network or HTTP error submitting job: {e}")
        print(f"Response status: {e.response.status_code if e.response else 'N/A'}")
        print(f"Response text: {e.response.text if e.response else 'N/A'}")
        raise
    except json.JSONDecodeError:
        print("Error: Could not decode JSON response from server.")
        print(f"Response text: {response.text}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred during job submission: {e}")
        raise
    finally:
        # Ensure the file is closed if opened
        if files and "file" in files:
            files["file"][1].close()


def poll_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Polls the API for the status of a given job ID.

    Args:
        job_id: The ID of the job to poll.

    Returns:
        The result dictionary if the job is complete, otherwise None for failure or error.
    """
    print(f"Polling status for Job ID: {job_id}...")
    while True:
        try:
            response = requests.get(JOB_STATUS_ENDPOINT, params={"job_id": job_id})
            response.raise_for_status()
            result = response.json()
            status = result.get("status")

            if status == "complete":
                print("\n--- Transcription Complete ---")
                final_result = result.get("result", {})
                print(json.dumps(final_result, indent=2))
                print("----------------------------")
                return final_result
            elif status == "failed":
                print("\n--- Transcription Failed ---")
                error_details = result.get("result", {})
                print(json.dumps(error_details, indent=2))
                print("--------------------------")
                return None
            elif status == "pending":
                print(f"Job status: {status}. Polling again in {POLL_INTERVAL_SECONDS} seconds...")
            elif status == "not_found":
                print(f"Error: Job ID '{job_id}' not found on the server.")
                return None
            else:
                print(f"Unknown job status received: {status}. Continuing to poll...")

        except requests.exceptions.RequestException as e:
            print(f"Network or HTTP error polling job status: {e}")
            # Continue polling after a delay
        except json.JSONDecodeError:
            print("Error: Could not decode JSON response during polling.")
            print(f"Response text: {response.text}")
            # Continue polling after a delay
        except Exception as e:
            print(f"An unexpected error occurred during polling: {e}")
            # Continue polling after a delay

        time.sleep(POLL_INTERVAL_SECONDS)


# --- Main Execution ---

if __name__ == "__main__":
    # --- Example Usage ---
    # Choose ONE of the following methods to test:

    # 1. Test with YouTube URL:
    # TEST_URL = "https://www.youtube.com/shorts/7cfoMtZ7VKQ" # Replace with a valid short URL
    # TEST_FILE_PATH = None

    # 2. Test with Local File:
    TEST_URL = None
    # IMPORTANT: Replace with the ACTUAL path to a video file on your system
    TEST_FILE_PATH = r"D:\Projects\whisper_gradio\outputs\example_video.mp4"

    # --- End of selection ---

    print("--- Starting Transcription Request ---")
    submitted_job_id = None
    try:
        # Validate file path if provided
        if TEST_FILE_PATH and not os.path.exists(TEST_FILE_PATH):
             raise FileNotFoundError(f"Test file not found: {TEST_FILE_PATH}")

        submitted_job_id = submit_transcription_job(
            youtube_url=TEST_URL,
            file_path=TEST_FILE_PATH
            # Add other parameters here if needed, e.g., lang="en"
        )

        if submitted_job_id:
            poll_job_status(submitted_job_id)
        else:
            print("Job submission failed. Cannot poll status.")

    except FileNotFoundError as e:
        print(f"Configuration error: {e}")
    except ValueError as e:
         print(f"Configuration error: {e}")
    except Exception as e:
        # Catch errors from submission or polling if they weren't handled internally
        print(f"An error occurred in the main workflow: {e}")

    print("--- Script Finished ---")
