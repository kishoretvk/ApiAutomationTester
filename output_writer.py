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
    """Write enhanced API metrics to JSON file with robust error handling"""
    try:
        metrics_dir = Path("output/metrics")
        metrics_dir.mkdir(parents=True, exist_ok=True)
        
        # Safely calculate derived metrics with zero-division protection
        latencies = metrics.get('latencies', [])
        metrics['avg_latency'] = sum(latencies)/len(latencies) if latencies else 0
        
        payload_sizes = metrics.get('payload_sizes', [])
        metrics['avg_payload_size'] = sum(payload_sizes)/len(payload_sizes) if payload_sizes else 0
        
        total_requests = metrics.get('processed', 0) + metrics.get('errors', 0)
        metrics['error_percentage'] = (metrics['errors']/total_requests)*100 if total_requests > 0 else 0
        metrics['success_percentage'] = (metrics.get('successes', 0)/total_requests)*100 if total_requests > 0 else 0
        
        metrics_file = metrics_dir / f"{api_name}_metrics.json"
        
        # Write to temp file first then rename to ensure atomic write
        temp_file = metrics_dir / f"temp_{api_name}_metrics.json"
        with open(temp_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        # Replace existing file
        temp_file.replace(metrics_file)
        logging.info(f"Successfully saved metrics for {api_name}")
        
    except Exception as e:
        logging.error(f"Error writing metrics for {api_name}: {str(e)}")
        raise
