import pandas as pd
import streamlit as st
from io import StringIO

def load_questions(file_obj, file_type: str, column_name: str = None):
    """
    Loads questions from a given file object or path.

    Args:
        file_obj: File object (Streamlit UploadedFile or file path string)
        file_type: Type of the file ('txt', 'csv', 'xlsx')
        column_name: Column name for CSV/Excel files containing questions

    Returns:
        List of questions or empty list on error
    """
    questions = []
    try:
        # Handle text files
        if file_type == 'txt':
            if hasattr(file_obj, 'read'):
                content = file_obj.read().decode('utf-8')
                questions = [line.strip() for line in content.splitlines() if line.strip()]
            else:
                with open(file_obj, 'r') as f:
                    questions = [line.strip() for line in f if line.strip()]

        # Handle CSV/Excel files
        elif file_type in ['csv', 'xlsx']:
            if not column_name:
                st.error(f"Column name is required for {file_type.upper()} files")
                return []

            if hasattr(file_obj, 'read'):
                if file_type == 'csv':
                    df = pd.read_csv(StringIO(file_obj.read().decode('utf-8')))
                else:  # xlsx
                    df = pd.read_excel(file_obj)
            else:
                if file_type == 'csv':
                    df = pd.read_csv(file_obj)
                else:  # xlsx
                    df = pd.read_excel(file_obj)

            if column_name not in df.columns:
                st.error(f"Column '{column_name}' not found")
                return []

            questions = df[column_name].dropna().tolist()

        if not questions:
            st.warning("No questions found in the file")

    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return []

    return questions
