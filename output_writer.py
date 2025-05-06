import json
import logging
from pathlib import Path
from datetime import datetime

def write_api_log(api_name: str, request: dict, response: dict):
    """Write API call log to JSONL file"""
    try:
        log_dir = Path("output/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"{api_name}_calls.jsonl"
        with open(log_file, 'a') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "api_name": api_name,
                "request": request,
                "response": response,
                "processing_time": (datetime.now() - request['start_time']).total_seconds()
            }, f)
            f.write('\n')
    except Exception as e:
        logging.error(f"Error writing API log: {e}")

def write_api_metrics(api_name: str, metrics: dict):
    """Write API metrics to JSON file"""
    try:
        metrics_dir = Path("output/metrics")
        metrics_dir.mkdir(parents=True, exist_ok=True)
        
        metrics_file = metrics_dir / f"{api_name}_metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
    except Exception as e:
        logging.error(f"Error writing metrics: {e}")
