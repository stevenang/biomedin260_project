#!/usr/bin/env python3
import os
import pandas as pd
import glob
from pathlib import Path

# Define the root directory
root_dir = "/Users/stevenang/Downloads/dataset/ADHD200/raw_data"

# Define required fields that must be included
REQUIRED_FIELDS = ['adhd_index', 'adhd_measure', 'age', 'dx', 'gender']

# List to store all individual dataframes
all_dfs = []
# Dictionary to keep track of all unique columns across files
all_columns = set()

# Count for statistics
total_folders = 0
processed_files = 0
skipped_folders = 0
columns_by_file = {}
missing_required_fields = {}

print(f"Scanning {root_dir} for participants.tsv files...")

# First pass: identify all possible columns across all files
for dirpath, dirnames, filenames in os.walk(root_dir):
    total_folders += 1
    tsv_path = os.path.join(dirpath, "participants.tsv")

    # Check if participants.tsv exists in this folder
    if os.path.exists(tsv_path):
        try:
            # Read the TSV file header only to get columns
            df_cols = pd.read_csv(tsv_path, sep='\t', nrows=0).columns.tolist()
            source_folder = os.path.relpath(dirpath, root_dir)

            # Add these columns to our master set
            all_columns.update(df_cols)

            # Keep track of which columns are in which file
            columns_by_file[source_folder] = df_cols

            # Check if required fields are missing
            missing_fields = [field for field in REQUIRED_FIELDS if field not in df_cols]
            if missing_fields:
                missing_required_fields[source_folder] = missing_fields
                print(f"Warning: {source_folder} is missing required fields: {', '.join(missing_fields)}")

        except Exception as e:
            print(f"Error reading headers from {tsv_path}: {str(e)}")
    else:
        skipped_folders += 1

# Add source_folder to our columns
all_columns.add('source_folder')

# Make sure all required fields are in the column list
for field in REQUIRED_FIELDS:
    if field not in all_columns:
        all_columns.add(field)
        print(f"Added required field '{field}' to columns (not found in any file)")

# Display column analysis
print("\n--- Column Analysis ---")
print(f"Found {len(all_columns)} unique columns across all files")
print(f"Required fields: {', '.join(REQUIRED_FIELDS)}")

# Second pass: read the files and ensure consistent columns
for dirpath, dirnames, filenames in os.walk(root_dir):
    tsv_path = os.path.join(dirpath, "participants.tsv")

    # Check if participants.tsv exists in this folder
    if os.path.exists(tsv_path):
        try:
            # Read the TSV file
            df = pd.read_csv(tsv_path, sep='\t')

            # Add a column to indicate the source folder
            source_folder = os.path.relpath(dirpath, root_dir)
            df['source_folder'] = source_folder

            # Add missing columns with NaN values
            for col in all_columns:
                if col not in df.columns:
                    df[col] = pd.NA

            # If any required fields are missing, try alternative columns that might contain the same data
            for field in REQUIRED_FIELDS:
                if field not in df.columns or df[field].isna().all():
                    # Try common alternative column names
                    alternatives = {
                        'adhd_index': ['adhd_score', 'adhd_idx', 'adhd_rating'],
                        'adhd_measure': ['measure', 'assessment', 'scale'],
                        'age': ['age_years', 'age_at_scan', 'participant_age'],
                        'dx': ['diagnosis', 'group', 'condition', 'clinical_group'],
                        'gender': ['sex', 'biological_sex', 'participant_gender']
                    }

                    if field in alternatives:
                        for alt in alternatives[field]:
                            if alt in df.columns and not df[alt].isna().all():
                                print(f"  Using '{alt}' for required field '{field}' in {source_folder}")
                                df[field] = df[alt]
                                break

            # Append to our list of dataframes
            all_dfs.append(df)
            processed_files += 1

            # Check if any required fields are still missing after our attempts to fill them
            missing_after_processing = [field for field in REQUIRED_FIELDS if
                                        field not in df.columns or df[field].isna().all()]
            if missing_after_processing:
                print(f"  Warning: {source_folder} still missing data for: {', '.join(missing_after_processing)}")
            else:
                print(f"Processed: {tsv_path} - Found {len(df)} participants with all required fields")

        except Exception as e:
            print(f"Error processing {tsv_path}: {str(e)}")

# If we found any dataframes, combine them
if all_dfs:
    try:
        # Combine all dataframes
        combined_df = pd.concat(all_dfs, ignore_index=True)

        # Define priority column order:
        # 1. First: Your requested columns from the example
        # 2. Second: Required fields not already included in the first group
        # 3. Third: All other columns
        priority_columns = ['participant_id', 'gender', 'age', 'handedness', 'verbal_iq', 'source_folder']

        # Add any required fields that aren't already in the priority columns
        required_fields_to_add = [field for field in REQUIRED_FIELDS if field not in priority_columns]

        # Create final column order
        all_priority_columns = priority_columns + required_fields_to_add
        other_columns = [col for col in combined_df.columns if col not in all_priority_columns]

        # Reorder columns (handling the case where some priority columns might not exist)
        existing_priority_cols = [col for col in all_priority_columns if col in combined_df.columns]
        col_order = existing_priority_cols + other_columns
        combined_df = combined_df[col_order]

        # Display information about the combined dataframe
        print("\n--- Combined DataFrame Information ---")
        print(f"Total participants: {len(combined_df)}")
        print(f"Total columns: {len(combined_df.columns)}")

        # Calculate column completeness
        completeness = {}
        for col in combined_df.columns:
            non_null_count = combined_df[col].notna().sum()
            completeness[col] = f"{non_null_count}/{len(combined_df)} ({non_null_count / len(combined_df) * 100:.1f}%)"

        print("\n--- Priority Column Completeness ---")
        for col in existing_priority_cols:
            print(f"{col}: {completeness[col]}")

        # Save the combined dataframe as TSV
        output_path_tsv = os.path.join(root_dir, "combined_participants.tsv")
        combined_df.to_csv(output_path_tsv, sep='\t', index=False)
        print(f"\nCombined data saved to: {output_path_tsv}")

        # Also save as CSV
        output_path_csv = os.path.join(root_dir, "combined_participants.csv")
        combined_df.to_csv(output_path_csv, index=False)
        print(f"Combined data also saved as CSV: {output_path_csv}")

        # Generate diagnosis statistics
        print("\n\n======== DIAGNOSIS STATISTICS ========")

        # Create a standardized diagnosis column
        # Some datasets use different values for diagnosis, so we'll try to standardize
        if 'dx' in combined_df.columns:
            # Make a copy to avoid SettingWithCopyWarning
            combined_df = combined_df.copy()

            # Create a standardized diagnosis column
            combined_df['diagnosis_status'] = 'Unknown'

            # Look for common ADHD indicators in the 'dx' column
            adhd_indicators = ['adhd', 'ADHD', '1', 'yes', 'positive', 'patient']
            td_indicators = ['td', 'TD', 'TDC', 'control', '0', 'no', 'negative', 'typical', 'healthy']

            # Apply standardization rules
            for idx, row in combined_df.iterrows():
                dx_value = str(row.get('dx', '')).strip().lower()
                if any(indicator.lower() in dx_value for indicator in adhd_indicators):
                    combined_df.at[idx, 'diagnosis_status'] = 'ADHD'
                elif any(indicator.lower() in dx_value for indicator in td_indicators):
                    combined_df.at[idx, 'diagnosis_status'] = 'Typical Development'

            # Count overall diagnosis statistics
            diagnosis_counts = combined_df['diagnosis_status'].value_counts()
            print("\n--- Overall Diagnosis Counts ---")
            for status, count in diagnosis_counts.items():
                percentage = (count / len(combined_df)) * 100
                print(f"{status}: {count} ({percentage:.1f}%)")

            # Create age bins
            age_bins = [0, 8, 12, 18, float('inf')]
            age_labels = ['Under 8', '8-12', '13-18', 'Over 18']

            # Only process age statistics if the age column exists and has data
            if 'age' in combined_df.columns and not combined_df['age'].isna().all():
                combined_df['age_group'] = pd.cut(combined_df['age'], bins=age_bins, labels=age_labels)

                # Diagnosis by age group
                print("\n--- Diagnosis by Age Group ---")
                age_diagnosis = pd.crosstab(combined_df['age_group'], combined_df['diagnosis_status'],
                                            normalize='index') * 100
                age_diagnosis_counts = pd.crosstab(combined_df['age_group'], combined_df['diagnosis_status'])

                for age_group in age_diagnosis.index:
                    print(f"\nAge Group: {age_group} (Total: {age_diagnosis_counts.loc[age_group].sum()})")
                    for status in age_diagnosis.columns:
                        count = age_diagnosis_counts.loc[age_group, status]
                        percentage = age_diagnosis.loc[age_group, status]
                        print(f"  {status}: {count} ({percentage:.1f}%)")

            # Only process gender statistics if the gender column exists and has data
            if 'gender' in combined_df.columns and not combined_df['gender'].isna().all():
                # Standardize gender values
                combined_df['gender_std'] = combined_df['gender'].str.lower()
                combined_df.loc[combined_df['gender_std'].str.contains('f', na=False), 'gender_std'] = 'female'
                combined_df.loc[combined_df['gender_std'].str.contains('m', na=False), 'gender_std'] = 'male'

                # Diagnosis by gender
                print("\n--- Diagnosis by Gender ---")
                gender_diagnosis = pd.crosstab(combined_df['gender_std'], combined_df['diagnosis_status'],
                                               normalize='index') * 100
                gender_diagnosis_counts = pd.crosstab(combined_df['gender_std'], combined_df['diagnosis_status'])

                for gender in gender_diagnosis.index:
                    print(f"\nGender: {gender.title()} (Total: {gender_diagnosis_counts.loc[gender].sum()})")
                    for status in gender_diagnosis.columns:
                        count = gender_diagnosis_counts.loc[gender, status]
                        percentage = gender_diagnosis.loc[gender, status]
                        print(f"  {status}: {count} ({percentage:.1f}%)")

                # Cross-tabulation: Age group x Gender x Diagnosis
                if 'age_group' in combined_df.columns:
                    print("\n--- Diagnosis by Age Group and Gender ---")
                    for age_group in combined_df['age_group'].unique():
                        if pd.isna(age_group):
                            continue
                        print(f"\nAge Group: {age_group}")
                        subset = combined_df[combined_df['age_group'] == age_group]
                        age_gender_diag = pd.crosstab(subset['gender_std'], subset['diagnosis_status'],
                                                      normalize='index') * 100
                        age_gender_diag_counts = pd.crosstab(subset['gender_std'], subset['diagnosis_status'])

                        for gender in age_gender_diag.index:
                            print(f"  Gender: {gender.title()} (Total: {age_gender_diag_counts.loc[gender].sum()})")
                            for status in age_gender_diag.columns:
                                count = age_gender_diag_counts.loc[gender, status]
                                percentage = age_gender_diag.loc[gender, status]
                                print(f"    {status}: {count} ({percentage:.1f}%)")

            # Save the diagnostic statistics to a separate file
            stats_path = os.path.join(root_dir, "diagnostic_statistics.txt")
            with open(stats_path, 'w') as f:
                f.write("ADHD200 DATASET - DIAGNOSTIC STATISTICS\n")
                f.write("=====================================\n\n")
                f.write(f"Total participants: {len(combined_df)}\n\n")

                f.write("OVERALL DIAGNOSIS COUNTS\n")
                f.write("------------------------\n")
                for status, count in diagnosis_counts.items():
                    percentage = (count / len(combined_df)) * 100
                    f.write(f"{status}: {count} ({percentage:.1f}%)\n")

                if 'age_group' in combined_df.columns:
                    f.write("\nDIAGNOSIS BY AGE GROUP\n")
                    f.write("----------------------\n")
                    for age_group in age_diagnosis.index:
                        f.write(f"\nAge Group: {age_group} (Total: {age_diagnosis_counts.loc[age_group].sum()})\n")
                        for status in age_diagnosis.columns:
                            count = age_diagnosis_counts.loc[age_group, status]
                            percentage = age_diagnosis.loc[age_group, status]
                            f.write(f"  {status}: {count} ({percentage:.1f}%)\n")

                if 'gender_std' in combined_df.columns:
                    f.write("\nDIAGNOSIS BY GENDER\n")
                    f.write("------------------\n")
                    for gender in gender_diagnosis.index:
                        f.write(f"\nGender: {gender.title()} (Total: {gender_diagnosis_counts.loc[gender].sum()})\n")
                        for status in gender_diagnosis.columns:
                            count = gender_diagnosis_counts.loc[gender, status]
                            percentage = gender_diagnosis.loc[gender, status]
                            f.write(f"  {status}: {count} ({percentage:.1f}%)\n")

                    if 'age_group' in combined_df.columns:
                        f.write("\nDIAGNOSIS BY AGE GROUP AND GENDER\n")
                        f.write("--------------------------------\n")
                        for age_group in combined_df['age_group'].unique():
                            if pd.isna(age_group):
                                continue
                            f.write(f"\nAge Group: {age_group}\n")
                            subset = combined_df[combined_df['age_group'] == age_group]
                            age_gender_diag = pd.crosstab(subset['gender_std'], subset['diagnosis_status'],
                                                          normalize='index') * 100
                            age_gender_diag_counts = pd.crosstab(subset['gender_std'], subset['diagnosis_status'])

                            for gender in age_gender_diag.index:
                                f.write(
                                    f"  Gender: {gender.title()} (Total: {age_gender_diag_counts.loc[gender].sum()})\n")
                                for status in age_gender_diag.columns:
                                    count = age_gender_diag_counts.loc[gender, status]
                                    percentage = age_gender_diag.loc[gender, status]
                                    f.write(f"    {status}: {count} ({percentage:.1f}%)\n")

            print(f"\nDetailed diagnostic statistics saved to: {stats_path}")

            # Save dataset with standardized diagnosis column
            combined_df.to_csv(os.path.join(root_dir, "combined_participants_with_diagnosis.csv"), index=False)
            print(
                f"Enhanced dataset with standardized diagnosis saved to: {os.path.join(root_dir, 'combined_participants_with_diagnosis.csv')}")
        else:
            print("Unable to generate diagnosis statistics: 'dx' column not found in combined data.")

        # Print the first few rows of the combined dataframe (priority columns)
        print("\nPreview of combined data:")
        preview_cols = existing_priority_cols[:6]  # Limit preview to first 6 priority columns for readability
        if 'diagnosis_status' in combined_df.columns:
            preview_cols.append('diagnosis_status')
        print(combined_df[preview_cols].head())

    except Exception as e:
        print(f"Error combining dataframes: {str(e)}")
else:
    print("No participants.tsv files were found.")

# Print summary statistics
print("\n--- Summary ---")
print(f"Total folders scanned: {total_folders}")
print(f"Files processed: {processed_files}")
print(f"Folders skipped (no participants.tsv): {skipped_folders}")

# Create a report on column variations between files
print("\n--- Column Variations Report ---")
common_cols = set.intersection(*[set(cols) for cols in columns_by_file.values()]) if columns_by_file else set()
print(f"Common columns across all files: {', '.join(sorted(common_cols))}")

# Write a detailed report to a file
report_path = os.path.join(root_dir, "column_variations_report.txt")
with open(report_path, 'w') as f:
    f.write("COLUMN VARIATIONS ACROSS PARTICIPANTS.TSV FILES\n")
    f.write("==============================================\n\n")

    f.write(f"Total unique columns across all files: {len(all_columns)}\n")
    f.write(f"Columns present in all files: {len(common_cols)}\n\n")

    f.write("COLUMNS BY FILE\n")
    f.write("==============\n\n")
    for folder, cols in columns_by_file.items():
        f.write(f"{folder}:\n")
        f.write(f"  Total columns: {len(cols)}\n")
        unique_cols = set(cols) - common_cols
        if unique_cols:
            f.write(f"  Unique columns: {', '.join(sorted(unique_cols))}\n")
        missing_cols = all_columns - set(cols) - {'source_folder'}
        if missing_cols:
            f.write(f"  Missing columns: {', '.join(sorted(missing_cols))}\n")
        f.write("\n")

print(f"Detailed column variations report saved to: {report_path}")
print("Done!")