#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

# Define paths
root_dir = "/Users/stevenang/Downloads/dataset/ADHD200/raw_data"
input_file = os.path.join(root_dir, "combined_participants_with_diagnosis.csv")
output_dir = "/Users/stevenang/PycharmProjects/adhd/data"
anat_dir = "/Users/stevenang/Downloads/dataset/anat"  # Directory containing anatomical images

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Load the combined data
print(f"Loading data from {input_file}")
try:
    df = pd.read_csv(input_file)
    print(f"Loaded dataset with {len(df)} participants and {len(df.columns)} columns")
except FileNotFoundError:
    # Try the regular combined file if the one with diagnosis doesn't exist
    input_file = os.path.join(root_dir, "combined_participants.csv")
    df = pd.read_csv(input_file)
    print(f"Using alternative file. Loaded {len(df)} participants")

    # Create diagnosis column if it doesn't exist
    if 'diagnosis_status' not in df.columns and 'dx' in df.columns:
        df['diagnosis_status'] = 'Unknown'

        # Common indicators
        adhd_indicators = ['adhd', 'ADHD', '1', 'yes', 'positive', 'patient']
        td_indicators = ['td', 'TD', 'TDC', 'control', '0', 'no', 'negative', 'typical', 'healthy']

        # Standardize diagnosis
        for idx, row in df.iterrows():
            dx_value = str(row.get('dx', '')).strip().lower()
            if any(indicator.lower() in dx_value for indicator in adhd_indicators):
                df.at[idx, 'diagnosis_status'] = 'ADHD'
            elif any(indicator.lower() in dx_value for indicator in td_indicators):
                df.at[idx, 'diagnosis_status'] = 'Typical Development'

# Standardize gender
if 'gender' in df.columns:
    df['gender_std'] = df['gender'].astype(str).str.lower()
    df.loc[df['gender_std'].str.contains('f', na=False), 'gender_std'] = 'female'
    df.loc[df['gender_std'].str.contains('m', na=False), 'gender_std'] = 'male'
else:
    print("Warning: 'gender' column not found")
    df['gender_std'] = 'unknown'

# Create age groups if age column exists
if 'age' in df.columns:
    # Create buckets for age: child (<=12), adolescent (13-17), adult (>=18)
    df['age_group'] = pd.cut(
        df['age'],
        bins=[0, 12, 17, 100],
        labels=['child', 'adolescent', 'adult'],
        right=True
    )
else:
    print("Warning: 'age' column not found")
    df['age_group'] = 'unknown'


# Function to check if anatomical image exists for a participant
def has_anat_image(participant_id):
    # Format participant ID with 'sub-' prefix and zero-padding
    pid_str = str(participant_id)
    if pid_str.startswith('sub-'):
        pid_str = pid_str[4:]

    try:
        numeric_id = int(pid_str)
        formatted_id = f"sub-{numeric_id:07d}"
    except ValueError:
        formatted_id = f"sub-{pid_str}"

    # Check if directory exists in anat folder
    participant_dir = os.path.join(anat_dir, formatted_id)
    if os.path.isdir(participant_dir):
        # Check if directory has at least one file
        files = os.listdir(participant_dir)
        return len(files) > 0

    # Also check without leading zeros (in case formatting is different)
    try:
        alternate_id = f"sub-{int(pid_str)}"
        alternate_dir = os.path.join(anat_dir, alternate_id)
        if os.path.isdir(alternate_dir):
            files = os.listdir(alternate_dir)
            return len(files) > 0
    except (ValueError, TypeError):
        pass

    return False


# Filter participants based on image availability
print(f"Checking anatomical image availability in {anat_dir}...")
df['has_image'] = df['participant_id'].apply(has_anat_image)
image_available_df = df[df['has_image'] == True].copy()

print(f"Found {len(image_available_df)} participants with available anatomical images")
if len(image_available_df) < 10:
    print("WARNING: Very few participants with images found. Check your directory paths.")

# Filter to only keep rows with valid diagnosis, gender, and age group
filtered_df = image_available_df[
    (image_available_df['diagnosis_status'].isin(['ADHD', 'Typical Development'])) &
    (image_available_df['gender_std'].isin(['male', 'female'])) &
    (image_available_df['age_group'].notna())
    ].copy()

print(f"After filtering for valid demographics, {len(filtered_df)} participants remain")

# If we have fewer than 100 valid participants, we'll need to be less strict
if len(filtered_df) < 100:
    print(f"Warning: Not enough participants with complete data (only {len(filtered_df)} available)")
    required_count = min(100, len(image_available_df))
    if len(filtered_df) < required_count:
        print("Using relaxed filtering criteria...")
        filtered_df = image_available_df[
            image_available_df['diagnosis_status'].isin(['ADHD', 'Typical Development'])].copy()
        print(f"After relaxed filtering, {len(filtered_df)} participants remain")

# Check distribution
print("\nDiagnosis distribution:")
print(filtered_df['diagnosis_status'].value_counts())

print("\nGender distribution:")
print(filtered_df['gender_std'].value_counts())

if 'age_group' in filtered_df.columns:
    print("\nAge group distribution:")
    print(filtered_df['age_group'].value_counts())

# Create a stratified sample of up to 100 participants (or all available if fewer than 100)
# We'll stratify by diagnosis, gender, and age group if possible
try:
    # Determine stratification columns based on available data
    strat_columns = ['diagnosis_status', 'gender_std']
    if 'age_group' in filtered_df.columns and not filtered_df['age_group'].isna().any():
        strat_columns.append('age_group')

    # Create a combined stratification column
    filtered_df['strat'] = filtered_df[strat_columns].astype(str).agg('_'.join, axis=1)

    # Check if we have enough data for stratification
    strat_counts = filtered_df['strat'].value_counts()
    min_count = strat_counts.min()

    if min_count == 0:
        # Handle empty strata by removing problematic categories
        print("\nWarning: Some stratification categories are empty. Using simplified stratification.")
        strat_columns = ['diagnosis_status']
        filtered_df['strat'] = filtered_df[strat_columns].astype(str)

    # For the final stratified sample
    n_samples = min(100, len(filtered_df))

    # Try stratified sampling, falling back to random if needed
    try:
        selected_df = filtered_df.groupby('strat', group_keys=False).apply(
            lambda x: x.sample(min(len(x), int(np.ceil(n_samples * len(x) / len(filtered_df)))))
        )

        # If we have more than desired, randomly select to get exactly n_samples
        if len(selected_df) > n_samples:
            selected_df = selected_df.sample(n_samples, random_state=42)
        # If we have less than desired, add more random samples
        elif len(selected_df) < n_samples and len(filtered_df) >= n_samples:
            remaining = filtered_df[~filtered_df.index.isin(selected_df.index)]
            additional = remaining.sample(n_samples - len(selected_df), random_state=42)
            selected_df = pd.concat([selected_df, additional])
    except ValueError as e:
        print(f"Error in stratified sampling: {e}")
        print("Falling back to random sampling")
        selected_df = filtered_df.sample(n_samples, random_state=42)
except Exception as e:
    print(f"Error in creating stratified sample: {e}")
    print("Falling back to random sampling")
    n_samples = min(100, len(filtered_df))
    selected_df = filtered_df.sample(n_samples, random_state=42)

print(f"\nSelected {len(selected_df)} participants for the ML dataset")

# Check final distribution
print("\nFinal diagnosis distribution:")
print(selected_df['diagnosis_status'].value_counts())

print("\nFinal gender distribution:")
print(selected_df['gender_std'].value_counts())

if 'age_group' in selected_df.columns:
    print("\nFinal age group distribution:")
    print(selected_df['age_group'].value_counts())

# Split into train (60%), validation (20%), test (20%)
train_df, temp_df = train_test_split(
    selected_df, test_size=0.4, random_state=42,
    stratify=selected_df['diagnosis_status'] if 'diagnosis_status' in selected_df.columns else None
)

val_df, test_df = train_test_split(
    temp_df, test_size=0.5, random_state=42,
    stratify=temp_df['diagnosis_status'] if 'diagnosis_status' in temp_df.columns else None
)

print(f"\nSplit results: Training={len(train_df)}, Validation={len(val_df)}, Test={len(test_df)}")

# Choose columns for the final dataset
# Priority columns + diagnosis + standardized columns + key clinical measures
priority_columns = ['participant_id', 'gender_std', 'age', 'age_group', 'diagnosis_status', 'source_folder']

# Add important clinical measures if they exist
potential_clinical_columns = [
    'adhd_index', 'adhd_measure', 'iq', 'verbal_iq', 'performance_iq',
    'full_iq', 'handedness', 'scanned', 'site'
]

final_columns = priority_columns + [col for col in potential_clinical_columns
                                    if col in selected_df.columns]

# Make sure all essential columns are present
for col in ['participant_id', 'gender_std', 'diagnosis_status']:
    if col not in final_columns and col in selected_df.columns:
        final_columns.append(col)

# Save the datasets
train_df[final_columns].to_csv(os.path.join(output_dir, 'train_data.csv'), index=False)
val_df[final_columns].to_csv(os.path.join(output_dir, 'validation_data.csv'), index=False)
test_df[final_columns].to_csv(os.path.join(output_dir, 'test_data.csv'), index=False)

# Also save the full selected dataset
selected_df[final_columns].to_csv(os.path.join(output_dir, 'full_dataset.csv'), index=False)

# Save participant IDs to text files with proper formatting
if 'participant_id' in selected_df.columns:
    # Save all participant IDs with 'sub-' prefix and zero-padding
    with open(os.path.join(output_dir, 'all_participant_ids.txt'), 'w') as f:
        for participant_id in selected_df['participant_id']:
            # Convert to string, strip any existing prefixes
            pid_str = str(participant_id)
            if pid_str.startswith('sub-'):
                pid_str = pid_str[4:]

            # Zero-pad to 7 digits and add 'sub-' prefix
            try:
                # For numeric IDs
                numeric_id = int(pid_str)
                formatted_id = f"sub-{numeric_id:07d}"
            except ValueError:
                # For non-numeric IDs, just add the prefix
                formatted_id = f"sub-{pid_str}"

            f.write(f"{formatted_id}\n")

    # Save train participant IDs with the same formatting
    with open(os.path.join(output_dir, 'train_participant_ids.txt'), 'w') as f:
        for participant_id in train_df['participant_id']:
            # Convert to string, strip any existing prefixes
            pid_str = str(participant_id)
            if pid_str.startswith('sub-'):
                pid_str = pid_str[4:]

            # Zero-pad to 7 digits and add 'sub-' prefix
            try:
                numeric_id = int(pid_str)
                formatted_id = f"sub-{numeric_id:07d}"
            except ValueError:
                formatted_id = f"sub-{pid_str}"

            f.write(f"{formatted_id}\n")

    # Save validation participant IDs with the same formatting
    with open(os.path.join(output_dir, 'validation_participant_ids.txt'), 'w') as f:
        for participant_id in val_df['participant_id']:
            # Convert to string, strip any existing prefixes
            pid_str = str(participant_id)
            if pid_str.startswith('sub-'):
                pid_str = pid_str[4:]

            # Zero-pad to 7 digits and add 'sub-' prefix
            try:
                numeric_id = int(pid_str)
                formatted_id = f"sub-{numeric_id:07d}"
            except ValueError:
                formatted_id = f"sub-{pid_str}"

            f.write(f"{formatted_id}\n")

    # Save test participant IDs with the same formatting
    with open(os.path.join(output_dir, 'test_participant_ids.txt'), 'w') as f:
        for participant_id in test_df['participant_id']:
            # Convert to string, strip any existing prefixes
            pid_str = str(participant_id)
            if pid_str.startswith('sub-'):
                pid_str = pid_str[4:]

            # Zero-pad to 7 digits and add 'sub-' prefix
            try:
                numeric_id = int(pid_str)
                formatted_id = f"sub-{numeric_id:07d}"
            except ValueError:
                formatted_id = f"sub-{pid_str}"

            f.write(f"{formatted_id}\n")

    print(f"Participant IDs saved to text files with 'sub-' prefix and zero-padding:")
    print(f"  - all_participant_ids.txt: {len(selected_df)} IDs")
    print(f"  - train_participant_ids.txt: {len(train_df)} IDs")
    print(f"  - validation_participant_ids.txt: {len(val_df)} IDs")
    print(f"  - test_participant_ids.txt: {len(test_df)} IDs")

# Create a metadata file
with open(os.path.join(output_dir, 'dataset_info.txt'), 'w') as f:
    f.write("ADHD200 MACHINE LEARNING DATASET\n")
    f.write("===============================\n\n")
    f.write(f"Total samples: {len(selected_df)}\n")
    f.write(f"Training samples: {len(train_df)} (60%)\n")
    f.write(f"Validation samples: {len(val_df)} (20%)\n")
    f.write(f"Test samples: {len(test_df)} (20%)\n\n")
    f.write(f"All participants have anatomical images available in: {anat_dir}\n\n")

    f.write("DATASET DISTRIBUTION\n")
    f.write("-------------------\n\n")

    f.write("Diagnosis distribution:\n")
    diag_counts = selected_df['diagnosis_status'].value_counts()
    for diag, count in diag_counts.items():
        f.write(f"  {diag}: {count} ({count / len(selected_df) * 100:.1f}%)\n")

    f.write("\nGender distribution:\n")
    gender_counts = selected_df['gender_std'].value_counts()
    for gender, count in gender_counts.items():
        f.write(f"  {gender}: {count} ({count / len(selected_df) * 100:.1f}%)\n")

    if 'age_group' in selected_df.columns:
        f.write("\nAge group distribution:\n")
        age_counts = selected_df['age_group'].value_counts()
        for age, count in age_counts.items():
            f.write(f"  {age}: {count} ({count / len(selected_df) * 100:.1f}%)\n")

    f.write("\nCROSS-TABULATION\n")
    f.write("--------------\n\n")

    f.write("Diagnosis by Gender:\n")
    diag_gender = pd.crosstab(selected_df['diagnosis_status'], selected_df['gender_std'])
    for diag in diag_gender.index:
        f.write(f"  {diag}:\n")
        for gender in diag_gender.columns:
            count = diag_gender.loc[diag, gender]
            f.write(f"    {gender}: {count}\n")

    if 'age_group' in selected_df.columns:
        f.write("\nDiagnosis by Age Group:\n")
        diag_age = pd.crosstab(selected_df['diagnosis_status'], selected_df['age_group'])
        for diag in diag_age.index:
            f.write(f"  {diag}:\n")
            for age in diag_age.columns:
                count = diag_age.loc[diag, age]
                f.write(f"    {age}: {count}\n")

    f.write("\nFEATURES\n")
    f.write("--------\n\n")
    f.write("Columns included in the dataset:\n")
    for col in final_columns:
        f.write(f"  - {col}\n")

print(f"\nDatasets saved to {output_dir}")
print(f"  - train_data.csv: {len(train_df)} samples")
print(f"  - validation_data.csv: {len(val_df)} samples")
print(f"  - test_data.csv: {len(test_df)} samples")
print(f"  - full_dataset.csv: {len(selected_df)} samples")
print(f"  - dataset_info.txt: Dataset information and statistics")
print("\nDone!")

# Save participant IDs to text files
if 'participant_id' in selected_df.columns:
    # Save all participant IDs with 'sub-' prefix and zero-padding
    with open(os.path.join(output_dir, 'all_participant_ids.txt'), 'w') as f:
        for participant_id in selected_df['participant_id']:
            # Convert to string, strip any existing prefixes
            pid_str = str(participant_id)
            if pid_str.startswith('sub-'):
                pid_str = pid_str[4:]

            # Zero-pad to 7 digits and add 'sub-' prefix
            try:
                # For numeric IDs
                numeric_id = int(pid_str)
                formatted_id = f"sub-{numeric_id:07d}"
            except ValueError:
                # For non-numeric IDs, just add the prefix
                formatted_id = f"sub-{pid_str}"

            f.write(f"{formatted_id}\n")

    # Save train participant IDs with the same formatting
    with open(os.path.join(output_dir, 'train_participant_ids.txt'), 'w') as f:
        for participant_id in train_df['participant_id']:
            # Convert to string, strip any existing prefixes
            pid_str = str(participant_id)
            if pid_str.startswith('sub-'):
                pid_str = pid_str[4:]

            # Zero-pad to 7 digits and add 'sub-' prefix
            try:
                numeric_id = int(pid_str)
                formatted_id = f"sub-{numeric_id:07d}"
            except ValueError:
                formatted_id = f"sub-{pid_str}"

            f.write(f"{formatted_id}\n")

    # Save validation participant IDs with the same formatting
    with open(os.path.join(output_dir, 'validation_participant_ids.txt'), 'w') as f:
        for participant_id in val_df['participant_id']:
            # Convert to string, strip any existing prefixes
            pid_str = str(participant_id)
            if pid_str.startswith('sub-'):
                pid_str = pid_str[4:]

            # Zero-pad to 7 digits and add 'sub-' prefix
            try:
                numeric_id = int(pid_str)
                formatted_id = f"sub-{numeric_id:07d}"
            except ValueError:
                formatted_id = f"sub-{pid_str}"

            f.write(f"{formatted_id}\n")

    # Save test participant IDs with the same formatting
    with open(os.path.join(output_dir, 'test_participant_ids.txt'), 'w') as f:
        for participant_id in test_df['participant_id']:
            # Convert to string, strip any existing prefixes
            pid_str = str(participant_id)
            if pid_str.startswith('sub-'):
                pid_str = pid_str[4:]

            # Zero-pad to 7 digits and add 'sub-' prefix
            try:
                numeric_id = int(pid_str)
                formatted_id = f"sub-{numeric_id:07d}"
            except ValueError:
                formatted_id = f"sub-{pid_str}"

            f.write(f"{formatted_id}\n")

    print(f"Participant IDs saved to text files with 'sub-' prefix and zero-padding:")
    print(f"  - all_participant_ids.txt: {len(selected_df)} IDs")
    print(f"  - train_participant_ids.txt: {len(train_df)} IDs")
    print(f"  - validation_participant_ids.txt: {len(val_df)} IDs")
    print(f"  - test_participant_ids.txt: {len(test_df)} IDs")

# Create a metadata file
with open(os.path.join(output_dir, 'dataset_info.txt'), 'w') as f:
    f.write("ADHD200 MACHINE LEARNING DATASET\n")
    f.write("===============================\n\n")
    f.write(f"Total samples: {len(selected_df)}\n")
    f.write(f"Training samples: {len(train_df)} (60%)\n")
    f.write(f"Validation samples: {len(val_df)} (20%)\n")
    f.write(f"Test samples: {len(test_df)} (20%)\n\n")

    f.write("DATASET DISTRIBUTION\n")
    f.write("-------------------\n\n")

    f.write("Diagnosis distribution:\n")
    diag_counts = selected_df['diagnosis_status'].value_counts()
    for diag, count in diag_counts.items():
        f.write(f"  {diag}: {count} ({count / len(selected_df) * 100:.1f}%)\n")

    f.write("\nGender distribution:\n")
    gender_counts = selected_df['gender_std'].value_counts()
    for gender, count in gender_counts.items():
        f.write(f"  {gender}: {count} ({count / len(selected_df) * 100:.1f}%)\n")

    if 'age_group' in selected_df.columns:
        f.write("\nAge group distribution:\n")
        age_counts = selected_df['age_group'].value_counts()
        for age, count in age_counts.items():
            f.write(f"  {age}: {count} ({count / len(selected_df) * 100:.1f}%)\n")

    f.write("\nCROSS-TABULATION\n")
    f.write("--------------\n\n")

    f.write("Diagnosis by Gender:\n")
    diag_gender = pd.crosstab(selected_df['diagnosis_status'], selected_df['gender_std'])
    for diag in diag_gender.index:
        f.write(f"  {diag}:\n")
        for gender in diag_gender.columns:
            count = diag_gender.loc[diag, gender]
            f.write(f"    {gender}: {count}\n")

    if 'age_group' in selected_df.columns:
        f.write("\nDiagnosis by Age Group:\n")
        diag_age = pd.crosstab(selected_df['diagnosis_status'], selected_df['age_group'])
        for diag in diag_age.index:
            f.write(f"  {diag}:\n")
            for age in diag_age.columns:
                count = diag_age.loc[diag, age]
                f.write(f"    {age}: {count}\n")

    f.write("\nFEATURES\n")
    f.write("--------\n\n")
    f.write("Columns included in the dataset:\n")
    for col in final_columns:
        f.write(f"  - {col}\n")

print(f"\nDatasets saved to {output_dir}")
print(f"  - train_data.csv: {len(train_df)} samples")
print(f"  - validation_data.csv: {len(val_df)} samples")
print(f"  - test_data.csv: {len(test_df)} samples")
print(f"  - full_dataset.csv: {len(selected_df)} samples")
print(f"  - dataset_info.txt: Dataset information and statistics")
print("\nDone!")