# state_manager.py

import json
import os
import logging # Import logging module

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

STATE_FILE = "processing_state.json"

def load_state(state_file=STATE_FILE):
    """Loads the processing state from a JSON file."""
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
                logging.info(f"Successfully loaded state from {state_file}")
                return state
        except FileNotFoundError:
             # This case should be covered by os.path.exists, but included for robustness
             logging.warning(f"State file not found at {state_file}. Starting with empty state.")
             return {}
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from state file {state_file}. File might be corrupt. Starting with empty state.")
            return {} # Return empty state if file is corrupt
        except Exception as e:
            logging.error(f"An unexpected error occurred while loading state from {state_file}: {e}")
            return {} # Handle other potential exceptions
    else:
        logging.info(f"State file not found at {state_file}. Starting with empty state.")
    return {} # Return empty state if file doesn't exist

def save_state(state, state_file=STATE_FILE):
    """Saves the processing state to a JSON file."""
    try:
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=4)
        logging.info(f"Successfully saved state to {state_file}")
    except IOError as e:
        logging.error(f"Error saving state to file {state_file}: {e}")
        # Depending on requirements, you might want to handle this error
        # (e.g., notify user, attempt backup save)
    except Exception as e:
        logging.error(f"An unexpected error occurred while saving state to {state_file}: {e}")
        # Handle other potential exceptions during serialization or writing


def is_processed(state, question, api_name):
    """Checks if a question has been processed by a specific API."""
    # Ensure question is hashable if used as a dictionary key.
    # For simplicity, assuming question is a string or other hashable type.
    return state.get(question, {}).get(api_name, False)

def mark_as_processed(state, question, api_name):
    """Marks a question as processed by a specific API."""
    # Ensure question is hashable
    if question not in state:
        state[question] = {}
    state[question][api_name] = True

# TODO: Consider more robust state management for very large datasets (e.g., using a database)
