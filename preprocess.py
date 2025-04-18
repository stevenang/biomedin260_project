#!/usr/bin/env python3
import subprocess
import time
import datetime
import os

# File containing commands, one per line
SUBJECTS_FILE = "/Users/stevenang/PycharmProjects/adhd/data/all_participant_ids.txt"

# Optional: set a count limit
MAX_ITERATIONS = 98  # Set to your desired number or comment out for infinite loop


def get_first_command():
    """Read the first line from the commands file."""
    try:
        with open(SUBJECTS_FILE, 'r') as file:
            lines = sorted(file.readlines())
            if not lines:
                return None
            return lines[0].strip()
    except Exception as e:
        print(f"Error reading file: {e}")
        return None


def remove_first_line():
    """Remove the first line from the commands file."""
    try:
        with open(SUBJECTS_FILE, 'r') as file:
            lines = sorted(file.readlines())

        if lines:
            with open(SUBJECTS_FILE, 'w') as file:
                file.writelines(lines[1:])
            return True
        return False
    except Exception as e:
        print(f"Error modifying file: {e}")
        return False


def run_command():
    """Run the first command from file and return the exit code."""
    subject_id = get_first_command()
    if not subject_id:
        print("No subject_id left in file.")
        return None

    # Define command as a list of arguments (important for subprocess)
    commands = [
        "/Users/stevenang/PycharmProjects/adhd/preprocessing.sh",
        "--data-dir",
        "/Users/stevenang/Downloads/dataset/anat",
        "--output-dir",
        "/Users/stevenang/PycharmProjects/adhd/preprocessed_data",
        "--subjects",
        "/Users/stevenang/PycharmProjects/adhd/data/all_participant_ids.txt",
        "-p",
        "8"
    ]
    command_str = ' '.join(commands)

    try:
        print(f"Start processing {subject_id}")
        print(f"Starting command: {command_str}")
        print(f"Start time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Use the list of arguments instead of a string
        process = subprocess.Popen(commands)

        counter = 0
        # Monitor the process
        while process.poll() is None:  # None means the process is still running
            if counter % 15 == 0:
                print(f"Command still running... ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
            counter += 1
            time.sleep(60)  # Check every minute (adjust as needed)

        # Process has completed
        exit_code = process.returncode
        print(f"End time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # If successful, remove the command from the file
        if exit_code == 0:
            if remove_first_line():
                print("Command removed from file after successful execution.")
            else:
                print("Failed to remove command from file.")

        return exit_code

    except Exception as e:
        print(f"Error executing command: {e}")
        return 1


def main():
    iteration = 1
    success = 0
    failed = 0

    # Check if commands file exists
    if not os.path.exists(SUBJECTS_FILE):
        print(f"Commands file '{SUBJECTS_FILE}' not found. Please create it first.")
        return

    while True:
        print(f"\n{'=' * 50}")
        print(f"Starting iteration {iteration} at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 50}")

        # Run the command and wait for it to complete
        exit_code = run_command()

        # Check if we're out of commands
        if exit_code is None:
            print("No more commands to process. Exiting.")
            break

        # Check result
        if exit_code == 0:
            print(f"Iteration {iteration} completed successfully")
            success += 1
        else:
            print(f"Iteration {iteration} failed with exit code {exit_code}")
            failed += 1
            # We should still remove the line if the command fails to prevent infinite loops
            remove_first_line()
            print("Removed failed command from file to prevent repeated failure.")

        # Increment iteration counter
        iteration += 1

        # Optional: Break after MAX_ITERATIONS
        if 'MAX_ITERATIONS' in globals() and iteration > MAX_ITERATIONS:
            print(f"Reached maximum iterations ({MAX_ITERATIONS}). Exiting.")
            break

        # Check if there are more commands
        if get_first_command() is None:
            print("No more commands to process. Exiting.")
            break

        print(f"Starting next iteration in 5 seconds...")
        time.sleep(5)

    # print summary
    print(f"\n{'=' * 50}")
    print(f"Success: {success} / Failed: {failed}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()