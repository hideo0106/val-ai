# valai/pinnacle/guidance.py

# Our guidance strategies for formatting output for models

from typing import List


class GuidanceStrategy:
    tokens = {
        "abort_tokens": [],
        "stop_tokens": ['\n'],
        "sequence_tokens": []
    }

    def format_system(self, system : list[str], output_head : bool = True, output_end : bool = True, **kwargs) -> str:
        fixed = [e for e in self.fix_prompt(lines=system)]
        return '\n'.join(fixed)

    def format_turn(self, turn : list[str], **kwargs) -> str:
        fixed = [e for e in self.fix_prompt(lines=turn)]
        prompt = '\n'.join(fixed)
        return prompt

    def fix_prompt(self, lines : List[str], **kwargs) -> List[str]:
        return lines
    
    def filter_display(self, lines : List[str]) -> List[str]:
        return lines
    
    @classmethod
    def from_config(cls, model_guidance : str, **kwargs):
        return guidance_factory(model_guidance, **kwargs)

class SimplePromptStrategy(GuidanceStrategy):
    tokens = {
        "abort_tokens": ['>', '<', '|', '['],
        "stop_tokens": ['\n'],
        "sequence_tokens": [['\n','[']]
    }

    def __init__(self):
        pass

    def fix_prompt(self, lines : List[str], filter_codex : bool = False, **kwargs) -> List[str]:
        prev = []
        matchers = ['>', '$']
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

class ChatMLPromptStrategy(GuidanceStrategy):
    """<|im_start|>system
You are Dolphin, a helpful AI assistant.<|im_end|>
<|im_start|>user
{prompt}<|im_end|>
<|im_start|>assistant
"""
    """$player: Hello
Character: Hi
"""
    tokens = {
        "abort_tokens": ['$'],
        "stop_tokens": [],
        "sequence_tokens": [['\n','<'], ['\n', '[']],
    }

    def __init__(self, player_name : str = '$player', **kwargs):
        self.player_name = player_name

    def format_system(self, system : list[str], output_head : bool = True, output_end : bool = True, **kwargs) -> str:
        fixed = [e for e in self.fix_prompt(lines=system, system=True)]
        if output_head:
            fixed.insert(0, '<|im_start|>System')
        if output_end:
            fixed.append('')
            fixed.append('### Instruction: The following is a interactive game text adventure.')
            fixed.append('### Request:  Following System guidance, play the role of the characters and ZxdrOS in the dialogue.')
            fixed.append('### Response (endless, following guidance):')
            fixed.append('<|im_end|>')
        prompt = '\n'.join(fixed)
        return prompt

    def fix_prompt(self, lines : List[str], system : bool = False, filter_codex : bool = False, **kwargs) -> List[str]:
        prev = []
        player_match = '>'
        filters = ['']
        if filter_codex:
            filters.append('#')
        for line in lines:
            if len(line) == 0 or line[0] in filters:
                continue
            if line[0] == '[':
                yield f'<|im_start|>system name=zxdros\n{line}<|im_end|>'
            if line[0] in player_match:
                name = self.player_name
                if system:
                    name = f'system user=example_{name}'
                yield f'<|im_start|>{name}\n{line[2:]}<|im_end|>'
            else:
                name, rest = line.split(' ', 1)
                name = name[:-1].lower()
                if system:
                    name = f'system user=example_{name}'
                yield f'<|im_start|>{name}\n{rest}<|im_end|>'
            prev = line
        return []



class DialogPromptStrategy(GuidanceStrategy):
    """$player: Hello
Character: Hi
"""
    tokens = {
        "abort_tokens": ['>', '<', '|', '[', '$'],
        "stop_tokens": ['\n'],
        "sequence_tokens": [['\n','['], ['\n', '']]
    }

    def __init__(self, player_name : str = '$player', **kwargs):
        self.player_name = player_name

    def format_system(self, system : list[str], output_head : bool = True, output_end : bool = True, **kwargs) -> str:
        fixed = [e for e in self.fix_prompt(lines=system)]
        if output_head:
            fixed.insert(0, '### System')
        if output_end:
            fixed.append('')
            fixed.append('### Instruction: The following is a interactive game text adventure.')
            fixed.append('### Request:  Following System guidance, play the role of the characters and ZxdrOS in the dialogue.')
            fixed.append('### Response (endless, following guidance):')
        prompt = '\n'.join(fixed)
        return prompt

    def format_turn(self, turn : list[str], **kwargs) -> str:
        fixed = [e for e in self.fix_prompt(lines=turn)]
        prompt = '\n'.join(fixed)
        return prompt

    def fix_prompt(self, lines : List[str], filter_codex : bool = False, **kwargs) -> List[str]:
        prev = []
        player_match = '>'
        player_match2 = '$'
        filters = ['']
        if filter_codex:
            filters.append('#')
        for line in lines:
            if len(line) == 0 or line[0] in filters:
                continue
            if ((prev is None or len(prev) > 0 and prev[0] != '[')) and line[0] == '[':
                yield ''
            if line[0] in player_match:
                yield ''
                yield f'{self.player_name}: {line[2:]}'
            elif line[0] in player_match2:
                yield ''
                yield line
            else:
                yield line
            prev = line
        return []


class AlpacaPromptStrategy(GuidanceStrategy):
    """### Instruction:
Summarize following text.

### Input:
Text to be summarized

### Response:"""
    tokens = {
        "abort_tokens": ['>', '<', '|', '#'],
        "stop_tokens": ['\n'],
        "sequence_tokens": [['\n','['], ['#', "#"], ['.', ''], ['\n', '$']]
    }

    def __init__(self, player_name : str = '$player', **kwargs):
        self.player_name = player_name

    def format_system(self, system : list[str], output_head : bool = True, output_end : bool = True, **kwargs) -> str:
        fixed = [e for e in self.fix_prompt(lines=system)]
        if output_head:
            fixed.insert(0, '### Instruction:')
            fixed.insert(1, 'The following is a interactive game text adventure.   Following System guidance, play the role of the characters and ZxdrOS in the dialogue.')
            fixed.insert(2, '### Input (system):')
        if output_end:
            fixed.append('### Response (endless, following dialog):\n')
        prompt = '\n'.join(fixed)
        return prompt

    def format_turn(self, turn : list[str], hide_system : bool = True, **kwargs) -> str:
        fixed = [e for e in self.fix_prompt(lines=turn)]
        if not hide_system:
            fixed.append('### Response (endless, following dialog):\n')
        prompt = '\n'.join(fixed)
        return prompt

    def fix_prompt(self, lines : List[str], filter_codex : bool = False, **kwargs) -> List[str]:
        prev = []
        player_match = '>'
        player_match2 = '$'
        filters = ['']
        if filter_codex:
            filters.append('#')
        for line in lines:
            if len(line) == 0 or line[0] in filters:
                continue
            if ((prev is None or len(prev) > 0 and prev[0] not in ("#"))) and line[0] == '#':
                yield ''
            if ((prev is None or len(prev) > 0 and prev[0] not in ('[', "#"))) and line[0] == '[':
                yield ''
            if line[0] in player_match:
                yield ''
                yield f'{self.player_name}: {line[2:]}'
            elif line[0] in player_match2:
                yield ''
                yield line
            else:
                yield line
            prev = line
        return []

    def filter_display(self, lines : List[str]):
        return [l for l in lines if l[:3] != '###']

def guidance_factory(model_guidance : str, **kwargs) -> GuidanceStrategy:
    if model_guidance == 'simple':
        return SimplePromptStrategy()
    elif model_guidance == 'chatml':
        return ChatMLPromptStrategy(**kwargs)
    elif model_guidance == 'dialog':
        return DialogPromptStrategy(**kwargs)
    elif model_guidance == 'alpaca':
        return AlpacaPromptStrategy(**kwargs)
    else:
        raise ValueError(f"Unknown guidance strategy {model_guidance}")
