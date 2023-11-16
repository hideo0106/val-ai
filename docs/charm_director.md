# The Director

The Director is who organizes a scene to keep things under control.

## The Scene

A scene is a place where the action happens. It can be a room, a building, a forest, etc.  It contains the props and the actors.  There are objectives that can be achieved in a scene, based on the global objectives of the story.

## The Props

Props are the objects which are generated at the beginning of or while in a scene.  They can be used by the actors in a scene.

## The Actors

Actors are the characters that are in a scene.

## The Objectives

The objectives are the goals that the actors can achieve in a scene.  They are based on the global objectives of the story.

## The Action

The action is what the actors do in a scene.  It is based on the objectives of the scene, and the characters personalities.

## Turns

The Director is the arbiter of who's turn it currently is, making sure that all actors get a chance to act, but also that the action is not interrupted by other actors.

A conversation has a flow to it, and certian stages.

## Math

- Actors each have a personality vector, creating matrix A.
- There is a matrix R (relationship) that defines the relationship between two actors.
- There is a matrix I (item) that defines an actor's interest in a prop.
- There is a matrix G (goals) that defines an actor's interest in an objective.
- There is a matrix U (usefulness) that defines a prop's usefulness in achieving an objective.
- Objectives each have a difficulty and a progress, creating vectors d and p, and matrices D and P.

When a scene is entered, the Director will generate the props and objectives for the scene.  The Director will then generate the actors for the scene, and assign them to the scene.  The Director will then generate the relationships between the actors, and the interests in the props and objectives.

## Flow

The flow of a conversation is as follows:
- Opening: Most conversations start with some form of opening greeting or introduction. This establishes the roles of the participants and readiness to engage.
- Purpose: There is usually an overall purpose or objective that drives the conversation. This could be exchanging information, making a request, solving a problem, building rapport, etc.
- Topic Introduction: One or both parties introduce a topic they want to discuss. This provides focus and frames the ensuing discourse.
- Information Exchange: Participants take turns sharing information relevant to the topic. This includes asking and answering questions, elaborating, clarifying, etc.
- Feedback: People provide verbal and non-verbal feedback as the conversation progresses, signaling understanding, agreement, confusion, etc.
- Wrap-up: As the conversation concludes, people summarize key points and highlight conclusions or decisions made.
- Closing: The conversation draws to a close with some form of parting words, farewells, and a transition out of the discussion.


Here is a proposed conversation flow matrix representing different stages of a conversation and influencing factors:

| Stage | Purpose | Topic | Tone | Turn-taking | Active Listening |
|-|-|-|-|-|-|
| Opening | Establish contact and willingness to engage | N/A | Positive, welcoming | Brief turns to greet and introduce | Attentive to greeting |
| Information Exchange | Share, gather, clarify info | Introduce new topics organically | Engaged, cooperative | Balanced participation | Engaged, reflective |  
| Feedback | Check understanding, agreement | N/A | Supportive, constructive | Short turns to confirm | Reflective, summarizing |
| Wrap-Up | Synthesize discussion | Summarize key topics | Evaluative, decisive | Longer turns to conclude | Reflective, highlighting key points |
| Closing | End discussion and disengage | N/A | Appreciative, grateful | Brief turns to close | Attentive to farewells |

The stages move from opening to closing. Purpose describes goals for each stage. Topics emerge organically in the middle stages. Tone conveys attitude and emotions. Turn-taking refers to the balance of participation. Active listening describes how people should listen. This matrix aims to capture core elements that influence conversation flow. Let me know if you would like me to elaborate on any part of this matrix.