#!/usr/bin/env python3
"""
n8n Resume Integration Helper
Helps integrate resume functionality with existing n8n workflows
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:7861"

def check_and_resume_jobs():
    """Check for incomplete jobs and resume them"""
    print("🔄 Checking for incomplete transcription jobs...")

    try:
        # Get incomplete jobs
        response = requests.get(f"{BASE_URL}/gradio/incomplete_jobs")
        if response.status_code != 200:
            print(f"❌ Failed to get incomplete jobs: {response.status_code}")
            return

        data = response.json()
        incomplete_count = data.get('count', 0)
        job_ids = data.get('incomplete_jobs', [])

        if incomplete_count == 0:
            print("✅ No incomplete jobs found")
            return

        print(f"📋 Found {incomplete_count} incomplete job(s):")
        for job_id in job_ids:
            print(f"  - {job_id}")

        # Resume each job
        for job_id in job_ids:
            print(f"\n▶️  Resuming job: {job_id}")
            resume_response = requests.post(
                f"{BASE_URL}/gradio/resume_job",
                json={"job_id": job_id}
            )

            if resume_response.status_code == 200:
                result = resume_response.json()
                print(f"✅ Resume initiated: {result}")

                # Check if the job failed due to missing parameters
                if "error" in str(result).lower():
                    print(f"⚠️  Job {job_id} cannot be resumed (likely created before resume feature)")
                    print("   This job will need to be restarted manually")
            else:
                print(f"❌ Failed to resume job {job_id}: {resume_response.status_code}")
                if resume_response.text:
                    print(f"   Error details: {resume_response.text}")

    except Exception as e:
        print(f"❌ Error: {e}")

def monitor_job_progress(job_id, max_checks=20):
    """Monitor a job's progress until completion"""
    print(f"📊 Monitoring job: {job_id}")

    for i in range(max_checks):
        try:
            response = requests.get(f"{BASE_URL}/gradio/job_status/{job_id}")
            if response.status_code == 200:
                status = response.json()
                job_status = status.get('status', 'unknown')
                progress = status.get('progress', 0)

                print(f"📈 Status: {job_status} | Progress: {progress}%")

                if job_status in ['complete', 'failed']:
                    print(f"🎉 Job finished with status: {job_status}")
                    if 'result' in status and status['result']:
                        result = status['result']
                        if 'text' in result:
                            print(f"📝 Transcription length: {len(result['text'])} characters")
                        if 'srt_path' in result:
                            print(f"📁 SRT file: {result['srt_path']}")
                    return True
            else:
                print(f"❌ Failed to get status: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error monitoring job: {e}")
            return False

        time.sleep(3)  # Wait 3 seconds between checks

    print("⏰ Monitoring timeout reached")
    return False

def get_job_status(job_id):
    """Get detailed status of a specific job"""
    try:
        response = requests.get(f"{BASE_URL}/gradio/job_status/{job_id}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get job status: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error getting job status: {e}")
        return None

def main():
    """Main function for n8n resume integration"""
    print("🎯 n8n Resume Integration Helper")
    print("=" * 40)

    while True:
        print("\nChoose an option:")
        print("1. Check and resume incomplete jobs")
        print("2. Monitor a specific job")
        print("3. Get job status")
        print("4. Exit")

        choice = input("\nEnter your choice (1-4): ").strip()

        if choice == '1':
            check_and_resume_jobs()

        elif choice == '2':
            job_id = input("Enter job ID to monitor: ").strip()
            if job_id:
                monitor_job_progress(job_id)
            else:
                print("❌ Invalid job ID")

        elif choice == '3':
            job_id = input("Enter job ID to check: ").strip()
            if job_id:
                status = get_job_status(job_id)
                if status:
                    print("📊 Job Status:")
                    print(json.dumps(status, indent=2))
            else:
                print("❌ Invalid job ID")

        elif choice == '4':
            print("👋 Goodbye!")
            break

        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    main()