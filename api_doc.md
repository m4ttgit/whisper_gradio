API documentation
http://127.0.0.1:7860/

API Recorder

4 API endpoints

Choose a language to see the code snippets for interacting with the API.

1. Install the python client (docs) if you don't already have it installed.

copy
$ pip install gradio_client 2. Find the API endpoint below corresponding to your desired function in the app. Copy the code snippet, replacing the placeholder values with your own input data. Or use the
API Recorder

to automatically generate your API requests.

api_name: /update_groq_api_key_ui
copy
from gradio_client import Client

client = Client("http://127.0.0.1:7860/")
result = client.predict(
method_choice="Local Whisper",
api_key="Hello!!",
api_name="/update_groq_api_key_ui"
)
print(result)
Accepts 2 parameters:
method_choice Literal['Local Whisper', 'Groq API'] Default: "Local Whisper"

The input value that is provided in the "Transcription Method" Radio component.

api_key str Required

The input value that is provided in the "Groq API Key" Textbox component.

Returns tuple of 5 elements
[0] str

The output value that appears in the "Groq API Key" Textbox component.

[1] str
