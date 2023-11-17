# valai/flow/output.py

import logging
import sys

logger = logging.getLogger(__name__)


class OutputHandler:
    async def handle_token(self, token : str):
        sys.stdout.write(token)
        sys.stdout.flush()

