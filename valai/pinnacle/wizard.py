# valai/pinnacle/wizard.py

import asyncio
import logging
import os
from typing import Optional

from ..analysis.summarizer import ChainOfAnalysis
from ..engine import EngineException, FlowEngine, OutputHandler
from ..engine.grammar import load_grammar
from ..ioutil import CaptureFD

from .charmer import DirectorCharmer
from .exception import DirectorError
from .token import TokenFeatures

logger = logging.getLogger(__name__)


class DirectorWizard:
    current_system : Optional[str]

    def __init__(self, charmer : DirectorCharmer, engine : FlowEngine, output : OutputHandler):
        self.output = output
        self.charmer = charmer
        self.engine = engine
        self.current_system = None
        self.command_chain = []

    @staticmethod
    def expand_config(config : dict, **kwargs) -> dict:
        # TODO this should be a typed dict coming out
        config = {
            'resources_path': 'resources',
            'scene_name': 'novara',
            'model_guidance': 'dialog',
            'resources_path': 'resources',
            'scene_name': 'novara',
            'player': '$player',
            'location_name': 'Novara',
            'model_guidance': 'dialog',
            **config,
            **kwargs
        }
        config['scene_path'] = os.path.join(config['resources_path'], 'scene', config['scene_name'])
        config['grammar_path'] = os.path.join(config['resources_path'], 'grammar')
        return config

    @classmethod
    def from_config(cls, **kwargs):
        output = OutputHandler()

        charmer = DirectorCharmer.from_config(**kwargs)
        if not kwargs.get('verbose', False):
            with CaptureFD() as co:
                engine = FlowEngine.from_config(output=output, **kwargs)
        else:
            engine = FlowEngine.from_config(output=output, **kwargs)
        
        return cls(charmer=charmer, engine=engine, output=output)

    def reset_engine(self, restart : bool = False, level : str = 'game', **kwargs) -> bool:
        try:
            logger.debug(f"Resetting Engine (Restart: {restart}, system: {level})")
            if level == 'game':
                self.engine.set_context(system_context='system', prompt=self.current_system, **kwargs)
                self.engine.prepare(system_context='system', restart=restart, **kwargs)
                prompt = "### Input (new scene):"
                prompt += self.charmer.scene_header(output_end=False, **kwargs)
                prompt += "\n### Response (dialog, endless):\n"        
                # TODO discover the actual scene boundary in the history, and potentally feed history
                # into the engine differently; potentially unexpanded, and before the scene definition.
                # The scene header could potentially be injected into the stream in some more
                # elegant way as well.
                logger.debug(f"Sending prompt: {len(prompt)}")
                self.engine.execute(prompt=prompt, checkpoint=None, scope='scene', show_progress = True, **kwargs)
                self.engine.set_checkpoint('scene', **kwargs)
            elif level == 'scene':
                self.engine.reload_turn(checkpoint='scene', **kwargs)

            prompt = self.charmer(**kwargs)
            self.engine.execute(prompt=prompt, checkpoint='turn', scope='history', show_progress = True, **kwargs)
            return True
        except EngineException as e:
            logging.error(f"Engine Exception: {e}")
            return False
    
    def println(self, text : str, **kwargs):
        self.output.handle_system(text)

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
        if system is not None:
            self.current_system = system

        if restart:
            self.engine.clear_saved_context(**kwargs)
        self.reset_engine(restart=restart, level='game', **kwargs)

        return True

    def execute_scene_analysis(self, **kwargs) -> bool:
        history = self.charmer.get_history(**kwargs)
        token_features = TokenFeatures.from_history(history=history, **kwargs)
        scenes = token_features.scene_documents(**kwargs)
        for c in scenes:
            self.println(f"{c}")

        return True

    def show_history(self, n_show : int = 10, **kwargs):
        self.println(self.charmer.format_history(n_show=n_show, **kwargs))

    def print_help(self):
        self.println('Commands:')
        self.println('  a/attack/kill <enemy> - Attack an enemy')
        self.println('  b/buy <item> <price> - Buy an item from a merchant')
        self.println('  c/cast <spell> <target (optional) - Cast a spell')
        self.println('  i/inventory - show your inventory')
        self.println('  l/location - show your current location')
        self.println('  l/look <function word (optional)> <target (optional)> - Look at something, or look around')
        self.println('  p/party - show your party')
        self.println('  r/rest <target (optional)> - rest for the night')
        self.println('  s/search <target> - search something')
        self.println('  t/talk/say <character> <prompt> - Say something to a character')
        self.println('  u/use <item> - Use an item')
        self.println('  x/travel/go <location> - Travel to a location')
        self.println(f'  q/ask <prompt> - Ask {self.charmer.director.roster.game_master.sheet.name} a question')
        self.println('  join/invite <character> - invite a character to your party')
        self.println('  kick <character> - kick a character from your party')
        self.println('  save - save the game')
        self.println('  load - load a saved game')
        self.println('  show - show the last 10 turns')
        self.println('  history - show the entire history')
        self.println('  scene - analyze the scene')
        self.println('  renew - reload the game configuration')
        self.println('  restart - restart the game')
        self.println('  quit - exit the game')
        self.println('  help - show this help')
        self.println('Cheats:')
        self.println('  nr <prompt> - write prompt to engine, no return')
        self.println('  ne <prompt> - write prompt to engine, no read')

    def read_prompt(self, prompt_style: str, prompt_path : str = "prompts", **kwargs) -> str:
        filename = f"{prompt_path}/{prompt_style}.txt"
        if not os.path.exists(filename):
            logger.warn(f"Prompt file {filename} does not exist.")
            return ''
        with open(filename, 'r') as f:
            data = f.read()
        return data

    async def run_wizard(self, r_length : int, r_temp : float, refresh_threshold : int = 10, **kwargs):
        self.println("Starting Director...")
        self.init(**kwargs)

        running = True
        retry = False
        self.println("Game Starting")
        self.show_history(**kwargs)
        refresh = refresh_threshold
        last_input = ''
        check_input = True
        grammar_s = load_grammar(grammar_file="pinnacle_turn_s.gbnf", **kwargs)
        grammar_d = load_grammar(grammar_file="pinnacle_turn_d.gbnf", **kwargs)
        while running:
            try:
                nr = False
                ne = False
                if check_input:
                    action = input('\n> ')
                    asplit = action.split(" ", 1)
                    a2split = action.split(" ", 2)
                    ansplit = action.split(" ")
                    lines = []
                    if action == '':
                        continue
                    elif a2split[0] == 'gram':
                        grammar_s = load_grammar(grammar_file="pinnacle_turn_s.gbnf", **kwargs)
                        grammar_d = load_grammar(grammar_file="pinnacle_turn_d.gbnf", **kwargs)
                        continue
                    elif a2split[0] == 'speak' or a2split[0] == 'talk' or a2split[0] == 'say' or a2split[0] == 't':
                        if len(a2split) != 3:
                            self.println("Invalid talk command: talk <character> <prompt>")
                            self.println(f"Valid characters: {', '.join(self.charmer.director.character_keywords())}")
                            continue
                        try:
                            player_input = self.charmer.director.speak(target=a2split[1].strip(), dialog=a2split[2].strip(), **kwargs)
                        except DirectorError as e:
                            self.println(f"Director Error: {e}")
                            self.println(f"Valid characters: {', '.join(self.charmer.director.character_keywords())}")
                            continue
                    elif a2split[0] == 'buy' or a2split[0] == 'b':
                        if len(a2split) != 3:
                            self.println("Invalid buy command: buy <item> <price>")
                            continue
                        try:
                            player_input = self.charmer.director.buy(item=a2split[1].strip(), price=a2split[2].strip(), **kwargs)
                        except DirectorError as e:
                            self.println(f"Director Error: {e}")
                            items = self.charmer.director.scene.get_prices()
                            for item in items:
                                self.println(f"{item[0]} - {item[1]} - {item[2]} silver")
                            continue
                    elif ansplit[0] == 'cast' or ansplit[0] == 'c':
                        if 2 > len(a2split) < 3:
                            self.println("Invalid cast command: cast <spell> <target (optional)>")
                            continue
                        try:
                            if len(ansplit) == 2:
                                player_input = self.charmer.director.cast(spell=a2split[1].strip(), **kwargs)
                            elif len(ansplit) == 3:
                                player_input = self.charmer.director.cast(spell=a2split[1].strip(), target=a2split[2].strip(), **kwargs)
                            elif len(ansplit) > 3:
                                player_input = self.charmer.director.cast(spell=a2split[1].strip(), description=' '.join(a2split[2:]), **kwargs)
                        except DirectorError as e:
                            self.println(f"Director Error: {e}")
                            continue
                    elif asplit[0] == 'ask' or asplit[0] == 'q':
                        if len(asplit) != 2:
                            self.println("Invalid ask command: ask <prompt>")
                            continue
                        try:
                            player_input = self.charmer.director.speak('none', dialog=asplit[1].strip(), override=self.charmer.director.roster.game_master, **kwargs)
                        except DirectorError as e:
                            self.println(f"Director Error: {e}")
                            continue
                    elif a2split[0] == 'travel' or a2split[0] == 'go' or a2split[0] == 'x':
                        if len(a2split) != 2:
                            self.println("Invalid travel command: travel <location>")
                            self.println(f"Valid locations: {', '.join(self.charmer.director.exit_keywords())}")
                            continue
                        try:
                            player_input = self.charmer.director.travel(a2split[1].strip(), **kwargs)
                            self.reset_engine(restart=False, level='game', **kwargs)
                            refresh = refresh_threshold
                        except DirectorError as e:
                            self.println(f"Director Error: {e}")
                            self.println(f"Valid locations: {', '.join(self.charmer.director.exit_keywords())}")
                            continue
                    elif a2split[0] == 'rest' or a2split[0] == 'r':
                        if len(a2split) > 2:
                            self.println("Invalid rest command: rest <target (optional)>")
                            continue
                        try:
                            if len(a2split) == 1:
                                player_input = self.charmer.director.rest(**kwargs)
                            else:
                                player_input = self.charmer.director.rest(a2split[1].strip(), **kwargs)
                        except DirectorError as e:
                            self.println(f"Director Error: {e}")
                            continue
                    elif a2split[0] == 'take':
                        try:
                            #player_input = self.charmer.director.take(a2split[1].strip(), **kwargs)
                            continue
                        except DirectorError as e:
                            self.println(f"Director Error: {e}")
                            continue
                    elif a2split[0] == 'inventory' or a2split[0] == 'i':
                        try:
                            self.println(f"Silver - {self.charmer.director.roster.player.silver}")
                            self.println("Your inventory:")
                            for i in self.charmer.director.roster.player.inventory:
                                self.println(f"- {i}")

                            self.println("Known Spells:")
                            for s in self.charmer.director.roster.player.sheet.spells:
                                self.println(f"- {s}")
                            #player_input = self.charmer.director.take(a2split[1].strip(), **kwargs)
                            continue
                        except DirectorError as e:
                            self.println(f"Director Error: {e}")
                            continue
                    elif a2split[0] == 'party':
                        # Show party details
                        if len(self.charmer.director.roster.party) == 0:
                            self.println("No one is in your party.")
                            continue
                        self.println("Your party:")
                        for c in self.charmer.director.roster.get_party():
                            self.println(f"{c}")
                        continue
                    elif a2split[0] == 'join' or a2split[0] == 'invite':
                        if len(a2split) != 2:
                            self.println("Invalid join command: join <character>")
                            self.println(f"Valid characters: {', '.join(self.charmer.director.party)}")
                            continue
                        try:
                            player_input = self.charmer.director.party(a2split[1].strip(), True, **kwargs)
                        except DirectorError as e:
                            self.println(f"Director Error: {e}")
                            self.println(f"Valid characters: {', '.join(self.charmer.director.party_keywords())}")
                            continue
                    elif a2split[0] == 'kick':
                        if len(a2split) != 2:
                            self.println("Invalid join command: kick <character>")
                            self.println(f"Valid characters: {', '.join(self.charmer.director.party_keywords())}")
                            continue
                        try:
                            player_input = self.charmer.director.party(a2split[1].strip(), False, **kwargs)
                        except DirectorError as e:
                            self.println(f"Director Error: {e}")
                            self.println(f"Valid characters: {', '.join(self.charmer.director.character_keywords())}")
                            continue
                    elif a2split[0] == 'look' or a2split[0] == 'l':
                        try:
                            if len(a2split) >= 3:
                                target = ' '.join(a2split[1:]).strip()
                                player_input = self.charmer.director.look(target=target, **kwargs)
                            elif len(a2split) == 1:
                                player_input = self.charmer.director.look(target=None, **kwargs)
                            else:
                                self.println("Invalid look command: look <function word (optional)> <target (optional)>")
                                continue
                        except DirectorError as e:
                            self.println(f"Director Error: {e}")
                            continue
                    elif a2split[0] == 'search' or a2split[0] == 's':
                        try:
                            if len(a2split) > 2:
                                target = ' '.join(a2split[1:]).strip()
                                player_input = self.charmer.director.search(target=target, **kwargs)
                            else:
                                self.println("Invalid look command: search <target>")
                                continue
                        except DirectorError as e:
                            self.println(f"Director Error: {e}")
                            continue
                    elif asplit[0] == 'use' or asplit[0] == 'u':
                        if len(asplit) != 2:
                            self.println("Invalid use command: use <item>")
                            continue
                        try:
                            player_input = self.charmer.director.use(asplit[1].strip(), **kwargs)
                        except DirectorError as e:
                            self.println(f"Director Error: {e}")
                            continue
                    elif asplit[0] == 'attack' or asplit[0] == 'a' or asplit[0] == 'kill':
                        if len(asplit) != 2:
                            self.println("Invalid use command: attack <enemy>")
                            continue
                        try:
                            player_input = self.charmer.director.attack(asplit[1].strip(), **kwargs)
                        except DirectorError as e:
                            self.println(f"Director Error: {e}")
                            continue
                    elif action == 'l' or action == 'location':
                        self.println(f"Current Location:")
                        self.println(self.charmer.director.scene.location.location_line())
                        self.println(self.charmer.director.scene.location.description_line())
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
                            self.println('No prompt specified')
                            continue
                        else:
                            player_input = f"{asplit[1].strip()}"
                    elif action == 'quit':
                        self.println('Are you sure? (y/N)')
                        quitting = input('> ')
                        if quitting == 'y':
                            self.println('Goodbye')
                            exit(0)
                        else:
                            self.println('Continuing')
                            continue
                    elif action == 'show':
                        self.show_history(**kwargs)
                        continue
                    elif action == 'load':
                        self.println('Loading Game')
                        self.init(restart = False, load_history=True, load_shadow=True, **kwargs)
                        self.show_history(**kwargs)
                        refresh = refresh_threshold
                        self.println('Game Loaded')
                        continue
                    elif action == 'renew':
                        self.println('Refreshing Shadow')
                        self.init(restart=True, load_history=False, load_shadow=True, **kwargs)
                        self.show_history(**kwargs)
                        continue
                    elif action == 'scene':
                        self.println('Scene Analysis')
                        self.execute_scene_analysis(**kwargs)
                        continue
                    elif action == 'save':
                        self.println('Saving Game')
                        self.charmer.save_game(**kwargs)
                        self.println('Game Saved')
                        continue
                    elif action == 'restart':
                        self.println('Are you sure? (y/N)')
                        idata = input('> ')
                        if idata == 'y':
                            self.println('Game Restarted')
                            self.charmer.director.roster.reset_scene()
                            self.init(restart=True, load_history=False, load_shadow=True, **kwargs)
                            #self.charmer.set_scene('^location_novara^', **kwargs)
                            self.show_history(**kwargs)
                            refresh = refresh_threshold
                            continue
                        else:
                            self.println('Continuing')
                            continue
                    elif action == 'history':
                        self.println('History')
                        self.show_history(n_show = -1, **kwargs)
                        continue
                    elif action == 'help':
                        self.print_help()
                        continue
                    else:
                        self.println("Invalid request")
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

                if player_input is not None:
                    self.println(f"{player_input}")

                if retry:
                    self.charmer.pop()
                    self.engine.reload_turn(**kwargs)
                    refresh += 1

                if refresh <= 0:
                    logger.info("Refreshing Engine")
                    prompt = self.charmer(**kwargs)
                    if nr == False:
                        prompt = f'{prompt}\n'
                    self.reset_engine(restart=False, level='scene', **kwargs)
                    #self.engine.prepare(system_context='system', restart=False, **kwargs)
                    self.engine.execute(prompt=prompt, checkpoint=True, scope='refresh', show_progress = True, **kwargs)
                    refresh = refresh_threshold
                elif player_input is not None:
                    turn = self.charmer.last_turn(**kwargs)
                    turn += lines
                    expanded_input = self.charmer.turn(turn, **kwargs)
                    self.engine.execute(prompt=f"{expanded_input}\n", checkpoint=True, show_progress = False, **kwargs)
                    refresh -= 1
                    retry = False

                if ne == False:
                    iters = 0
                    while True:
                        grammar_s.reset()
                        grammar_d.reset()
                
                        iters += 1
                        traited = self.charmer.director.trait is not None
                        current_speaker = self.charmer.director.speaker_turn()
                        if current_speaker is None:
                            # End of turn
                            break
                        logger.debug(f"Current Speaker: {current_speaker.split('(')[0]}")
                        prefix = f"{current_speaker}"
                        self.output.handle_token(current_speaker)
                        self.engine.execute(prompt=prefix, checkpoint=False, show_progress=False, **kwargs)
                        if traited:
                            t_grammar = grammar_s
                        else:
                            t_grammar = grammar_d
                        result = self.engine.read(max_tokens=r_length, n_temp=r_temp, token_handler=self.output,
                                                  grammar=t_grammar, **self.charmer.guidance.tokens, **kwargs)
                        if result is None:
                            # Rollback?
                            self.println("No response from engine.")
                            continue
                        else:
                            response = ''.join(result).strip()
                            if len(response) <= 1:
                                # End of turn
                                break
                            response = f"{prefix}{response}"
                            #self.println(f"{response}")
                            self.charmer.add_history('model', response)
                check_input = True

            except EngineException as e:
                # We have too many tokens in our prompt.  Lets halve our history and
                # try again.
                logger.warn(f"Engine Exception: {e}")
                self.charmer.history_halve(current_clearance=e.tokens, **kwargs)
                check_input = False

def run_director(**kwargs):
    config = DirectorWizard.expand_config(config=kwargs)
    app = DirectorWizard.from_config(**config)
    asyncio.run(app.run_wizard(**config))

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    config = {
        'model_path': '/mnt/biggy/ai/llama/gguf/',
        'model_file': 'zephyr-7b-beta.Q8_0.gguf',
        'model_guidance': 'alpaca',
        'resources_path': 'resources',
        'scene_name': 'novara',
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
