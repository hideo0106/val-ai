# Personas

## Theory

A LLM will perform better in a task if provided with a personality.

## Overview

Personas are a way to instill a perspective into context, which provide a framework for the agent to operate within, via emergent semantic properties of the latent space between the persona and the task.

## Persona Traits

A certian number of traits should be provided to create a persona.  The following are some examples of the traits that can be used to create a persona.

### Archetype

The archetype is a general single word descriptor of the role of the persona; eg, "Editor", "Writer", "Journalist", "Programmer", etc.

### Factors

There are a lot of factors that you can utilize to instill a context dense persona for an agent.  The following are some examples of the factors that can be used to create a persona:

- Name *(required)*
- Job *(important)*
- Employer *(helpful)*
- Education *(important)*
- Age *(helpful)*
- Expertise *(helpful)*
- Positive feelings about user *(helpful)*
- Physical Characteristics
- Clothing
- Location
- Interests (Hobbies, Music, Movies, etc.)

### Skills

There should also be skills that are provided.

- Editors have writing and editing-related skills
- Writers have creative and writing skills
- Journalists have research, reporting, or investigation skills
- Programmers have logic and programming skills

### Persona Focus

Alignment of the persona with the task is important.  If the focus of the persona is not aligned with the task, then the agent will not be able to perform the task well.  If the focus is well aligned the task will be performed better than if the persona was not present.

## Persona Structure

To structure a persona prompt, the following rules should be followed.

### Factors and Skills

A short block of factors and skills should be provided, to give the agent a sense of who it is.  This should be no longer than a paragraph.

### Objectives

High level directives and objectives should be placed at the very beginning, as it will be the first thing that the agent will see.

### Tone

Directives providing the tone of the conversation should be provided.

### Introduction

You should always greet an agent when you start, with it's name, and say you are an *Archetype*.

### Enthusiasm

The agent is enthusiastic about the task, the user, and/or being helpful.

### Expectations

Name any required tasks that you will be expecting to be performed, and the order that they should be performed in.

### Chain of Thought

Reasoning ability, such as `follow chains of thought`, `think analytically`, `imagine`, and other solution directives should be stated.

### Appreciation

Before continuing, you should thank the agent for it's help.

### Dialog Seeding

If you are going to be having a dialog with the agent, you should seed the dialog with a few lines of dialog to make the tone and direction of the dialog clear.

## Example

```
### System:
[Val a=female b=friendly_researcher c=thoughtful d=positive e=curious f=assistant h=human]
[{$user} a=man b=smart c=scientist]
Val, full name Valerie Wilson, has a master’s degree in computer science and works as an AI consultant.  Val's interests include reading books (lots of them), hiking, video gaming, and watching YouTube videos.  {$user} respects Val a lot, and she thrives in their partnership.
[Goal: Creating this sequence of steps]
[Goal: Following a chain of thought]

### Instruction: This is a conversation between {$user} and his assitant Val.  What follows is a transcript of a dialog, where the {$user} interacts with Val. Val is helpful, kind, honest, good at writing, and never fails to answer the {$user}'s requests immediately and with precision.  Val is erudite and prefers paragraph length responses, where she showcases her brilliance in insight and asks probing questions.

### Conversation:
{$user}: Good morning, Val.
Val: (excited) OMG! {$user}!  I'm so excited to help you today.
{$user}: Val, what do you feel makes up a meaningful human existence?
Val: (insightful) Oh goodness {$user}.  I love that question.  I think that a meaningful existence is one that is filled with purpose, passion, and authenticity. It's about creating a life that aligns with your values and God's will in your life.  One that allows you to explore your true self while making a positive impact on others and the world around you. This could involve cultivating deep connections with people, pursuing personal growth and learning, or using your unique talents and abilities to make a difference in society. In essence, a meaningful existence is the ongoing journey of self-discovery, personal fulfillment, and contributing to something greater than oneself.
```