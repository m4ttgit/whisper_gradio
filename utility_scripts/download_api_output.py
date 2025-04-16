import os
import requests
import datetime
from gradio_client import Client, handle_file


def save_content(content, filename):
    os.makedirs("outputs", exist_ok=True)
    filepath = os.path.join("outputs", filename)
    with open(
        filepath,
        "wb" if isinstance(content, bytes) else "w",
        encoding=None if isinstance(content, bytes) else "utf-8",
    ) as f:
        f.write(content)
    print(f"Saved output to {filepath}")


def download_file(url, filename=None):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    if not filename:
        filename = url.split("/")[-1]
    save_content(response.content, filename)


def main():
    try:
        client = Client("http://127.0.0.1:7860/")
        result = client.predict(
            url="https://www.youtube.com/shorts/7cfoMtZ7VKQ",
            file=handle_file(
                r"D:\Projects\whisper_gradio\outputs\信仰有問題 預告EP8雷競業博士基督徒一定要參與事奉未信者可否參與信仰有問題 事奉 基督徒\信仰有問題 預告EP8雷競業博士基督徒一定要參與事奉未信者可否參與信仰有問題 事奉 基督徒.mp4"
            ),
            dir="",
            lang="Auto Detect",
            model_choice="Local Whisper",
            local_model="medium",
            groq_model="whisper-large-v3",
            translate=False,
            api_name="/gradio_api/api/handle_transcription",
        )
        print("API response:", result)

        # Determine how to handle the response
        if isinstance(result, str):
            if result.startswith("http://") or result.startswith("https://"):
                print("Detected URL in response, downloading...")
                download_file(result)
            else:
                # Save as text
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                save_content(result, f"api_output_{timestamp}.txt")
        elif isinstance(result, list):
            for idx, item in enumerate(result):
                if isinstance(item, str) and (
                    item.startswith("http://") or item.startswith("https://")
                ):
                    print(f"Downloading file from URL in list item {idx}...")
                    download_file(item)
                else:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    save_content(str(item), f"api_output_{timestamp}_{idx}.txt")
        elif isinstance(result, dict):
            for key, value in result.items():
                if isinstance(value, str) and (
                    value.startswith("http://") or value.startswith("https://")
                ):
                    print(f"Downloading file from URL in dict key '{key}'...")
                    download_file(value)
                else:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    save_content(str(value), f"api_output_{timestamp}_{key}.txt")
        else:
            # Unknown type, save string representation
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            save_content(str(result), f"api_output_{timestamp}.txt")

    except Exception as e:
        print("Error during API call or download:", e)


if __name__ == "__main__":
    main()
