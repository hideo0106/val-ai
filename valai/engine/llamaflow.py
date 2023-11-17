# valai/llamaflow.py

from ctypes import c_float, c_size_t, c_void_p, c_char, c_int, c_uint8, c_int8, c_int32, pointer, byref
import logging
import os
import multiprocessing
from typing import Any, List, Optional, Dict
import llama_cpp

from .output import OutputHandler

logger = logging.getLogger(__name__)

class EngineException(Exception):
    """An exception for errors in the FlowEngine class"""
    def __init__(self, message, tokens):
        super().__init__(message)
        self.tokens = tokens

"""
void llama_batch_clear(struct llama_batch & batch) {
    batch.n_tokens = 0;
}

void llama_batch_add(
                 struct llama_batch & batch,
                        llama_token   id,
                          llama_pos   pos,
    const std::vector<llama_seq_id> & seq_ids,
                               bool   logits) {
    batch.token   [batch.n_tokens] = id;
    batch.pos     [batch.n_tokens] = pos,
    batch.n_seq_id[batch.n_tokens] = seq_ids.size();
    for (size_t i = 0; i < seq_ids.size(); ++i) {
        batch.seq_id[batch.n_tokens][i] = seq_ids[i];
    }
    batch.logits  [batch.n_tokens] = logits;

    batch.n_tokens++;
}
"""

def llama_batch_clear(batch : llama_cpp.llama_batch):
    batch.n_tokens = 0

def llama_batch_add(batch : llama_cpp.llama_batch, id : int, pos : int, seq_ids : list[int], logits : int):
    batch.token[batch.n_tokens] = c_int32(id)
    batch.pos[batch.n_tokens] = c_int32(pos)
    batch.n_seq_id[batch.n_tokens] = c_int32(len(seq_ids))
    #for i in range(len(seq_ids)):
    #    batch.seq_id[batch.n_tokens][i] = c_int32(seq_ids[i])
    #batch.logits[batch.n_tokens] = c_int8(logits)

    batch.n_tokens += 1

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
    def from_config(cls, model_path : str, model_file : str, n_ctx : int, output : Optional[OutputHandler] = None, **kwargs):
        """Create a new FlowEngine with the given parameters"""
        llama_cpp.llama_backend_init(numa=False)

        model_loc = os.path.join(model_path, model_file)

        mparams = cls.get_mparams(**kwargs)

        model = llama_cpp.llama_load_model_from_file(model_loc.encode('utf-8'), mparams)

        cparams = cls.get_cparams(n_ctx=n_ctx, **kwargs)

        ctx = llama_cpp.llama_new_context_with_model(model, cparams)
        return cls(model=model, ctx=ctx, n_ctx=n_ctx, output=output)
    
    def __init__(self, model : c_void_p, ctx : c_void_p, n_ctx : int, output : Optional[OutputHandler] = None):
        self.model = model
        self.output = output
        self.ctx : llama_cpp.llama_context_p = ctx
        self.n_ctx = n_ctx
        self.n_past = 0
        self.n_prev =  0
        self.last_n_size = 64
        self.last_n_tokens_data = [0] * self.last_n_size
        self.session_tokens: List[llama_cpp.llama_token] = []
        self.systems : Dict[str, str] = {}
        self.n_system : Dict[str, int] = {}
        self.system_tokens : Dict[str, List[llama_cpp.llama_token]] = {}
        self.current_system : Optional[str] = None

    def set_output_handler(self, output : OutputHandler):
        self.output = output
    
    def load_context(self, save_file : str, **kwargs) -> int:
        if not os.path.exists(save_file):
            logger.info(f"Error: {save_file} does not exist")
            return -1

        # Load state from file
        state_size = llama_cpp.llama_get_state_size(self.ctx)
        logger.debug(f"Context: State size: {state_size}")
        state_mem = (c_uint8 * state_size)()

        with open(save_file, "rb") as fp_read:
            bytes_read = fp_read.readinto(state_mem)
            logger.debug(f"Context: Read {bytes_read} {state_size} bytes from {save_file}")
            if bytes_read != state_size:
                logger.error("Error: failed to read state")
                return -1

        rc = llama_cpp.llama_set_state_data(self.ctx, state_mem)

        return rc

    def save_context(self, save_file : str = 'local/game.context.dat', **kwargs) -> int:
        if len(self.session_tokens) > 0:
            state_size = llama_cpp.llama_get_state_size(self.ctx)
            state_mem = (c_uint8 * state_size)()

            rc = llama_cpp.llama_copy_state_data(self.ctx, state_mem)
            if rc < 0:
                logger.error("Failed to copy state data")
                return rc

            # Save the data to a binary file
            with open(save_file, "wb") as fp:
                fp.write(state_mem)
        
            llama_cpp.llama_set_state_data(self.ctx, state_mem)

            return rc
        return 0
    
    def clear_saved_context(self, save_file : str = 'local/game.context.dat', **kwargs) -> int:
        """Delete our file"""
        if os.path.exists(save_file):
            os.remove(save_file)
            return 0
        return 1

    def token_clearance(self, new_tokens : int = 0, padding : int = 0, **kwargs) -> int:
        """Get the number of tokens remaining"""
        result = self.n_ctx - self.n_past - new_tokens - padding
        logger.debug(f"Token Clearance: {self.n_ctx} - {self.n_past} - {new_tokens} - {padding} = {result}")
        return result

    def reset(self, system : bool = True, **kwargs):
        self.last_n_tokens_data = [0] * self.last_n_size
        self.session_tokens = []
        self.prev_tokens = []
        self.n_past = 0
        self.n_prev = 0
        if system:
            self.n_system = {}
            self.system_tokens = {}
            self.systems = {}
            self.current_system = None
        
    def set_checkpoint(self, checkpoint : str, **kwargs) -> bool:
        """Set a checkpoint for the current state"""
        return self.save_context(save_file=f"local/{checkpoint}.context.dat", **kwargs)

    def execute(self, prompt : str, retry : bool = False, scope : Optional[str] = None, checkpoint : Optional[str] = None, **kwargs) -> int:
        """Execute the given prompt with the model"""

        self.prev_tokens = self.session_tokens.copy()
        self.n_prev = self.n_past
        if checkpoint is not None:
            self.set_checkpoint(checkpoint=checkpoint, **kwargs)

        rc = self.feed(prompt=prompt, scope=scope, **kwargs)
        return rc

    def reload_turn(self, checkpoint : str = 'turn', **kwargs) -> int:
        """Reset our turn data"""
        rc = self.load_context(save_file=f"local/{checkpoint}.context.dat", **kwargs)
        if rc >= 0:
            logger.info(f"Using previous {checkpoint} context")
            self.session_tokens = self.system_tokens.get(checkpoint, []).copy()
            self.n_past = self.n_system.get(checkpoint, 0)

            self.prev_tokens = self.session_tokens.copy()
            self.n_prev = self.n_past
        return rc

    def set_context(self, system_context : str, prompt : str, **kwargs) -> int:
        self.systems[system_context] = prompt
        logger.debug(f"Set system {system_context}")

    def prepare(self, system_context : str, restart : bool = True, **kwargs) -> int:
        """
        Execute the given system prompt
        system: The system prompt to execute.  If the system has changed, we will reset the model
        restart: If true, we will reset the model and start from the beginning
        """

        logger.debug(f"Preparing system {system_context}")

        if system_context not in self.systems:
            logger.error(f"System {system_context} not found: {','.join(self.systems.keys())}")
            return -1

        system = self.systems[system_context]

        if restart:
            self.reset(system=False, **kwargs)
            if len(system) > 0:
                rc = self.feed(prompt=system, scope=system_context, show_progress=True, **kwargs)
                if rc < 0:
                    logger.error("Failed to feed system prompt")
                    return rc
                self.n_system[system_context] = self.n_past
                self.system_tokens[system_context] = self.session_tokens.copy()
            rc = self.save_context(**kwargs)
            if rc < 0:
                logger.error("Failed to save our context")
                return rc
        else:
            # Load our saved system
            rc = self.load_context(save_file=f"local/game.context.dat", **kwargs)
            if rc < 0:
                logger.error("Failed to load our context")
                return rc
            self.n_past = self.n_system.get(system_context, 0)
            self.session_tokens = self.system_tokens.get(system_context, []).copy()

        self.prev_tokens = self.session_tokens.copy()
        self.n_prev = self.n_past
        self.current_system = system_context
        return rc

    def feed(self, prompt : str, n_batch : int, n_ctx : int, scope : Optional[str] = None, show_progress : bool = False, **kwargs) -> int:
        """Feed the given prompt to the model"""
        if prompt is None:
            logger.warning(f"Feeding empty prompt")
            return -1
        kwargs['n_ctx'] = n_ctx
        b_prompt = prompt.encode('ascii', 'ignore')
        b_prompt = b" " + b_prompt
        pl = len(b_prompt)

        # I hate that we alloc all of this extra space, but otherwise we overrun our buffer
        embd_inp = (llama_cpp.llama_token * (pl + 1))()
        n_of_tok = llama_cpp.llama_tokenize(
            model=self.model, text=b_prompt, text_len=pl, tokens=embd_inp, n_max_tokens=embd_inp._length_,
            add_bos=True, special=False)

        embd_inp = embd_inp[:n_of_tok]

        clearance = self.token_clearance(n_of_tok, 100)
        if clearance < 0:
            raise EngineException("Too many tokens in prompt", clearance)

        # This is a hack to make sure we don't overrun our buffer
        # Lets create an offset that clips to the last n_ctx - 100 tokens
        n_ctx_floor = n_ctx - 100
        n_ctx_floor = n_ctx_floor if n_of_tok > n_ctx_floor else n_of_tok
        embd_inp = embd_inp[-n_ctx_floor:]

        input_consumed = 0

        first_n = self.n_past
        logger.debug(f"Feeding ({pl} chars -> {n_of_tok} tokens), {input_consumed} consumed, {len(embd_inp)} remaining")
        logger.debug(f"```{prompt}```")
        if self.output is not None and show_progress:
            if scope is not None:
                self.output.handle_token(f"{scope} - ")
            self.output.handle_progress(0.0)

        if True:
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
                    logger.debug(f"Writing to model {len(embd)} tokens, {input_consumed} consumed")
                    return_code = llama_cpp.llama_eval(ctx=self.ctx, tokens=tokens, n_tokens=len(embd), n_past=self.n_past)
                    if return_code != 0:
                        logger.error(f"Break - Model Eval return code {return_code}")
                        break
                    
                    self.session_tokens += tokens
                    self.n_past += len(embd)
                    embd = []
                    if self.output is not None and show_progress:
                        self.output.handle_progress(float(input_consumed) / len(embd_inp))
        else:
            # TODO this is from the master branch of llama-cpp-python, so beware on 0.2.11
            embed_size = len(embd_inp)
            batch_size = min(n_batch, embed_size)
            llama_batch = llama_cpp.llama_batch_init(c_int32(batch_size), 0, c_int32(1))
            #llama_batch = llama_cpp.llama_batch_init(c_int32(n_batch), 0, c_int32(n_batch))
            batch_ix = 0

            while embed_size > input_consumed:
                while embed_size > input_consumed:
                    if batch_ix >= batch_size:
                        break

                    llama_batch_add(batch=llama_batch, id=embd_inp[input_consumed], pos=batch_ix, seq_ids=[], logits=False)

                    self.last_n_tokens_data = self.last_n_tokens_data[1:] + [embd_inp[input_consumed]]
                    input_consumed += 1
                    batch_ix += 1

                if batch_ix > 0:
                    # Docs say to use llama_decode and llama_batch
                    #tokens = (llama_cpp.llama_token * len(embd))(*embd)
                    logger.debug(f"Writing to model {batch_ix} tokens")
                    llama_batch.logits[llama_batch.n_tokens - 1] = True
                    #return_code = llama_cpp.llama_eval(ctx=self.ctx, tokens=tokens, n_tokens=len(embd), n_past=self.n_past)
                    rc = llama_cpp.llama_decode(self.ctx, llama_batch)
                    if rc != 0:
                        logger.error(f"Break - Model Decode return code {rc}")
                        break
                    
                    self.n_past += llama_batch.n_tokens
                    self.session_tokens += llama_batch.token[:llama_batch.n_tokens]
                    batch_ix = 0
                    llama_batch_clear(llama_batch)

            llama_cpp.llama_batch_free(llama_batch)


        return self.n_past - first_n

    def read(self, max_tokens : int = 512, abort_tokens : list = [], stop_tokens : list = [],
              sequence_tokens : list = [], log_chunk_length : int = 25, n_temp: float = 0.7,
              mirostat: int = 0, mirostat_tau : float = 0, mirostat_eta : float = 0, top_k: int = 40,
              n_tfs_z: float = 0.0, n_typical_p: float = 0.0, n_top_p: float = 0.0,
                **kwargs) -> Optional[List[Any]]:
        """Read from the model until the given number of tokens is reached"""
        remaining_tokens = max_tokens
        last_n_repeat = 64
        repeat_penalty = 1.08
        frequency_penalty = 0.0
        presence_penalty = 0.0
        stop_set = set(stop_tokens)
        abort_set = set(abort_tokens)
        sequence_set = set([tuple(o) for o in sequence_tokens])

        response_tokens = []
        n_generated = 0

        buf = (c_char * 32)()
        log_chunks = []
        last_piece = ''
        last_id = 0

        try:
            while remaining_tokens > 0:
                logits = llama_cpp.llama_get_logits(self.ctx)
                n_vocab = llama_cpp.llama_n_vocab(self.model)

                _arr = (llama_cpp.llama_token_data * n_vocab)(*[
                    llama_cpp.llama_token_data(token_id, logits[token_id], 0.0)
                    for token_id in range(n_vocab)
                ])
                candidates_p = pointer(llama_cpp.llama_token_data_array(_arr, len(_arr), False))

                _arr = (c_int * len(self.last_n_tokens_data))(*self.last_n_tokens_data)
                llama_cpp.llama_sample_repetition_penalties(ctx=self.ctx, candidates=candidates_p, last_tokens_data=_arr, 
                                            penalty_last_n=c_size_t(last_n_repeat), penalty_repeat=c_float(repeat_penalty),
                                            penalty_freq=c_float(frequency_penalty), penalty_present=c_float(presence_penalty))
                if mirostat == 1:
                    mirostat_mu = 2.0 * mirostat_tau
                    mirostat_m = 100
                    llama_cpp.llama_sample_temperature(ctx=self.ctx, candidates=candidates_p, temp=c_float(n_temp))
                    id = llama_cpp.llama_sample_token_mirostat(ctx=self.ctx, candidates=candidates_p,
                        tau=c_float(mirostat_tau), eta=c_float(mirostat_eta), m=c_size_t(mirostat_m), mu=c_float(mirostat_mu))
                elif mirostat == 2:
                    mirostat_mu = 2.0 * mirostat_tau
                    llama_cpp.llama_sample_temperature(ctx=self.ctx, candidates=candidates_p, temp=c_float(n_temp))
                    id = llama_cpp.llama_sample_token_mirostat_v2(ctx=self.ctx, candidates=candidates_p,
                        tau=c_float(mirostat_tau), eta=c_float(mirostat_eta), mu=c_float(mirostat_mu))
                else:
                    # Temperature sampling
                    llama_cpp.llama_sample_top_k(ctx=self.ctx, candidates=candidates_p,
                                                 k=top_k, min_keep=c_size_t(1))
                    llama_cpp.llama_sample_tail_free(ctx=self.ctx, candidates=candidates_p,
                                                     z=c_float(n_tfs_z), min_keep=c_size_t(1))
                    llama_cpp.llama_sample_typical(ctx=self.ctx, candidates=candidates_p,
                                                   p=c_float(n_typical_p), min_keep=c_size_t(1))
                    llama_cpp.llama_sample_top_p(ctx=self.ctx, candidates=candidates_p,
                                                 p=c_float(n_top_p), min_keep=c_size_t(1))
                    llama_cpp.llama_sample_temperature(ctx=self.ctx, candidates=candidates_p, temp=c_float(n_temp))
                    id = llama_cpp.llama_sample_token(self.ctx, candidates_p)

                n = llama_cpp.llama_token_to_piece(
                    self.model, llama_cpp.llama_token(id), buf, 32
                )
                piece = buf[:n].decode('utf-8', 'ignore')

                self.last_n_tokens_data = self.last_n_tokens_data[1:] + [id]
                running = True
                if piece in abort_set:
                    logger.debug(f"Break ({len(log_chunks)}): Aborting on {piece} ({id})")
                    running = False
                    # TODO Do I need to inject a newline in-context here?
                    id = None
                    return None
                elif id == 2 and n_generated == 0:
                    # 2 is '', repeating, this is bad model output.
                    running = False
                    id = None
                    return None
                elif (last_piece, piece) in sequence_set:
                    logger.debug(f"Break ({len(log_chunks)}): sequence {last_piece}, {piece} ({id})")
                    running = False
                    id = None
                elif piece == '\n' and last_piece == '\n':
                    logger.debug(f"Break ({len(log_chunks)}): Double Newline ({id})")
                    running = False
                    id = None
                elif id == llama_cpp.llama_token_eos(self.ctx):
                    logger.debug(f"Break ({len(log_chunks)}): EOS ({id})")
                    running = False
                    # TODO Do I need to inject a newline in-context here?
                    id = 13

                if id is not None:
                    #tokens = (llama_cpp.llama_token * 1)(id)
                    #return_code = llama_cpp.llama_decode(ctx=self.ctx, batch=llama_cpp.llama_batch_get_one(tokens=tokens, n_tokens=1, pos_0=self.n_past, seq_id=0))

                    tokens = (llama_cpp.llama_token * 1)(id)
                    return_code = llama_cpp.llama_eval(ctx=self.ctx, tokens=tokens, n_tokens=1, n_past=self.n_past)
                    log_chunks.append(piece)
                    if return_code != 0:
                        logger.error(f"Break - Model Eval return code {return_code}")
                        running = False
                    else:
                        self.n_past += 1
                        n_generated += 1

                    self.session_tokens.append(id)
                    response_tokens.append(piece)
                    if self.output is not None:
                        self.output.handle_token(piece)
                    remaining_tokens -= 1
                    last_piece = piece
                    last_id = id

                if piece in stop_set:
                    running = False

                if len(log_chunks) > 0 and (not running or len(log_chunks) % log_chunk_length == 0):
                    logger.debug(f"Generated ({n_generated}): {''.join(log_chunks).strip()}")
                    #logger.debug(f"Tokens ({n_generated}): {log_chunks}")
                    log_chunks = []

                if not running:
                    break
        finally: 
            #llama_cpp.llama_batch_free(llama_batch)
            pass


        return response_tokens

    def __del__(self):
        llama_cpp.llama_free(self.ctx)

