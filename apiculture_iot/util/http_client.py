#!/uae/bin/env python3
"""
HTTP Client Utility with Connection Pooling and Retry Strategy

This module provides a configured requests Session with:
- Connection pooling for better performance
- Automatic retry logic with exponential backoff
- Timeout configuration
- Proper error handling

Usage:
    from apiculture_iot.util.httpclient import http_session, make_request

    # Using the session
    response = http_session.post(url, json=data, timeout=(5, 30))

    # using the helper function with automatic retry
    response = make_request('POST', url, json=data, max_retries=3)
"""

import requests
import logging
import time
import timefrom typing import Optional, Tuple
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logger
logger = logging.getLogger(__name__)


class ResilientHTTPSession:
    """
    A resilient HTTP session with connection pooling and retry strategy.

    Features:
    - Connection pooling (reuses TCP connections)
    - Automatic retry on network failures and specific HTTP status codes
    - Exponential backoff between retries
    - Configurable timeouts
    """

    def __init__(
            self,
            total_retries: int = 3,
            backoff_factor: float = 1.0,
            status_forcelist: Tuple[int, ...] = (429, 500, 502, 503, 504),
            pool_connections: int = 10,
            pool_maxsize: int = 10
    ):
        """
        Initialize the resilient HTTP session.

        Args:
            total_retries: Total number of retries to attempt.
            backoff_factor: Backoff factor to apply between retries (in seconds).
            status_forcelist: List of HTTP status codes to force a retry on.
            pool_connections: Maximum number of connections to keep open with each host.
            pool_maxsize: Maximum total connections to keep open.
        """
        self.session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=total_retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE", "PATCH"]
        )

        # Configure HTTP adapter with retry strategy and connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize
        )

        # Mount adapter for both HTTP and HTTPS
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(f"Initialized ResilientHTTPSession with {total_retries} retries, "
                    f"backoff_factor {backoff_factor}, pool_size {pool_maxsize}")

    def request(
        self,
        method: str,
        url: str,
        timeout: Optional[Tuple[int, int]] = None,
        **kwargs
    ) -> requests.Response:
        """
        Make an HTTP request using the configured session.

        Args:
            method: HTTP method (e.g., GET, POST, PUT, DELETE).
            url: Request URL.
            timeout: Timeout in seconds for the request.
            **kwargs: Additional request parameters (e.g., JSON payload).

        Returns:
            Response object

        Raises:
            requests.RequestException: If an error occurs while making the request.
        """
        # Default timeout: 10s connect, 30s read
        if timeout is None:
            timeout = (10, 30)

        # Add Connection: close header to prevent stale connections
        headers = kwargs.get('headers', {})
        if 'Connection' not in headers:
            headers['Connection'] = 'close'
        kwargs['headers'] = headers

        return self.session.request(method, url, timeout=timeout, **kwargs)

    def get(self, url: str, **kwargs) -> requests.Response:
        """Convenience method for making a GET request."""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """Convenience method for making a POST request."""
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> requests.Response:
        """Convenience method for making a PUT request."""
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs) -> requests.Response:
        """Convenience method for making a DELETE request."""
        return self.request("DELETE", url, **kwargs)

    def patch(self, url: str, **kwargs) -> requests.Response:
        """Convenience method for making a PATCH request."""
        return self.request("PATCH", url, **kwargs)

    def close(self):
        """Close the session and release resources"""
        self.session.close()
        logger.info("HTTP session closed")


# Global singleton instance
_global_session = Optional[ResilientHTTPSession] = None


def get_http_session(
    total_retries: int = 3,
    backoff_factor: float = 1.0,
    pool_maxsize: int = 10
) -> ResilientHTTPSession:
    """
    Get or create the global HTTP session singleton.

    Args:
        total_retries: Total number of retries to attempt.
        backoff_factor: Backoff factor to apply between retries (in seconds).
        pool_maxsize: Maximum total connections to keep open.

    Returns:
        ResilientHTTPSession instance.
    """
    global _global_session

    if _global_session is None:
        _global_session = ResilientHTTPSession(
            total_retries=total_retries,
            backoff_factor=backoff_factor,
            pool_maxsize=pool_maxsize
        )

    return _global_session


def make_request(
        method: str,
        url: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: Optional[Tuple[float, float]] = None,
        **kwargs
) -> Optional[requests.Response]:
    """
    Make an HTTP request with manual retry logic and exponential backoff.

    This function provides additional retry logic on top of the session's
    built-in retry mechanism, specifically for handling connection resets.

    Args:
         method: HTTP method (e.g., GET, POST, PUT, DELETE).
         url: Request URL.
         max_retries: Maximum number of retries to attempt.
         retry_delay: Initial delay between retries (in seconds).
         timeout: Timeout in seconds for the request.
         **kwargs: Additional request parameters (e.g., JSON payload).

    Returns:
          Response object if successful, None otherwise.
    """
    session = get_http_session()

    if timeout is None:
        timeout = (10, 30)

    for attempt in range(max_retries):
        try:
            logger.info(f"Making {method} request to {url} (attempt {attempt + 1}/{max_retries})")

            response = session.request(method, url, timeout=timeout, **kwargs)

            # Check if response was successful
            if response.status_code in (200, 201, 204):
                logger.info(f"Request successful: {method} {url} - Status: {response.status_code}")
                return response
            else:
                logger.warning(f"Request returned status {response.status_code}: {method} {url}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed after {max_retries} attempts. {method} {url}")
                return response

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed after {max_retries} connection error attempts. {method} {url}")
                return None

        except requests.exceptions.Timeout as e:
            logger.error(f"Connection error on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed after {max_retries} timeout attempts. {method} {url}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Connection error on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed after {max_retries} request error attempts. {method} {url}")
                return None

    return None


# Convenience wraapper for the global session
http_session = get_http_session()


# Cleanup function
def cleanup_http_session():
    """Clean up the global HTTP session"""
    global _global_session
    if _global_session is not None:
        _global_session.close()
        _global_session = None
