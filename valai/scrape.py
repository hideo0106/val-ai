# valai/scrape.py

import logging
import trafilatura

logger = logging.getLogger(__name__)

def fetch_url(url : str, *args, **kwargs) -> str:
    """Fetch a url and return the extracted text"""
    logger.debug(f"Fetching url: {url}")
    downloaded = trafilatura.fetch_url(url)
    extracted = trafilatura.extract(downloaded)
    if extracted is None:
        raise ValueError(f"Failed to extract text from {url}")
    logger.info(f"Fetched {len(extracted)} bytes from {url}")
    logger.debug(extracted)
    return extracted
