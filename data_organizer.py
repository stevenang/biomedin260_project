import os
import shutil
import re


def create_directory(path):
    """Create a directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")


def zero_pad_subject_id(subject_id):
    """Add leading zeros to subject ID to make it 7 digits."""
    # Extract the numeric part
    match = re.search(r'(\d+)', subject_id)
    if match:
        num = match.group(1)
        # Pad with zeros to 7 digits
        padded_num = num.zfill(7)
        # Replace the original number with the padded one
        return f"sub-{padded_num}"
    return subject_id


def organize_mri_data(source_root, dest_root):
    """Organize MRI data into the specified structure, handling both direct and session-based structures."""
    # Create destination directories
    anat_dir = os.path.join(dest_root, "anat")
    func_dir = os.path.join(dest_root, "func")
    create_directory(anat_dir)
    create_directory(func_dir)

    # Track statistics
    stats = {"anat_files": 0, "func_files": 0, "errors": 0}

    # Walk through the source directory
    for root, dirs, files in os.walk(source_root):
        # Check if this is an anat or func directory
        current_dir = os.path.basename(root)

        if current_dir in ["anat", "func"]:
            # Get the subject ID
            # First, find the parent path that contains the subject ID
            parent_path = os.path.dirname(root)
            parent_dir = os.path.basename(parent_path)

            # If the parent is a session directory (like ses-1), get the subject from its parent
            if parent_dir.startswith("ses-"):
                subject_id = os.path.basename(os.path.dirname(parent_path))
                session_id = parent_dir
            else:
                subject_id = parent_dir
                session_id = None

            # Only process if it matches the subject pattern
            if subject_id.startswith("sub-"):
                # Create the zero-padded subject directory
                padded_subject_id = zero_pad_subject_id(subject_id)

                # Determine if this is anat or func
                data_type = current_dir
                dest_subdir = os.path.join(dest_root, data_type, padded_subject_id)

                # If there was a session, include it in the filename prefix
                session_prefix = f"{session_id}_" if session_id else ""

                create_directory(dest_subdir)

                # Process files in this directory
                for file in files:
                    if file.endswith(".nii") or file.endswith(".nii.gz"):
                        source_file = os.path.join(root, file)

                        # If there was a session, add it to the filename before any run or task designations
                        if session_id and session_id not in file:
                            # Add session info to the filename
                            # First, split the filename at the first underscore after the subject ID
                            filename_parts = file.split('_', 1)
                            if len(filename_parts) > 1:
                                new_filename = f"{filename_parts[0]}_{session_prefix}{filename_parts[1]}"
                            else:
                                new_filename = f"{file.rstrip('.nii.gz')}_{session_id}.nii.gz" if file.endswith(
                                    '.nii.gz') else f"{file.rstrip('.nii')}_{session_id}.nii"
                            dest_file = os.path.join(dest_subdir, new_filename)
                        else:
                            dest_file = os.path.join(dest_subdir, file)

                        try:
                            # Copy the file (use shutil.move if you want to move instead)
                            shutil.copy2(source_file, dest_file)
                            print(f"Copied: {source_file} -> {dest_file}")

                            # Update statistics
                            if data_type == "anat":
                                stats["anat_files"] += 1
                            else:
                                stats["func_files"] += 1

                        except Exception as e:
                            print(f"Error copying {source_file}: {e}")
                            stats["errors"] += 1

    # Print summary
    print("\nSummary:")
    print(f"Anatomical files processed: {stats['anat_files']}")
    print(f"Functional files processed: {stats['func_files']}")
    print(f"Errors encountered: {stats['errors']}")


if __name__ == "__main__":
    # Define source and destination roots
    # Change these paths to match your system
    source_root = [
        "/Users/stevenang/Downloads/dataset/ADHD200/raw_data/KII",
        "/Users/stevenang/Downloads/dataset/ADHD200/raw_data/NeuroIMAGE",
        "/Users/stevenang/Downloads/dataset/ADHD200/raw_data/NYU",
        "/Users/stevenang/Downloads/dataset/ADHD200/raw_data/OHSU",
        "/Users/stevenang/Downloads/dataset/ADHD200/raw_data/Peking_1",
        "/Users/stevenang/Downloads/dataset/ADHD200/raw_data/Peking_2",
        "/Users/stevenang/Downloads/dataset/ADHD200/raw_data/Peking_3",
        "/Users/stevenang/Downloads/dataset/ADHD200/raw_data/Pittsburgh",
        "/Users/stevenang/Downloads/dataset/ADHD200/raw_data/WashU"
    ]
    dest_root = os.path.expanduser("/Users/stevenang/Downloads/dataset")

    for source in source_root:
        organize_mri_data(source, dest_root)