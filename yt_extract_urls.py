import argparse
from youtube_api import extract_channel_info

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract video Titles and URLs from a YouTube channel into a CSV file using yt-dlp.")
    parser.add_argument("channel_url", help="The URL of the YouTube channel (e.g., https://www.youtube.com/@MrBeast/videos)")
    parser.add_argument("output_csv", help="Path for the output CSV file (e.g., channel_videos.csv)")

    args = parser.parse_args()

    extract_channel_info(args.channel_url, args.output_csv)
