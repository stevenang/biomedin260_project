# File containing commands, one per line
NEW_SUBJECTS_FILE= "/Users/stevenang/PycharmProjects/adhd/data/additional/additional_participant_ids.txt"
SUBJECTS_FILE= "/Users/stevenang/PycharmProjects/adhd/data/additional/additional_participant_ids_reversed.txt"

def remove_first_line():
    """Remove the first line from the commands file."""
    try:
        with open(SUBJECTS_FILE, 'r') as file:
            lines = sorted(file.readlines(), reverse=False)

        if lines:
            with open(NEW_SUBJECTS_FILE, 'w') as file:
                file.writelines(lines)
            return True
        return False
    except Exception as e:
        print(f"Error modifying file: {e}")
        return False

remove_first_line()