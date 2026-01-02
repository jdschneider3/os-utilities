"""
bulk_file_rename.py

Summary:
    Renames the files and folders within the given input root directory based on input file and folder .CSV mappings.
   
Arguments:
    1) [Required] --root:        Path to the root folder, within which the renaming will occur.
    2) [Required] --filemap:     Path to the .CSV that maps old to new file names.
    3) [Required] --foldermap:   Path to the .CSV that maps old to new folder names.
    4) [Optional] --dryrun:      Dry Run mode - nothing is renamed. Used for debugging and troubleshooting.

Notes:
    .CSV mappings should have 2 columns:
    old_name,new_name
"""

import os
import argparse
import pandas as pd
import re
from pathlib import Path

conflict_log = []
error_log = []
reserved_paths = set()

def sanitize_filename(name):
    
    # Replaces characters that are invalid in file names
    return re.sub(r'[<>:"/\\|?*]', '_', str(name))

def get_unique_path(old_file_path, new_file_path):
    
    if not new_file_path.exists() and new_file_path not in reserved_paths:
        reserved_paths.add(new_file_path)
        return new_file_path
    
    # Increments a folder/filename with _1, _2... if the path already exists.
    # For files: 'test.txt' -> 'test_1.txt', For folders: 'MyFolder' -> 'MyFolder_1'
    counter = 1    
    stem = new_file_path.stem
    suffix = new_file_path.suffix
    parent = new_file_path.parent

    while True:
        new_unique_file_name = f"{stem}_{counter}{suffix}"
        new_unique_file_path = parent / new_unique_file_name
        if not new_unique_file_path.exists() and new_unique_file_path not in reserved_paths:
            conflict_log.append(f"Renaming: {old_file_path} -> {new_unique_file_name} to avoid conflict")
            reserved_paths.add(new_unique_file_path)
            return new_unique_file_path
        counter += 1

def rename_items(root_directory, files_csv, folders_csv, dry_run=True):
    
    file_counter = 0
    folder_counter = 0

    # Load the ID-->Name mappings from CSVs
    file_map_df = pd.read_csv(files_csv, header=None, names=['old_name', 'new_name'])
    folder_map_df = pd.read_csv(folders_csv, header=None, names=['old_name', 'new_name'])
    
    # Create dictionaries for lookup
    file_map = {str(row['old_name']): sanitize_filename(row['new_name']) for _, row in file_map_df.iterrows()}
    folder_map = {str(row['old_name']): sanitize_filename(row['new_name']) for _, row in folder_map_df.iterrows()}
    
    mode_label = "[DRY RUN]" if dry_run else "[EXECUTING]"
    print(f"{mode_label} Loaded {len(file_map)} file mappings and {len(folder_map)} folder mappings.")

    # Using topdown=False to handle children before parents
    for root, dirs, files in os.walk(root_directory, topdown=False):
        
        # Rename Files
        for file_name in files:
            old_file_path = Path(root) / file_name
            old_stem = old_file_path.stem
            extension = old_file_path.suffix
            
            if old_stem in file_map:
                new_file_name = file_map[old_stem] + extension
                new_file_path = old_file_path.with_name(new_file_name)
                
                # Check for conflicts and get a unique name when necessary
                new_file_path = get_unique_path(old_file_path, new_file_path)
                
                print(f"{mode_label} File: {old_file_path} -> {new_file_path.name}")
                file_counter += 1
                if not dry_run:
                    try:
                        old_file_path.rename(new_file_path)
                    except Exception as e:
                        error_log.append(f"Failed to rename file {old_file_path} -> {new_file_path.name}: {e}")


        # Rename Folders
        for dir_name in dirs:
            old_dir_path = Path(root) / dir_name
            if dir_name in folder_map:
                new_dir_name = folder_map[dir_name]
                new_dir_path = old_dir_path.with_name(new_dir_name)
                
                # Check for conflicts and get a unique name when necessary
                new_dir_path = get_unique_path(old_dir_path, new_dir_path)
                
                print(f"{mode_label} Folder: {old_dir_path} -> {new_dir_path.name}")
                folder_counter += 1
                if not dry_run:
                    try:
                        old_dir_path.rename(new_dir_path)
                    except Exception as e:
                        error_log.append(f"Failed to rename folder {old_dir_path} -> {new_dir_path.name}: {e}")


    if conflict_log:
        print("\n--- Warning: Rename Conflicts ---")
        for entry in conflict_log:
            print(entry)
        print("")

    if error_log:
        print("\n--- Errors Encountered During Renaming ---")
        for entry in error_log:
            print(entry)
        print("")

    return file_counter, folder_counter

def main():

    # Handle Arguments
    parser = argparse.ArgumentParser(description="Renames the files and folders within the given input root directory based on input file and folder .CSV mappings.")
    
    parser.add_argument("-root", "--root", type=str, required=True, help="Path to the root folder, within which the renaming will occur.")
    parser.add_argument("-filemap", "--filemap", type=str, required=True, help="Path to the .CSV that maps old to new file names.")
    parser.add_argument("-foldermap", "--foldermap", type=str, required=True, help="Path to the .CSV that maps old to new folder names.")
    parser.add_argument("-dryrun", "--dryrun", action="store_true", help="Dry Run mode - nothing is renamed. Used for debugging and troubleshooting.")

    args = parser.parse_args()

    # Validate Root Directory
    if not os.path.exists(args.root) or not os.path.isdir(args.root):
        print(f"Error: The root directory '{args.root}' does not exist or is not a directory.")
        return

    # Validate File Map
    if not os.path.isfile(args.filemap):
        print(f"Error: The file map '{args.filemap}' does not exist.")
        return
    
    if not args.filemap.lower().endswith(".csv"):
        print(f"Error: The file map '{args.filemap}' is not a CSV file.")
        return

    # Validate Folder Map
    if not os.path.isfile(args.foldermap):
        print(f"Error: The folder map '{args.foldermap}' does not exist.")
        return
    
    if not args.foldermap.lower().endswith(".csv"):
        print(f"Error: The folder map '{args.foldermap}' is not a CSV file.")
        return

    print(f"Starting script in {'DRY RUN' if args.dryrun else 'LIVE'} mode...")
    file_counter, folder_counter = rename_items(args.root, args.filemap, args.foldermap, args.dryrun)
    mode = "would have been" if args.dryrun else "have been"
    print(f"Done - {file_counter} file(s) and {folder_counter} folder(s) {mode} renamed.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130)