# valai/charm/wizard.py

import logging
import os
import random
from typing import Optional

from ..analysis.summarizer import ChainOfAnalysis
from ..ioutil import CaptureFD
from ..llamaflow import FlowEngine, EngineException

from .charmer import Charmer
from .token import TokenFeatures

logger = logging.getLogger(__name__)


# The charm library was a project I was working on to create a text-based adventure game, and provides an early
# implementation of the context shadowing concept.

class CharmWizard:
    def __init__(self, charmer : Charmer, engine : FlowEngine, system : Optional[str] = None):
        self.charmer = charmer
        self.engine = engine
        self.current_system = system

    def reset_engine(self, restart : bool = False, **kwargs) -> bool:
        try:
            self.engine.set_context(system_context='system', prompt=self.current_system, **kwargs)
            self.engine.prepare(system_context='system', restart=restart, **kwargs)
            self.engine.execute(prompt=self.charmer(**kwargs), **kwargs)
            return True
        except EngineException as e:
            logging.error(f"Engine Exception: {e}")
            return False
    
    @classmethod
    def from_config(cls, **kwargs):
        charmer = Charmer.from_config(**kwargs)
        if not kwargs.get('verbose', False):
            with CaptureFD() as co:
                engine = FlowEngine.from_config(**kwargs)
        else:
            engine = FlowEngine.from_config(**kwargs)
        
        return cls(charmer=charmer, engine=engine, system=charmer.system(**kwargs))

    def init(self, restart : bool = True, load_history : bool = True, load_shadow : bool = True, **kwargs) -> bool:
        if restart:
            self.engine.clear_saved_context(**kwargs)
        if load_shadow:
            self.charmer.shadow.reload(**kwargs)
        self.charmer.init_history(load=load_history, **kwargs)
        self.current_system = self.charmer.system(**kwargs)

        self.reset_engine(restart=restart, **kwargs)

        return True

    def execute_chapter(self, **kwargs) -> bool:
        self.engine.reset()
        cod = ChainOfAnalysis(engine=self.engine)
        result = cod(data='\n'.join(self.charmer.current_history), subject="Dialog", iterations=2, observations=7, paragraphs=2, theories=5, **kwargs)
        result = f"Codex: ```{result}```"
        self.charmer.add_history('chapter', result)

        return True

    def execute_scene_analysis(self, **kwargs) -> bool:
        history = self.charmer.get_history(**kwargs)
        token_features = TokenFeatures.from_history(history=history, **kwargs)
        scenes = token_features.scene_documents(**kwargs)
        for c in scenes:
            print(f"{c}")

        return True

    def execute_load(self, **kwargs) -> bool:
        self.init(restart = False, load_history=True, load_shadow=True, **kwargs)
        self.charmer.init_history(load=True, **kwargs)
        self.reset_engine(restart=False, **kwargs)

        return True

    def execute_save(self, **kwargs) -> bool:
        self.charmer.save_game(**kwargs)

        return True

    def execute_shadow_reload(self, **kwargs) -> bool:
        self.charmer.shadow.reload(**kwargs)
        self.current_system = self.charmer.system(**kwargs)
        self.reset_engine(restart=True, **kwargs)

    def show_history(self, n_show : int = 10, **kwargs):
        print(self.charmer.format_history(n_show=n_show, **kwargs))

    def read_prompt(self, prompt_style: str, prompt_path : str = "prompts", **kwargs) -> str:
        filename = f"{prompt_path}/{prompt_style}.txt"
        if not os.path.exists(filename):
            logger.warn(f"Prompt file {filename} does not exist.")
            return ''
        with open(filename, 'r') as f:
            data = f.read()
        return data

    def run_charm(self, r_length : int, r_temp : float, refresh_threshold : int = 10, **kwargs):
        print("Starting Game...")
        self.init(**kwargs)

        running = True
        retry = False
        self.show_history(**kwargs)
        refresh = refresh_threshold
        last_input = ''
        check_input = True
        while running:
            try:
                if check_input:
                    action = input('\n> ')
                    asplit = action.split(" ", 1)
                    additional = ''
                    if action == '':
                        continue
                    elif action == 'chapter':
                        cod = ChainOfAnalysis(engine=self.engine)
                        result = cod(data='\n'.join(self.charmer.current_history), subject="Dialog", iterations=2, observations=7, paragraphs=2, theories=5, **kwargs)
                        print(result)
                        continue
                    elif action == 'summary':
                        cod = ChainOfAnalysis(engine=self.engine)
                        result = cod.summarize(subject="Dialog", paragraphs=3, s_length=150, s_temp=0.7, **kwargs)
                        print(result)
                        continue
                    elif action == 'improve':
                        cod = ChainOfAnalysis(engine=self.engine)
                        result = cod.improve(subject="Dialog", theories=5, s_length=50, s_temp=0.7, **kwargs)
                        print(result)
                        continue
                    elif action == 'resummarize':
                        cod = ChainOfAnalysis(engine=self.engine)
                        result = cod.resummarize(subject="Dialog", paragraphs=2, s_length=250, s_temp=0.7, **kwargs)
                        print(result)
                        continue
                    elif action == 'show':
                        self.show_history(**kwargs)
                        continue
                    elif action == 'load':
                        print('Loading Game')
                        self.execute_load(**kwargs)
                        self.show_history(**kwargs)
                        refresh = refresh_threshold
                        print('Game Loaded')
                        continue
                    elif action == 'renew':
                        print('Refreshing Shadow')
                        self.execute_shadow_reload(**kwargs)
                        self.show_history(**kwargs)
                        continue
                    elif action == 'scene':
                        print('Scene Analysis')
                        self.execute_scene_analysis(**kwargs)
                        continue
                    elif action == 'save':
                        print('Saving Game')
                        self.execute_save(**kwargs)
                        print('Game Saved')
                        continue
                    elif action == 'last':
                        print('Last')
                        turn = self.charmer.last_turn(include_player=True, **kwargs)
                        print('\n'.join(turn))
                        continue
                    elif action == 'expand':
                        self.reset_engine(restart=False)
                        refresh = refresh_threshold
                        continue
                    elif action == 'back':
                        self.charmer.pop()
                        refresh = 0
                        print("Removed Last Entry")
                        turn = self.charmer.last_turn(include_player=True, **kwargs)
                        print('\n'.join(turn))
                        continue
                    elif action == 'context':
                        print('Context')
                        print(f"Tokens {self.engine.n_past}")
                        print(f"System {self.engine.n_system}")
                        print(f"Context {self.engine.n_ctx}")
                        continue
                    elif asplit[0] == 'retry':
                        self.charmer.pop()
                        player_input = last_input
                        if len(asplit) > 1:
                            additional = asplit[1]
                        retry = True
                        refresh -= 1
                        print(f"Retrying Last Entry: {player_input}")
                    elif asplit[0] == 'write':
                        self.engine.execute(prompt=f"{asplit[1]}", **kwargs)
                        continue
                    elif asplit[0] == 'readall':
                        limit = 10
                        if len(asplit) > 1:
                            # If this is a number, we will use it as our limit, otherwise as a prefix.
                            if asplit[1].isdigit():
                                prefix = None
                                limit = int(asplit[1])
                            else:
                                prefix = asplit[1]
                        else:
                            prefix = None
                        ix = 0
                        while True:
                            if ix >= limit:
                                break
                            ix += 1
                            if prefix is not None:
                                self.engine.execute(prompt=f"{prefix}", **kwargs)
                            result = self.engine.read(max_tokens=r_length, n_temp=r_temp, **self.charmer.guidance.tokens, **kwargs)
                            if result is None:
                                # Rollback
                                self.engine.reload_turn(**kwargs)
                                logger.warn("No response from engine, rolling back.")
                                break
                            response = ''.join(result).strip()
                            print(f"{response}")
                            continue
                        continue
                    elif asplit[0] == 'read':
                        result = self.engine.read(max_tokens=r_length, n_temp=r_temp, **self.charmer.guidance.tokens, **kwargs)
                        if result is None:
                            # Rollback
                            self.engine.reload_turn(**kwargs)
                            logger.warn("No response from engine, rolling back.")
                            continue
                        response = ''.join(result).strip()
                        print(f"{response}")
                        continue
                    elif asplit[0] == 'wipe':
                        self.engine.reset()
                        self.init(restart=False, load_history=False, load_shadow=False, **kwargs)
                        print('Engine Wiped')
                        continue
                    elif asplit[0] == 'prompt_reset':
                        prompt = self.read_prompt(asplit[1], **kwargs)
                        self.engine.reload_turn(**kwargs)
                        self.engine.execute(prompt=prompt, retry=False, **kwargs)
                        continue
                    elif asplit[0] == 'prompt':
                        prompt = self.read_prompt(asplit[1], **kwargs)
                        self.engine.execute(prompt=prompt, retry=False, **kwargs)
                        continue
                    elif asplit[0] == 'historyinfo':
                        hist = self.charmer.get_history(expand_history=True, **kwargs)
                        print(f'History Length: {len(hist)}')
                        continue
                    elif asplit[0] == 'history':
                        args = asplit[1].split(" ")
                        if len(args) == 1:
                            end = int(args[0])
                            start = 0
                        else:
                            start = int(args[0])
                            end = int(args[1])
                        logger.info(f"Playing History: {start} {end}")
                        history = self.charmer.get_history(expand_history=True, start=start, end=end, **kwargs)
                        for h in history:
                            print(h)
                        print(f"History Length: {len(history)}")
                        continue
                    elif asplit[0] == 'play_history':
                        args = asplit[1].split(" ")
                        if len(args) == 1:
                            end = int(args[0])
                            start = 0
                        else:
                            start = int(args[0])
                            end = int(args[1])
                        logger.info(f"Playing History: {start} {end}")
                        hist = self.charmer.get_history(expand_history=True, start=start, end=end, **kwargs)
                        prompt = self.charmer.guidance.format_turn(hist)
                        logger.debug(f"Prompt: {prompt}")
                        self.engine.execute(prompt=prompt, retry=False, **kwargs)
                        continue
                    elif asplit[0] == 'replay_history':
                        args = asplit[1].split(" ")
                        if len(args) == 1:
                            end = int(args[0])
                            start = 0
                        else:
                            start = int(args[0])
                            end = int(args[1])
                        logger.info(f"Playing History: {start} {end}")
                        hist = self.charmer.get_history(expand_history=True, start=start, end=end, **kwargs)
                        prompt = self.charmer.guidance.format_turn(hist)
                        logger.debug(f"Prompt: {prompt}")
                        self.engine.execute(prompt=prompt, retry=False, **kwargs)
                        continue
                    elif action == 'restart':
                        print('Are you sure? (y/N)')
                        idata = input('> ')
                        if idata == 'y':
                            print('Game Restarted')
                            self.charmer.init_history(load=False, **kwargs)
                            self.init(restart=True, load_history=False, load_shadow=True, **kwargs)
                            self.show_history(**kwargs)
                            refresh = refresh_threshold
                            continue
                        else:
                            print('Continuing')
                            continue
                    elif action == 'history':
                        print('History')
                        self.show_history(n_show = -1, **kwargs)
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
                        print('  read, readall, write, wipe, prompt, prompt_reset, historyinfo, play_history')
                        print('  scene, summary, improve, resummarize')
                        print('  context, back')
                        continue
                    else:
                        player_input = f"> {action.strip()}"
                    if self.charmer.add_history('player', player_input):
                        # If we rolled our history, we need to refresh
                        refresh = 0
                    last_input = player_input
                else:
                    logger.debug("Using previous input")
                if retry:
                    self.charmer.pop()
                    self.engine.reload_turn(**kwargs)
                    refresh += 1
                if refresh <= 0:
                    logger.info("Rebuilding Context")
                    self.engine.prepare(system_context='system', restart=False, **kwargs)
                    self.engine.execute(prompt=f"{self.charmer(**kwargs)}\n{additional}", **kwargs)
                    refresh = refresh_threshold
                else:
                    turn = self.charmer.last_turn(**kwargs)
                    expanded_input = self.charmer.turn(turn, **kwargs)
                    self.engine.execute(prompt=f"{expanded_input}\n{additional}", **kwargs)
                    refresh -= 1
                    retry = False
                zx = False
                for i in range(3):
                    if zx:
                        # We just saw ZxdrOS, let's get a response from the narrator.
                        prefix = "Narrator:"
                        self.engine.execute(prompt=prefix, **kwargs)
                        result = self.engine.read(max_tokens=r_length, n_temp=r_temp, **self.charmer.guidance.tokens, **kwargs)
                        if result is None:
                            # Rollback
                            self.engine.reload_turn(**kwargs)
                        else:
                            response = ''.join(result).strip()
                            if len(response) <= 1:
                                logger.warn("No response from engine.")
                            response = f"{prefix} {response}"
                        zx = False
                    else:
                        result = self.engine.read(max_tokens=r_length, n_temp=r_temp, **self.charmer.guidance.tokens, **kwargs)
                        if result is None:
                            # Rollback
                            self.engine.reload_turn(**kwargs)
                        else:
                            response = ''.join(result).strip()
                            if len(response) <= 1 and i == 0:
                                logger.warn("No response from engine.")
                            if additional != '':
                                response = f"{additional}{response}"
                                additional = ''
                    if len(response) <= 1:
                        if i != 0:
                            break
                        moods = ['inquiring', 'insulting', 'amused', 'informative', 'angry', 'sad', 'happy', 'silly', 'suspicious', 'fearful', 'confused', 'disgusted', 'surprised', 'neutral']
                        # This usually occurs when a model is falling outside of it's trained context, but sometimes it's just a bad response.
                        # Let's bootstrap the recovery with a character interaction.
                        # The first response turn, We don't want to break, but we do want a response.  Let's get ZxdrOS involved?
                        mood = random.choice(moods)
                        prefix = f"ZxdrOS: ({mood})  So, the $player wants to"
                        self.engine.execute(prompt=prefix, **kwargs)
                        result = self.engine.read(max_tokens=r_length, n_temp=r_temp, **self.charmer.guidance.tokens, **kwargs)
                        response = ''.join(result).strip()
                        if len(response) <= 1:
                            logger.warn("No response from engine.")
                        response = f"{prefix} {response}"
                        zx = True
                    print(f"{response}")
                    self.charmer.add_history('model', response)
                    check_input = True
            except EngineException as e:
                # We have too many tokens in our prompt.  Lets halve our history and
                # try again.
                logger.warn(f"Engine Exception: {e}")
                self.charmer.history_halve(current_clearance=e.tokens, **kwargs)
                check_input = False

def run_charm(**kwargs):
    app = CharmWizard.from_config(**kwargs)
    app.run_charm(**kwargs)

if __name__ == "__main__":
    from ..llamaflow import FlowEngine

    logging.basicConfig(level=logging.DEBUG)

    config = {
        'model_path': '/mnt/biggy/ai/llama/gguf/',
        'model_file': 'zephyr-7b-beta.Q8_0.gguf',
        'n_ctx': 2 ** 14,
        'n_batch': 512,
        'n_gpu_layers': 18,
        }

    app = CharmWizard.from_config(**config)
    #print(app.read_prompt('get_summary', **config))
    app.charmer.init_history(load=True, **config)

    
