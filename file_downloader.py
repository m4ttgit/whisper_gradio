"""
Utility script to copy files from a source folder to an output folder,
excluding MP4 files.
"""

import os
import shutil


def copy_files_except_mp4(source_folder: str, output_folder: str) -> None:
    """
    Copies all files from the source folder to the output folder,
    excluding files with the .mp4 extension.

    Args:
        source_folder: Path to the folder containing the original files.
        output_folder: Path to the folder where the selected files will be copied.
    """
    # Ensure the output folder exists; create it if it doesn't
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")

    # Iterate over all files in the source folder
    copied_count = 0
    skipped_count = 0
    for filename in os.listdir(source_folder):
        file_path = os.path.join(source_folder, filename)

        # Check if it's a file (not a directory)
        if os.path.isfile(file_path):
            # Exclude .mp4 files (case-insensitive)
            if not filename.lower().endswith(".mp4"):
                try:
                    shutil.copy2(file_path, output_folder)
                    print(f"Copied: {filename}")
                    copied_count += 1
                except Exception as e:
                    print(f"Error copying {filename}: {e}")
                    skipped_count += 1
            else:
                print(f"Skipped MP4: {filename}")
                skipped_count += 1
        else:
            print(f"Skipped directory: {filename}")
            skipped_count += 1

    print(f"\nCopy complete. Copied {copied_count} files, skipped {skipped_count} items.")


# Example usage
if __name__ == "__main__":
    # Define the source and output folders
    # IMPORTANT: Replace these paths with your actual source and output folder paths
    # Example paths are provided below, modify them as needed.
    source_folder_example = r"D:\Projects\whisper_gradio\outputs\example_source_folder_name"
    output_folder_example = r"D:\Projects\whisper_gradio\outputs\example_output_folder_name"

    # Check if the example source folder exists before running
    if os.path.exists(source_folder_example):
        print(f"Starting file copy from '{source_folder_example}' to '{output_folder_example}'...")
        copy_files_except_mp4(source_folder_example, output_folder_example)
    else:
        print(f"Error: Source folder '{source_folder_example}' not found.")
        print("Please update the 'source_folder_example' variable in the script with the correct path.")
