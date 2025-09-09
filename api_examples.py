#!/usr/bin/env python3
"""
Whisper Gradio API Examples
Demonstrates how to use all API endpoints programmatically
"""

import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:7862"

def start_transcription_job(url, language="Auto Detect", model_choice="Local Whisper", model="medium"):
    """Start a new transcription job"""
    endpoint = f"{BASE_URL}/gradio/handle_transcription"

    payload = {
        "data": [{
            "url": url,
            "lang": language,
            "model_choice": model_choice,
            "local_model": model,
            "groq_model": "whisper-large-v3",
            "translate": False
        }]
    }

    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()

        result = response.json()
        job_id = result["job_ids"][0]
        print(f"✅ Job started successfully! Job ID: {job_id}")
        return job_id

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to start job: {e}")
        return None

def check_job_status(job_id):
    """Check the status of a job"""
    endpoint = f"{BASE_URL}/gradio/job_status"
    params = {"job_id": job_id}

    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()

        result = response.json()
        status = result.get("status")
        progress = result.get("progress", 0)

        print(f"📊 Job {job_id}: {status} ({progress}%)")

        if status == "complete":
            print("✅ Transcription completed!")
            if "result" in result:
                print(f"📝 Text length: {len(result['result'].get('text', ''))}")
                print(f"📄 SRT file: {result['result'].get('srt_path', 'N/A')}")
                print(f"📄 Text file: {result['result'].get('text_path', 'N/A')}")

        elif status == "failed":
            print("❌ Job failed!")
            if "result" in result and "error" in result["result"]:
                print(f"Error: {result['result']['error']}")

        return result

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to check status: {e}")
        return None

def get_job_details(job_id):
    """Get detailed information about a job"""
    endpoint = f"{BASE_URL}/gradio/job_details"
    params = {"job_id": job_id}

    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()

        result = response.json()
        print(f"📋 Detailed info for job {job_id}:")
        print(f"   Status: {result.get('status')}")
        print(f"   Progress: {result.get('progress', 0)}%")
        print(f"   Source URL: {result.get('source_url', 'N/A')}")
        print(f"   Created: {time.ctime(result.get('created_at', 0))}")

        if result.get('params'):
            params = result['params']
            print(f"   Language: {params.get('lang', 'N/A')}")
            print(f"   Model: {params.get('local_model', 'N/A')}")

        return result

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to get job details: {e}")
        return None

def resume_job(job_id):
    """Resume an interrupted job"""
    endpoint = f"{BASE_URL}/gradio/resume_job"

    payload = {"job_id": job_id}

    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()

        result = response.json()
        status = result.get("status")

        if status == "resumed":
            print(f"▶️ Job {job_id} resumed successfully!")
            return True
        elif status == "already_finished":
            print(f"✅ Job {job_id} is already finished")
            return True
        elif status == "not_found":
            print(f"❌ Job {job_id} not found")
            return False
        else:
            print(f"❌ Failed to resume job: {status}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to resume job: {e}")
        return False

def list_incomplete_jobs():
    """List all incomplete jobs"""
    endpoint = f"{BASE_URL}/gradio/incomplete_jobs"

    try:
        response = requests.get(endpoint)
        response.raise_for_status()

        result = response.json()
        jobs = result.get("incomplete_jobs", [])
        count = result.get("count", 0)

        print(f"📋 Found {count} incomplete jobs:")
        for job_id in jobs:
            print(f"   - {job_id}")

        return jobs

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to list incomplete jobs: {e}")
        return []

def monitor_job_progress(job_id, check_interval=5):
    """Monitor a job's progress until completion"""
    print(f"🔍 Monitoring job {job_id}...")

    while True:
        status_result = check_job_status(job_id)

        if status_result:
            status = status_result.get("status")

            if status in ["complete", "failed"]:
                print(f"🏁 Job {job_id} finished with status: {status}")
                return status_result

        time.sleep(check_interval)

def demo_complete_workflow():
    """Demonstrate a complete workflow from start to finish"""
    print("🚀 Starting Whisper Gradio API Demo")
    print("=" * 50)

    # Example YouTube URL (replace with your own)
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up

    # 1. Start transcription job
    print("\n1️⃣ Starting transcription job...")
    job_id = start_transcription_job(video_url)

    if not job_id:
        print("❌ Failed to start job. Exiting demo.")
        return

    # 2. Monitor progress
    print("\n2️⃣ Monitoring progress...")
    final_result = monitor_job_progress(job_id)

    # 3. Get detailed results
    if final_result and final_result.get("status") == "complete":
        print("\n3️⃣ Getting detailed results...")
        details = get_job_details(job_id)

        # 4. Show transcription text (first 500 characters)
        if details and "result" in details and "text" in details["result"]:
            text = details["result"]["text"]
            print("\n📝 Transcription preview (first 500 chars):")
            print("-" * 50)
            print(text[:500] + "..." if len(text) > 500 else text)
            print("-" * 50)

    print("\n✅ Demo completed!")

def demo_resume_workflow():
    """Demonstrate job resume functionality"""
    print("🔄 Resume Workflow Demo")
    print("=" * 30)

    # 1. List incomplete jobs
    print("\n1️⃣ Checking for incomplete jobs...")
    incomplete_jobs = list_incomplete_jobs()

    if not incomplete_jobs:
        print("ℹ️ No incomplete jobs found. Start a job first, then interrupt it to test resume.")
        return

    # 2. Resume the first incomplete job
    job_id = incomplete_jobs[0]
    print(f"\n2️⃣ Resuming job {job_id}...")
    resume_success = resume_job(job_id)

    if resume_success:
        # 3. Monitor the resumed job
        print(f"\n3️⃣ Monitoring resumed job {job_id}...")
        monitor_job_progress(job_id)

def interactive_menu():
    """Interactive menu for testing endpoints"""
    while True:
        print("\n🔧 Whisper Gradio API Test Menu")
        print("=" * 40)
        print("1. Start new transcription job")
        print("2. Check job status")
        print("3. Get job details")
        print("4. Resume job")
        print("5. List incomplete jobs")
        print("6. Monitor job progress")
        print("7. Run complete workflow demo")
        print("8. Run resume workflow demo")
        print("9. Exit")

        choice = input("\nEnter your choice (1-9): ").strip()

        if choice == "1":
            url = input("Enter YouTube URL: ").strip()
            if url:
                job_id = start_transcription_job(url)
                if job_id:
                    print(f"Job ID: {job_id}")

        elif choice == "2":
            job_id = input("Enter job ID: ").strip()
            if job_id:
                check_job_status(job_id)

        elif choice == "3":
            job_id = input("Enter job ID: ").strip()
            if job_id:
                get_job_details(job_id)

        elif choice == "4":
            job_id = input("Enter job ID: ").strip()
            if job_id:
                resume_job(job_id)

        elif choice == "5":
            list_incomplete_jobs()

        elif choice == "6":
            job_id = input("Enter job ID to monitor: ").strip()
            if job_id:
                monitor_job_progress(job_id)

        elif choice == "7":
            demo_complete_workflow()

        elif choice == "8":
            demo_resume_workflow()

        elif choice == "9":
            print("👋 Goodbye!")
            break

        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "demo":
            demo_complete_workflow()
        elif command == "resume-demo":
            demo_resume_workflow()
        elif command == "interactive":
            interactive_menu()
        else:
            print("Usage: python api_examples.py [demo|resume-demo|interactive]")
            print("  demo        - Run complete workflow demo")
            print("  resume-demo - Run resume workflow demo")
            print("  interactive - Interactive menu")
    else:
        print("Whisper Gradio API Examples")
        print("Usage: python api_examples.py [command]")
        print("")
        print("Commands:")
        print("  demo        - Run complete workflow demo")
        print("  resume-demo - Run resume workflow demo")
        print("  interactive - Interactive menu for testing endpoints")
        print("")
        print("Examples:")
        print("  python api_examples.py demo")
        print("  python api_examples.py interactive")