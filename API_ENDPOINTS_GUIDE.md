# Whisper Gradio API Endpoints Guide

This guide shows how to use all the API endpoints available in the Whisper Gradio application.

## Base URL
The API runs on port 7861 by default: `http://localhost:7861`

## Endpoints Overview

### 1. Start Transcription Job
**Endpoint:** `POST /gradio/handle_transcription`

Starts a new transcription job via JSON API.

**Request Body:**
```json
{
  "data": [
    {
      "url": "https://www.youtube.com/watch?v=VIDEO_ID",
      "dir": "/path/to/output",
      "lang": "Auto Detect",
      "model_choice": "Local Whisper",
      "local_model": "medium",
      "groq_model": "whisper-large-v3",
      "translate": false
    }
  ]
}
```

**Parameters:**
- `url` (optional): YouTube URL to transcribe
- `dir` (optional): Output directory path
- `lang`: Language ("Auto Detect" or specific language name)
- `model_choice`: "Local Whisper" or "Groq API"
- `local_model`: Whisper model size (tiny, base, small, medium, large, etc.)
- `groq_model`: Groq model name
- `translate`: Boolean for translation to English

**Example using curl:**
```bash
curl -X POST "http://localhost:7861/gradio/handle_transcription" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [{
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "lang": "Auto Detect",
      "model_choice": "Local Whisper",
      "local_model": "medium"
    }]
  }'
```

**Response:**
```json
{
  "job_ids": ["uuid-string-here"]
}
```

---

### 2. Check Job Status
**Endpoint:** `GET /gradio/job_status?job_id={job_id}`

Gets the current status of a transcription job.

**Parameters:**
- `job_id` (query parameter): The job ID returned from handle_transcription

**Example:**
```bash
curl "http://localhost:7861/gradio/job_status?job_id=12345678-1234-1234-1234-123456789abc"
```

**Response:**
```json
{
  "status": "complete",
  "result": {
    "text": "Full transcription text...",
    "srt_path": "/path/to/output/video.srt",
    "text_path": "/path/to/output/video.txt",
    "video_path_out": "/path/to/output/video.mp4"
  },
  "progress": 100
}
```

**Status Values:**
- `"pending"`: Job is queued
- `"downloading"`: Downloading video
- `"transcribing"`: Actively transcribing
- `"complete"`: Job finished successfully
- `"failed"`: Job failed with error

---

### 3. Get Detailed Job Information
**Endpoint:** `GET /gradio/job_details?job_id={job_id}`

Gets comprehensive details about a job including parameters and metadata.

**Example:**
```bash
curl "http://localhost:7861/gradio/job_details?job_id=12345678-1234-1234-1234-123456789abc"
```

**Response:**
```json
{
  "job_id": "12345678-1234-1234-1234-123456789abc",
  "status": "complete",
  "progress": 100,
  "created_at": 1634567890.123,
  "last_checkpoint": 1634567990.456,
  "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "source_file": null,
  "params": {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "dir": "",
    "lang": "Auto Detect",
    "model_choice": "Local Whisper",
    "local_model": "medium",
    "groq_model": "whisper-large-v3",
    "translate": false
  },
  "result": {
    "text": "Full transcription text...",
    "srt_path": "/path/to/output/video.srt",
    "text_path": "/path/to/output/video.txt",
    "video_path_out": "/path/to/output/video.mp4"
  }
}
```

---

### 4. Resume Interrupted Job
**Endpoint:** `POST /gradio/resume_job`

Resumes a job that was interrupted or failed.

**Request Methods:**
1. **Query Parameter:** `POST /gradio/resume_job?job_id={job_id}`
2. **JSON Body:** `POST /gradio/resume_job` with `{"job_id": "uuid"}`

**Examples:**

**Using query parameter:**
```bash
curl -X POST "http://localhost:7861/gradio/resume_job?job_id=12345678-1234-1234-1234-123456789abc"
```

**Using JSON body:**
```bash
curl -X POST "http://localhost:7861/gradio/resume_job" \
  -H "Content-Type: application/json" \
  -d '{"job_id": "12345678-1234-1234-1234-123456789abc"}'
```

**Response:**
```json
{
  "status": "resumed",
  "job_id": "12345678-1234-1234-1234-123456789abc"
}
```

**Error Responses:**
```json
{
  "status": "not_found"
}
```
```json
{
  "status": "already_finished",
  "job_status": "complete"
}
```
```json
{
  "status": "cannot_resume"
}
```

---

### 5. List Incomplete Jobs
**Endpoint:** `GET /gradio/incomplete_jobs`

Gets a list of all jobs that haven't completed yet (pending, downloading, transcribing, resuming, failed).

**Example:**
```bash
curl "http://localhost:7861/gradio/incomplete_jobs"
```

**Response:**
```json
{
  "incomplete_jobs": [
    "12345678-1234-1234-1234-123456789abc",
    "87654321-4321-4321-4321-cba987654321"
  ],
  "count": 2
}
```

---

## Complete Workflow Example

Here's a complete example of using the API from start to finish:

### 1. Start a transcription job
```bash
curl -X POST "http://localhost:7861/gradio/handle_transcription" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [{
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "lang": "Auto Detect",
      "model_choice": "Local Whisper",
      "local_model": "medium"
    }]
  }'
```

**Response:**
```json
{
  "job_ids": ["12345678-1234-1234-1234-123456789abc"]
}
```

### 2. Monitor progress
```bash
# Check status every few seconds
curl "http://localhost:7861/gradio/job_status?job_id=12345678-1234-1234-1234-123456789abc"
```

**Response while processing:**
```json
{
  "status": "transcribing",
  "progress": 45
}
```

### 3. Get final results
```bash
curl "http://localhost:7861/gradio/job_details?job_id=12345678-1234-1234-1234-123456789abc"
```

**Final response:**
```json
{
  "job_id": "12345678-1234-1234-1234-123456789abc",
  "status": "complete",
  "progress": 100,
  "result": {
    "text": "Never gonna give you up...",
    "srt_path": "outputs/Rick Astley - Never Gonna Give You Up.srt",
    "text_path": "outputs/Rick Astley - Never Gonna Give You Up.txt",
    "video_path_out": "outputs/Rick Astley - Never Gonna Give You Up.mp4"
  }
}
```

---

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200`: Success
- `404`: Job not found
- `422`: Missing required parameters
- `400`: Bad request or processing error

Error responses include descriptive error messages in the response body.

---

## Language Support

The API supports all languages that Whisper supports. Use these language names in the `lang` parameter:

- "Auto Detect" (default)
- "English", "Spanish", "French", "German", "Chinese", "Japanese", "Korean", "Russian", "Portuguese", "Italian", "Hindi", "Arabic", etc.

---

## Model Options

### Local Whisper Models:
- "tiny", "base", "small", "medium", "large", "large-v2", "large-v3"

### Groq API Models:
- "whisper-large-v3"
- "whisper-large-v3-turbo"
- "distil-whisper-large-v3-en"

---

## Notes

1. **File Upload**: The JSON API only supports URL-based transcription. For file uploads, use the Gradio web interface.

2. **Progress Monitoring**: Use the `job_status` endpoint to monitor progress. Progress is reported as a percentage (0-100).

3. **Resume Capability**: If a job fails or gets interrupted, use the `resume_job` endpoint to continue from where it left off.

4. **Output Files**: Successful transcription generates:
   - `.txt`: Plain text transcription
   - `.srt`: SRT subtitle file with timestamps
   - `.mp4`: Downloaded video file

5. **Concurrent Jobs**: Multiple jobs can run simultaneously. Each job gets a unique ID for tracking.

6. **Resource Usage**: Large videos and high-quality models require significant CPU/GPU resources and time.