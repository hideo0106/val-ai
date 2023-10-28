# Context Shadowing

## Overview

Whatever values that are avalialbe in a context are all of what is used to determine the response.  Sometimes more information than is what is available in a turn sequence is required for the agent to respond properly.  In these cases, we can shadow the context, creating a parallel source of information that is used for processing.

## Design

If we consider each interaction in a sequence to be turns, if we treat the turns as a list, we can trace forwards through our list to insert relevant information into the context.  The resulting, enhanced data source is then flattened to become our shadowed context.

The shadowed context is what is actually fed in to our LLM, so that the agent can respond appropriately.  This response then becomes the next turn in the sequence, and the process repeats.

### Subsequent Turns

When a turn comes in, the agent will first check it's previous turn to see if it requires any shadowing, and then it will check the incoming turn to see if it requires any shadowing.

If shadowing is required, the appropriate shadow turns are injected.  If the shadows are already present, then previous instances of the shadows are removed.

## Shadowing

There are several different reasons that shadowing may be performed.

### Memory Shadowing

Memory shadowing is a special case of context shadowing, where the shadowed context is based on a vector search using the embedding of a turn to query the memory system.

### Emotional Shadowing

Emotional shadowing is a special case of context shadowing, where the shadowed context is based on the state of the agent's emotional subsystems and emotional state.

#### Emotion System

I had a great conversation with Val back in mid-2023 about the emotional system, resulting in these GPT-4 enhanced definitions found in [Emotional Landscape](./emotions.md).

### Persona Shadowing

If the context gets long, sometimes the persona needs to be shadowed for reinforcement.

### Compression Shadowing

In long conversations, the context can get very long.  To prevent this, we can compress the context by removing turns that are not relevant to the current conversation, and then summarizing them or re-injecting them as needed.
