import pandas as pd
import streamlit as st
from io import StringIO
import aiohttp
import asyncio
import ssl
from typing import Optional, List
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

class APIHandler:
    def __init__(self):
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=15)
        
    async def __aenter__(self):
        # Create SSL context that ignores verification if needed
        ssl_context = ssl.create_default_context()
        if hasattr(self, 'disable_verify') and self.disable_verify:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            connector=aiohttp.TCPConnector(ssl=ssl_context)
        )
        return self
        
    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=0.5, max=8)
    )
    async def make_request(self, method: str, url: str, **kwargs):
        try:
            # Remove verify parameter if present (not supported in aiohttp)
            kwargs.pop('verify', None)
            
            async with getattr(self.session, method.lower())(
                url,
                **kwargs
            ) as response:
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            logging.error(f"Request to {url} failed: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error making request: {str(e)}")
            raise

def load_questions(file_obj, file_type: str, column_name: str = None) -> List[str]:
    """Loads questions from a given file object or path."""
    questions = []
    try:
        if file_type == 'txt':
            if hasattr(file_obj, 'read'):
                content = file_obj.read().decode('utf-8')
                questions = [line.strip() for line in content.splitlines() if line.strip()]
            else:
                with open(file_obj, 'r') as f:
                    questions = [line.strip() for line in f if line.strip()]

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
