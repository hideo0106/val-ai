# valai/charming.py

from collections import defaultdict
import logging
import os
from typing import List, Optional


from .analysis.summarizer import ChainOfAnalysis
from .charm.context import ContextInjection
from .charm.database import DatabaseManager
from .charm.flatdata import ContextShadowing
from .charm.prompt import Librarian
from .charm.scene import Scene
from .ioutil import CaptureFD
from .llamaflow import FlowEngine

logger = logging.getLogger(__name__)

# The charm library was a project I was working on to create a text-based adventure game, and provides an early
# implementation of the context shadowing concept.

class Charmer:
    def __init__(self, library : Librarian, shadow : ContextShadowing) -> None:
        #self.db = db
        #self.scene = scene
        #self.charm = charm
        self.library = library
        self.shadow = shadow
        self.turn_count = 0
        self.recent = {}
        self.history = []
        self.active_history = []
        self.char_dialog = defaultdict(list)

    @staticmethod
    def fix_prompt(lines : List[str], filter_codex : bool = False, **kwargs) -> List[str]:
        prev = []
        matchers = ['>']
        filters = ['']
        if filter_codex:
            filters.append('#')
        else:
            matchers.append('#')
        for line in lines:
            if len(line) == 0 or line[0] in filters:
                continue
            if line[0] in matchers:
                yield ''
            if len(prev) > 0 and prev[0] != '[' and line[0] == '[':
                yield ''
            yield line
            prev = line
        return []

    def init_history(self, load : bool = False, **kwargs) -> None:
        history = None
        if load: 
            history = self.load_game_text()
        initial_q = "> New Game"
        initial_a = "Narrator: (informative) Welcome to Verana"
        if history is None:
            history = [initial_q, initial_a]
        self.history = history

    def player_stats(self):
        return "($player a=wizard b=human c=male d=charming)"

    def header(self):
        return self.library.read_document('system_header') + '\n' + self.library.read_document('system_actor')

    def mid_pre(self):
        return self.library.read_document('system_mid_pre', player_stats=self.player_stats())

    def mid_post(self):
        return self.library.read_document('system_mid_post', player_stats=self.player_stats())

    def system(self, **kwargs) -> List[str]:
        header : List[str] = self.header().split('\n')
        mid_pre : List[str] = self.mid_pre().split('\n')
        mid_post : List[str] = self.mid_post().split('\n')
        assets = self.shadow.get_assets()
        sheets = list(assets['sheets'])
        dialog = list(assets['dialog'])
        system = header + sheets + mid_pre + dialog + sheets + mid_post
        fixed = self.fix_prompt(system)
        prompt = '\n'.join(fixed)
        return prompt

    def __call__(self, processing : Optional[list[str]] = None, **kwargs) -> List[str]:
        self.turn_count = 0

        idp = True
        if processing is None:
            processing = self.history
            idp = True

        expansion = self.shadow.expand(processing, **kwargs)
        expansion = [e for e in expansion]
        new_items = [e for e in expansion if e not in processing]
        
        if idp:
            self.recent = {e: self.turn_count for e in new_items}
        
        fixed = self.fix_prompt(expansion, filter_codex=True)
        fixed = [e for e in self.fix_prompt(lines=expansion)]
        logger.debug(f"Expansion: {len(fixed)}")
        prompt = '\n'.join(fixed)

        return prompt

    def expire_recent(self, turn_expiration : int = 4, **kwargs) -> None:
        expire_threshold = self.turn_count - turn_expiration
        self.recent = {k: v for k, v in self.recent.items() if v > expire_threshold}

    def turn(self, turn : list[str], last : int = 1, turn_expriation : int = 4, **kwargs) -> List[str]:
        self.turn_count += 1
        self.expire_recent(turn_expriation, **kwargs)

        expansion = self.shadow.expand(turn, low=False, high=False, **kwargs)
        new_items = [e for e in expansion if e not in turn and e not in self.recent]

        self.recent = {**{e: self.turn_count for e in new_items}, **self.recent}

        fixed = [e for e in self.fix_prompt(lines=new_items + turn[-last:])]
        logger.debug(f"Expansion: {len(fixed)}")
        prompt = '\n'.join(fixed)
        
        return prompt

    def extract_dialog(self, line : str) -> bool:
        # Inspect our response, to get our char history
        parts = line.split(':', 1)
        if len(parts) > 1:
            char = parts[0].strip()
            self.char_dialog[char].append(parts[1])
            return True
        return False

    def pop(self) -> str:
        while len(self.history[-1]) == 0 or self.history[-1][0] != '>':
            self.history.pop()
        player_input = self.history.pop()
        return player_input

    def add_history(self, source : str, turn : str, **kwargs):
        self.history.append(turn)

    @classmethod
    def from_config(cls, **kwargs) -> 'Charmer':
        config = { 
            'database_uri': 'sqlite:///local/char.db',
            'scene_path': 'scene/verana',
            'player': '$player',
            'party': [],
            'location_name': 'Verana',
            **kwargs }
        library = Librarian.from_config(**config)
        shadow = ContextShadowing.from_file(**config)
        #db = DatabaseManager.from_config(**config)
        #scene = Scene.from_db(db=db, **config)
        #charm = ContextInjection.from_db(db, scene, **config)
        return cls(library=library, shadow=shadow)
    
    @classmethod
    def init_game(cls, **kwargs) -> None:
        from .charm.loader import load
        config = { 
            'database_uri': 'sqlite:///local/char.db',
            'scene_path': 'scene/verana',
            **kwargs }
        load(**config)
    
    def save_game(self, **kwargs) -> str:
        return self.save_game_text(self.history, **kwargs)

    @classmethod
    def save_game_text(cls, history: list[str], **kwargs) -> str:
        config = {
            'save_file': 'local/savegame.txt',
            **kwargs
        }

        save_file = config['save_file']
        with open(save_file, 'w') as f:
            for h in history:
                f.write(h + '\n')

        return save_file        

    @classmethod
    def load_game_text(cls, **kwargs) -> Optional[list[str]]:
        config = {
            'save_file': 'local/savegame.txt',
            **kwargs
        }

        if not os.path.exists(config['save_file']):
            return None

        def generate_lines():
            with open(config['save_file'], 'r') as f:
                while True:
                    line = f.readline()
                    if line == '':
                        break
                    yield line.strip()
        
        return [line for line in generate_lines()]

    @classmethod
    def save_game_binary(cls, history: list[str], **kwargs):
        config = {
            'save_file': 'local/savegame.dat',
            **kwargs
        }

        with open(config['save_file'], 'wb') as f:
            separator = b'\x1E'  # custom separator byte
            for entry in history:
                f.write(entry.encode() + separator)

    @classmethod
    def load_game_binary(cls, **kwargs) -> Optional[list[str]]:
        config = {
            'save_file': 'local/savegame.dat',
            **kwargs
        }

        if not os.path.exists(config['save_file']):
            return None

        with open(config['save_file'], 'rb') as f:
            separator = b'\x1E'  # custom separator byte
            history = []
            entry = b''
            while True:
                byte = f.read(1)
                if byte == separator:
                    history.append(entry.decode())
                    entry = b''
                elif byte == b'':
                    break
                else:
                    entry += byte

        return history

    def show_history(self, n_show : int = 10, **kwargs):
        self.print_history(self.history, n_show)

    @staticmethod
    def print_history(history : List[str], n : int):
        if n == -1:
            n = len(history)
        print('\n'.join(Charmer.fix_prompt(history[-n:])))

    def last_turn(self, include_player : bool = False, **kwargs) -> List[str]:
        return self.get_turn(self.history, include_player=include_player, **kwargs)

    @classmethod
    def get_turn(cls, history : List[str], include_player : bool, **kwargs) -> List[str]:
        turn = []
        player_count = 2 if include_player else 1
        for i in range(1,5):
            if i > 1 and history[-i][0] == '>':
                player_count -= 1

            if player_count == 0:
                break

            turn.append(history[-i])
        turn = turn[::-1]
        return turn

    @classmethod
    def run_charm(cls, r_length : int, r_temp : float, refresh_threshold : int = 10, **kwargs):
        charmer = cls.from_config(**kwargs)
        if not kwargs.get('verbose', False):
            with CaptureFD() as co:
                engine = FlowEngine.from_config(**kwargs)
        else:
            engine = FlowEngine.from_config(**kwargs)
        print("Starting Game...")
        engine.clear_saved_context(**kwargs)
        charmer.init_history(load=True, **kwargs)
        system = charmer.system(**kwargs)
        engine.execute(system=system, prompt=charmer(**kwargs), restart=True, **kwargs)
        running = True
        retry = False
        charmer.show_history(**kwargs)
        refresh = 5
        last_input = ''
        while running:
            action = input('\n> ')
            asplit = action.split(" ", 1)
            additional = ''
            if action == '':
                continue
            elif action == 'chapter':
                engine.reset()
                cod = ChainOfAnalysis(engine=engine)
                result = cod(data='\n'.join(charmer.history), subject="Dialog", iterations=2, observations=7, paragraphs=2, theories=5, **kwargs)
                result = f"Codex: ```{result}```"
                charmer.add_history('chapter', result)
                charmer.show_history(**kwargs)
                print(f"""Chapter added to history""")
                print(f"""renew required""")
                continue
            elif action == 'show':
                charmer.show_history(**kwargs)
                continue
            elif action == 'load':
                print('Loading Game')
                charmer.init_history(load=True, **kwargs)
                engine.execute(system=system, prompt=charmer(**kwargs), rebuild=True, **kwargs)
                charmer.show_history(**kwargs)
                refresh = refresh_threshold
                print('Game Loaded')
                continue
            elif action == 'renew':
                print('Renewing Game State')
                engine.execute(system=system, prompt=charmer(**kwargs), restart=True, **kwargs)
                charmer.show_history(**kwargs)
                refresh = refresh_threshold
                continue
            elif action == 'save':
                print('Saving Game')
                charmer.save_game(**kwargs)
                print('Game Saved')
                continue
            elif action == 'last':
                print('Last')
                turn = charmer.last_turn(include_player=True, **kwargs)
                print('\n'.join(turn))
                continue
            elif action == 'expand':
                engine.execute(system=system, prompt=charmer(**kwargs), rebuild=True, **kwargs)
                refresh = refresh_threshold
                continue
            elif action == 'pop':
                charmer.pop()
                refresh = 0
                print("Popped Last Entry")
                continue
            elif asplit[0] == 'retry':
                charmer.pop()
                player_input = last_input
                if len(asplit) > 1:
                    additional = asplit[1]
                retry = True
                refresh -= 1
                print(f"Retrying Last Entry: {player_input}")
            elif action == 'restart':
                print('Are you sure? (y/N)')
                idata = input('> ')
                if idata == 'y':
                    print('Game Restarted')
                    charmer.init_history(load=False, **kwargs)
                    system = charmer.system(**kwargs)
                    engine.execute(system=system, prompt=charmer(**kwargs), restart=True, **kwargs)
                    charmer.show_history(**kwargs)
                    refresh = refresh_threshold
                    continue
                else:
                    print('Continuing')
                    continue
            elif action == 'history':
                print('History')
                charmer.show_history(n_show = -1, **kwargs)
                continue
            elif action == 'quit':
                print('Are you sure? (y/N)')
                quitting = input('> ')
                if quitting == 'y':
                    print('Goodbye')
                    exit(0)
                else:
                    print('Continuing')
                    continue
            elif action == 'help':
                print('Commands:')
                print('  chapter, show, load, renew, save, last, expand, pop, restart, retry, history, quit, help')
                continue
            else:
                player_input = f"> {action.strip()}"
            charmer.add_history('player', player_input)
            last_input = player_input
            if refresh <= 0:
                logger.info("Rebuilding Context")
                engine.execute(system=system, prompt=f"{charmer(**kwargs)}\n{additional}", rebuild=True, **kwargs)
                refresh = refresh_threshold
            else:
                turn = charmer.last_turn(**kwargs)
                expanded_input = charmer.turn(turn, **kwargs)
                refresh -= 1
                engine.execute(system=system, prompt=f"{expanded_input}\n{additional}", retry=retry, **kwargs)
                retry = False
            zx = False
            for i in range(3):
                if zx:
                    # We just saw ZxdrOS, let's get a response from the narrator.
                    prefix = "Narrator:"
                    engine.execute(system=system, prompt=prefix, **kwargs)
                    result = engine.read(max_tokens=r_length, n_temp=r_temp, abort_tokens=['>', '<', '|', '['], stop_tokens=['\n'], sequence_tokens=[['\n','[']], **kwargs)
                    response = ''.join(result).strip()
                    if len(response) <= 1:
                        logger.warn("No response from engine.")
                    response = f"{prefix} {response}"
                else:
                    result = engine.read(max_tokens=r_length, n_temp=r_temp, abort_tokens=['>', '<', '|', '['], stop_tokens=['\n'], sequence_tokens=[['\n','[']], **kwargs)
                    response = ''.join(result).strip()
                    if additional != '':
                        response = f"{additional}{response}"
                        additional = ''
                if len(response) <= 1:
                    if i != 0:
                        break

                    # This usually occurs when a model is falling outside of it's trained context, but sometimes it's just a bad response.
                    # Let's bootstrap the recovery with a character interaction.
                    # The first response turn, We don't want to break, but we do want a response.  Let's get ZxdrOS involved?
                    prefix = "ZxdrOS: (inquiring)"
                    engine.execute(system=system, prompt=prefix, **kwargs)
                    result = engine.read(max_tokens=r_length, n_temp=r_temp, abort_tokens=['>'], stop_tokens=['\n'], sequence_tokens=[['\n','[']], **kwargs)
                    response = ''.join(result).strip()
                    if len(response) <= 1:
                        logger.warn("No response from engine.")
                    response = f"{prefix} {response}"
                    zx = True
                print(f"{response}")
                charmer.add_history('model', response)

if __name__ == "__main__":
    from .llamaflow import FlowEngine

    logging.basicConfig(level=logging.DEBUG)

    config = {
        'model_path': '/mnt/biggy/ai/llama/gguf/',
        'model_file': 'zephyr-7b-beta.Q8_0.gguf',
        'n_ctx': 2 ** 14,
        'n_batch': 512,
        'n_gpu_layers': 18,
        }
    
    Charmer.run_charm(**config)
