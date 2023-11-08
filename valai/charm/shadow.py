# valai/charm/shadow.py

import logging
import os
import re
from typing import List, Dict

from .model import Symbolizer, SymbolState

logger = logging.getLogger(__name__)


class ContextShadowing:
    """A class to represent the context shadowing algorithm."""

    def __init__(self, control: Symbolizer, state: SymbolState, scene_path: str):
        self.control = control
        self.state = state
        self.scene_path = scene_path
        self.high = self.control.broaden(self.state.symbols, recurse=3, mode='maximal')
        self.low = self.control.broaden(self.state.symbols, recurse=3, mode='minimal')

    def get_assets(self) -> Dict[str, list[str]]:
        sheets, dialog = self.control.character_data()
        return {
            'sheets': sheets,
            'dialog': dialog,
        }

    def low_expand(self, turn : List[str] = [], **kwargs) -> List[str]:
        matches = set()
        for back in range(0, len(turn)):
            line = turn[-back]
            for word in line.split():
                symbols = self.state.keywords.get(word.lower(), set())
                matches.update(symbols)

        symbols = list(matches)
        
        for item in symbols:
            if item in self.state.values:
                yield f"[{item} - {self.state.values[item]}]"
    
        return []

    def expand(self, history : List[str] = [], low : bool = True, high : bool = True, **kwargs) -> List[str]:
        scan : List[set] = []
        matched = set()
        for back in range(0, len(history)):
            line = history[-back]
            matches = set()
            for word in re.sub(r'[^a-zA-Z0-9 ]', '', line).split():
                word_symbols = self.state.keywords.get(word.lower(), set())
                matches.update(word_symbols)
            new_matches = matches - matched
            if len(new_matches) > 0:
                scan.append(new_matches)
            else:
                scan.append(set())
            matched.update(new_matches)

        scan = scan[::-1]

        matched = set()
        if low:
            for forward in range(len(scan)):
                line = scan[forward]
                matches = set()
                matches.update(line)
                for item in line:
                    matches.update(self.low.get(item))

                new_matches = matches - matched
                if len(new_matches) > 0:
                    scan[forward].update(new_matches)
                    matched.update(new_matches)

        if high:
            for forward in range(len(scan)):
                line = scan[forward]
                matches = set()
                matches.update(line)
                for item in line:
                    line_item = self.high.get(item)
                    if line_item is None:
                        continue
                    matches.update(line_item)

                new_matches = matches - matched
                if len(new_matches) > 0:
                    scan[forward].update(new_matches)
                    matched.update(new_matches)
            
        turns = []
        symbols = []
        player = None

        for output in range(len(history)):
            line = history[output]
            data = scan[output]
            # The order of a turn is:
            # 1. Symbols that need to be in the history
            # 3. The player's input
            # 4. Any other system output
            if len(data) > 0:
                for item in data:
                    if item in self.state.values:
                        symbols.append(f"[{item} - {self.state.values[item]}]")
            if line.startswith('['):
                symbols.append(line)
            elif line.startswith('>'):
                for item in symbols:
                    yield item
                symbols = []
                for turn in turns:
                    yield turn
                turns = [line]
            else:
                turns.append(line)

        return []

    def reload(self, **kwargs):
        filepath = os.path.join(self.scene_path, 'characters.json')
        self.control = Symbolizer.from_file(filepath)
        self.state = self.control.compile()
    
    @classmethod
    def from_file(cls, scene_path : str, **kwargs):
        filepath = os.path.join(scene_path, 'characters.json')
        control = Symbolizer.from_file(filepath)
        state = control.compile()
        return cls(control, state, scene_path)
