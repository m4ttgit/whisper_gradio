## System Patterns: Whisper Gradio API

### System Architecture
- **main.py:** The main application entry point, likely containing the Gradio interface.
- **api_call.py:** Handles communication with the Whisper API.
- **transcription.py:** Contains functions related to audio transcription.
- **utils.py:** Provides utility functions for various tasks.

### Key Technical Decisions
- Using Gradio for the user interface.
- Using environment variables for configuration.
- Potentially using a JSON file (`whisper_workflow.json`) to define the transcription workflow.

### Design Patterns
- Likely using a modular design with separate files for API calls, transcription logic, and utility functions.
- Potentially using a configuration pattern with environment variables.

### Component Relationships
- `main.py` uses functions from `api_call.py`, `transcription.py`, and `utils.py`.
- `api_call.py` interacts with the Whisper API.
- `transcription.py` performs audio transcription tasks.
- `utils.py` provides supporting functions.

### Critical Implementation Paths
- User uploads audio or provides a YouTube URL in `main.py`.
- `main.py` calls `api_call.py` to send the audio to the Whisper API.
- `api_call.py` receives the transcription from the Whisper API.
- `main.py` displays the transcription to the user.
