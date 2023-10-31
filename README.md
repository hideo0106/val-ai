# ValAI

Val is your AI assistant.

## Overview

Val is a system based on the utilization of large language models (LLMs) to perform a variety of tasks.  The system is designed to be modular, and to allow for the easy addition of new models and tasks.

## Theory

Using multiple models and requests in different contexts, combined with the addition of memory is the key to creating a system that can understand and converse with the user.  These various systems can be combined to allow for the ability to inject the correct state in-context to facilitate effective decision making and proficiency in the task at hand.

## Usage

### Installation

Install using [python poetry](https://python-poetry.org/).  `poetry install`

#### Hacks

You didn't think it would be that easy...

```bash
mkdir local
# be sure to ln -s your model folders into local/models
cd local
# This is a volatile dependency chain, so both llama-cpp and llama-cpp-python must be built from source and updated frequently
git clone --recurse-submodules https://github.com/abetlen/llama-cpp-python
# You need ot make it with your llama build args or you won't get acceleration
CMAKE_ARGS="-DLLAMA_CUBLAS=on" python3 -m pip install ./llama-cpp-python/ --force-reinstall
```

### CLI

To run the CLI, simply invoke the package as a module:

```bash
$ python -m valai
usage: valai [-h] {summarize,charm,charm:init} ...

ValAI CLI (v0.1.1)

options:
  -h, --help            show this help message and exit

subcommands:
  {summarize,charm,charm:init}
                        Available commands
    summarize           Summarize an article
    charm               Run Charm
    charm:init          Charm Init Database
```

## Models

This package uses the llama-cpp-python low-level interface to interact with our model.

## Tasks

### Summarization

Text summarization is the process of distilling the most important information from a source (or sources) to produce an abridged version for a particular user (or users) and task (or tasks).  There are two main types of summarization: extractive and abstractive.  Extractive summarization involves selecting important sentences, paragraphs, or other units of text from the source.  Abstractive summarization involves generating new text that is not present in the source.

#### Abstractive Summarization

Abstractive summarization is the process of generating new text that is not present in the source.  This is a much more difficult task than extractive summarization, as it requires the model to understand the source text and generate new text that is both grammatically correct and semantically relevant.  Our state-of-the-art Analysis + Chain of Density (ACoD) model is able to generate abstractive summaries that are both grammatically correct and semantically relevant.

```bash
$ python -m valai summarize --help
usage: valai summarize [-h] [--model-path MODEL_PATH] [--model-file MODEL_FILE] [-n ITERATIONS] [-p PARAGRAPHS] [-o OBSERVATIONS] [-t THEORIES]
                       [--sl S_LENGTH] [--ol O_LENGTH] [--tl T_LENGTH] [--st S_TEMP] [--ot O_TEMP] [--tt T_TEMP] [--constrain CONSTRAIN_DATA]
                       [--batch N_BATCH] [--layers N_GPU_LAYERS] [--ctx N_CTX] [--log-chunk LOG_CHUNK_LENGTH] [-v]
                       URL

positional arguments:
  URL                   URL to summarize

options:
  -h, --help            show this help message and exit
  --model-path MODEL_PATH
                        Path to model
  --model-file MODEL_FILE
                        Model file (gguf)
  -n ITERATIONS, --iterations ITERATIONS
                        Number of iterations to run
  -p PARAGRAPHS, --paragraphs PARAGRAPHS
                        Number of paragraphs in summary
  -o OBSERVATIONS, --observations OBSERVATIONS
                        Number of initial observations to generate
  -t THEORIES, --theories THEORIES
                        Number of missing information theories to generate
  --sl S_LENGTH, --summary-length S_LENGTH
                        Max number of tokens in a summary paragraph
  --ol O_LENGTH, --observation-length O_LENGTH
                        Max number of tokens in a observation
  --tl T_LENGTH, --theory-length T_LENGTH
                        Max number of tokens in a theory
  --st S_TEMP, --summary-temperature S_TEMP
                        Summary generation temperature
  --ot O_TEMP, --observation-temperature O_TEMP
                        Observation generation temperature
  --tt T_TEMP, --theory-temperature T_TEMP
                        Theory generation temperature
  --constrain CONSTRAIN_DATA
                        Constrain the url data to this many bytes
  --batch N_BATCH       LLAMA Batch Size
  --layers N_GPU_LAYERS
                        LLAMA GPU Layers
  --ctx N_CTX           LLAMA Context Size
  --log-chunk LOG_CHUNK_LENGTH
                        Length of generated log chunks
  -v, --verbose         Verbose output
```

### Charm Game Engine

I have a little game that is sort of fun, which is a prototype for my context shadowing idea.  I had originally written it for koboldcpp as a test, but now with my FlowEngine, I can just run it here...

```bash
$ python -m valai charm --help
usage: valai charm [-h] [--model-path MODEL_PATH] [--model-file MODEL_FILE] [--scene-path SCENE_PATH] [--rl R_LENGTH] [--rt R_TEMP]
                   [--constrain CONSTRAIN_DATA] [--batch N_BATCH] [--layers N_GPU_LAYERS] [--ctx N_CTX] [-v]

options:
  -h, --help            show this help message and exit
  --model-path MODEL_PATH
                        Path to model
  --model-file MODEL_FILE
                        Model file (gguf)
  --scene-path SCENE_PATH
                        Path to scene
  --rl R_LENGTH, --length R_LENGTH
                        Max number of tokens in a game response
  --rt R_TEMP, --temperature R_TEMP
                        Response generation temperature
  --constrain CONSTRAIN_DATA
                        Constrain the history to this many bytes
  --batch N_BATCH       LLAMA Batch Size
  --layers N_GPU_LAYERS
                        LLAMA GPU Layers
  --ctx N_CTX           LLAMA Context Size
  -v, --verbose         Verbose output
```

You get gameplay like this:

```
> We run towards the blacksmith's shop.
Narrator: (describing) As you approach the blacksmith's shop, you see a group of people gathered around it. Smoke is billowing out of the door, and you can hear the sound of metal clanging against metal coming from inside.

> I rush to the door.
Narrator: (describing) The door creaks open as you push it aside. Inside, you see Cedric, the lucky farmer, lying on the ground, surrounded by a group of goblins. They're wielding crude weapons and wearing crude armor made from animal hides.

> Cedric!  I brandish my longsword, and move to engage.
Narrator: (describing) The goblins turn to face you, snarling and cackling as they prepare for battle. You raise your sword, ready to fight.

> help
Commands:
  show, load, save, last, expand, pop, restart, retry, quit, help

>
```

#### Game Initialization

To play, you have to load the game data into the database.  This is done with the `charm:init` command.

```bash
$ python -m valai charm:init --help
usage: valai charm:init [-h] [--scene_path SCENE_PATH] [-v]

options:
  -h, --help            show this help message and exit
  --scene_path SCENE_PATH
                        Path to scene
  -v, --verbose         Verbose output
```

## License

This software is licensed under the [Apache 2.0](./LICENSE.txt) license.

## Author

Martin Bukowski, [Byte Motive Data Systems, LLC](https://bmds.us) © 2023
