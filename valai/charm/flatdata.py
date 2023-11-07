# valai/charm/flatdata.py

from collections import defaultdict
import json
import logging
import os
import re
from typing import List, Dict, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class Location:
    """A class to represent a location in the game world."""

    def __init__(self, name: str, symbol: str, parent_symbol: Optional[str] = None,
                 related_symbols: List[str] = [], character_symbols: List[str] = []):
        self.id = id
        self.name = name
        self.symbol = symbol
        self.parent_symbol = parent_symbol
        self.related_symbols = related_symbols
        self.character_symbols = character_symbols

    @classmethod
    def from_dict(cls, **kwargs):
        return cls(**kwargs)


# Define the Symbol class
class Symbol:
    """A class to represent a symbol in the game world."""

    def __init__(self, symbol: str, value: str, keywords: List[str] = [], related_symbols: List[str] = []):
        self.symbol = symbol
        self.keywords = keywords
        self.related_symbols = related_symbols
        self.value = value

    @classmethod
    def from_dict(cls, **kwargs):
        return cls(**kwargs)

class Quest:
    def __init__(self, symbol: str, name: str, complete: bool, incomplete_symbol: str, complete_symbol: str):
        self.symbol = symbol
        self.name = name
        self.complete = complete
        self.incomplete_symbol = incomplete_symbol
        self.complete_symbol = complete_symbol

    def get_symbol(self):
        return self.complete_symbol if self.complete else self.incomplete_symbol

    @classmethod
    def from_dict(cls, **kwargs):
        return cls(**kwargs)


# Define the Character class
class Character:
    """A class to represent a character in the game world."""

    def __init__(self, id: int, name: str, symbol: str, related_symbols: List[str], job: str, traits: List[str],
                 location_symbol: str, description: str, disposition: int, status: str = None,
                 quests: Dict[str, Quest] = {}):
        self.id = id
        self.name = name
        self.symbol = symbol
        self.related_symbols = related_symbols
        self.job = job
        self.traits = traits
        self.location_symbol = location_symbol
        self.description = description
        self.disposition = disposition
        self.status = status
        self.quests = quests
    
    @classmethod
    def from_dict(cls, quests : list = [], **kwargs):
        quests = {q['symbol']: Quest.from_dict(**q) for q in quests}
        return cls(quests=quests, **kwargs)

    def character_line(self) -> str:
        """Fetch and format the data for a character."""
        # Format the character data
        character_data = f"[{self.name} "
        for i, trait in enumerate(self.traits):
            character_data += f" {chr(ord('a') + i)}={trait}"
        character_data += f" {self.symbol}]"

        return character_data

    def sample_dialog(self):
        yield f"> What is {self.name}'s job?"
        yield f"ZxdrOS: (job) {self.name} is a {self.job}."
        yield f"> I look at {self.name}."
        yield f"Narrator: (looking) {self.name} {self.description}"
        yield f"> What is {self.name} doing?"
        yield f"ZxdrOS: (status) {self.name} is {self.status}."

        yield f"> How does {self.name} feel about $player?"
        if (abs(self.disposition) - 15) < 0:
            yield f"ZxdrOS: (relationship) {self.name} doesn't have any strong opinions about $player."
            yield f'{self.name}: (curious) I see a new person in town. They open their mouth to speak, "...".  Perhaps they will speak to me first.'
        elif self.disposition > 50:
            yield f"ZxdrOS: (relationship) {self.name} loves $player."
            yield f'{self.name}: (happy) I see $player.  I hope they are doing well.'
        elif self.disposition > 15:
            yield f"ZxdrOS: (relationship) {self.name} likes $player."
            yield f'{self.name}: (neutral) I see $player.  I wonder what they are doing here.'
        elif self.disposition > -50:
            yield f"ZxdrOS: (relationship) {self.name} dislikes $player."
            yield f'{self.name}: (unhappy) I see $player.  I hope they don\'t bother me.'
        else:
            yield f"ZxdrOS: (relationship) {self.name} hates $player."
            yield f'{self.name}: (angry) I hope $player dies!'

        return []


class SymbolState:
    """A class to hold our compiled symbol state."""

    def __init__(self, symbols: Dict[str, Set[str]], keywords: Dict[str, Set[str]], values: Dict[str, str]):
        self.symbols = symbols
        self.keywords = keywords
        self.values = values
    
    def __str__(self):
        return f'Symbols: {self.symbols}\nKeywords: {self.keywords}\nValues: {self.values}'

    #def expand(self, mode : str = "minimal", recurse : int = 3, **kwargs):
    #    return Symbolizer.expand(self.symbols, recurse=recurse, mode=mode)


# Define the data object container
class Symbolizer:
    """A class to represent the game world."""

    def __init__(self, locations: Dict[str, Location], symbols: Dict[str, Symbol], characters: Dict[str, Character]):
        self.locations = locations
        self.symbols = symbols
        self.characters = characters

    @classmethod
    def from_file(cls, file_path: str):
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Parse locations
        locations = [Location.from_dict(**location_data) for location_data in data['locations']]
        locations = {location.symbol: location for location in locations}
        
        # Parse symbols
        symbols = [Symbol.from_dict(symbol=symbol, **details) for symbol, details in data['symbols'].items()]
        symbols = {symbol.symbol: symbol for symbol in symbols}
        
        # Parse characters
        characters = [Character.from_dict(**character_data) for character_data in data['characters']]
        characters = {character.symbol: character for character in characters}
        
        return cls(locations, symbols, characters)

    def character_data(self) -> tuple[list[str], list[str]]:
        """Fetch and format the data for a character."""

        stats, dialog = [], []
        for character in self.characters.values():
            stats.append(character.character_line())
            dialog += character.sample_dialog()

        return stats, dialog

    def compile(self) -> SymbolState:
        """Return a fully expanded list of all symbols in the game world, with their associated expansions."""
        symbol_mapping = defaultdict(set)
        keyword_mapping = defaultdict(set)
        value_mapping = defaultdict(str)

        # Process locations
        for location in self.locations.values():
            symbol_mapping[location.symbol].update([location.parent_symbol] + location.related_symbols + location.character_symbols)
            at_location = location.symbol.replace("^", "=")
            for symbol in location.related_symbols:
                symbol_mapping[symbol].add(at_location)

        # Process symbols
        for symbol_obj in self.symbols.values():
            symbol_mapping[symbol_obj.symbol].update(symbol_obj.related_symbols)
            for keyword in symbol_obj.keywords:
                keyword_mapping[keyword].add(symbol_obj.symbol)
            value_mapping[symbol_obj.symbol] = symbol_obj.value

        # Process characters
        for character in self.characters.values():
            symbol_mapping[character.symbol].update([character.location_symbol] + character.related_symbols)
            for symbol in character.related_symbols:
                symbol_mapping[symbol].update([character.symbol])
            symbol_mapping[character.location_symbol].update([character.symbol])

            # Process quests for the character
            for symbol, quest in character.quests.items():
                quest_symbol = quest.get_symbol()
                symbol_mapping[character.symbol].add(symbol)
                symbol_mapping[symbol].update([character.symbol, quest_symbol])
                symbol_mapping[quest_symbol].update([character.symbol])  # Relate the quest symbol back to the character symbol
        
        return SymbolState(symbols=symbol_mapping, keywords=keyword_mapping, values=value_mapping)
    
    def paint(self, history : List[str]):
        """Return a list of symbols that are related to the given history."""
        pass

    @staticmethod
    def symbol_strategy(symbol: Optional[str] = None) -> str:
        """Return the type of the symbol."""
        if symbol is None:
            return "unknown"
        return {
            '+': 'character',
            '^': 'location',
            '=': 'position',
            '%': 'symbol',
            '|': 'quest',
        }.get(symbol[0], 'unknown')

    @staticmethod
    def dive(symbols: Dict[str, Set[str]], symbol: str,
            s_type : str, expand_self : bool, expand_children : bool,
              matches : Set[str] = set(),
            recurse: int = 0) -> Set[str]:
        """Return the set of symbols related to the given symbol."""
        if recurse == 0 or symbol not in symbols:
            return matches
        if expand_self:
            logging.debug(f'Expanding {symbol} ({s_type})')
            matches.add(symbol)
        if expand_children:
            children = symbols[symbol]
            for c_symbol in children:
                if c_symbol in matches: continue
                c_type, c_p0, c_p1 = Symbolizer.symbol_strategy(c_symbol)
                matches.update(Symbolizer.dive(symbols, c_symbol, c_type, c_p0, c_p1, matches, recurse=recurse-1))
        return matches

    @classmethod
    def broaden(cls, symbols : Dict[str, Set[str]],
               mode : str = "minimal", e_count : int = 0,
               recurse : int = 0
               ) -> Dict[str, Set[str]]:
        """Expand our symbols to include all related symbols."""
        expanded_symbols = defaultdict(set)

        for s_symbol in list(symbols.keys()):
            s_type = cls.symbol_strategy(s_symbol)
            expanded_symbols[s_symbol]
            # For each symbol, we are going to do a breadth-first scan
            # to collect all of our related symbols
            #logger.info(f'Expanding {s_symbol} {mode} ({s_type}) ({s_p0}, {s_p1})')
            matched = set()
            queue = [(s_symbol, 0),]
            if s_type == 'location':
                l_symbol = s_symbol.replace('^', '=')
                l_related = symbols[l_symbol]
                queue.extend([(c, 1) for c in l_related])
            while len(queue) > 0:
                qv = queue.pop(0)
                r_symbol, r_depth = qv
                if r_symbol in matched: 
                    #logger.info(f'Skipping matched {s_symbol}/{r_symbol} {mode} ({s_type}/{r_type}) ({r_p0}, {r_p1})')
                    continue
                matched.add(r_symbol)
                r_type = cls.symbol_strategy(r_symbol)
                r_related = symbols[r_symbol]
                if r_related is None or None in r_related:
                    r_related = set()
                #logger.info(f"Queue popped {r_symbol} ({r_type}): {r_related}")
                if mode == 'minimal':
                    # For minimal mode, we just expand quest and symbol symbols,
                    # but anything else
                    if s_symbol == r_symbol:
                        queue.extend([(c, r_depth + 1) for c in r_related])
                        continue
                    if r_type == 'position' and r_depth > 1:
                        #logger.info(f'Skipping pos/pos {s_symbol}/{r_symbol} {mode} ({s_type}/{r_type}) ({r_p0}, {r_p1})')
                        continue
                    if r_type in ['quest', 'symbol']:
                        #logger.info(f'Expanding {s_symbol} {r_symbol} ({r_depth}) {mode} ({r_type}) ({r_p0}, {r_p1}): {r_related}')
                        expanded_symbols[s_symbol].add(r_symbol)
                        queue.extend([(c, r_depth + 1) for c in r_related])
                    else:
                        expanded_symbols[s_symbol].add(r_symbol)
                elif mode == 'maximal':
                    if s_symbol == r_symbol:
                        expanded_symbols[s_symbol].add(r_symbol)
                        queue.extend([(c, r_depth + 1) for c in r_related])
                        continue
                    if r_type == 'position' and r_depth > 1:
                        #logger.info(f'Skipping pos/pos {s_symbol}/{r_symbol} {mode} ({s_type}/{r_type}) ({r_p0}, {r_p1})')
                        continue
                    expanded_symbols[s_symbol].add(r_symbol)
                    #logger.info(f'Expanding {r_symbol} {mode} ({r_type}) ({r_p0}, {r_p1}): {r_related}')
                    queue.extend([(c, r_depth + 1) for c in r_related])
    
        count = sum([len(v) for v in expanded_symbols.values()])
        if count == e_count or recurse == 0:
            return expanded_symbols

        logger.info(f'Expanded {count} symbols, recursing...')

        return cls.broaden(expanded_symbols, mode=mode, e_count=count, recurse=recurse-1)

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

if __name__ == '__main__':

    from ..charming import Charmer

    logging.basicConfig(level=logging.DEBUG)
    shadow = ContextShadowing.from_file()
    history = Charmer.load_game_text()
    expanded = shadow.expand(history=history)
    for i, row in enumerate(expanded, start=0):
        print(i, row)
    #print({loc.symbol: loc.name for loc in symbolizer.locations})
    #print([sym.symbol for sym in symbolizer.symbols])
    #print({char.symbol: char.name for char in symbolizer.characters})
    #nsymbolset = control.expand(symbolset,mode="maximal",recurse=10)
    
