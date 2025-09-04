import os
import pandas as pd
import datetime

def save_folders_to_excel(root_path, output_file="folders_list.xlsx"):
    folders = []
    dates = []
    
    for item in os.listdir(root_path):
        item_path = os.path.join(root_path, item)
        if os.path.isdir(item_path):
            folders.append(item)
            # Get the modification time and convert to datetime
            mod_time = os.path.getmtime(item_path)
            mod_date = datetime.datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
            dates.append(mod_date)
    
    df = pd.DataFrame({
        'Folder Names': folders,
        'Date Modified': dates
    })
    df.to_excel(output_file, index=False)
    print(f"Saved {len(folders)} folders to {output_file}")

if __name__ == "__main__":
    # Example usage
    folder_path = r"D:\Projects\acsm\exmilton_gordon"
    save_folders_to_excel(folder_path)