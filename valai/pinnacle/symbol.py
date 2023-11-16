# valai/pinnacle/symbol.py

from collections import defaultdict
import json
import logging
import os
import re
from typing import List, Dict, Optional, Set

from .model import Location, Symbol, Character, CharacterDialog, Quest

logger = logging.getLogger(__name__)


class SymbolState:
    """A class to hold our compiled symbol state."""

    def __init__(self, symbols: Dict[str, Set[str]], keywords: Dict[str, Set[str]], values: Dict[str, str]):
        self.symbols = symbols
        self.keywords = keywords
        self.values = values
    
    def __str__(self):
        return f'Symbols: {self.symbols}\nKeywords: {self.keywords}\nValues: {self.values}'


class Symbolizer:
    """A class to represent the game world."""

    def __init__(self, player : Character,
                 locations: Dict[str, Location],
                 characters: Dict[str, Character],
                 symbols: Dict[str, Symbol],
                 quests: Dict[str, Quest],
                 character_dialog : CharacterDialog):
        self.player = player
        self.locations = locations
        self.characters = characters
        self.symbols = symbols
        self.quests = quests
        self.character_dialog = character_dialog

    @classmethod
    def from_config(cls, scene_path : str, character_dialog : CharacterDialog, **kwargs):
        filepath = os.path.join(scene_path, 'characters.json')
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Parse player
        player = Character.from_dict(**data['player'])
            
        # Parse locations
        locations = [Location.from_dict(symbol=l, **location_data) for l, location_data in data['locations'].items()]
        locations = {location.symbol: location for location in locations}
        
        # Parse symbols
        symbols = [Symbol.from_dict(symbol=s, **details) for s, details in data['symbols'].items()]
        symbols = {symbol.symbol: symbol for symbol in symbols}
        
        # Parse characters
        characters = [Character.from_dict(symbol=c, **character_data) for c, character_data in data['characters'].items()]
        characters = {character.symbol: character for character in characters}

        quests = [Quest.from_dict(symbol=q, **quest_data) for q, quest_data in data['quests'].items()]
        quests = {quest.symbol: quest for quest in quests}
        
        return cls(player, locations, characters, symbols, quests, character_dialog)

    def character_data(self) -> tuple[list[str], list[str]]:
        """Fetch and format the data for a character."""

        stats, dialog = [], []
        for character in self.characters.values():
            stats.append(character.character_line())
            dialog += self.character_dialog(character)

        return stats, dialog

    def compile(self, location_symbol : str, party : Set[str] = set(), quest_characters : Dict[str, Character] = [], **kwargs) -> SymbolState:
        """Return a fully expanded list of all symbols in the game world, with their associated expansions."""
        # This is for our symbol to related symbol mapping
        symbol_mapping = defaultdict(set)
        # This is for our keyword to symbol mapping
        keyword_mapping = defaultdict(set)
        # This is for our character to symbol mapping
        character_mapping = defaultdict(set)
        # Every symbol needs a value mapping
        value_mapping = defaultdict(str)

        if location_symbol not in self.locations:
            raise ValueError(f'Invalid location symbol {location_symbol}')

        # First, grap all related symbols from the location
        # Then, grab any characters that are at the location
        # Then grab any general symbols or quests that are associated with the characters

        location_obj = self.locations[location_symbol]

        value_mapping[location_obj.at_location] = location_obj.description
        symbol_mapping[location_obj.symbol].update(location_obj.related_symbols)
        symbol_mapping[location_obj.symbol].add(location_obj.at_location)
        symbol_mapping[location_obj.at_location] = set()
        for symbol in location_obj.related_symbols:
            symbol_mapping[location_obj.at_location].add(symbol)

        for c, character_obj in self.characters.items():
            add = False
            if character_obj.location_symbol == location_obj.at_location:
                add = True
                logger.debug(f'Adding {c} to {location_symbol}')
            elif character_obj.symbol in party:
                add = True
                logger.debug(f'Adding {c} to {location_symbol} (party)')
            else:
                #logger.debug(f'Skipping {c} to {location_symbol}')
                pass

            if add:
                character_mapping[c].add(location_symbol)
                value_mapping[c] = character_obj.title
                symbol_mapping[c].add(location_symbol)

                for related_symbol in character_obj.related_symbols:
                    character_mapping[c].add(related_symbol)
                    symbol_mapping[related_symbol].add(c)
                    symbol_mapping[c].add(related_symbol)

                for keyword in character_obj.character_keywords:
                    keyword_mapping[keyword].add(c)

                for s, new_symbol in character_obj.symbols.items():
                    character_mapping[c].add(s)
                    for related_symbol in new_symbol.related_symbols:
                        symbol_mapping[related_symbol].add(s)
                    for keyword in new_symbol.keywords:
                        keyword_mapping[keyword].add(s)
                    value_mapping[s] = new_symbol.value

        # Process quests to see if any need to decorate with new characters or symbols
        for q, quest in self.quests.items():
            # TODO Quests
            quest_symbols = quest.get_symbols()
            for qs, symbol_obj in quest_symbols['symbols'].items():
                related = False
                #print (qs, symbol_obj)
                for related_symbol in symbol_obj.related_symbols:
                    if related_symbol not in symbol_mapping:
                        #print("Skipping", related_symbol)
                        continue
                    symbol_mapping[related_symbol].add(qs)
                    related = True
                if related:
                    for keyword in symbol_obj.keywords:
                        keyword_mapping[keyword].add(qs)
                    value_mapping[qs] = symbol_obj.value
            
            for qc, character_obj in quest_symbols['characters'].items():
                #print (qc, character_obj, character_obj.location_symbol, location_obj.at_location)
                if character_obj.location_symbol != location_obj.at_location:
                    continue
                character_mapping[qc].add(location_symbol)
                value_mapping[qc] = character_obj.title
                symbol_mapping[qc].add(location_symbol)

                for related_symbol in character_obj.related_symbols:
                    character_mapping[qc].add(related_symbol)
                    symbol_mapping[related_symbol].add(qc)
                    symbol_mapping[qc].add(related_symbol)

                for keyword in character_obj.character_keywords:
                    keyword_mapping[keyword].add(qc)

                for s, new_symbol in character_obj.symbols.items():
                    character_mapping[qc].add(s)
                    for related_symbol in new_symbol.related_symbols:
                        symbol_mapping[related_symbol].add(s)
                    for keyword in new_symbol.keywords:
                        keyword_mapping[keyword].add(s)
                    value_mapping[s] = new_symbol.value
                
        # Process symbols
        for symbol_obj in self.symbols.values():
            if symbol_obj.symbol in symbol_mapping:
                for related_symbol in symbol_obj.related_symbols:
                    symbol_mapping[related_symbol].add(symbol_obj.symbol)
                value_mapping[symbol_obj.symbol] = symbol_obj.value
                for keyword in symbol_obj.keywords:
                    keyword_mapping[keyword].add(symbol_obj.symbol)

        #print (symbol_mapping, keyword_mapping, value_mapping)

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

        logger.debug(f'Expanded {count} symbols, recursing...')

        return cls.broaden(expanded_symbols, mode=mode, e_count=count, recurse=recurse-1)


class ContextShadowing:
    """A class to represent the context shadowing algorithm."""

    state : Optional[SymbolState]
    high : Optional[Dict[str, set[str]]]
    low : Optional[Dict[str, set[str]]]

    def __init__(self, control: Symbolizer):
        self.control = control
    
    def set_state(self, location_symbol : str, party : Set[str] = {}):
        self.state = self.control.compile(location_symbol, party=party)
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
        if low and self.low is None:
            raise ValueError("Low context has not been set")
        if high and self.high is None:
            raise ValueError("High context has not been set")
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
                    lval = self.low.get(item)
                    if lval is not None:
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
            elif line[0] in ['>', '$']:
                for item in symbols:
                    yield item
                symbols = []
                for turn in turns:
                    yield turn
                turns = [line]
            else:
                turns.append(line)
        if len(symbols) > 0:
            for item in symbols:
                yield item
        if len(turns) > 0:
            for turn in turns:
                yield turn

        return []

    def reload(self, location_symbol : Optional[str] = None, party : Set[str] = set(), **kwargs):
        # It's a bit hacky to pull our dialog generator out of the last instance, but it works
        character_dialog = self.control.character_dialog
        self.control = Symbolizer.from_config(character_dialog=character_dialog, **kwargs)
        self.state = None
        self.low = None
        self.high = None
        self.set_state(location_symbol, party=party)
    
    @classmethod
    def from_config(cls, **kwargs):
        control = Symbolizer.from_config(**kwargs)
        return cls(control)