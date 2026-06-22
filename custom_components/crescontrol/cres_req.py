import aiohttp
import asyncio
import logging
import random
from typing import Optional

_LOGGER = logging.getLogger(__name__)

# Global lock shared across all CresRequest instances to serialize
# HTTP requests to the embedded device
_GLOBAL_REQUEST_LOCK = asyncio.Lock()

# Maximum URL length to prevent 414 errors
MAX_URL_LENGTH = 1800
# Request timeout in seconds (increased for embedded devices)
REQUEST_TIMEOUT = 15
# Number of retries for failed requests
MAX_RETRIES = 3
# Base delay for exponential backoff between retries
RETRY_BASE_DELAY = 1
# Maximum delay for retry backoff
RETRY_MAX_DELAY = 10
# Delay between requests to avoid overwhelming the device
REQUEST_DELAY = 0.5


class CresRequestError(Exception):
    """Base exception for CresRequest errors."""
    pass


class CresRequestURITooLong(CresRequestError):
    """Raised when the URI exceeds the maximum allowed length."""
    pass


class CresRequestTimeout(CresRequestError):
    """Raised when a request times out."""
    pass


class CresRequestConnectionError(CresRequestError):
    """Raised when a connection error occurs."""
    pass


class CresRequestAuthError(CresRequestError):
    """Raised on HTTP 401/403 (authentication/authorization failure)."""
    pass


class CresRequest:
    """HTTP client for CresControl API requests with retry logic and error handling."""
    
    def __init__(self, reqAddr, session: Optional[aiohttp.ClientSession] = None):
        self.reqAddr = reqAddr
        self._timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        self._session: Optional[aiohttp.ClientSession] = session
        self._owns_session = session is None
        self._last_request_time = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            # Use a TCP connector optimized for embedded devices:
            # - limit=1: only one connection at a time to avoid overwhelming the device
            # - enable_cleanup_closed: clean up closed connections to avoid stale sockets
            # - force_close=True: close connections after each request to avoid connection pool issues
            connector = aiohttp.TCPConnector(
                limit=1,
                limit_per_host=1,
                enable_cleanup_closed=True,
                force_close=True,
            )
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                connector=connector,
            )
        return self._session

    async def close(self):
        """Close the aiohttp session if owned."""
        if self._session and not self._session.closed and self._owns_session:
            await self._session.close()
            self._session = None

    def _build_url(self, endpoint: str) -> str:
        """Build the request URL."""
        return f"http://{self.reqAddr}/command?query={endpoint}"

    def _validate_url_length(self, url: str):
        """Check if URL exceeds maximum length."""
        if len(url) > MAX_URL_LENGTH:
            raise CresRequestURITooLong(
                f"URL length ({len(url)}) exceeds maximum ({MAX_URL_LENGTH}). "
                f"Reduce the number of parameters in the request."
            )

    async def _get_request(self, endpoint: str):
        """Execute a GET request with retries and error handling."""
        url = self._build_url(endpoint)
        
        # Check URL length before sending
        self._validate_url_length(url)
        
        _LOGGER.debug(f"GET Request URL: {url}")

        # Rate limiting - ensure minimum delay between requests
        # Global lock protects the entire request lifecycle to prevent concurrent requests
        # across all subsystems talking to the same embedded device
        async with _GLOBAL_REQUEST_LOCK:
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self._last_request_time
            if time_since_last < REQUEST_DELAY:
                wait = REQUEST_DELAY - time_since_last
                _LOGGER.debug(f"Rate limiting: waiting {wait:.2f}s")
                await asyncio.sleep(wait)
            self._last_request_time = asyncio.get_event_loop().time()

            last_error = None
            
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    session = await self._get_session()
                    async with session.get(url) as response:
                        if response.status == 200:
                            content_type = response.headers.get("Content-Type", "")
                            
                            if "application/json" in content_type:
                                result = await response.json()
                                _LOGGER.debug(f"GET Response (JSON): {result}")
                                return result
                            elif "text/plain" in content_type:
                                content = await response.text()
                                _LOGGER.debug(f"GET Response (text/plain): {content}")
                                return content
                            else:
                                content = await response.text()
                                _LOGGER.debug(
                                    f"Unexpected content type '{content_type}', returning raw text"
                                )
                                return content
                        
                        elif response.status == 414:
                            raise CresRequestURITooLong(
                                f"URI Too Long ({len(url)} chars). Split your request into smaller batches."
                            )
                        elif response.status in (401, 403):
                            raise CresRequestAuthError(
                                f"Authentication error (HTTP {response.status})"
                            )
                        else:
                            response.raise_for_status()
                            
                except CresRequestURITooLong:
                    raise
                except CresRequestAuthError:
                    raise
                except asyncio.TimeoutError as e:
                    last_error = CresRequestTimeout(f"Request timeout (attempt {attempt}/{MAX_RETRIES})")
                    if attempt < MAX_RETRIES:
                        _LOGGER.debug(f"Request timeout (attempt {attempt}/{MAX_RETRIES}): {url}")
                    else:
                        _LOGGER.warning(f"Request timeout (attempt {attempt}/{MAX_RETRIES}): {url}")
                except aiohttp.ClientConnectionError as e:
                    last_error = CresRequestConnectionError(f"Connection error (attempt {attempt}/{MAX_RETRIES}): {e}")
                    if attempt < MAX_RETRIES:
                        _LOGGER.debug(f"Connection error (attempt {attempt}/{MAX_RETRIES}): {e}")
                    else:
                        _LOGGER.warning(f"Connection error (attempt {attempt}/{MAX_RETRIES}): {e}")
                    await self.close()
                except aiohttp.ClientResponseError as e:
                    last_error = CresRequestError(f"HTTP {e.status}: {e.message} (attempt {attempt}/{MAX_RETRIES})")
                    if attempt < MAX_RETRIES:
                        _LOGGER.debug(f"HTTP error {e.status} (attempt {attempt}/{MAX_RETRIES}): {url}")
                    else:
                        _LOGGER.warning(f"HTTP error {e.status} (attempt {attempt}/{MAX_RETRIES}): {url}")
                except Exception as e:
                    last_error = CresRequestError(f"Unexpected error (attempt {attempt}/{MAX_RETRIES}): {e}")
                    if attempt < MAX_RETRIES:
                        _LOGGER.debug(f"Unexpected error (attempt {attempt}/{MAX_RETRIES}): {e}")
                    else:
                        _LOGGER.warning(f"Unexpected error (attempt {attempt}/{MAX_RETRIES}): {e}")
                
                if attempt < MAX_RETRIES:
                    wait_time = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), RETRY_MAX_DELAY)
                    jitter = random.uniform(0, wait_time * 0.5)
                    wait_time += jitter
                    _LOGGER.debug(f"Waiting {wait_time:.1f}s before retry...")
                    await asyncio.sleep(wait_time)
            
            _LOGGER.error(f"All {MAX_RETRIES} attempts failed for: {url}")
            raise last_error

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
