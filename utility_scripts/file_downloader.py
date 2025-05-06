import os
import shutil


def copy_files_except_mp4(source_folder, output_folder):
    """
    Copies all files from the source folder to the output folder,
    excluding files with the .mp4 extension.

    :param source_folder: Path to the folder containing the original files.
    :param output_folder: Path to the folder where the selected files will be copied.
    """
    # Ensure the output folder exists; create it if it doesn't
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Iterate over all files in the source folder
    for filename in os.listdir(source_folder):
        # Construct full file path
        file_path = os.path.join(source_folder, filename)

        # Check if it's a file (not a directory) and not an .mp4 file
        if os.path.isfile(file_path) and not filename.lower().endswith(".mp4"):
            # Copy the file to the output folder
            shutil.copy2(file_path, output_folder)
            print(f"Copied: {filename}")


def copy_files_recursive(root_folder, output_base_folder):
    """
    Recursively copies all non-mp4 files from the root folder and its subfolders,
    maintaining the same folder structure in the output.

    :param root_folder: Path to the root folder containing subfolders with files
    :param output_base_folder: Path to the base output folder where files will be copied
    """
    # Walk through all folders and subfolders
    for current_folder, subdirs, files in os.walk(root_folder):
        # Calculate the relative path from root folder
        rel_path = os.path.relpath(current_folder, root_folder)

        # Create the corresponding output folder path
        current_output_folder = os.path.join(output_base_folder, rel_path)

        # Create the output folder if it doesn't exist
        if not os.path.exists(current_output_folder):
            os.makedirs(current_output_folder)

        # Copy non-mp4 files from current folder
        for filename in files:
            if not filename.lower().endswith(".mp4"):
                source_file = os.path.join(current_folder, filename)
                dest_file = os.path.join(current_output_folder, filename)
                shutil.copy2(source_file, dest_file)
                print(f"Copied: {os.path.join(rel_path, filename)}")


# Example usage
if __name__ == "__main__":
    # Example 1: Copy files from a single folder
    # source_folder = r"D:\Projects\whisper_gradio\outputs\信仰有問題 預告EP8雷競業博士基督徒一定要參與事奉未信者可否參與信仰有問題 事奉 基督徒"
    # output_folder = r"D:\Projects\whisper_gradio\outputs\信仰有問題 預告EP8雷競業博士基督徒一定要參與事奉未信者可否參與信仰有問題 事奉 基督徒_up"

    # Call the function to copy files from a single folder
    # copy_files_except_mp4(source_folder, output_folder)

    # Example 2: Copy files recursively from multiple folders
    root_folder = r"D:\Projects\acsm\蕭壽華牧師"  # Replace with your root folder containing multiple subfolders
    output_base_folder = r"D:\Projects\acsm\蕭壽華牧師_scripts"  # Replace with your desired output base folder

    # Call the function to copy files recursively
    copy_files_recursive(root_folder, output_base_folder)
