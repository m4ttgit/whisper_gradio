import subprocess
import sys
import os
import json
import csv

from utils import check_yt_dlp

def extract_channel_info(channel_url, output_csv_file):
    """
    Extracts video titles and URLs from a YouTube channel and saves to a CSV file.
    """
    check_yt_dlp()

    command = [
        "yt-dlp",
        "--skip-download",
        "--dump-single-json",
        "-i",
        channel_url
    ]

    print(f"Executing command: {' '.join(command)}\n")
    extracted_count = 0

    try:
        output_dir = os.path.dirname(output_csv_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        stdout_data, _ = process.communicate()

        with open(output_csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(['Title', 'URL'])

            try:
                data = json.loads(stdout_data)
                entries = data.get('entries', [])
                for video_info in entries:
                    title = video_info.get('title', 'N/A')
                    url = video_info.get('webpage_url', video_info.get('url', 'N/A'))

                    if url != 'N/A' and url.startswith('http'):
                        writer.writerow([title, url])
                        extracted_count += 1
                        print(f"Extracted: {title[:60]}...")
                    else:
                        print(f"Skipping entry with missing URL: {title[:60]}...")

            except json.JSONDecodeError:
                print("Error: Failed to parse yt-dlp JSON output.", file=sys.stderr)
            except Exception as e:
                print(f"Unexpected error parsing yt-dlp output: {e}", file=sys.stderr)

        process.wait()

        stderr_output = process.stderr.read()
        if process.returncode != 0:
            print(f"\nyt-dlp exited with code {process.returncode}.", file=sys.stderr)
            if stderr_output:
                print("\n--- yt-dlp Errors/Warnings ---", file=sys.stderr)
                print(stderr_output, file=sys.stderr)
                print("--- End yt-dlp Errors/Warnings ---", file=sys.stderr)
        elif stderr_output:
            print("\n--- yt-dlp Messages (stderr) ---", file=sys.stderr)
            print(stderr_output, file=sys.stderr)
            print("--- End yt-dlp Messages ---", file=sys.stderr)

        if extracted_count > 0:
            print(f"\nSuccessfully extracted {extracted_count} videos.")
            print(f"Data saved to: {output_csv_file}")
        else:
            print("\nNo video information was extracted. Check the channel URL and yt-dlp output/errors.")

    except FileNotFoundError:
        print("Error: yt-dlp not found. Please install it.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
