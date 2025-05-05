# output_writer.py

import asyncio
import json
import aiofiles # Import aiofiles for asynchronous file operations
import logging # Import logging module

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def write_result(file_path: str, result: dict):
    """
    Asynchronously writes a single result (JSON object) to a JSONL file.

    Args:
        file_path: Path to the output JSONL file.
        result: The result dictionary to write.
    """
    try:
        async with aiofiles.open(file_path, mode='a') as f:
            await f.write(json.dumps(result) + '\n')
        logging.info(f"Successfully wrote result to {file_path}")
    except IOError as e:
        logging.error(f"Error writing result to file {file_path}: {e}")
        # Depending on requirements, you might want to re-raise the exception
        # or handle it differently (e.g., store failed writes)
    except Exception as e:
        logging.error(f"An unexpected error occurred while writing to {file_path}: {e}")
        # Handle other potential exceptions during serialization or writing
