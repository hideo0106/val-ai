# valai/charm/prompt.py

import logging
import os
import re

from .database import DatabaseManager

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

def get_symbol_value(db : DatabaseManager, session, symbol : str):
    """Get the value of a symbol from the database."""
    # Query the InjectionSymbol table
    injection_symbol = db.get_symbol(session, symbol)

    # Return the value if the InjectionSymbol object is not None, otherwise return None
    if injection_symbol is not None:
        #return f"ZxdrOS: ({injection_symbol.keyword}) {injection_symbol.value}"
        return f"[{injection_symbol.keyword}: {injection_symbol.value}]"
    else:
        return None

def symbol_expansion(db : DatabaseManager, session, symbol : str, matched : set[str] = set[str]()):
    def expand_symbol(symbol: str, symbols=set[str](), values=set[str](), depth=0) -> set[str]:
        """Recursively expand a symbol."""
        if symbol in matched:
            return values
        value = get_symbol_value(db, session, symbol)
        matched.add(symbol)
        logger.debug(f'Expand, {symbol}, {value}')
        if value is None:
            return values
        if symbol in symbols:
            return values
        symbols.add(symbol)
        values.add((depth, value))
        matches = re.findall(r'%\w+%', value)
        for match in matches:
            expand_symbol(match, symbols, values, depth+1)
        return values

    return expand_symbol(symbol)