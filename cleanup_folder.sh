#!/bin/bash

# Define source and destination directories
SOURCE_DIR="/Users/stevenang/Downloads/dataset/anat"
BACKUP_DIR="/Users/stevenang/Downloads/dataset/backup"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Counters for statistics
total_processed=0
total_moved=0

# Process each subdirectory
find "$SOURCE_DIR" -type d -mindepth 1 | while read -r subdir; do
    # Skip the backup directory if it's a subdirectory of the source
    if [[ "$subdir" == "$BACKUP_DIR"* ]]; then
        continue
    fi

    # Get all files in the current subdirectory (not recursive)
    files=()
    while IFS= read -r file; do
        files+=("$file")
    done < <(find "$subdir" -type f -maxdepth 1)

    # Get the count of files
    file_count=${#files[@]}
    total_processed=$((total_processed + file_count))

    # If more than one file exists
    if [ $file_count -gt 1 ]; then
        echo "Processing: $subdir (found $file_count files)"

        # Keep the first file, move the rest
        for ((i=1; i<file_count; i++)); do
            file="${files[$i]}"
            filename=$(basename "$file")
            # Create a unique name to avoid conflicts in the backup directory
            subdir_name=$(basename "$subdir")
            new_filename="${subdir_name}_${filename}"
            echo "  Moving: $filename to $BACKUP_DIR/$new_filename"

            # Move the file
            mv "$file" "$BACKUP_DIR/$new_filename"
            total_moved=$((total_moved + 1))
        done
    else
        echo "Skipping: $subdir (found $file_count files)"
    fi
done

# Print summary
echo "----------------------------------------"
echo "Summary:"
echo "  Total directories processed: $(find "$SOURCE_DIR" -type d -mindepth 1 | wc -l)"
echo "  Total files processed: $total_processed"
echo "  Total files moved: $total_moved"
echo "----------------------------------------"

echo "Operation completed successfully!"