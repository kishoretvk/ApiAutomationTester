import asyncio
import time
import json
import httpx # Using httpx for async HTTP requests
import logging # Import logging module

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Simple rate limiter (reusing the existing structure)
class RateLimiter:
    def __init__(self, rate: int, period: int):
        self.rate = rate # requests per period
        self.period = period # seconds
        self._allowance = rate
        self._last_check = time.monotonic()
        self._lock = asyncio.Lock()

    async def wait_for_permission(self):
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_check
            self._last_check = now
            self._allowance += elapsed * (self.rate / self.period)
            if self._allowance > self.rate:
                self._allowance = self.rate # cap allowance

            if self._allowance < 1.0:
                sleep_time = (1.0 - self._allowance) * (self.period / self.rate)
                logging.info(f"Rate limit exceeded, sleeping for {sleep_time:.2f} seconds.")
                await asyncio.sleep(sleep_time)
                self._allowance = 0
            else:
                self._allowance -= 1.0

class ApiClient:
    def __init__(self, api_config, global_rate_limiter: RateLimiter, timeout: int = 30):
        self.api_config = api_config
        self.global_rate_limiter = global_rate_limiter
        self.timeout = timeout # Request timeout in seconds
        self.client = httpx.AsyncClient(timeout=self.timeout) # Use a single client instance with timeout

    async def call_api(self, question: str, retries: int = 3, backoff_factor: float = 0.5):
        await self.global_rate_limiter.wait_for_permission() # Wait for global rate limit

        url = self.api_config.get("url")
        method = self.api_config.get("method", "POST").upper()
        headers = json.loads(self.api_config.get("headers", "{}"))
        payload_template = self.api_config.get("payload", "")
        api_name = self.api_config.get("name", "Unnamed API")

        # Construct the payload from template and question
        payload_data = None
        try:
            # Assuming payload_template is a JSON string with a placeholder like "{question}"
            payload = payload_template.replace("{question}", json.dumps(question))
            # Attempt to parse as JSON if method is POST/PUT/PATCH
            if method in ["POST", "PUT", "PATCH"]:
                 payload_data = json.loads(payload)
            else:
                 payload_data = None # GET/DELETE methods typically don't have bodies
        except json.JSONDecodeError:
            # If payload template is not valid JSON after replacement, send as plain text for POST/PUT/PATCH
            if method in ["POST", "PUT", "PATCH"]:
                 payload_data = payload
            else:
                 payload_data = None
            logging.warning(f"Could not parse payload as JSON for API {api_name}. Sending as is.")

        for attempt in range(retries):
            start_time = time.monotonic()
            try:
                if method == "GET":
                    response = await self.client.get(url, headers=headers, params=payload_data) # Use params for GET
                elif method == "POST":
                    response = await self.client.post(url, headers=headers, json=payload_data if isinstance(payload_data, dict) else None, content=payload_data if not isinstance(payload_data, dict) else None)
                elif method == "PUT":
                    response = await self.client.put(url, headers=headers, json=payload_data if isinstance(payload_data, dict) else None, content=payload_data if not isinstance(payload_data, dict) else None)
                elif method == "DELETE":
                    response = await self.client.delete(url, headers=headers, json=payload_data if isinstance(payload_data, dict) else None, content=payload_data if not isinstance(payload_data, dict) else None)
                elif method == "PATCH":
                     response = await self.client.patch(url, headers=headers, json=payload_data if isinstance(payload_data, dict) else None, content=payload_data if not isinstance(payload_data, dict) else None)
                else:
                    error_message = f"Unsupported HTTP method: {method}"
                    logging.error(error_message)
                    return {"error": error_message}, 0, 0, None, False, time.monotonic()

                response.raise_for_status() # Raise an exception for 4xx or 5xx status codes

                latency = time.monotonic() - start_time
                completion_time = time.monotonic()
                payload_size = len(response.content) # Actual response payload size
                status_code = response.status_code
                response_data = response.json() if response.content else {} # Attempt to parse JSON if content exists
                success = True

                # Return status_code along with other metrics and completion time
                return response_data, latency, payload_size, status_code, success, completion_time

            except httpx.TimeoutException as e:
                latency = time.monotonic() - start_time
                completion_time = time.monotonic()
                error_message = f"Timeout error for {api_name} ({url}): {e}"
                logging.warning(f"Attempt {attempt + 1} failed: {error_message}")
                if attempt < retries - 1:
                    sleep_time = backoff_factor * (2 ** attempt)
                    logging.info(f"Retrying in {sleep_time:.2f} seconds...")
                    await asyncio.sleep(sleep_time)
                else:
                    logging.error(f"Max retries reached for {api_name} ({url}).")
                    return {"error": error_message}, latency, 0, None, False, completion_time
            except httpx.RequestError as e:
                latency = time.monotonic() - start_time
                completion_time = time.monotonic()
                error_message = f"Request error for {api_name} ({url}): {e}"
                logging.warning(f"Attempt {attempt + 1} failed: {error_message}")
                if attempt < retries - 1:
                    sleep_time = backoff_factor * (2 ** attempt)
                    logging.info(f"Retrying in {sleep_time:.2f} seconds...")
                    await asyncio.sleep(sleep_time)
                else:
                    logging.error(f"Max retries reached for {api_name} ({url}).")
                    # Return status_code as None or 0 in case of request error before getting a response
                    return {"error": error_message}, latency, 0, None, False, completion_time
            except httpx.HTTPStatusError as e:
                latency = time.monotonic() - start_time
                completion_time = time.monotonic()
                status_code = e.response.status_code
                error_message = f"HTTP error for {api_name} ({url}): {status_code} - {e.response.text}"
                logging.warning(f"Attempt {attempt + 1} failed: {error_message}")
                # Retry only on specific status codes (e.g., 5xx errors, 429 Too Many Requests)
                if status_code >= 500 or status_code == 429:
                     if attempt < retries - 1:
                         sleep_time = backoff_factor * (2 ** attempt)
                         logging.info(f"Retrying in {sleep_time:.2f} seconds...")
                         await asyncio.sleep(sleep_time)
                     else:
                         logging.error(f"Max retries reached for {api_name} ({url}).")
                         # Return the actual status code from the HTTPStatusError
                         return {"error": error_message}, latency, len(e.response.content), status_code, False, completion_time
                else:
                    # Do not retry for other HTTP errors (e.g., 400, 404)
                    logging.error(f"Non-retryable HTTP error for {api_name} ({url}): {status_code}")
                    return {"error": error_message}, latency, len(e.response.content), status_code, False, completion_time
            except json.JSONDecodeError:
                 latency = time.monotonic() - start_time
                 completion_time = time.monotonic()
                 # Assuming response object is available from the try block before the exception
                 status_code = response.status_code if 'response' in locals() else None
                 error_message = f"JSON decode error for {api_name} ({url}): Response content was not valid JSON."
                 logging.warning(f"Attempt {attempt + 1} failed: {error_message}")
                 # Decide if JSON decode errors should be retried. Often not, as it indicates a consistent API response format issue.
                 # For now, we won't retry JSON decode errors.
                 logging.error(f"JSON decode error for {api_name} ({url}). Not retrying.")
                 # Return status_code if available
                 return {"error": error_message}, latency, len(response.content) if 'response' in locals() and response.content else 0, status_code, False, completion_time
            except Exception as e:
                latency = time.monotonic() - start_time
                completion_time = time.monotonic()
                error_message = f"An unexpected error occurred for {api_name} ({url}): {e}"
                logging.warning(f"Attempt {attempt + 1} failed: {error_message}")
                if attempt < retries - 1:
                    sleep_time = backoff_factor * (2 ** attempt)
                    logging.info(f"Retrying in {sleep_time:.2f} seconds...")
                    await asyncio.sleep(sleep_time)
                else:
                    logging.error(f"Max retries reached for {api_name} ({url}).")
                    # Return status_code as None or 0 for unexpected errors
                    return {"error": error_message}, latency, 0, None, False, completion_time

        # This part should ideally not be reached if retries are exhausted
        error_message = f"Processing failed for {api_name} ({url}) after {retries} attempts."
        logging.error(error_message)
        return {"error": error_message}, 0, 0, None, False, time.monotonic()


    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.close()

# TODO: Add certificate handling
