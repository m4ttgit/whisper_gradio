# Project Brief: Whisper Gradio API - YouTube Transcription SRT

## Core Requirements and Goals

- **Primary Goal:** Provide a user-friendly interface (likely using Gradio) to interact with the Whisper API for audio transcription.
- **Key Functionality:**
    - Transcribe audio using the Whisper API.
    - Potentially handle YouTube video transcription, possibly generating SRT subtitle files.
    - Include necessary API call logic (`api_call.py`).
    - Manage dependencies (`requirements.txt`).
    - Provide documentation (`README.md`, `api_doc.md`, `groq_api.md`).
    - Include utility scripts for related tasks (e.g., downloading, URL extraction).
- **Interface:** A web-based interface built with Gradio, running on port 7861.
- **Workflow:** A defined workflow, possibly described in `whisper_workflow.json`.
- **Configuration:** Use environment variables for sensitive information (`.env.example`).

## Scope

This project focuses on building and maintaining the transcription service and its associated components.

## Stakeholders

- Users who need to transcribe audio or YouTube videos.
- Developers maintaining and extending the project.

## Success Criteria

- Accurate and efficient transcription.
- User-friendly Gradio interface.
- Reliable handling of YouTube input (if applicable).
- Well-documented codebase and API usage.
