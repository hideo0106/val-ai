# valai/llamaflow.py

from ctypes import c_void_p, c_char, pointer
import logging
import os
import multiprocessing
from typing import List, Optional
import llama_cpp

logger = logging.getLogger(__name__)

class FlowEngine:
    """
        FlowEngine is a wrapper around the llama_cpp library that provides a simple interface for reading and writing to the model
    """
    @staticmethod
    def get_mparams(
            n_gpu_layers: int = 0,
            main_gpu: int = 0,
            tensor_split: Optional[List[float]] = None,
            vocab_only: bool = False,
            use_mmap: bool = True,
            use_mlock: bool = False,
            **kwargs
    ):
        """Generate a llama_model_params struct with the given parameters"""
        mparams = llama_cpp.llama_model_default_params()
        mparams.n_gpu_layers = (
            0x7FFFFFFF if n_gpu_layers == -1 else n_gpu_layers
        )  # 0x7FFFFFFF is INT32 max, will be auto set to all layers
        mparams.main_gpu = main_gpu
        mparams.vocab_only = vocab_only
        mparams.use_mmap = use_mmap
        mparams.use_mlock = use_mlock
        return mparams

    @staticmethod
    def get_cparams(
            seed: int = llama_cpp.LLAMA_DEFAULT_SEED,
            n_ctx: int = 4096,
            n_batch: int = 512,
            n_threads: Optional[int] = None,
            n_threads_batch: Optional[int] = None,
            rope_freq_base: float = 0.0,
            rope_freq_scale: float = 0.0,
            mul_mat_q: bool = True,
            f16_kv: bool = True,
            logits_all: bool = False,
            embedding: bool = False,
            **kwargs
            ):
        """Generate a llama_context_params struct with the given parameters"""
        cparams = llama_cpp.llama_context_default_params()
        n_batch = min(n_ctx, n_batch) # We don't want a batch being larger than our context
        n_threads = n_threads or max(multiprocessing.cpu_count() // 2, 1)
        n_threads_batch = n_threads_batch or max(
                multiprocessing.cpu_count() // 2, 1
            )
        cparams.seed = seed
        cparams.n_ctx = n_ctx
        cparams.n_batch = n_batch
        cparams.n_threads = n_threads
        cparams.n_threads_batch = n_threads_batch
        cparams.rope_freq_base = (
            rope_freq_base if rope_freq_base != 0.0 else 0
        )
        cparams.rope_freq_scale = (
            rope_freq_scale if rope_freq_scale != 0.0 else 0
        )
        cparams.mul_mat_q = mul_mat_q
        cparams.f16_kv = f16_kv
        cparams.logits_all = logits_all
        cparams.embedding = embedding
        return cparams

    @classmethod
    def factory(cls, model_path : str, model_file : str, **kwargs):
        """Create a new FlowEngine with the given parameters"""
        llama_cpp.llama_backend_init(numa=False)

        model_loc = os.path.join(model_path, model_file)

        mparams = cls.get_mparams(**kwargs)

        model = llama_cpp.llama_load_model_from_file(model_loc.encode('utf-8'), mparams)

        cparams = cls.get_cparams(**kwargs)

        ctx = llama_cpp.llama_new_context_with_model(model, cparams)
        return cls(model=model, ctx=ctx, n_ctx=cparams.n_ctx)
    
    def __init__(self, model : c_void_p, ctx : c_void_p, n_ctx : int = 4096):
        self.model = model
        self.ctx = ctx
        self.n_ctx = n_ctx
        self.n_past = 0
        self.last_n_size = 64
        self.last_n_tokens_data = [0] * self.last_n_size

    def reset(self, **kwargs):
        self.last_n_tokens_data = [0] * self.last_n_size
        self.n_past = 0

    def feed(self, prompt : str, n_batch : int = 512, reset : bool = False, n_ctx : int = 4096, **kwargs):
        """Feed the given prompt to the model"""
        kwargs['n_ctx'] = n_ctx
        if reset:
            self.reset()
        b_prompt = prompt.encode('ascii', 'ignore')
        b_prompt = b" " + b_prompt
        pl = len(b_prompt)
        logger.debug(f"Feeding ({pl}): {b_prompt}")

        embd_inp = (llama_cpp.llama_token * n_ctx)()
        n_of_tok = llama_cpp.llama_tokenize(self.model, b_prompt, pl, embd_inp, embd_inp._length_, True)
        #logger.info(f"tokens: {n_of_tok} embeddings: {embd_inp._length_}")
        embd_inp = embd_inp[:n_of_tok]

        input_consumed = 0
        embd = []

        while len(embd_inp) > input_consumed:
            while len(embd_inp) > input_consumed:
                if len(embd) >= n_batch:
                    break

                embd.append(embd_inp[input_consumed])
                self.last_n_tokens_data = self.last_n_tokens_data[1:] + [embd_inp[input_consumed]]
                input_consumed += 1
                
            if len(embd) > 0:
                # Docs say to use llama_decode and llama_batch
                tokens = (llama_cpp.llama_token * len(embd))(*embd)
                return_code = llama_cpp.llama_eval(ctx=self.ctx, tokens=tokens, n_tokens=len(embd), n_past=self.n_past)
                if return_code != 0:
                    logger.error(f"Break - Model Eval return code {return_code}")
                    break
                
                self.n_past += len(embd)
                embd = []

    def read(self, max_tokens : int = 512, abort_tokens : list = [], stop_tokens : list = [],
              log_chunk_length : int = 25, n_temp: float = 0.7, **kwargs):
        """Read from the model until the given number of tokens is reached"""
        remaining_tokens = max_tokens
        last_n_repeat = 64
        repeat_penalty = 1.08
        frequency_penalty = 0.0
        presence_penalty = 0.0
        stop_set = set(stop_tokens)
        abort_set = set(abort_tokens)

        response_tokens = []
        n_generated = 0

        buf = (c_char * 32)()
        log_chunks = []
        last_piece = ''

        while remaining_tokens > 0:
            logits = llama_cpp.llama_get_logits(self.ctx)
            n_vocab = llama_cpp.llama_n_vocab(self.model)

            _arr = (llama_cpp.llama_token_data * n_vocab)(*[
                llama_cpp.llama_token_data(token_id, logits[token_id], 0.0)
                for token_id in range(n_vocab)
            ])
            candidates_p = pointer(llama_cpp.llama_token_data_array(_arr, len(_arr), False))

            _arr = (llama_cpp.c_int * len(self.last_n_tokens_data))(*self.last_n_tokens_data)
            llama_cpp.llama_sample_repetition_penalty(self.ctx, candidates_p,_arr, last_n_repeat, repeat_penalty)
            llama_cpp.llama_sample_frequency_and_presence_penalties(self.ctx, candidates_p, _arr, last_n_repeat, frequency_penalty, presence_penalty)
            llama_cpp.llama_sample_top_k(self.ctx, candidates_p, k=40, min_keep=1)
            llama_cpp.llama_sample_top_p(self.ctx, candidates_p, p=0.8, min_keep=1)
            llama_cpp.llama_sample_temperature(self.ctx, candidates_p, temp=n_temp)
            id = llama_cpp.llama_sample_token(self.ctx, candidates_p)

            self.last_n_tokens_data = self.last_n_tokens_data[1:] + [id]
            n = llama_cpp.llama_token_to_piece(
                self.model, llama_cpp.llama_token(id), buf, 32
            )
            piece = buf[:n].decode('utf-8', 'ignore')
            running = True
            if piece in abort_set:
                logger.info(f"Break ({len(log_chunks)}): Aborting on {piece} ({id})")
                running = False
                # TODO Do I need to inject a newline in-context here?
                id = 13
            elif piece == '\n' and last_piece == '\n':
                logger.info(f"Break ({len(log_chunks)}): Double Newline ({id})")
                running = False
                id = None
            elif id == llama_cpp.llama_token_eos(self.ctx):
                logger.info(f"Break ({len(log_chunks)}): EOS ({id})")
                running = False
                # TODO Do I need to inject a newline in-context here?
                id = 13
            if id is not None:
                # Docs say to use llama_decode and llama_batch
                tokens = (llama_cpp.llama_token * 1)(id)
                return_code = llama_cpp.llama_eval(ctx=self.ctx, tokens=tokens, n_tokens=1, n_past=self.n_past)
                log_chunks.append(piece)
                if return_code != 0:
                    logger.error(f"Break - Model Eval return code {return_code}")
                    running = False
                else:
                    self.n_past += 1
                    n_generated += 1

                response_tokens.append(piece)
                remaining_tokens -= 1
                last_piece = piece

            if piece in stop_set:
                running = False

            if len(log_chunks) > 0 and (not running or len(log_chunks) % log_chunk_length == 0):
                logger.info(f"Generated ({n_generated}): {''.join(log_chunks).strip()}")
                log_chunks = []

            if not running:
                break


        return response_tokens

    def __del__(self):
        llama_cpp.llama_free(self.ctx)
