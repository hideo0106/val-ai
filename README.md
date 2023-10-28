# ValAI

Val is your AI assistant.

## Overview

Val is a system based on the utilization of large language models (LLMs) to perform a variety of tasks.  The system is designed to be modular, and to allow for the easy addition of new models and tasks.

## Theory

Using multiple models and requests in different contexts, combined with the addition of memory is the key to creating a system that can understand and converse with the user.  These various systems can be combined to allow for the ability to inject the correct state in-context to facilitate effective decision making and proficiency in the task at hand.

## Usage

### Installation

Install using [python poetry](https://python-poetry.org/).  `poetry install`

### CLI

To run the CLI, simply invoke the package as a module:

```bash
$ python -m valai --help
usage: valai [-h] {summarize} ...

ValAI CLI (v0.0.1)

options:
  -h, --help   show this help message and exit

subcommands:
  {summarize}  Available commands
    summarize  Summarize an article
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
                       [--sl S_LENGTH] [--ol O_LENGTH] [--tl T_LENGTH] [--st S_TEMP] [--ot O_TEMP] [--tt T_TEMP]
                       [--constrain_data CONSTRAIN_DATA] [--n_batch N_BATCH] [--n_gpu_layers N_GPU_LAYERS] [--n_ctx N_CTX]
                       [--log_chunk_length LOG_CHUNK_LENGTH] [-v]
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
  --sl S_LENGTH, --summary_length S_LENGTH
                        Max number of tokens in a summary paragraph
  --ol O_LENGTH, --observation_length O_LENGTH
                        Max number of tokens in a observation
  --tl T_LENGTH, --theory_length T_LENGTH
                        Max number of tokens in a theory
  --st S_TEMP, --summary_temperature S_TEMP
                        Summary generation temperature
  --ot O_TEMP, --observation_temperature O_TEMP
                        Observation generation temperature
  --tt T_TEMP, --theory_temperature T_TEMP
                        Theory generation temperature
  --constrain_data CONSTRAIN_DATA
                        Constrain the url data to this many bytes
  --n_batch N_BATCH     LLAMA Batch Size
  --n_gpu_layers N_GPU_LAYERS
                        LLAMA GPU Layers
  --n_ctx N_CTX         LLAMA Context Size
  --log_chunk_length LOG_CHUNK_LENGTH
                        Length of generated log chunks
  -v, --verbose         Verbose output
```

## License

This software is licensed under the [Apache 2.0](./LICENSE.txt) license.

## Author

Martin Bukowski, [Byte Motive Data Systems, LLC](https://bmds.us) © 2023
