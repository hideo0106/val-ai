from .analysis.summarizer import ChainOfAnalysis
from .charming import Charmer
from .charm.loader import load as run_charm_load
from .scrape import fetch_url
from .ioutil import CaptureFD

VERSION = "0.1.0"

DEFAULT_MODEL_PATH = 'local/models'
DEFAULT_SCENE_PATH = 'scene/verana'
DEFAULT_MODEL = 'zephyr-7b-beta.Q8_0.gguf'
DEFAULT_GPU_LAYERS = 14
DEFAULT_BATCH_SIZE = 512
DEFAULT_CONTEXT_SIZE = 2 ** 12
    
def run_summarize(url, **kwargs):
    co = None
    try:
        data = fetch_url(url, **kwargs)

        if not data:
            raise ValueError(f"Data is empty, the url may be invalid")

        with CaptureFD() as co:
            cod = ChainOfAnalysis.from_config(**kwargs)

        if len(data) < 100:
            raise ValueError(f"Data is too small: (size {len(data)}), the url may be invalid")
        summary = cod(data=data, **kwargs)

        print(f"""
    Article Summary Chain:

    """)
        for i, s in enumerate(cod.summaries):
            print(s)
        print(f"""Final Summary: {summary}""")
    except ValueError as e:
        print(f"Failed to summarize {url}: {e}")
    except Exception as e:
        print(f"Failed to summarize {url}: {e}")
        if co:
            print(co.stdout)
            print(co.stderr)

if __name__ == '__main__':
    import argparse
    import logging

    parser = argparse.ArgumentParser(description=f"ValAI CLI (v{VERSION})", prog='valai')

    subparsers = parser.add_subparsers(title='subcommands', help='Available commands', dest='command')

    summary_parser = argparse.ArgumentParser(add_help=False)
    summary_parser.add_argument('--model-path', type=str, default=DEFAULT_MODEL_PATH, help='Path to model')
    summary_parser.add_argument('--model-file', type=str, default=DEFAULT_MODEL, help='Model file (gguf)')
    summary_parser.add_argument('-n', '--iterations', type=int, default=3, help='Number of iterations to run')
    summary_parser.add_argument('-p', '--paragraphs', type=int, default=3, help='Number of paragraphs in summary')
    summary_parser.add_argument('-o', '--observations', type=int, default=8, help='Number of initial observations to generate')
    summary_parser.add_argument('-t', '--theories', type=int, default=3, help='Number of missing information theories to generate')
    summary_parser.add_argument('--sl', '--summary_length', type=int, default=150, dest='s_length', help='Max number of tokens in a summary paragraph')
    summary_parser.add_argument('--ol', '--observation_length', type=int, default=50, dest='o_length', help='Max number of tokens in a observation')
    summary_parser.add_argument('--tl', '--theory_length', type=int, default=50, dest='t_length', help='Max number of tokens in a theory')
    summary_parser.add_argument('--st', '--summary_temperature', type=float, default=0.5, dest="s_temp", help='Summary generation temperature')
    summary_parser.add_argument('--ot', '--observation_temperature', type=float, default=0.7, dest="o_temp", help='Observation generation temperature')
    summary_parser.add_argument('--tt', '--theory_temperature', type=float, default=1.0, dest="t_temp", help='Theory generation temperature')
    summary_parser.add_argument('--constrain_data', type=int, default=12000, help='Constrain the url data to this many bytes')
    summary_parser.add_argument('--n_batch', type=int, default=DEFAULT_BATCH_SIZE, help='LLAMA Batch Size')
    summary_parser.add_argument('--n_gpu_layers', type=int, default=DEFAULT_GPU_LAYERS, help='LLAMA GPU Layers')
    summary_parser.add_argument('--n_ctx', type=int, default=DEFAULT_CONTEXT_SIZE, help='LLAMA Context Size')
    summary_parser.add_argument('--log_chunk_length', type=int, default=50, help='Length of generated log chunks')
    summary_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    summary_parser.add_argument('url', type=str, metavar='URL', help='URL to summarize')

    charm_parser = argparse.ArgumentParser(add_help=False)
    charm_parser.add_argument('--model-path', type=str, default=DEFAULT_MODEL_PATH, help='Path to model')
    charm_parser.add_argument('--model-file', type=str, default=DEFAULT_MODEL, help='Model file (gguf)')
    charm_parser.add_argument('--scene_path', type=str, default=DEFAULT_SCENE_PATH, help='Path to scene')
    charm_parser.add_argument('--rl', '--response_length', type=int, default=250, dest='r_length', help='Max number of tokens in a game response')
    charm_parser.add_argument('--rt', '--response_temperature', type=float, default=0.7, dest="r_temp", help='Response generation temperature')
    charm_parser.add_argument('--constrain_data', type=int, default=12000, help='Constrain the history to this many bytes')
    charm_parser.add_argument('--n_batch', type=int, default=DEFAULT_BATCH_SIZE, help='LLAMA Batch Size')
    charm_parser.add_argument('--n_gpu_layers', type=int, default=DEFAULT_GPU_LAYERS, help='LLAMA GPU Layers')
    charm_parser.add_argument('--n_ctx', type=int, default=DEFAULT_CONTEXT_SIZE, help='LLAMA Context Size')
    charm_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    charm_load_parser = argparse.ArgumentParser(add_help=False)
    charm_load_parser.add_argument('--scene_path', type=str, default=DEFAULT_SCENE_PATH, help='Path to scene')
    charm_load_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    # Add your original parser as a subparser
    summ_cmd = subparsers.add_parser('summarize', parents=[summary_parser], help='Summarize an article')
    summ_cmd = subparsers.add_parser('charm', parents=[charm_parser], help='Run Charm')
    summ_cmd = subparsers.add_parser('charm:init', parents=[charm_load_parser], help='Charm Init Database')

    args = parser.parse_args()
    kwargs = dict(args._get_kwargs())

    def default():
        parser.print_help()
    
    if kwargs.get('verbose', False):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    {
        'summarize': lambda: run_summarize(**kwargs),
        'charm': lambda: Charmer.run_charm(**kwargs),
        'charm:init': lambda: run_charm_load(**kwargs),
    }.get(kwargs.get('command', None), default)()
