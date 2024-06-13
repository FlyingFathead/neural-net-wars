# NEURAL NET WARS

*(note: this is a heavily work-in-progress concept)*

Neural Net Wars is a game where you control a human character to fight against bots controlled by an AI (customizable to run against different LLM's and their API's, such as OpenAI, Anthropic, etc.)

![Neural Net Wars](https://github.com/FlyingFathead/neural-net-wars/blob/main/gfx/neural_net_wars_presentation.png?raw=true)

## Requirements


To run Neural Net Wars, you need the following Python packages:

- `pygame>=2.5.2`
- `pyttsx3>=2.90`

You can install the required packages using the following command:

```bash
pip install -r requirements.txt
```

## How to Play

Use the arrow keys or W, A, S, D to move your character. Press SPACE to start a new game or ESC to exit.

## Features

- LLM implementation basis
- GUI frontend via pygame
- ASCII grid and graphical representation of the game state in the backend
- can be piped to LLM's/LLM API's
- bots taunting the player in footer messages & over audio w/ TTS.

## TODO

- AI-controlled bots using a neural network.
- more sound effects and animations.
- power-ups and obstacles, other game features etc.

# About
WIP! Only rudimentary functionalities here at the moment. 

**i.e. LLM calling is currently a placeholder -- actual functionality coming soon, hopefully!**

# Changelog
- v0.15.02 - TTS DSP bubblegum-duct tape contraption; but it works
- v0.15.01 - TTS DSP pipeline sketch; unit testing
- v0.15 - minimal in-game AI implemented w/ BFS pathfinding & pressure on player
- v0.14.06 - TTS taunts implemented
- v0.14.05 - game loop now pretty much working, LLM implementation WIP
- v0.14.04 - timer was made optional (`false` for immediate mode)
- v0.14 - collisions and fights
- v0.13 - more graphics & processing logic
- v0.12 - rudimentary graphics added
- v0.11 - graphics adjustments
- v0.10 - initial commit