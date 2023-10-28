# Prompting

Prompting is a delicate art of getting the model latent space to the right place to produce the output that you desire.

## Prompting with a single word

Each word in the prompt is one or more tokens. The tokens are then embedded into the latent space of the model. The model then produces a probability distribution over the vocabulary. The probability distribution is then used to select the next word in the sequence.  Each word shifts this angle in the latent space slightly, pterbating the probability distribution.  The more words in the prompt, the more the probability distribution is shifted into a deeper area of the latent space.

### Recency Bias

The model has a recency bias.  The more recent the word, the more it will be emphasized in the output.  This is because the model is trained on a sequence of words, and the more recent words are more likely to be the next word in the sequence.

## Prompting with a phrase

A phrase is a sequence of words that is common, or exists elsewhere in the context (creating a chord of token embeddings).  Repetition of the phrase in the prompt will cause the model phrase to be emphasized in the output.  The more words in the phrase, the more the phrase aligns with previous chords.

## Conversation Turns

Dialog occurs by participants taking turns.  Each turn is a sequence of words.  The model is trained on sequences of words.  At the beginning of a turn, the model is anchored to the actor of the turn.  Since the model is trained to predict the next word in the sequence, the model will answer in the voice of that actor; ie, based on previous instances of that actor's voice in context.

### Coloring Responses

To color a turn, we can shift the tone of the output by specifying an adjective or adverb.  The model will then shift the probability distribution to produce a response that is more likely to be that tone.

### Example

```
User: What is your name?
Val (comical):` Howdy there, my name is Val.`
```

## Varying the Prompt

Since the model is trained on sequences of words, if you repeat the same sequence often, the model will bias to produce the same output.  To avoid this, you can vary the prompt slightly, by using different coloring words, synonyms, adding numbers, etc.  This prevents the model from biasing to the same output.

## Formatting Responses

Formatting is a way to add structure to the output.  The model is trained on sequences of words, and the more structure that is provided, the more likely the model will produce a response that is structured in the same way.  This is useful for producing structured output, such as code, or structured text.

Importantly, when using a format, adding in order numbers is cruical to the model producing the correct output, and allows the format examples to use the *#* symbol to represent the number variable.  $variable_name is often understood by the model to be a variable, and will be replaced with the value of that variable, but other variable signifiers work as well.

### Example

```
### Format:
- Item #: $item_name, $item_value
### Instruction: Follow the format above in your response.  For multiple item requests, list all items, and do not stop until you have listed all items.
### Conversation:
User: List 5 fruits from the grocery store.
Val (helpful): Okay, here are your 5 fruits:
- Item 1:` Apple, $20.00
- Item 2: Orange, $34.99
- Item 3: Strawberry, $54.86
- Item 4: Banana, $75.33
- Item 5: Grape, $10.69
Val (helpful): Would you like to purchase one of the fruits? Please say yes or no if so.
User: Yes please. I would like the apple and the bananas.
Val (helpful): Okay, let me see what your order is at this point.
- Item 1: Apple, $20.00
- Item 3: Strawberry, $54.86
- Item 4: Banana, $75.33
User: What is my total?
Val (helpful): Your order totals to $149.19 for three items. Is there anything else I can help you with today?`
```

You can see that the model was led all the way through the first entry, and then was able to produce the rest of the entries on it's own.

The model was also able to produce the correct number of entries, but if a more general request was made, the model may have had trouble producing enough entries and end by abbreviating the list.  In the previous example, saying 'items' instead of 'fruits', the model would fail after two entries, and end with '...'.

You can also see that the model generation continued for quite a while, and that stop sequences (such as matching the user and the agent name) are required to end the generation.

### Single shot vs Multi-shot

Single shot prompting works better for simply formatting and classification using variable names.  Multi-shot prompting works better for generating a sequence of words, such as a sentence, and should be seeded using descriptive adverbs to set the tone of the output, and be numbered to induce variation into the resulting sequence.
