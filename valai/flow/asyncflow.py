import asyncio
from ctypes import c_float, c_char, c_int, c_uint8, c_int32, c_size_t, pointer, c_void_p
import os
import llama_cpp
import logging
from typing import Any, List, Optional, Dict

from .llamaflow import FlowEngine
from .output import OutputHandler

logger = logging.getLogger(__name__)


class AsyncFlowEngine(FlowEngine):
    """
        FlowEngine is a wrapper around the llama_cpp library that provides a simple interface for reading and writing to the model
    """
    
    async def read(self, token_handler : OutputHandler,
                   max_tokens : int = 512, abort_tokens : list = [], stop_tokens : list = [],
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
                    await token_handler.handle_token(piece)

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
