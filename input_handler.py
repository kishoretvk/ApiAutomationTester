# input_handler.py

import pandas as pd
import streamlit as st # Import streamlit to use st.error/warning

def load_questions(file_path: str, file_type: str, column_name: str = None):
    """
    Loads questions from a given file.

    Args:
        file_path: Path to the input file.
        file_type: Type of the file ('txt', 'csv', 'xlsx').
        column_name: Column name for CSV/Excel files containing questions. Required for CSV/Excel.

    Returns:
        A list of questions, or an empty list if an error occurs.
    """
    questions = []
    try:
        if file_type == 'txt':
            with open(file_path, 'r') as f:
                questions = [line.strip() for line in f if line.strip()]
        elif file_type in ['csv', 'xlsx']:
            if not column_name:
                st.error(f"Column name is required for {file_type.upper()} files.")
                return []

            df = None
            if file_type == 'csv':
                df = pd.read_csv(file_path)
            else: # xlsx
                df = pd.read_excel(file_path)

            if column_name not in df.columns:
                st.error(f"Column '{column_name}' not found in the {file_type.upper()} file.")
                return []

            questions = df[column_name].dropna().tolist()

        if not questions:
            st.warning(f"No questions found in the file '{file_path}'. Please check the file content and column name.")

    except FileNotFoundError:
        st.error(f"Error: Input file not found at '{file_path}'.")
        return []
    except pd.errors.EmptyDataError:
        st.error(f"Error: The {file_type.upper()} file '{file_path}' is empty.")
        return []
    except pd.errors.ParserError:
        st.error(f"Error: Could not parse the {file_type.upper()} file '{file_path}'. Please check the file format.")
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred while reading the file: {e}")
        return []

    return questions
