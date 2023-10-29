# valai/ioutil.py

import io
import os
import sys
from textwrap import wrap

class CaptureOutput:
    """Capture stdout and stderr to a string"""
    def __init__(self):
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        self.captured_stdout = io.StringIO()
        self.captured_stderr = io.StringIO()

    def __enter__(self):
        sys.stdout = self.captured_stdout
        sys.stderr = self.captured_stderr
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._stdout
        sys.stderr = self._stderr

    @property
    def stdout(self):
        return self.captured_stdout.getvalue()

    @property
    def stderr(self):
        return self.captured_stderr.getvalue()

class CaptureFD:
    """Capture stdout and stderr to a string using file descriptors"""
    def __init__(self):
        self.stdout_fd = os.dup(1)  # Duplicate original stdout file descriptor
        self.stderr_fd = os.dup(2)  # Duplicate original stderr file descriptor
        self.captured_stdout = io.StringIO()
        self.captured_stderr = io.StringIO()
        self.pipe_out, self.pipe_out_wr = os.pipe()
        self.pipe_err, self.pipe_err_wr = os.pipe()

    def __enter__(self):
        os.dup2(self.pipe_out_wr, 1)  # Redirect stdout to write end of pipe
        os.dup2(self.pipe_err_wr, 2)  # Redirect stderr to write end of pipe
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.dup2(self.stdout_fd, 1)  # Restore original stdout
        os.dup2(self.stderr_fd, 2)  # Restore original stderr
        os.close(self.stdout_fd)
        os.close(self.stderr_fd)
        os.close(self.pipe_out_wr)
        os.close(self.pipe_err_wr)
        self.captured_stdout.write(os.read(self.pipe_out, 10000).decode('utf-8'))
        self.captured_stderr.write(os.read(self.pipe_err, 10000).decode('utf-8'))

    @property
    def stdout(self):
        return self.captured_stdout.getvalue()

    @property
    def stderr(self):
        return self.captured_stderr.getvalue()

def wrap_print(text, width=80):
    """Text wrapped to the given width"""
    return '\n'.join(wrap(text, width))
