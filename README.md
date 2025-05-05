# API Processor App

This application is a versatile Streamlit-based tool designed to process questions or data points from various file formats (TXT, CSV, XLSX) by sending them to one or more configured external APIs. It efficiently manages API calls, respects rate limits, and provides features for resuming interrupted processing jobs.

## Features

*   **Flexible Input:** Supports reading questions/data from `.txt`, `.csv`, and `.xlsx` files.
*   **Multiple API Support:** Configure and send data to multiple API endpoints simultaneously.
*   **Rate Limiting:** Manages request rates to avoid overwhelming APIs.
*   **State Management:** Saves processing progress, allowing you to resume jobs from where they left off.
*   **Real-time Metrics:** Displays live processing statistics, including latency, payload size, error rates, and requests per minute (RPM).
*   **Configurable:** Easily set up API URLs, methods, headers, payloads, and global settings through the Configuration page.

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd streamlit_api_processor
    ```
    *(Replace `<repository_url>` with the actual URL of your repository)*

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: A `requirements.txt` file is needed. You can generate one using `pip freeze > requirements.txt` after installing necessary packages.)*

## How to Run

1.  **Ensure your virtual environment is active.**
2.  **Run the Streamlit application:**
    ```bash
    streamlit run app.py
    ```
3.  The application will open in your web browser.

## Usage

Navigate through the pages in the sidebar:

*   **⚙️ Configuration**: Set up your API endpoints, rate limits, timeouts, and retry logic.
*   **📊 Metrics**: Upload your input file, start/stop processing, and view real-time metrics and results.

## Screenshots

*(Screenshots will be added here)*
