# valai/flow/output.py

import logging
import sys

logger = logging.getLogger(__name__)


class OutputHandler:
    def handle_progress(self, progress : float):
        progress = int(progress * 100.0)
        if progress >= 100:
            sys.stdout.write(f"{progress}%\n")
        else:
            sys.stdout.write(f"{progress}%..")
        sys.stdout.flush()

    def handle_token(self, token : str):
        sys.stdout.write(token)
        sys.stdout.flush()

    def handle_system(self, message : str):
        sys.stdout.write(f"{message}\n")
        sys.stdout.flush()
