# valai/charming.py

import logging
import os
from typing import List, Optional
from valai.charm.flatdata import ContextShadowing

from valai.ioutil import CaptureFD

from .charm.context import ContextInjection
from .charm.database import DatabaseManager
from .charm.scene import Scene
from .llamaflow import FlowEngine

logger = logging.getLogger(__name__)

# The charm library was a project I was working on to create a text-based adventure game, and provides an early
# implementation of the context shadowing concept.

class Charmer:
    def __init__(self, db : DatabaseManager, scene : Scene, charm : ContextInjection) -> None:
        self.db = db
        self.scene = scene
        self.charm = charm
        self.shadow = ContextShadowing.from_file()
        self.turn_count = 0
        self.recent = {}

    @staticmethod
    def fix_prompt(lines : List[str]) -> List[str]:
        prev = None
        for line in lines:
            if len(line) > 0 and line[0] == '>':
                yield ''
            if prev is None or len(prev) == 0:
                yield line
            elif len(line) > 0:
                if prev[0] != '[' and line[0] == '[':
                    yield ''
                yield line
            prev = line
        return []

    def system(self, **kwargs) -> List[str]:
        header : List[str] = self.charm.header().split('\n')
        mid_pre : List[str] = self.charm.mid_pre().split('\n')
        mid_post : List[str] = self.charm.mid_post().split('\n')
        assets = self.shadow.get_assets()
        sheets = list(assets['sheets'])
        dialog = list(assets['dialog'])
        system = header + sheets + mid_pre + dialog + sheets + mid_post
        fixed = self.fix_prompt(system)
        prompt = '\n'.join(fixed)
        return prompt

    def __call__(self, history : list[str], **kwargs) -> List[str]:
        self.turn_count = 0

        expansion = self.shadow.expand(history, **kwargs)
        expansion = [e for e in expansion]
        new_items = [e for e in expansion if e not in history]
        
        self.recent = {e: self.turn_count for e in new_items}
        
        fixed = self.fix_prompt(expansion)
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

    @classmethod
    def from_config(cls, **kwargs) -> 'Charmer':
        config = { 
            'database_uri': 'sqlite:///local/char.db',
            'scene_path': 'scene/verana',
            'player': '$player',
            'party': [],
            'location_name': 'Verana',
            **kwargs }
        db = DatabaseManager.from_config(**config)
        scene = Scene.from_db(db=db, **config)
        charm = ContextInjection.from_db(db, scene, **config)
        return cls(db, scene, charm)
    
    @classmethod
    def init_game(cls, **kwargs) -> None:
        from .charm.loader import load
        config = { 
            'database_uri': 'sqlite:///local/char.db',
            'scene_path': 'scene/verana',
            **kwargs }
        load(**config)

    @classmethod
    def save_game_text(cls, history: list[str], **kwargs):
        config = {
            'save_file': 'local/savegame.txt',
            **kwargs
        }

        with open(config['save_file'], 'w') as f:
            for h in history:
                f.write(h + '\n')

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

    @staticmethod
    def print_history(history, n):
        for entry in history[-10:]:
            if len(entry) > 0 and entry[0] == '>':
                print('')
            print(entry)

    @classmethod
    def get_turn(cls, history : List[str], **kwargs) -> List[str]:
        turn = []
        for i in range(1,5):
            if i > 1 and history[-i][0] == '>':
                break
            else:
                turn.append(history[-i])
        turn = turn[::-1]
        return turn

    @classmethod
    def run_charm(cls, r_length : int, r_temp : float, **kwargs):
        charmer = cls.from_config(**kwargs)
        if not kwargs.get('verbose', False):
            with CaptureFD() as co:
                engine = FlowEngine.from_config(**kwargs)
        else:
            engine = FlowEngine.from_config(**kwargs)
        print("Starting Game...")
        engine.clear_saved_context(**kwargs)
        history = cls.load_game_text()
        initial_q = "> New Game"
        initial_a = "Narrator: (informative) Welcome to Verana"
        if history is None:
            history = [initial_q, initial_a]
        logger.debug(f"Loaded Game: {len(history)} history")
        system = charmer.system(**kwargs)
        engine.execute(system=system, prompt=charmer(history, **kwargs), restart=True, **kwargs)
        running = True
        cls.print_history(history, 10)
        refresh = 5
        while running:
            action = input('\n> ')
            if action == '':
                continue
            elif action == 'show':
                cls.print_history(history, 10)
                continue
            elif action == 'load':
                print('Loading Game')
                history = cls.load_game_text(**kwargs)
                engine.execute(system=system, prompt=charmer(history, **kwargs), rebuild=True, **kwargs)
                cls.print_history(history, 10)
                refresh = 8
                print('Game Loaded')
                continue
            elif action == 'save':
                print('Saving Game')
                cls.save_game_text(history, **kwargs)
                print('Game Saved')
                continue
            elif action == 'last':
                print('Last')
                turn = cls.get_turn(history=history, **kwargs)
                print('\n'.join(turn))
                continue
            elif action == 'expand':
                engine.execute(system=system, prompt=charmer(history, **kwargs), rebuild=True, **kwargs)
                refresh = 8
                continue
            elif action == 'pop':
                while len(history[-1]) == 0 or history[-1][0] != '>':
                    history.pop()
                history.pop()
                refresh = 0
                print("Popped Last Entry")
                continue
            elif action == 'retry':
                while len(history[-1]) == 0 or history[-1][0] != '>':
                    history.pop()
                player_input = history.pop()
                refresh = 0
                print(f"Retrying Last Entry: {player_input}")
            elif action == 'restart':
                print('Are you sure? (y/N)')
                idata = input('> ')
                if idata == 'y':
                    print('Game Restarted')
                    history = [initial_q, initial_a]
                    system = charmer.system(**kwargs)
                    engine.execute(system=system, prompt=charmer(history, **kwargs), restart=True, **kwargs)
                    cls.print_history(history, 10)
                    refresh = 5
                    continue
                else:
                    print('Continuing')
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
                print('  show, load, save, last, expand, pop, restart, retry, quit, help')
                continue
            else:
                player_input = f"> {action.strip()}"
            history.append(player_input)
            if refresh <= 0:
                logger.info("Rebuilding Context")
                engine.execute(system=system, prompt=charmer(history, **kwargs), rebuild=True, **kwargs)
                refresh = 5
            else:
                turn = cls.get_turn(history=history, **kwargs)
                expanded_input = charmer.turn(turn, **kwargs)
                refresh -= 1
                engine.execute(system=system, prompt=f"{expanded_input}\n", **kwargs)
            for _ in range(3):
                result = engine.read(max_tokens=r_length, n_temp=r_temp, abort_tokens=['>'], stop_tokens=['\n'], sequence_tokens=[['\n','[']], **kwargs)
                response = ''.join(result).strip()
                if len(response) <= 1:
                    break
                print(f"{response}")
                history.append(response)

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
