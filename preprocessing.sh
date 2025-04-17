#!/bin/bash
#
# Automated FreeSurfer Processing for ADHD Classification
# This script automates the FreeSurfer recon-all processing on multiple subjects
# from the ADHD-200 dataset or any dataset with similar structure.
#
# Usage: ./process_freesurfer.sh [options]
#   Options:
#     -d, --data-dir DIR       Path to the root data directory
#     -o, --output-dir DIR     Path to output directory for FreeSurfer results
#     -p, --parallel N         Number of parallel processes (default: 4)
#     -s, --subjects LIST      File with list of subject IDs to process
#     -a, --all                Process all subjects in the data directory
#     -c, --clean              Remove any existing output for the subject
#     -h, --help               Display this help message
#
# Example: ./process_freesurfer.sh -d /path/to/ADHD200 -o /path/to/output -p 8 -a

# Default values
DATA_DIR=""
OUTPUT_DIR=""
PARALLEL=4
SUBJECT_LIST=""
PROCESS_ALL=false
CLEAN=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -d|--data-dir)
            DATA_DIR="$2"
            shift
            shift
            ;;
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift
            shift
            ;;
        -p|--parallel)
            PARALLEL="$2"
            shift
            shift
            ;;
        -s|--subjects)
            SUBJECT_LIST="$2"
            shift
            shift
            ;;
        -a|--all)
            PROCESS_ALL=true
            shift
            ;;
        -c|--clean)
            CLEAN=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -d, --data-dir DIR       Path to the root data directory"
            echo "  -o, --output-dir DIR     Path to output directory for FreeSurfer results"
            echo "  -p, --parallel N         Number of parallel processes (default: 4)"
            echo "  -s, --subjects LIST      File with list of subject IDs to process"
            echo "  -a, --all                Process all subjects in the data directory"
            echo "  -c, --clean              Remove any existing output for the subject"
            echo "  -h, --help               Display this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate inputs
if [[ -z "$DATA_DIR" ]]; then
    echo "Error: Data directory (-d) is required"
    exit 1
fi

if [[ -z "$OUTPUT_DIR" ]]; then
    echo "Error: Output directory (-o) is required"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Set up FreeSurfer environment if not already set
if [[ -z "$FREESURFER_HOME" ]]; then
    echo "FREESURFER_HOME not set. Please set it to your FreeSurfer installation directory."
    echo "Example: export FREESURFER_HOME=/Applications/freesurfer/8.0.0"
    exit 1
fi

if [[ ! -f "$FREESURFER_HOME/SetUpFreeSurfer.sh" ]]; then
    echo "FreeSurfer setup script not found at $FREESURFER_HOME/SetUpFreeSurfer.sh"
    exit 1
fi

source "$FREESURFER_HOME/SetUpFreeSurfer.sh"

# Set SUBJECTS_DIR for FreeSurfer
export SUBJECTS_DIR="$OUTPUT_DIR"

# Create log directory
mkdir -p "$SUBJECTS_DIR/logs"

# Find all subjects to process
if [[ "$PROCESS_ALL" = true ]]; then
    # Find all T1w files
    T1_FILES=$(find "$DATA_DIR" -type f -name "*T1w.nii.gz" | sort)
    echo "Found $(echo "$T1_FILES" | wc -l) T1 MRI files to process"
elif [[ -n "$SUBJECT_LIST" && -f "$SUBJECT_LIST" ]]; then
    # Read subjects from file
    T1_FILES=()
    while IFS= read -r subject; do
        # Skip empty lines and comments
        [[ -z "$subject" || "$subject" =~ ^# ]] && continue

        # Find T1 image for this subject
        T1_PATH=$(find "$DATA_DIR" -type f -name "${subject}*T1w.nii.gz" | head -n 1)
        if [[ -n "$T1_PATH" ]]; then
            T1_FILES+=("$T1_PATH")
        else
            echo "Warning: No T1 image found for subject $subject"
        fi
    done < "$SUBJECT_LIST"
else
    echo "Error: Either --all or --subjects must be specified"
    exit 1
fi

# Function to process a single subject
process_subject() {
    local t1_path="$1"

    # Extract subject ID from the file path - improved extraction
    local filename=$(basename "$t1_path")
    local subject_id=$(echo "$filename" | sed -E 's/^(sub-[0-9]+)_.*/\1/')

    echo "Processing subject: $subject_id"
    echo "T1 image: $t1_path"

    # Clean existing output if requested
    if [[ "$CLEAN" = true && -d "$SUBJECTS_DIR/$subject_id" ]]; then
        echo "Removing existing output for $subject_id"
        rm -rf "$SUBJECTS_DIR/$subject_id"
    fi

    # Check if subject has already been processed
    if [[ -f "$SUBJECTS_DIR/$subject_id/scripts/recon-all.done" ]]; then
        echo "Subject $subject_id has already been processed. Skipping."
        return 0
    fi

    # Run recon-all with full pipeline
    echo "Starting FreeSurfer processing for $subject_id"
    recon-all -subject "$subject_id" -i "$t1_path" -all \
        -openmp 1 \
        -no-isrunning \
        > "$SUBJECTS_DIR/logs/${subject_id}_recon-all.log" 2>&1

    local exit_code=$?
    if [[ $exit_code -eq 0 ]]; then
        echo "Subject $subject_id processed successfully"
        return 0
    else
        echo "Error processing subject $subject_id (exit code: $exit_code)"
        return 1
    fi
}

# Export the function so it's available to parallel
export -f process_subject
export SUBJECTS_DIR
export CLEAN

# Process subjects sequentially or in parallel
if command -v parallel >/dev/null 2>&1 && [ ${#T1_FILES[@]} -gt 0 ]; then
    echo "Processing ${#T1_FILES[@]} subjects using $PARALLEL parallel processes..."
    echo "$T1_FILES" | parallel -j "$PARALLEL" process_subject
else
    echo "GNU Parallel not found or no files to process. Processing subjects sequentially..."
    # Use for loop for sequential processing
    for t1_path in $T1_FILES; do
        process_subject "$t1_path"
    done
fi

echo "Processing complete!"

# Generate a summary report
echo "Generating summary report..."
successful=0
failed=0

for t1_path in $T1_FILES; do
    filename=$(basename "$t1_path")
    subject_id=$(echo "$filename" | sed -E 's/^(sub-[0-9]+)_.*/\1/')

    if [[ -f "$SUBJECTS_DIR/$subject_id/scripts/recon-all.done" ]]; then
        ((successful++))
    else
        ((failed++))
    fi
done

echo "========================================"
echo "FreeSurfer Processing Summary"
echo "========================================"
echo "Total subjects: $(echo "$T1_FILES" | wc -l)"
echo "Successfully processed: $successful"
echo "Failed: $failed"
echo "========================================"

# Optional: Create a script to extract features from processed subjects
cat > "$SUBJECTS_DIR/extract_features.sh" << EOF
#!/bin/bash
# This script extracts morphometric features from the processed subjects
# Run this after all subjects have been processed

export SUBJECTS_DIR="$OUTPUT_DIR"

# Create output directory for tables
mkdir -p "\$SUBJECTS_DIR/stats_tables"

# Generate list of successfully processed subjects
find "\$SUBJECTS_DIR" -name "recon-all.done" | xargs dirname | xargs dirname | xargs basename > "\$SUBJECTS_DIR/processed_subjects.txt"

# Extract cortical thickness
aparcstats2table --subjects \$(cat "\$SUBJECTS_DIR/processed_subjects.txt") \\
                 --hemi lh \\
                 --meas thickness \\
                 --tablefile "\$SUBJECTS_DIR/stats_tables/lh_thickness.txt"

aparcstats2table --subjects \$(cat "\$SUBJECTS_DIR/processed_subjects.txt") \\
                 --hemi rh \\
                 --meas thickness \\
                 --tablefile "\$SUBJECTS_DIR/stats_tables/rh_thickness.txt"

# Extract surface area
aparcstats2table --subjects \$(cat "\$SUBJECTS_DIR/processed_subjects.txt") \\
                 --hemi lh \\
                 --meas area \\
                 --tablefile "\$SUBJECTS_DIR/stats_tables/lh_area.txt"

aparcstats2table --subjects \$(cat "\$SUBJECTS_DIR/processed_subjects.txt") \\
                 --hemi rh \\
                 --meas area \\
                 --tablefile "\$SUBJECTS_DIR/stats_tables/rh_area.txt"

# Extract volume
aparcstats2table --subjects \$(cat "\$SUBJECTS_DIR/processed_subjects.txt") \\
                 --hemi lh \\
                 --meas volume \\
                 --tablefile "\$SUBJECTS_DIR/stats_tables/lh_volume.txt"

aparcstats2table --subjects \$(cat "\$SUBJECTS_DIR/processed_subjects.txt") \\
                 --hemi rh \\
                 --meas volume \\
                 --tablefile "\$SUBJECTS_DIR/stats_tables/rh_volume.txt"

# Extract subcortical volumes
asegstats2table --subjects \$(cat "\$SUBJECTS_DIR/processed_subjects.txt") \\
                --meas volume \\
                --tablefile "\$SUBJECTS_DIR/stats_tables/aseg_volumes.txt"

echo "Feature extraction complete! Results saved in \$SUBJECTS_DIR/stats_tables/"
EOF

chmod +x "$SUBJECTS_DIR/extract_features.sh"
echo "Created feature extraction script at $SUBJECTS_DIR/extract_features.sh"
echo "Run this script after all subjects have been processed to extract features for ADHD classification."

# Create a quality control script
cat > "$SUBJECTS_DIR/check_quality.sh" << EOF
#!/bin/bash
# This script generates quality control snapshots for all processed subjects

export SUBJECTS_DIR="$OUTPUT_DIR"

# Generate list of successfully processed subjects
find "\$SUBJECTS_DIR" -name "recon-all.done" | xargs dirname | xargs dirname | xargs basename > "\$SUBJECTS_DIR/processed_subjects.txt"

# Create QC directory
mkdir -p "\$SUBJECTS_DIR/qc_snapshots"

# Generate QC snapshots for each subject
while read subject; do
    echo "Generating QC snapshots for \$subject"

    # Create snapshot directory for this subject
    mkdir -p "\$SUBJECTS_DIR/qc_snapshots/\$subject"

    # Surface overlays
    freeview -v \\
        "\$SUBJECTS_DIR/\$subject/mri/T1.mgz" \\
        "\$SUBJECTS_DIR/\$subject/mri/aparc+aseg.mgz":colormap=lut:opacity=0.25 \\
        -f \\
        "\$SUBJECTS_DIR/\$subject/surf/lh.white":edgecolor=blue \\
        "\$SUBJECTS_DIR/\$subject/surf/lh.pial":edgecolor=red \\
        "\$SUBJECTS_DIR/\$subject/surf/rh.white":edgecolor=blue \\
        "\$SUBJECTS_DIR/\$subject/surf/rh.pial":edgecolor=red \\
        -viewport coronal \\
        -ss "\$SUBJECTS_DIR/qc_snapshots/\$subject/coronal.jpg" \\
        -quit

    # Axial view
    freeview -v \\
        "\$SUBJECTS_DIR/\$subject/mri/T1.mgz" \\
        "\$SUBJECTS_DIR/\$subject/mri/aparc+aseg.mgz":colormap=lut:opacity=0.25 \\
        -viewport axial \\
        -ss "\$SUBJECTS_DIR/qc_snapshots/\$subject/axial.jpg" \\
        -quit

    # Sagittal view
    freeview -v \\
        "\$SUBJECTS_DIR/\$subject/mri/T1.mgz" \\
        "\$SUBJECTS_DIR/\$subject/mri/aparc+aseg.mgz":colormap=lut:opacity=0.25 \\
        -viewport sagittal \\
        -ss "\$SUBJECTS_DIR/qc_snapshots/\$subject/sagittal.jpg" \\
        -quit

done < "\$SUBJECTS_DIR/processed_subjects.txt"

echo "QC snapshots generated in \$SUBJECTS_DIR/qc_snapshots/"
echo "Please review these snapshots to identify any processing issues."
EOF

chmod +x "$SUBJECTS_DIR/check_quality.sh"
echo "Created quality control script at $SUBJECTS_DIR/check_quality.sh"
echo "Run this script to generate quality control snapshots for visual inspection."