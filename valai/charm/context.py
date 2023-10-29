# valai/charm/context.py

import logging
import re

from .prompt import Librarian
from .database import DatabaseManager
from .scene import Scene
from .prompt import symbol_expansion

logger = logging.getLogger(__name__)

class ContextInjection(object):
    """Class for handling context injection."""

    @classmethod
    def from_db(cls, db : DatabaseManager, scene : Scene, **kwargs):
        """Factory method to create a ContextInjection object from a database URI."""
        librarian = Librarian.from_config(**kwargs)
        return cls(db, librarian, scene)

    def __init__(self, db : DatabaseManager, librarian : Librarian, scene : Scene):
        """Initialize the ContextInjection object."""
        self.db = db
        self.librarian = librarian
        self.scene = scene
        self.last_turn = None

    def set_location(self, location_name: str):
        with self.db.get_session() as session:
            self.scene.set_location(session, location_name)

    def header(self):
        return self.librarian.read_document('system_header') + '\n' + self.librarian.read_document('system_actor')

    def mid_pre(self):
        player_stats = self.scene.player_stats()
        return self.librarian.read_document('system_mid_pre', player_stats=player_stats)

    def mid_post(self):
        player_stats = self.scene.player_stats()
        return self.librarian.read_document('system_mid_post', player_stats=player_stats)

    def extract_delta(self, turn_text):
        """Extract the trailing difference between turn_text and self.last_turn."""
        # If there's no previous turn, the delta is the entire text
        if self.last_turn is None:
            return turn_text

        # Function to find the index of the nth occurrence of a character from the end
        def rfind_nth(string, char, n):
            index = len(string)
            for _ in range(n):
                index = string.rfind(char, 0, index)
                if index == -1:  # If the character is not found, return -1
                    return -1
            return index

        # Find the index of the third last newline character in the last turn
        index = rfind_nth(self.last_turn, '\n', 3)

        # The last three lines are everything after this index
        last_three_lines = self.last_turn[index+1:]

        # Find the index of the last three lines in the turn text
        index = turn_text.find(last_three_lines)

        # If the last three lines are found in the turn text, the delta is everything after them
        if index != -1:
            delta = turn_text[index + len(last_three_lines):]
        else:
            # If the last three lines are not found in the turn text, the delta is the entire turn text
            delta = turn_text

        return delta

    def feedback_context(self, text_delta):
        """Find and execute command in the text_delta."""

        # Define the command handlers
        commands = {
            'echo': lambda *args: ' '.join(['echo', *args]),
            'quest': lambda *args: ' '.join(['quest', *args]),
            'join': lambda *args: ' '.join(['join', *args]),
            'leave': lambda *args: ' '.join(['leave', *args]),
            'travel': lambda *args: ' '.join(['travel', *args]),
        }

        # Default handler if command is not found
        FAILURE = lambda: "Command Failed"

        # Extract the command and arguments from the text_delta
        match = re.search('<COMMAND: (\w+)(.*?)>', text_delta)

        if match:
            # Convert the command to lowercase and get the action
            command = match.group(1).lower()
            action = commands.get(command, FAILURE)

            # Extract the arguments
            args = match.group(2).strip().split()

            # Execute the action with the arguments and return its result
            result = action(*args)

            if result is None: return None
            
            return {'state': 'command', 'command': command, 'result': result}

        # If no command is found, return None
        return None

    def expand(self, text: str, constrain_data : int = 12000, **kwargs):
        """Expand the text using the context dictionary."""
        logger.debug(f"Expanding: {len(text)}")
        text = text[-constrain_data:]
        # Extract the delta between text and last_turn
        # delta = self.extract_delta(text)

        # Feed the delta into feedback_context
        # feedback = self.feedback_context(delta)

        # Create a new session
        with self.db.get_session() as session:
            # If feedback_context returns anything but None, return None
            #if feedback is not None:
            #    logger.info("Command:", feedback)
            #    return feedback

            all_stats = []
            all_symbols = []
            all_dialog = []
            matched = set[str]()

            for character_name in self.scene.characters:
                char_stats, char_symbols, char_dialog = self.scene.fetch_character_data(session, character_name)
                all_stats = all_stats + char_stats
                all_symbols = all_symbols + char_symbols
                all_dialog = all_dialog + char_dialog

            loc_stats, loc_symbols, loc_dialog = self.scene.fetch_location_data()

            # Build the symbol-keyword dictionary
            symbol_kw_dict = self.scene.get_kw_symbol()
            kw_pattern = r"\b(" + "|".join(symbol_kw_dict.values()) + r")\b"

            # Split the text into lines
            lines = text.split('\n')

            # Initialize a dictionary to keep track of the last occurrence index of each symbol
            symbol_indices = {}

            symbol_min = len(lines) - 12
            if symbol_min < 0:
                symbol_min = 0

            low_index = len(lines) - 8
            if low_index < 0:
                low_index = 0

            mid_index = len(lines) - 12
            if mid_index < 0:
                mid_index = 0

            last_player_index = 0
            # First pass: Identify the last index of each symbol and all its children symbols
            for i in range(0, len(lines)):
                if len(lines[i]) > 0 and lines[i][0] == '>':
                    last_player_index = i
                matches = re.findall(r'%\w+%', lines[i])
                for symbol in matches:
                    # Record the index of the last occurrence of the symbol
                    matched.add(symbol)
                    children_symbols = symbol_expansion(self.db, session, symbol, matched=matched)
                    for depth, child_symbol in children_symbols:
                        matched.add(child_symbol)
                        if depth == 0 or symbol not in symbol_indices:
                            symbol_indices[symbol] = min(i, symbol_min, last_player_index - 1)
                            logger.debug(f"Trigger, {match}, Set, {symbol}, {symbol_indices[symbol]}")

                matches = re.findall(kw_pattern, lines[i], flags=re.IGNORECASE)
                for match in matches:
                    entries = [k for k,v in symbol_kw_dict.items() if v == match.lower()]

                    for entry in entries:
                        # Record the index of the last occurrence of the symbol
                        entry_symbols = symbol_expansion(self.db, session, entry)
                        for depth, symbol in entry_symbols:
                            if depth == 0: 
                                symbol_indices[symbol] = min(i, low_index, last_player_index)
                                logger.debug(f"Keyword {match} {entry} Set {symbol} {symbol_indices[symbol]}")
                            elif symbol not in symbol_indices:
                                symbol_indices[symbol] = min(i, symbol_min, last_player_index)
                                logger.debug(f"Keyword {match} {entry} Set {symbol} {symbol_indices[symbol]}")

            for symbol in loc_symbols + all_symbols:
                if symbol not in symbol_indices:
                    child_symbols = symbol_expansion(self.db, session, symbol)
                    for depth, child_symbol in child_symbols:
                        if depth == 0 or child_symbol not in symbol_indices:
                            symbol_indices[child_symbol] = mid_index

            # Second pass: Update the lines with the expanded values
            def generate_lines():
                yield self.header()
                for stats in all_stats:
                    yield stats
                yield ''
                yield ''
                yield self.mid_pre()
                for dialog in all_dialog:
                    if len(dialog) > 0 and dialog[0] == '>':
                        yield ''
                    yield dialog
                yield ''
                for i, line in enumerate(lines):
                    if i == mid_index:
                        yield ''
                        yield self.mid_post()
                    entries = [e for e, x in symbol_indices.items() if x == i]
                    if len(entries) > 0:
                        yield '\n' + '\n'.join(entries)
                    if len(line) > 0 and line[0] == '>':
                        yield ''
                    yield line
                if len(line) > 0 and line[0] != '>':
                    yield ''

            # TODO this should be replaced by going backwards through the lines and inserting the symbols, 
            # then joining the lines together

            # Close the session
            session.close()

        self.last_turn = text

        # Join the lines back together and return the result
        return {'state': 'content', 'content': '\n'.join(line for line in generate_lines())}

if __name__ == "__main__":
    context_text = "Hello World %village%"
