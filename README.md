### ADHD MRI Data Preprocessing

This project aims to be used to preprocess ADHD200 T1 MRI Image using FreeSurfer [Link](https://freesurfer.net)

#### Scripts:
1. preprocessing.sh - This scripts will read your image and perform the image processing using FreeSurfer


#### How to use:
##### Prerequisites
1. Download this repo
2. Download and Install Freesurfer [link](https://surfer.nmr.mgh.harvard.edu/fswiki/rel7downloads)
3. Run `pip install -r requirements.txt`
4. Run `brew install parallel`

##### How to use:
1. Run `download_s3_objects.py` to download the data from S3
2. Execute the following:
   ```aiignore
   ./preprocessing.sh --data-dir {data_path} --output-dir {output_path} --subjects {path to all_participant_ids.txt} -p 4
   ```
   Where `data_path` is where you stored the image data. `output_path` is where you want to stored the preprocessed data and `all_participant_ids.txt` contains the subject ids you want to process (sample can be found in `data/all_participant_ids.txt`)
2. 