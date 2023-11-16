# valai/pinnacle/wizard.py

import logging
import os
from typing import Optional

from ..analysis.summarizer import ChainOfAnalysis
from ..ioutil import CaptureFD
from ..llamaflow import FlowEngine, EngineException

from .charmer import DirectorCharmer
from .exception import DirectorError
from .token import TokenFeatures

logger = logging.getLogger(__name__)


class DirectorWizard:
    current_system : Optional[str]

    def __init__(self, charmer : DirectorCharmer, engine : FlowEngine):
        self.charmer = charmer
        self.engine = engine
        self.current_system = None
        self.command_chain = []

    def reset_engine(self, restart : bool = False, **kwargs) -> bool:
        try:
            self.engine.set_context(system_context='system', prompt=self.current_system, **kwargs)
            self.engine.prepare(system_context='system', restart=restart, **kwargs)
            prompt = self.charmer.scene_header(**kwargs)
            prompt += self.charmer(**kwargs)
            self.engine.execute(prompt=prompt, **kwargs)
            return True
        except EngineException as e:
            logging.error(f"Engine Exception: {e}")
            return False
    
    @classmethod
    def from_config(cls, **kwargs):
        charmer = DirectorCharmer.from_config(**kwargs)
        if not kwargs.get('verbose', False):
            with CaptureFD() as co:
                engine = FlowEngine.from_config(**kwargs)
        else:
            engine = FlowEngine.from_config(**kwargs)
        
        return cls(charmer=charmer, engine=engine)

    def init(self, restart : bool = True, load_history : bool = True, load_shadow : bool = True, **kwargs) -> bool:
        self.charmer.init_history(load=load_history, **kwargs)
        location_symbol = self.charmer.discover_scene(**kwargs)
        if location_symbol is None:
            if self.charmer.director.roster.player.sheet.location_symbol is not None:
                location_symbol = self.charmer.director.roster.player.sheet.location_symbol
            else:
                location_symbol = '^location_novara^'
        if load_shadow:
            self.charmer.shadow.reload(location_symbol=location_symbol, party=self.charmer.director.roster.party, **kwargs)
        self.charmer.set_scene(location_symbol, quiet=True, **kwargs)
        system = self.charmer.system_header(**kwargs)
        self.current_system = system

        if restart:
            self.engine.clear_saved_context(**kwargs)
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
        self.init(restart=True, load_history=False, load_shadow=True, **kwargs)

    def show_history(self, n_show : int = 10, **kwargs):
        print(self.charmer.format_history(n_show=n_show, **kwargs))

    def print_help(self):
        print('Commands:')
        print('  a/attack/kill <enemy> - Attack an enemy')
        print('  b/buy <item> <price> - Buy an item from a merchant')
        print('  c/cast <spell> <target (optional) - Cast a spell')
        print('  i/inventory - show your inventory')
        print('  l/location - show your current location')
        print('  l/look <function word (optional)> <target (optional)> - Look at something, or look around')
        print('  p/party - show your party')
        print('  r/rest <target (optional)> - rest for the night')
        print('  s/search <target> - search something')
        print('  t/talk/say <character> <prompt> - Say something to a character')
        print('  u/use <item> - Use an item')
        print('  x/travel/go <location> - Travel to a location')
        print(f'  q/ask <prompt> - Ask {self.charmer.director.roster.game_master} a question')
        print('  join/invite <character> - invite a character to your party')
        print('  kick <character> - kick a character from your party')
        print('  save - save the game')
        print('  load - load a saved game')
        print('  show - show the last 10 turns')
        print('  history - show the entire history')
        print('  scene - analyze the scene')
        print('  renew - reload the game configuration')
        print('  restart - restart the game')
        print('  quit - exit the game')
        print('  help - show this help')
        print('Cheats:')
        print('  nr <prompt> - write prompt to engine, no return')
        print('  ne <prompt> - write prompt to engine, no read')

    def read_prompt(self, prompt_style: str, prompt_path : str = "prompts", **kwargs) -> str:
        filename = f"{prompt_path}/{prompt_style}.txt"
        if not os.path.exists(filename):
            logger.warn(f"Prompt file {filename} does not exist.")
            return ''
        with open(filename, 'r') as f:
            data = f.read()
        return data

    def run_wizard(self, r_length : int, r_temp : float, refresh_threshold : int = 10, **kwargs):
        print("Starting Director...")
        self.init(**kwargs)

        running = True
        retry = False
        reset_no_restart = False
        print("Game Starting")
        self.show_history(**kwargs)
        refresh = refresh_threshold
        last_input = ''
        check_input = True
        while running:
            try:
                nr = False
                ne = False
                if check_input:
                    action = input('\n> ')
                    asplit = action.split(" ", 1)
                    a2split = action.split(" ", 2)
                    ansplit = action.split(" ")
                    additional = ''
                    lines = []
                    if action == '':
                        continue
                    elif a2split[0] == 'speak' or a2split[0] == 'talk' or a2split[0] == 'say' or a2split[0] == 't':
                        if len(a2split) != 3:
                            print("Invalid speak command: speak <character> <prompt>")
                            print(f"Valid characters: {', '.join(self.charmer.director.character_keywords())}")
                            continue
                        try:
                            player_input = self.charmer.director.speak(target=a2split[1].strip(), dialog=a2split[2].strip(), **kwargs)
                        except DirectorError as e:
                            print(f"Director Error: {e}")
                            print(f"Valid characters: {', '.join(self.charmer.director.character_keywords())}")
                            continue
                    elif a2split[0] == 'buy' or a2split[0] == 'b':
                        if len(a2split) != 3:
                            print("Invalid speak command: buy <item> <price>")
                            continue
                        try:
                            player_input = self.charmer.director.buy(item=a2split[1].strip(), price=a2split[2].strip(), **kwargs)
                        except DirectorError as e:
                            print(f"Director Error: {e}")
                            items = self.charmer.director.scene.get_prices()
                            for item in items:
                                print(f"{item[0]} - {item[1]} - {item[2]} silver")
                            continue
                    elif ansplit[0] == 'cast' or ansplit[0] == 'c':
                        if 2 > len(a2split) < 3:
                            print("Invalid speak command: cast <spell> <target (optional)>")
                            continue
                        try:
                            if len(ansplit) == 2:
                                player_input = self.charmer.director.cast(spell=a2split[1].strip(), **kwargs)
                            elif len(ansplit) == 3:
                                player_input = self.charmer.director.cast(spell=a2split[1].strip(), target=a2split[2].strip(), **kwargs)
                            elif len(ansplit) > 3:
                                player_input = self.charmer.director.cast(spell=a2split[1].strip(), description=' '.join(a2split[2:]), **kwargs)
                        except DirectorError as e:
                            print(f"Director Error: {e}")
                            continue
                    elif asplit[0] == 'ask' or asplit[0] == 'q':
                        if len(asplit) != 2:
                            print("Invalid speak command: ask <prompt>")
                            continue
                        try:
                            player_input = self.charmer.director.speak('none', dialog=asplit[1].strip(), override=self.charmer.director.roster.game_master, **kwargs)
                        except DirectorError as e:
                            print(f"Director Error: {e}")
                            continue
                    elif a2split[0] == 'travel' or a2split[0] == 'go' or a2split[0] == 'x':
                        if len(a2split) != 2:
                            print("Invalid travel command: travel <location>")
                            print(f"Valid locations: {', '.join(self.charmer.director.exit_keywords())}")
                            continue
                        try:
                            player_input = self.charmer.director.travel(a2split[1].strip(), **kwargs)
                            reset_no_restart = True
                        except DirectorError as e:
                            print(f"Director Error: {e}")
                            print(f"Valid locations: {', '.join(self.charmer.director.exit_keywords())}")
                            continue
                    elif a2split[0] == 'rest' or a2split[0] == 'r':
                        if len(a2split) > 2:
                            print("Invalid rest command: rest <target (optional)>")
                            continue
                        try:
                            if len(a2split) == 1:
                                player_input = self.charmer.director.rest(**kwargs)
                            else:
                                player_input = self.charmer.director.rest(a2split[1].strip(), **kwargs)
                        except DirectorError as e:
                            print(f"Director Error: {e}")
                            continue
                    elif a2split[0] == 'take':
                        try:
                            #player_input = self.charmer.director.take(a2split[1].strip(), **kwargs)
                            continue
                        except DirectorError as e:
                            print(f"Director Error: {e}")
                            continue
                    elif a2split[0] == 'inventory' or a2split[0] == 'i':
                        try:
                            print(f"Silver - {self.charmer.director.roster.player.silver}")
                            print("Your inventory:")
                            for i in self.charmer.director.roster.player.inventory:
                                print(f"- {i}")

                            print("Known Spells:")
                            for s in self.charmer.director.roster.player.sheet.spells:
                                print(f"- {s}")
                            #player_input = self.charmer.director.take(a2split[1].strip(), **kwargs)
                            continue
                        except DirectorError as e:
                            print(f"Director Error: {e}")
                            continue
                    elif a2split[0] == 'party':
                        # Show party details
                        if len(self.charmer.director.roster.party) == 0:
                            print("No one is in your party.")
                            continue
                        print("Your party:")
                        for c in self.charmer.director.roster.get_party():
                            print(f"{c}")
                        continue
                    elif a2split[0] == 'join' or a2split[0] == 'invite':
                        if len(a2split) != 2:
                            print("Invalid join command: join <character>")
                            print(f"Valid characters: {', '.join(self.charmer.director.party)}")
                            continue
                        try:
                            player_input = self.charmer.director.party(a2split[1].strip(), True, **kwargs)
                        except DirectorError as e:
                            print(f"Director Error: {e}")
                            print(f"Valid characters: {', '.join(self.charmer.director.party_keywords())}")
                            continue
                    elif a2split[0] == 'kick':
                        if len(a2split) != 2:
                            print("Invalid join command: kick <character>")
                            print(f"Valid characters: {', '.join(self.charmer.director.party_keywords())}")
                            continue
                        try:
                            player_input = self.charmer.director.party(a2split[1].strip(), False, **kwargs)
                        except DirectorError as e:
                            print(f"Director Error: {e}")
                            print(f"Valid characters: {', '.join(self.charmer.director.character_keywords())}")
                            continue
                    elif a2split[0] == 'look' or a2split[0] == 'l':
                        try:
                            if len(a2split) >= 3:
                                target = ' '.join(a2split[1:]).strip()
                                player_input = self.charmer.director.look(target=target, **kwargs)
                            elif len(a2split) == 1:
                                player_input = self.charmer.director.look(target=None, **kwargs)
                            else:
                                print("Invalid look command: look <function word (optional)> <target (optional)>")
                                continue
                        except DirectorError as e:
                            print(f"Director Error: {e}")
                            continue
                    elif a2split[0] == 'search' or a2split[0] == 's':
                        try:
                            if len(a2split) > 2:
                                target = ' '.join(a2split[1:]).strip()
                                player_input = self.charmer.director.search(target=target, **kwargs)
                            else:
                                print("Invalid look command: search <target>")
                                continue
                        except DirectorError as e:
                            print(f"Director Error: {e}")
                            continue
                    elif asplit[0] == 'use' or asplit[0] == 'u':
                        if len(asplit) != 2:
                            print("Invalid use command: use <item>")
                            continue
                        try:
                            player_input = self.charmer.director.use(asplit[1].strip(), **kwargs)
                        except DirectorError as e:
                            print(f"Director Error: {e}")
                            continue
                    elif asplit[0] == 'attack' or asplit[0] == 'a' or asplit[0] == 'kill':
                        if len(asplit) != 2:
                            print("Invalid use command: attack <enemy>")
                            continue
                        try:
                            player_input = self.charmer.director.attack(asplit[1].strip(), **kwargs)
                        except DirectorError as e:
                            print(f"Director Error: {e}")
                            continue
                    elif action == 'l' or action == 'location':
                        print(f"Current Location:")
                        print(self.charmer.director.scene.location.location_line())
                        print(self.charmer.director.scene.location.description_line())
                        continue
                    elif asplit[0] == 'nr':
                        nr = True
                        if len(asplit) == 1:
                            player_input = None
                        else:
                            player_input = f"{asplit[1].strip()}"
                    elif asplit[0] == 'ne':
                        ne = True
                        if (len(asplit) == 1):
                            print('No prompt specified')
                            continue
                        else:
                            player_input = f"{asplit[1].strip()}"
                    elif action == 'quit':
                        print('Are you sure? (y/N)')
                        quitting = input('> ')
                        if quitting == 'y':
                            print('Goodbye')
                            exit(0)
                        else:
                            print('Continuing')
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
                    elif action == 'restart':
                        print('Are you sure? (y/N)')
                        idata = input('> ')
                        if idata == 'y':
                            print('Game Restarted')
                            self.charmer.director.roster.reset_scene()
                            self.init(restart=True, load_history=False, load_shadow=True, **kwargs)
                            #self.charmer.set_scene('^location_novara^', **kwargs)
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
                    elif action == 'help':
                        self.print_help()
                        continue
                    else:
                        print("Invalid request")
                        self.print_help()
                        continue
                    
                    if player_input is not None and self.charmer.add_history('player', player_input):
                        # If we rolled our history, we need to refresh
                        refresh = 0

                    # Bind back any residue to our history
                    chatter = self.charmer.director.flush_chatter()
                    if self.charmer.add_residue(residue=chatter, **kwargs):
                        # If we rolled our history, we need to refresh
                        refresh = 0
                    else:
                        # Otherwise, we need to add our residue to our input
                        lines += chatter

                    # Bind back any residue to our history
                    residue = self.charmer.director.flush_residue()
                    if self.charmer.add_residue(residue=residue, **kwargs):
                        # If we rolled our history, we need to refresh
                        refresh = 0
                    else:
                        # Otherwise, we need to add our residue to our input
                        lines += residue

                    last_input = player_input
                else:
                    logger.debug("Using previous input")
                
                if reset_no_restart:
                    #self.reset_engine(restart=False, **kwargs)
                    refresh = 0

                if player_input is not None:
                    print(f"{player_input}")

                if retry:
                    self.charmer.pop()
                    self.engine.reload_turn(**kwargs)
                    refresh += 1

                if refresh <= 0:
                    logger.info("Rebuilding Context")
                    prompt = self.charmer(**kwargs)
                    if nr == False:
                        prompt = f'{prompt}\n{additional}'
                    self.engine.prepare(system_context=self.current_system, restart=False, **kwargs)
                    self.engine.execute(prompt=prompt, **kwargs)
                    refresh = refresh_threshold
                elif player_input is not None:
                    turn = self.charmer.last_turn(**kwargs)
                    turn += lines
                    expanded_input = self.charmer.turn(turn, **kwargs)
                    self.engine.execute(prompt=f"{expanded_input}\n{additional}", **kwargs)
                    refresh -= 1
                    retry = False

                if ne == False:
                    iters = 0
                    while True:
                        iters += 1
                        current_speaker = self.charmer.director.speaker_turn()
                        if current_speaker is None:
                            # End of turn
                            print('===')
                            break
                        logger.debug(f"Current Speaker: {current_speaker.split('(')[0]}")
                        prefix = f"{current_speaker}"
                        self.engine.execute(prompt=prefix, **kwargs)
                        result = self.engine.read(max_tokens=r_length, n_temp=r_temp, **self.charmer.guidance.tokens, **kwargs)
                        if result is None:
                            # Rollback?
                            print("No response from engine.")
                            continue
                        else:
                            response = ''.join(result).strip()
                            if len(response) <= 1:
                                # End of turn
                                break
                            response = f"{prefix}{response}"
                            print(f"{response}")
                            self.charmer.add_history('model', response)
                check_input = True

            except EngineException as e:
                # We have too many tokens in our prompt.  Lets halve our history and
                # try again.
                logger.warn(f"Engine Exception: {e}")
                self.charmer.history_halve(current_clearance=e.tokens, **kwargs)
                check_input = False

def run_director(**kwargs):
    app = DirectorWizard.from_config(**kwargs)
    app.run_wizard(**kwargs)

if __name__ == "__main__":
    from ..llamaflow import FlowEngine

    logging.basicConfig(level=logging.DEBUG)

    config = {
        'model_path': '/mnt/biggy/ai/llama/gguf/',
        'model_file': 'zephyr-7b-beta.Q8_0.gguf',
        'model_guidance': 'alpaca',
        'scene_path': 'scene/novara',
        'n_ctx': 2 ** 13,
        'n_batch': 512,
        'n_gpu_layers': 16,
        'r_length': 256,
        'r_temp': 0.9,
        }
    #config['model_file'] = 'dolphin-2.2.1-ashhlimarp-mistral-7b.Q8_0.gguf'
    config['model_file'] = 'speechless-mistral-dolphin-orca-platypus-samantha-7b.Q8_0.gguf'

    app = DirectorWizard.from_config(**config)

    app.run_wizard(**config)

    
