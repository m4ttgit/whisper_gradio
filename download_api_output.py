"""
Script to interact with the Gradio API for transcription and download results.
"""

import os
import requests
import datetime
from typing import Any, Union, Dict, List
from gradio_client import Client, handle_file

OUTPUT_DIR = "outputs"


def save_content(content: Union[str, bytes], filename: str) -> None:
    """Save content to a file in the output directory.
    
    Args:
        content: The content to save (string or bytes)
        filename: The name of the file to save
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    mode = "wb" if isinstance(content, bytes) else "w"
    encoding = None if isinstance(content, bytes) else "utf-8"
    
    try:
        with open(filepath, mode, encoding=encoding) as f:
            f.write(content)
        print(f"Saved output to {filepath}")
    except Exception as e:
        print(f"Error saving file {filepath}: {e}")


def download_file(url: str, filename: str = None) -> None:
    """Download a file from a URL and save it.
    
    Args:
        url: The URL to download from
        filename: Optional filename to save as
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        if not filename:
            # Try to get filename from URL or use a default
            filename = url.split("/")[-1] or f"downloaded_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        save_content(response.content, filename)
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file from {url}: {e}")
    except Exception as e:
        print(f"Error saving downloaded file {filename}: {e}")


def handle_api_result(result: Any) -> None:
    """Process the API result, downloading files or saving text.
    
    Args:
        result: The result received from the Gradio API
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if isinstance(result, str):
        if result.startswith("http://") or result.startswith("https://"):
            print("Detected URL in response, downloading...")
            download_file(result)
        else:
            # Save as text
            save_content(result, f"api_output_{timestamp}.txt")
            
    elif isinstance(result, list):
        for idx, item in enumerate(result):
            if isinstance(item, str) and (item.startswith("http://") or item.startswith("https://")):
                print(f"Downloading file from URL in list item {idx}...")
                download_file(item)
            else:
                save_content(str(item), f"api_output_{timestamp}_{idx}.txt")
                
    elif isinstance(result, dict):
        for key, value in result.items():
            if isinstance(value, str) and (value.startswith("http://") or value.startswith("https://")):
                print(f"Downloading file from URL in dict key '{key}'...")
                download_file(value)
            else:
                save_content(str(value), f"api_output_{timestamp}_{key}.txt")
                
    else:
        # Unknown type, save string representation
        print(f"Received unknown result type: {type(result)}. Saving as text.")
        save_content(str(result), f"api_output_{timestamp}_unknown.txt")


def main() -> None:
    """Main function to call the Gradio API and handle the result."""
    # IMPORTANT: Update the file path and URL as needed for your test case.
    example_file_path = r"D:\Projects\whisper_gradio\outputs\example_video.mp4"
    example_url = "https://www.youtube.com/shorts/example_short_id"
    
    # Check if the example file exists
    if not os.path.exists(example_file_path):
        print(f"Error: Example file not found at '{example_file_path}'.")
        print("Please update 'example_file_path' in the script or ensure the file exists.")
        return

    try:
        # Initialize Gradio client (adjust URL if needed)
        client = Client("http://127.0.0.1:7860/")
        
        # Make the API prediction call
        # Choose either URL or file input for the test
        result = client.predict(
            # url=example_url,  # Uncomment to test with URL
            file=handle_file(example_file_path), # Comment out if testing with URL
            dir="",
            lang="Auto Detect",
            model_choice="Local Whisper",
            local_model="medium",
            groq_model="whisper-large-v3",
            translate=False,
            api_name="/gradio_api/api/handle_transcription", # Ensure this matches the endpoint in main.py
        )
        
        print("API response received.")
        handle_api_result(result)

    except Exception as e:
        print(f"Error during API call or processing: {e}")


if __name__ == "__main__":
    main()
