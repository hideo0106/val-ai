# valai/pinnacle/prompt.py

import logging
import os

logger = logging.getLogger(__name__)


class Librarian(object):
    """A class for managing and reading from a library of text files."""

    @classmethod
    def from_config(cls, scene_path : str, library_folder : str = 'library', **kwargs):
        """Factory method to create a Librarian object from a config dictionary."""
        library_path = os.path.join(scene_path, library_folder)
        logger.debug(f'Library path: {library_path}')

        return cls(library_path)

    def __init__(self, library_path: str):
        """Initialize the Librarian object."""
        self.library_path = library_path

    def read_document(self, document_name: str, **kwargs):
        """Read a document from the library, formatting it with the provided kwargs."""
        with open(os.path.join(self.library_path, f'{document_name}.txt'), 'r') as f:
            document = f.read()
        return document.format(**kwargs)
