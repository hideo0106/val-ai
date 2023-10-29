# valai/charming.py

import logging
import os
from typing import Optional

from valai.ioutil import CaptureFD

from .charm.context import ContextInjection
from .charm.database import DatabaseManager
from .charm.scene import Scene
from .llamaflow import FlowEngine

logger = logging.getLogger(__name__)

# The charm library was a project I was working on to create a text-based adventure game, and provides an early
# implementation of the context shadowing concept.

class Charmer:
    def __init__(self, db, scene, charm) -> None:
        self.db = db
        self.scene = scene
        self.charm = charm

    def __call__(self, history : list[str], **kwargs) -> str:
        prompt = '\n'.join([f"{h}" if len(h) > 0 and h[0] == '>' else h for h in history])
        expansion = self.charm.expand(prompt, **kwargs)
        expansion_state = expansion.get('state', 'error')
        if expansion_state == 'content' and 'content' in expansion:
            newprompt =  expansion['content']
            logging.debug(f"Prompt Expanded:\n{newprompt}")
            return f"{newprompt}\n"
        else:
            logging.warn("Non Content Response:", expansion)
            return prompt

    @classmethod
    def from_config(cls, **kwargs) -> 'Charmer':
        config = { 
            'database_uri': 'sqlite:///local/char.db',
            'data_path': 'scene/verana',
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
            'data_path': 'scene/verana',
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
    def run_charm(cls, r_length : int, r_temp : float, **kwargs):
        charmer = cls.from_config(**kwargs)
        with CaptureFD() as co:
            engine = FlowEngine.from_config(**kwargs)
        print("Starting Game...")
        history = cls.load_game_text()
        logger.debug(f"Loaded Game: {history}")
        initial_q = "> New Game"
        initial_a = "Narrator: (informative) Welcome to Verana"
        if history is None:
            history = [initial_q, initial_a]
            expanded = charmer(history, **kwargs)
        else:
            expanded = charmer(history, **kwargs)
        engine.feed(prompt=expanded, reset=True, **kwargs)
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
                engine.feed(prompt=charmer(history, **kwargs), reset=True, **kwargs)
                cls.print_history(history, 10)
                refresh = 5
                print('Game Loaded')
                continue
            elif action == 'save':
                print('Saving Game')
                cls.save_game_text(history, **kwargs)
                print('Game Saved')
                continue
            elif action == 'last':
                print('Last')
                for i in range(-4, 0):
                    if len(history) <= abs(i):
                        break
                    if history[i][0] == '>':
                        print('')
                    print(history[i])
                continue
            elif action == 'expand':
                engine.feed(prompt=charmer(history, **kwargs), reset=True, **kwargs)
                refresh = 5
                print("Expanded Context")
                continue
            elif action == 'pop':
                while len(history[-1]) == 0 or history[-1][0] != '>':
                    history.pop()
                history.pop()
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
                quitting = input('> ')
                if quitting == 'y':
                    print('Game Restarted')
                    history = [initial_q, initial_a]
                    engine.feed(prompt=charmer(history, **kwargs), reset=True, **kwargs)
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
                engine.feed(prompt=charmer(history, **kwargs), reset=True, **kwargs)
                refresh = 5
            else:
                logger.debug("Feeding Input")
                refresh -= 1
                engine.feed(prompt=f"{player_input}\n", **kwargs)
            for _ in range(3):
                result = engine.read(max_tokens=r_length, n_temp=r_temp, abort_tokens=['>'], stop_tokens=['\n'], sequence_tokens=[['\n','[']], **kwargs)
                response = ''.join(result).strip()
                if len(response) <= 1:
                    break
                logger.debug(f"{result}")
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
