# valai/charm/__main__.py

import logging

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
        
    logging.debug(f"Hello")