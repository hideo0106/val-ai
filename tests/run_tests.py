# tests/run_tests.py
import logging
import pytest
import os
import sys
from .config import EngineTestConfig, default_config

def main():
    logging.basicConfig(level=logging.DEBUG)
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'helpers'))
    # Change this to an individual test, or to a directory
    sys.exit(pytest.main(["./tests/engine/test_grammar.py"]))

if __name__ == "__main__":
    main()
