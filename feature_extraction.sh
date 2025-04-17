
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