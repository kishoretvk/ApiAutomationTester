import json
import os
from datetime import datetime
from pathlib import Path

class APILogger:
    def __init__(self, api_name):
        self.api_name = api_name
        self.log_dir = Path("output/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"{api_name}_requests.jsonl"
        
    def log_request(self, request, response, duration):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request": {
                "method": request.get('method', ''),
                "url": request.get('url', ''),
                "headers": request.get('headers', {}),
                "body": request.get('body', {})
            },
            "response": {
                "status_code": response.get('status_code', 500),
                "headers": response.get('headers', {}),
                "body": response.get('body', {})
            },
            "duration": duration
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
