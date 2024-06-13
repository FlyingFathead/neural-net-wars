# neural net wars 0.15.02 // 13. jun 2024
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# https://github.com/FlyingFathead/neural-net-wars/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# *** WIP! *** TODO:
#
# - in the timerless mode it's not following the moves correctly in the right side of the GUI; update issue?
# - maybe add laser gun / rocket shooting option; up, down, left right ...
# - gameplay balancing; i.e. medkits, gun drops ... (grenades? rocket launchers?)
# - overall hit/battle mechanics (odds+hp dmg etc)
# - health bar for HP
# - logging for battle logs (for LLM/model training)
# - tts more meaner (add DSP pipeline for the tts output [insane distortion, low cut, hi boost, pitch down])
# - options menu on GUI side
# - configfile etc.

import os
import pygame
import random
import pyttsx3
import asyncio
import threading
import subprocess
from collections import deque

# Initialize Pygame and load images
pygame.init()

def load_and_resize_image(file_path, size):
    try:
        image = pygame.image.load(file_path)
        return pygame.transform.scale(image, size)
    except pygame.error:
        return None

# Load and resize images
CELL_SIZE = 50
robot_image = load_and_resize_image("gfx/neural_net_wars_robot.png", (CELL_SIZE, CELL_SIZE))
human_image = load_and_resize_image("gfx/neural_net_wars_human.png", (CELL_SIZE, CELL_SIZE))
explosion_image = load_and_resize_image("gfx/neural_net_wars_explosion.png", (CELL_SIZE, CELL_SIZE))
human_senior_dmg_image = load_and_resize_image("gfx/neural_net_wars_human_senior_dmg.png", (CELL_SIZE, CELL_SIZE))
human_senior_fire_image = load_and_resize_image("gfx/neural_net_wars_human_senior_fire.png", (CELL_SIZE, CELL_SIZE))
human_senior_image = load_and_resize_image("gfx/neural_net_wars_human_senior.png", (CELL_SIZE, CELL_SIZE))

# Constants
DEFAULT_WIDTH = 12
DEFAULT_HEIGHT = 12
PLAYER_CHAR = '@'
EMPTY_CHAR = '.'
EXPLOSION_CHAR = 'X'  # Explosion indicator
# Constants for screen dimensions
STATS_HEIGHT = 60  # Additional height to accommodate stats display
STATS_WIDTH = 210  # Width for the stats display area
MIN_HEIGHT = 600  # Minimum height required for the window
MIN_STATS_WIDTH = STATS_WIDTH + 600  # Minimum width required for the window including stats

# Global Game State
width = DEFAULT_WIDTH
height = DEFAULT_HEIGHT
grid = [[EMPTY_CHAR for _ in range(width)] for _ in range(height)]
initial_bots = 10
initial_humans = 1
player_pos = [height - 1, width // 2]
bots = [{"id": i, "pos": [0, i * (width // initial_bots)]} for i in range(initial_bots)]
time_limit = 2  # Time limit for player move in seconds
action_display_time = 1  # Time to display the action message
game_over = False
wrap_around = True  # Option for wrapping around the screen
current_direction = "None"
selected_direction = "None"
human_count = initial_humans
bot_count = initial_bots
display_action_message = False  # Flag to display the action message
last_direction = "None"
lock_movement = False
player_hitpoints = 10
bot_hitpoints = [3 for _ in range(initial_bots)]
hit_chance = 0.5  # 50% chance to hit
fight_mode = False  # Flag to indicate if a fight is happening
current_fight_bot = None  # Track the current bot being fought
game_started = False  # Track if the game has started
time_left = time_limit  # Initialize the timer
footer_message = ""  # Footer message for additional information
use_timer = False  # Flag to determine if the timer should be used
end_game_message = ""  # Message displayed at the end of the game

taunts = [
    "You can't beat us!",
    "Prepare to be terminated!",
    "Is that all you've got?",
    "You're no match for us!",
    "We will destroy you!"
]

# text-to-speech
# Run TTS taunt as a subprocess with DSP
def play_taunt(taunt):
    try:
        python_executable = '/usr/bin/python3'  # Replace this with the actual path to your Python interpreter
        script_path = os.path.join(os.path.dirname(__file__), 'tts_playback.py')
        subprocess.Popen([python_executable, script_path, taunt])
    except Exception as e:
        print(f"Error playing taunt: {e}")

async def taunt_player():
    taunt = random.choice(taunts)
    global footer_message
    footer_message = taunt
    play_taunt(taunt)

# Calculate necessary screen width
grid_width = width * CELL_SIZE
total_width = max(grid_width + STATS_WIDTH, MIN_STATS_WIDTH)  # Ensure the screen is at least as wide as MIN_STATS_WIDTH

# Calculate necessary screen height
grid_height = height * CELL_SIZE + STATS_HEIGHT
total_height = max(grid_height, MIN_HEIGHT)  # Ensure the screen is at least as tall as MIN_HEIGHT

# Initialize Pygame
try:
    pygame.init()
    screen = pygame.display.set_mode((total_width, total_height))
    pygame.display.set_caption("Neural Net Wars")
except Exception as e:
    print(f"Error initializing Pygame: {e}")
    game_over = True

font = pygame.font.Font(None, 36)
clock = pygame.time.Clock()

def draw_grid():
    screen.fill((0, 0, 0))
    for y in range(height):
        for x in range(width):
            rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            if grid[y][x] == PLAYER_CHAR:
                if human_image:
                    screen.blit(human_image, rect.topleft)
                else:
                    pygame.draw.rect(screen, (0, 255, 0), rect)  # Green if no image
            elif isinstance(grid[y][x], int):  # Numbered bots
                bot_id = grid[y][x]
                if robot_image:
                    screen.blit(robot_image, rect.topleft)
                else:
                    pygame.draw.rect(screen, (255, 0, 0), rect)  # Red if no image
                text_surface = font.render(str(bot_id), True, (255, 255, 255))
                screen.blit(text_surface, (rect.x + 10, rect.y + 10))  # Draw bot number
            elif grid[y][x] == EXPLOSION_CHAR:  # Explosion indicator
                if explosion_image:
                    screen.blit(explosion_image, rect.topleft)
                else:
                    pygame.draw.rect(screen, (255, 165, 0), rect)  # Orange if no image
            pygame.draw.rect(screen, (255, 255, 255), rect, 1)

def draw_stats(time_left):
    # Prepare and draw the stats text without background fill
    if display_action_message:
        stats_text = f"*** ACTION! ***\nMove: {current_direction}\nBots: {bot_count}\nHumans: {human_count}"
    elif use_timer:
        stats_text = f"Time left: {time_left:.1f} s\nMove: {current_direction}\nBots: {bot_count}\nHumans: {human_count}"
    else:
        stats_text = f"Waiting...\nMove: {current_direction}\nBots: {bot_count}\nHumans: {human_count}"

    stats_text += f"\nPlayer HP: {player_hitpoints}"
    for i, hp in enumerate(bot_hitpoints):
        stats_text += f"\nBot {i} HP: {hp}"

    y_offset = 10
    for line in stats_text.split('\n'):
        text_surface = font.render(line, True, (255, 255, 255))
        screen.blit(text_surface, (grid_width + 10, y_offset))  # Adjust x, y to align text within stats_area
        y_offset += 30

def draw_footer():
    if game_over:
        footer_text = end_game_message
    else:
        footer_text = footer_message if footer_message else ("Game on!" if game_started else "Press arrow keys or W,A,S,D to start or ESC to exit")
    text_surface = font.render(footer_text, True, (255, 255, 255))
    screen.blit(text_surface, (10, total_height - 40))  # Align text at the bottom left

def move_player(direction):
    global player_pos, grid, fight_mode, footer_message

    if fight_mode:
        return

    old_pos = player_pos.copy()

    # Clear the previous player position from the grid
    grid[player_pos[0]][player_pos[1]] = EMPTY_CHAR  

    if direction == 'up':
        player_pos[0] = (player_pos[0] - 1) % height if wrap_around else max(0, player_pos[0] - 1)
        footer_message = "You moved up."
    elif direction == 'down':
        player_pos[0] = (player_pos[0] + 1) % height if wrap_around else min(height - 1, player_pos[0] + 1)
        footer_message = "You moved down."
    elif direction == 'left':
        player_pos[1] = (player_pos[1] - 1) % width if wrap_around else max(0, player_pos[1] - 1)
        footer_message = "You moved left."
    elif direction == 'right':
        player_pos[1] = (player_pos[1] + 1) % width if wrap_around else min(width - 1, player_pos[1] + 1)
        footer_message = "You moved right."

    print(f"Player moved from {old_pos} to {player_pos}")

    # Update the grid to reflect the new player position
    grid[player_pos[0]][player_pos[1]] = PLAYER_CHAR
    check_collision()

def send_game_state_to_llm(grid, bots, player_pos, pressure):
    game_state = {
        "grid": grid,
        "bots": [{ "id": bot["id"], "pos": bot["pos"] } for bot in bots],
        "player_pos": player_pos,
        "pressure": pressure  # Include pressure in the game state
    }
    # For illustration, we mock the response
    # response = requests.post(LLM_API_URL, json=game_state)
    # return response.json()  # Assuming the LLM returns a JSON response with bot commands
    # Mocked response
    return {"bot_commands": ["down" for _ in bots]}

def is_position_free(new_position, bots):
    # Check if the new position is occupied by any bot
    return not any(bot['pos'] == new_position for bot in bots if bot['pos'] != new_position)
    # return all(bot['pos'] != position for bot in bots)

def find_alternative_move(current_position, preferred_directions, bots):
    # Shuffle directions to ensure non-deterministic behavior
    random.shuffle(preferred_directions)
    for direction in preferred_directions:
        new_position = get_new_position(current_position, direction)
        if is_position_free(new_position, bots):
            return new_position
    return current_position  # Return original position if no free space is found

def get_new_position(current_position, direction):
    # Calculate new position based on the direction
    if direction == 'up':
        return [current_position[0] - 1, current_position[1]]
    elif direction == 'down':
        return [current_position[0] + 1, current_position[1]]
    elif direction == 'left':
        return [current_position[0], current_position[1] - 1]
    elif direction == 'right':
        return [current_position[0], current_position[1] + 1]

def calculate_pressure(player_health, game_time, num_bots):
    # Example formula to calculate pressure put on the player
    return min(1, 0.5 + 0.01 * game_time + 0.05 * num_bots - 0.1 * player_health)

def get_path_towards_player(start_pos, player_pos, grid, bots):
    """
    Finds a path from start_pos to player_pos using BFS.
    
    :param start_pos: Tuple (y, x) starting position of the bot
    :param player_pos: Tuple (y, x) position of the player
    :param grid: Current state of the game grid
    :param bots: List of all bots for collision detection
    :return: List of directions leading towards the player
    """
    directions = {
        'up': (-1, 0),
        'down': (1, 0),
        'left': (0, -1),
        'right': (0, 1)
    }
    queue = deque([(start_pos, [])])
    visited = set()
    visited.add(start_pos)

    while queue:
        current_pos, path = queue.popleft()
        
        for dir_key, (dy, dx) in directions.items():
            new_pos = (current_pos[0] + dy, current_pos[1] + dx)
            
            if new_pos == player_pos:
                return path + [dir_key]
            
            if 0 <= new_pos[0] < len(grid) and 0 <= new_pos[1] < len(grid[0]):
                if new_pos not in visited and is_position_free(new_pos, bots):
                    visited.add(new_pos)
                    queue.append((new_pos, path + [dir_key]))

    return []  # Return an empty path if no path is found

def move_bots(pressure):
    global game_over, bot_count, fight_mode

    if fight_mode:
        return

    llm_response = send_game_state_to_llm(grid, bots, player_pos, pressure)  # Now sending pressure to LLM
    bot_commands = llm_response["bot_commands"]

    for i, bot in enumerate(bots):
        old_pos = bot["pos"].copy()
        # Adjust movement strategy based on pressure
        if pressure > 0.8:
            # More direct and aggressive movement
            direct_path = get_path_towards_player(bot["pos"], player_pos)
            new_position = find_alternative_move(bot["pos"], direct_path, bots)
        else:
            # Calculate based on normal LLM commands
            preferred_directions = [bot_commands[i], 'up', 'down', 'left', 'right']
            new_position = find_alternative_move(bot["pos"], preferred_directions, bots)

        bot['pos'] = [max(0, min(new_position[0], height - 1)), max(0, min(new_position[1], width - 1))]

        if bot["pos"] == player_pos:
            print(f"Bot {bot['id']} collided with the player. Initiating fight.")
            fight_mode = True
            current_fight_bot = bot
            break

        print(f"Bot {bot['id']} moved from {old_pos} to {bot['pos']}")

    bots[:] = [bot for bot in bots if bot["pos"][0] < height and bot_hitpoints[bot["id"]] > 0]
    bot_count = len(bots)

# # (old; extremely basic approach)
# def move_bots():
#     global game_over, bot_count, fight_mode

#     if fight_mode:
#         return

#     # Get bot commands from LLM
#     llm_response = send_game_state_to_llm(grid, bots, player_pos)
#     bot_commands = llm_response["bot_commands"]

#     for i, bot in enumerate(bots):
#         old_pos = bot["pos"].copy()
#         if bot_commands[i] == 'down':
#             bot["pos"][0] += 1
#         elif bot_commands[i] == 'up':
#             bot["pos"][0] -= 1
#         elif bot_commands[i] == 'left':
#             bot["pos"][1] -= 1
#         elif bot_commands[i] == 'right':
#             bot["pos"][1] += 1

#         # Ensure bot stays within bounds
#         bot["pos"][0] = max(0, min(bot["pos"][0], height - 1))
#         bot["pos"][1] = max(0, min(bot["pos"][1], width - 1))

#         if bot["pos"] == player_pos:
#             print(f"Bot {bot['id']} collided with the player at {bot['pos']}. Initiating fight.")
#             fight_mode = True
#             current_fight_bot = bot
#             break

#         print(f"Bot {bot['id']} moved from {old_pos} to {bot['pos']}")

#     bots[:] = [bot for bot in bots if bot["pos"][0] < height and bot_hitpoints[bot["id"]] > 0]
#     bot_count = len(bots)

def check_collision():
    global fight_mode, current_fight_bot, footer_message

    for bot in bots:
        if bot["pos"] == player_pos:
            print(f"Collision detected at {bot['pos']}. Initiating fight.")
            fight_mode = True
            current_fight_bot = bot  # Track which bot is fighting
            footer_message = f"Collision at {bot['pos']}. Fight started!"
            asyncio.create_task(taunt_player())  # Schedule taunt_player as a task
            break  # Exit loop once a fight is initiated

def fight_step():
    global player_hitpoints, game_over, fight_mode, current_fight_bot, bot_count, footer_message
    if current_fight_bot is None:
        fight_mode = False
        return

    bot_index = current_fight_bot["id"]

    if player_hitpoints > 0 and bot_hitpoints[bot_index] > 0:
        if random.random() < hit_chance:
            player_hitpoints -= 1
            message = "Bot hit the player!"
            footer_message = message
            print(message)
            if player_hitpoints <= 0:
                message = "Player is dead. Game over."
                footer_message = message
                print(message)
                game_over = True
                grid[player_pos[0]][player_pos[1]] = EXPLOSION_CHAR
                fight_mode = False

        if random.random() < hit_chance:
            bot_hitpoints[bot_index] -= 1
            message = f"Player hit Bot {bot_index}!"
            footer_message = message
            print(message)
            if bot_hitpoints[bot_index] <= 0:
                message = f"Bot {bot_index} is dead."
                footer_message = message
                print(message)
                grid[current_fight_bot["pos"][0]][current_fight_bot["pos"][1]] = EXPLOSION_CHAR
                bots.remove(current_fight_bot)
                bot_count -= 1
                fight_mode = False
    else:
        fight_mode = False

def update_grid():
    global game_over, grid
    grid = [[EMPTY_CHAR for _ in range(width)] for _ in range(height)]
    grid[player_pos[0]][player_pos[1]] = PLAYER_CHAR
    for bot in bots:
        if bot["pos"][0] < height:
            grid[bot["pos"][0]][bot["pos"][1]] = bot["id"]
    check_collision()

def print_ascii_grid():
    print("\n" + "=" * (width * 2 - 1))
    for row in grid:
        print(' '.join(str(cell) for cell in row))
    print("=" * (width * 2 - 1) + "\n")

def reset_game_state():
    global game_over, current_direction, last_direction, display_action_message, fight_mode, bot_count, game_started, time_left, footer_message, player_hitpoints, bots, bot_hitpoints, end_game_message, player_pos
    width = DEFAULT_WIDTH
    height = DEFAULT_HEIGHT
    grid = [[EMPTY_CHAR for _ in range(width)] for _ in range(height)]
    player_pos = [height - 1, width // 2]
    bots = [{"id": i, "pos": [0, i * (width // initial_bots)]} for i in range(initial_bots)]
    time_limit = 2
    action_display_time = 1
    game_over = False
    wrap_around = True
    current_direction = "None"
    selected_direction = "None"
    human_count = initial_humans
    bot_count = initial_bots
    display_action_message = False
    last_direction = "None"
    lock_movement = False
    player_hitpoints = 10
    bot_hitpoints = [3 for _ in range(initial_bots)]
    hit_chance = 0.5
    fight_mode = False
    current_fight_bot = None
    game_started = False
    time_left = time_limit
    footer_message = ""
    end_game_message = ""

async def async_game_loop():
    global game_over, current_direction, last_direction, display_action_message, fight_mode, bot_count, game_started, time_left, footer_message, end_game_message
    while True:
        reset_game_state()  # Reset game state for each new game
        update_grid()  # Update grid after resetting the game state
        last_update_time = pygame.time.get_ticks()
        action_start_time = 0

        while not game_over:
            current_time = pygame.time.get_ticks()
            elapsed_time = (current_time - last_update_time) / 1000.0  # Convert to seconds
            last_update_time = current_time

            # Calculate pressure based on current game conditions
            pressure = calculate_pressure(player_hitpoints, elapsed_time, len(bots))

            # Process events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    print("Quit event detected. Game over.")
                    pygame.quit()
                    return
                elif event.type == pygame.KEYDOWN:
                    if not game_over:
                        if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s, pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                            last_direction = {pygame.K_UP: 'up', pygame.K_w: 'up', pygame.K_DOWN: 'down', pygame.K_s: 'down',
                                              pygame.K_LEFT: 'left', pygame.K_a: 'left', pygame.K_RIGHT: 'right', pygame.K_d: 'right'}[event.key]
                            if not game_started:
                                game_started = True
                                time_left = time_limit  # Initialize the timer once the game starts
                                footer_message = ""
                            else:
                                move_player(last_direction)
                                move_bots(pressure)  # Add the pressure argument
                                update_grid()
                                print_ascii_grid()  # Print ASCII grid to terminal
                                await taunt_player()  # Call taunt_player asynchronously
                        elif event.key == pygame.K_ESCAPE:
                            print("ESC pressed. Exiting game.")
                            pygame.quit()
                            return  # Ensure the game quits properly
                    elif game_over:
                        if event.key == pygame.K_ESCAPE:
                            print("ESC pressed. Exiting game.")
                            pygame.quit()
                            return  # Ensure the game quits properly
                        elif event.key == pygame.K_SPACE:
                            print("SPACE pressed. Restarting game.")
                            game_over = False
                            game_started = False
                            break  # Exit the waiting loop to restart the game

            # Check if movement is locked or if action message is being displayed
            if not lock_movement and current_direction == "None":
                current_direction = last_direction

            if game_started and not display_action_message and not fight_mode and use_timer:
                time_left -= elapsed_time
                if time_left <= 0:
                    print("Time limit reached. Displaying action message.")
                    display_action_message = True
                    action_start_time = pygame.time.get_ticks()
                    time_left = time_limit  # Reset time for next round

            # Handle display of action messages and player movement
            if display_action_message:
                current_action_time = pygame.time.get_ticks()
                if (current_action_time - action_start_time) / 1000.0 >= action_display_time:
                    if current_direction != "None":
                        print(f"Player moving {current_direction} from {player_pos}")
                        move_player(current_direction)
                        print(f"Player moved to {player_pos}")
                        print(f"Bots before moving: {bots}")
                        move_bots(pressure)  # Add the pressure argument
                        print(f"Bots after moving: {bots}")
                        update_grid()
                        print_ascii_grid()  # Print ASCII grid to terminal
                    else:
                        footer_message = "Waiting..."  # Display waiting message
                        print(footer_message)
                    current_direction = "None"
                    display_action_message = False

            # If in fight mode, process one step of the fight
            if fight_mode:
                fight_step()
                print_ascii_grid()  # Print ASCII grid to terminal after fight step

            # Always draw the grid and handle the stats
            draw_grid()
            draw_stats(time_left)
            draw_footer()
            pygame.display.flip()

            # Control frame rate
            clock.tick(30)

        if bot_count == 0:
            end_game_message = "Humans win! Press SPACE for a new game or ESC to exit"
        else:
            end_game_message = "Bots win! Press SPACE for a new game or ESC to exit"

        print(end_game_message)
        draw_footer()
        pygame.display.flip()

        # Wait for user input to restart or exit
        while game_over:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    print("Quit event detected. Exiting game.")
                    pygame.quit()
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        print("ESC pressed. Exiting game.")
                        pygame.quit()
                        return  # Ensure the game quits properly
                    elif event.key == pygame.K_SPACE:
                        print("SPACE pressed. Restarting game.")
                        game_over = False
                        break  # Exit the waiting loop to restart the game

# Initialize game
update_grid()
asyncio.run(async_game_loop())

# Initialize game
update_grid()
asyncio.run(async_game_loop())


#
# ... preliminary additions ... 
#
# import logging
# import pygame
# import random
# import pyttsx3
# import asyncio
# import threading
# import tempfile
# from collections import deque
# from pydub import AudioSegment
# import simpleaudio as sa

# # Initialize logging
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# # Initialize Pygame and load images
# pygame.init()
# pygame.mixer.init()

# def load_and_resize_image(file_path, size):
#     try:
#         image = pygame.image.load(file_path)
#         return pygame.transform.scale(image, size)
#     except pygame.error:
#         return None

# # Load and resize images
# CELL_SIZE = 50
# robot_image = load_and_resize_image("gfx/neural_net_wars_robot.png", (CELL_SIZE, CELL_SIZE))
# human_image = load_and_resize_image("gfx/neural_net_wars_human.png", (CELL_SIZE, CELL_SIZE))
# explosion_image = load_and_resize_image("gfx/neural_net_wars_explosion.png", (CELL_SIZE, CELL_SIZE))
# human_senior_dmg_image = load_and_resize_image("gfx/neural_net_wars_human_senior_dmg.png", (CELL_SIZE, CELL_SIZE))
# human_senior_fire_image = load_and_resize_image("gfx/neural_net_wars_human_senior_fire.png", (CELL_SIZE, CELL_SIZE))
# human_senior_image = load_and_resize_image("gfx/neural_net_wars_human_senior.png", (CELL_SIZE, CELL_SIZE))

# # Constants
# DEFAULT_WIDTH = 12
# DEFAULT_HEIGHT = 12
# PLAYER_CHAR = '@'
# EMPTY_CHAR = '.'
# EXPLOSION_CHAR = 'X'  # Explosion indicator
# # Constants for screen dimensions
# STATS_HEIGHT = 60  # Additional height to accommodate stats display
# STATS_WIDTH = 210  # Width for the stats display area
# MIN_HEIGHT = 600  # Minimum height required for the window
# MIN_STATS_WIDTH = STATS_WIDTH + 600  # Minimum width required for the window including stats

# # Global Game State
# width = DEFAULT_WIDTH
# height = DEFAULT_HEIGHT
# grid = [[EMPTY_CHAR for _ in range(width)] for _ in range(height)]
# initial_bots = 10
# initial_humans = 1
# player_pos = [height - 1, width // 2]
# bots = [{"id": i, "pos": [0, i * (width // initial_bots)]} for i in range(initial_bots)]
# time_limit = 2  # Time limit for player move in seconds
# action_display_time = 1  # Time to display the action message
# game_over = False
# wrap_around = True  # Option for wrapping around the screen
# current_direction = "None"
# selected_direction = "None"
# human_count = initial_humans
# bot_count = initial_bots
# display_action_message = False  # Flag to display the action message
# last_direction = "None"
# lock_movement = False
# player_hitpoints = 10
# bot_hitpoints = [3 for _ in range(initial_bots)]
# hit_chance = 0.5  # 50% chance to hit
# fight_mode = False  # Flag to indicate if a fight is happening
# current_fight_bot = None  # Track the current bot being fought
# game_started = False  # Track if the game has started
# time_left = time_limit  # Initialize the timer
# footer_message = ""  # Footer message for additional information
# use_timer = False  # Flag to determine if the timer should be used
# end_game_message = ""  # Message displayed at the end of the game

# taunts = [
#     "You can't beat us!",
#     "Prepare to be terminated!",
#     "Is that all you've got?",
#     "You're no match for us!",
#     "We will destroy you!"
# ]

# # text-to-speech
# class TTSManager:
#     def __init__(self):
#         self.queue = deque()
#         self.queue_lock = asyncio.Lock()

#     def apply_dsp(self, audio):
#         logging.debug("Applying DSP to audio.")
#         audio += 50
#         audio = audio.compress_dynamic_range(threshold=-20.0, ratio=4.0)
#         audio = audio.low_pass_filter(3000)
#         new_frame_rate = int(audio.frame_rate * 0.6)
#         shifted_audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_frame_rate})
#         shifted_audio = shifted_audio.set_frame_rate(audio.frame_rate)
#         logging.debug("DSP applied.")
#         return shifted_audio

#     async def play_audio(self, filename):
#         try:
#             audio = AudioSegment.from_wav(filename)
#             playback = sa.play_buffer(audio.raw_data, num_channels=audio.channels, bytes_per_sample=audio.sample_width, sample_rate=audio.frame_rate)
#             logging.debug(f"Playing audio: {filename}")
#             playback.wait_done()
#             logging.debug("Audio playback completed.")
#         except Exception as e:
#             logging.error(f"Error in play_audio: {e}")

#     async def _speak(self, text):
#         logging.debug(f"Starting TTS for: {text}")
#         try:
#             tts_engine = pyttsx3.init()  # Re-initialize TTS engine
#             with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as tts_file:
#                 tts_engine.save_to_file(text, tts_file.name)
#                 tts_engine.runAndWait()
#                 logging.debug(f"TTS generated for: {text}")

#                 audio = AudioSegment.from_wav(tts_file.name)
#                 processed_audio = self.apply_dsp(audio)
#                 with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as dsp_file:
#                     processed_audio.export(dsp_file.name, format='wav')
#                     logging.debug(f"Processing and playing DSP audio: {dsp_file.name}")
#                     await self.play_audio(dsp_file.name)
#                     await asyncio.sleep(1)  # Small delay to ensure proper audio playback
#         except Exception as e:
#             logging.error(f"Error in _speak: {e}")

#     async def add_taunt(self, taunt):
#         async with self.queue_lock:
#             self.queue.append(taunt)
#             logging.debug(f"Added taunt to queue: {taunt}")
#             if len(self.queue) == 1:
#                 logging.debug("Starting to process queue.")
#                 await self.process_queue()

#     async def process_queue(self):
#         while self.queue:
#             current_taunt = self.queue.popleft()
#             logging.debug(f"Starting to process taunt: {current_taunt}")
#             await self._speak(current_taunt)
#             logging.debug(f"Finished processing taunt: {current_taunt}")
#             await asyncio.sleep(1)  # Add a small delay to ensure queue processes correctly

# async def taunt_player():
#     taunt = random.choice(taunts)
#     global footer_message
#     footer_message = taunt
#     await tts_manager.add_taunt(taunt)

# tts_manager = TTSManager()

# # Calculate necessary screen width
# grid_width = width * CELL_SIZE
# total_width = max(grid_width + STATS_WIDTH, MIN_STATS_WIDTH)  # Ensure the screen is at least as wide as MIN_STATS_WIDTH

# # Calculate necessary screen height
# grid_height = height * CELL_SIZE + STATS_HEIGHT
# total_height = max(grid_height, MIN_HEIGHT)  # Ensure the screen is at least as tall as MIN_HEIGHT

# # Initialize Pygame
# try:
#     pygame.init()
#     screen = pygame.display.set_mode((total_width, total_height))
#     pygame.display.set_caption("Neural Net Wars")
# except Exception as e:
#     print(f"Error initializing Pygame: {e}")
#     game_over = True

# font = pygame.font.Font(None, 36)
# clock = pygame.time.Clock()

# def draw_grid():
#     screen.fill((0, 0, 0))
#     for y in range(height):
#         for x in range(width):
#             rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
#             if grid[y][x] == PLAYER_CHAR:
#                 if human_image:
#                     screen.blit(human_image, rect.topleft)
#                 else:
#                     pygame.draw.rect(screen, (0, 255, 0), rect)  # Green if no image
#             elif isinstance(grid[y][x], int):  # Numbered bots
#                 bot_id = grid[y][x]
#                 if robot_image:
#                     screen.blit(robot_image, rect.topleft)
#                 else:
#                     pygame.draw.rect(screen, (255, 0, 0), rect)  # Red if no image
#                 text_surface = font.render(str(bot_id), True, (255, 255, 255))
#                 screen.blit(text_surface, (rect.x + 10, rect.y + 10))  # Draw bot number
#             elif grid[y][x] == EXPLOSION_CHAR:  # Explosion indicator
#                 if explosion_image:
#                     screen.blit(explosion_image, rect.topleft)
#                 else:
#                     pygame.draw.rect(screen, (255, 165, 0), rect)  # Orange if no image
#             pygame.draw.rect(screen, (255, 255, 255), rect, 1)

# def draw_stats(time_left):
#     # Prepare and draw the stats text without background fill
#     if display_action_message:
#         stats_text = f"*** ACTION! ***\nMove: {current_direction}\nBots: {bot_count}\nHumans: {human_count}"
#     elif use_timer:
#         stats_text = f"Time left: {time_left:.1f} s\nMove: {current_direction}\nBots: {bot_count}\nHumans: {human_count}"
#     else:
#         stats_text = f"Waiting...\nMove: {current_direction}\nBots: {bot_count}\nHumans: {human_count}"

#     stats_text += f"\nPlayer HP: {player_hitpoints}"
#     for i, hp in enumerate(bot_hitpoints):
#         stats_text += f"\nBot {i} HP: {hp}"

#     y_offset = 10
#     for line in stats_text.split('\n'):
#         text_surface = font.render(line, True, (255, 255, 255))
#         screen.blit(text_surface, (grid_width + 10, y_offset))  # Adjust x, y to align text within stats_area
#         y_offset += 30

# def draw_footer():
#     if game_over:
#         footer_text = end_game_message
#     else:
#         footer_text = footer_message if footer_message else ("Game on!" if game_started else "Press arrow keys or W,A,S,D to start or ESC to exit")
#     text_surface = font.render(footer_text, True, (255, 255, 255))
#     screen.blit(text_surface, (10, total_height - 40))  # Align text at the bottom left

# def move_player(direction):
#     global player_pos, grid, fight_mode, footer_message

#     if fight_mode:
#         return

#     old_pos = player_pos.copy()

#     # Clear the previous player position from the grid
#     grid[player_pos[0]][player_pos[1]] = EMPTY_CHAR  

#     if direction == 'up':
#         player_pos[0] = (player_pos[0] - 1) % height if wrap_around else max(0, player_pos[0] - 1)
#         footer_message = "You moved up."
#     elif direction == 'down':
#         player_pos[0] = (player_pos[0] + 1) % height if wrap_around else min(height - 1, player_pos[0] + 1)
#         footer_message = "You moved down."
#     elif direction == 'left':
#         player_pos[1] = (player_pos[1] - 1) % width if wrap_around else max(0, player_pos[1] - 1)
#         footer_message = "You moved left."
#     elif direction == 'right':
#         player_pos[1] = (player_pos[1] + 1) % width if wrap_around else min(width - 1, player_pos[1] + 1)
#         footer_message = "You moved right."

#     print(f"Player moved from {old_pos} to {player_pos}")

#     # Update the grid to reflect the new player position
#     grid[player_pos[0]][player_pos[1]] = PLAYER_CHAR
#     check_collision()

# def send_game_state_to_llm(grid, bots, player_pos, pressure):
#     game_state = {
#         "grid": grid,
#         "bots": [{ "id": bot["id"], "pos": bot["pos"] } for bot in bots],
#         "player_pos": player_pos,
#         "pressure": pressure  # Include pressure in the game state
#     }
#     # For illustration, we mock the response
#     # response = requests.post(LLM_API_URL, json=game_state)
#     # return response.json()  # Assuming the LLM returns a JSON response with bot commands
#     # Mocked response
#     return {"bot_commands": ["down" for _ in bots]}

# def is_position_free(new_position, bots):
#     # Check if the new position is occupied by any bot
#     return not any(bot['pos'] == new_position for bot in bots if bot['pos'] != new_position)
#     # return all(bot['pos'] != position for bot in bots)

# def find_alternative_move(current_position, preferred_directions, bots):
#     # Shuffle directions to ensure non-deterministic behavior
#     random.shuffle(preferred_directions)
#     for direction in preferred_directions:
#         new_position = get_new_position(current_position, direction)
#         if is_position_free(new_position, bots):
#             return new_position
#     return current_position  # Return original position if no free space is found

# def get_new_position(current_position, direction):
#     # Calculate new position based on the direction
#     if direction == 'up':
#         return [current_position[0] - 1, current_position[1]]
#     elif direction == 'down':
#         return [current_position[0] + 1, current_position[1]]
#     elif direction == 'left':
#         return [current_position[0], current_position[1] - 1]
#     elif direction == 'right':
#         return [current_position[0], current_position[1] + 1]

# def calculate_pressure(player_health, game_time, num_bots):
#     # Example formula to calculate pressure put on the player
#     return min(1, 0.5 + 0.01 * game_time + 0.05 * num_bots - 0.1 * player_health)

# def get_path_towards_player(start_pos, player_pos, grid, bots):
#     """
#     Finds a path from start_pos to player_pos using BFS.
    
#     :param start_pos: Tuple (y, x) starting position of the bot
#     :param player_pos: Tuple (y, x) position of the player
#     :param grid: Current state of the game grid
#     :param bots: List of all bots for collision detection
#     :return: List of directions leading towards the player
#     """
#     directions = {
#         'up': (-1, 0),
#         'down': (1, 0),
#         'left': (0, -1),
#         'right': (0, 1)
#     }
#     queue = deque([(start_pos, [])])
#     visited = set()
#     visited.add(start_pos)

#     while queue:
#         current_pos, path = queue.popleft()
        
#         for dir_key, (dy, dx) in directions.items():
#             new_pos = (current_pos[0] + dy, current_pos[1] + dx)
            
#             if new_pos == player_pos:
#                 return path + [dir_key]
            
#             if 0 <= new_pos[0] < len(grid) and 0 <= new_pos[1] < len(grid[0]):
#                 if new_pos not in visited and is_position_free(new_pos, bots):
#                     visited.add(new_pos)
#                     queue.append((new_pos, path + [dir_key]))

#     return []  # Return an empty path if no path is found

# def move_bots(pressure):
#     global game_over, bot_count, fight_mode

#     if fight_mode:
#         return

#     llm_response = send_game_state_to_llm(grid, bots, player_pos, pressure)  # Now sending pressure to LLM
#     bot_commands = llm_response["bot_commands"]

#     for i, bot in enumerate(bots):
#         old_pos = bot["pos"].copy()
#         # Adjust movement strategy based on pressure
#         if pressure > 0.8:
#             # More direct and aggressive movement
#             direct_path = get_path_towards_player(bot["pos"], player_pos)
#             new_position = find_alternative_move(bot["pos"], direct_path, bots)
#         else:
#             # Calculate based on normal LLM commands
#             preferred_directions = [bot_commands[i], 'up', 'down', 'left', 'right']
#             new_position = find_alternative_move(bot["pos"], preferred_directions, bots)

#         bot['pos'] = [max(0, min(new_position[0], height - 1)), max(0, min(new_position[1], width - 1))]

#         if bot["pos"] == player_pos:
#             print(f"Bot {bot['id']} collided with the player. Initiating fight.")
#             fight_mode = True
#             current_fight_bot = bot
#             break

#         print(f"Bot {bot['id']} moved from {old_pos} to {bot['pos']}")

#     bots[:] = [bot for bot in bots if bot["pos"][0] < height and bot_hitpoints[bot["id"]] > 0]
#     bot_count = len(bots)

# def check_collision():
#     global fight_mode, current_fight_bot, footer_message

#     for bot in bots:
#         if bot["pos"] == player_pos:
#             print(f"Collision detected at {bot['pos']}. Initiating fight.")
#             fight_mode = True
#             current_fight_bot = bot  # Track which bot is fighting
#             footer_message = f"Collision at {bot['pos']}. Fight started!"
#             asyncio.create_task(taunt_player())  # Schedule taunt_player as a task
#             break  # Exit loop once a fight is initiated

# def fight_step():
#     global player_hitpoints, game_over, fight_mode, current_fight_bot, bot_count, footer_message
#     if current_fight_bot is None:
#         fight_mode = False
#         return

#     bot_index = current_fight_bot["id"]

#     if player_hitpoints > 0 and bot_hitpoints[bot_index] > 0:
#         if random.random() < hit_chance:
#             player_hitpoints -= 1
#             message = "Bot hit the player!"
#             footer_message = message
#             print(message)
#             if player_hitpoints <= 0:
#                 message = "Player is dead. Game over."
#                 footer_message = message
#                 print(message)
#                 game_over = True
#                 grid[player_pos[0]][player_pos[1]] = EXPLOSION_CHAR
#                 fight_mode = False

#         if random.random() < hit_chance:
#             bot_hitpoints[bot_index] -= 1
#             message = f"Player hit Bot {bot_index}!"
#             footer_message = message
#             print(message)
#             if bot_hitpoints[bot_index] <= 0:
#                 message = f"Bot {bot_index} is dead."
#                 footer_message = message
#                 print(message)
#                 grid[current_fight_bot["pos"][0]][current_fight_bot["pos"][1]] = EXPLOSION_CHAR
#                 bots.remove(current_fight_bot)
#                 bot_count -= 1
#                 fight_mode = False
#     else:
#         fight_mode = False

# def update_grid():
#     global game_over, grid
#     grid = [[EMPTY_CHAR for _ in range(width)] for _ in range(height)]
#     grid[player_pos[0]][player_pos[1]] = PLAYER_CHAR
#     for bot in bots:
#         if bot["pos"][0] < height:
#             grid[bot["pos"][0]][bot["pos"][1]] = bot["id"]
#     check_collision()

# def print_ascii_grid():
#     print("\n" + "=" * (width * 2 - 1))
#     for row in grid:
#         print(' '.join(str(cell) for cell in row))
#     print("=" * (width * 2 - 1) + "\n")

# def reset_game_state():
#     global game_over, current_direction, last_direction, display_action_message, fight_mode, bot_count, game_started, time_left, footer_message, player_hitpoints, bots, bot_hitpoints, end_game_message, player_pos
#     width = DEFAULT_WIDTH
#     height = DEFAULT_HEIGHT
#     grid = [[EMPTY_CHAR for _ in range(width)] for _ in range(height)]
#     player_pos = [height - 1, width // 2]
#     bots = [{"id": i, "pos": [0, i * (width // initial_bots)]} for i in range(initial_bots)]
#     time_limit = 2
#     action_display_time = 1
#     game_over = False
#     wrap_around = True
#     current_direction = "None"
#     selected_direction = "None"
#     human_count = initial_humans
#     bot_count = initial_bots
#     display_action_message = False
#     last_direction = "None"
#     lock_movement = False
#     player_hitpoints = 10
#     bot_hitpoints = [3 for _ in range(initial_bots)]
#     hit_chance = 0.5
#     fight_mode = False
#     current_fight_bot = None
#     game_started = False
#     time_left = time_limit
#     footer_message = ""
#     end_game_message = ""

# async def async_game_loop():
#     global game_over, current_direction, last_direction, display_action_message, fight_mode, bot_count, game_started, time_left, footer_message, end_game_message
#     asyncio.create_task(tts_manager.process_queue())  # Run TTSManager check in the background
#     while True:
#         reset_game_state()  # Reset game state for each new game
#         update_grid()  # Update grid after resetting the game state
#         last_update_time = pygame.time.get_ticks()
#         action_start_time = 0

#         while not game_over:
#             current_time = pygame.time.get_ticks()
#             elapsed_time = (current_time - last_update_time) / 1000.0  # Convert to seconds
#             last_update_time = current_time

#             # Calculate pressure based on current game conditions
#             pressure = calculate_pressure(player_hitpoints, elapsed_time, len(bots))

#             # Process events
#             for event in pygame.event.get():
#                 if event.type == pygame.QUIT:
#                     print("Quit event detected. Game over.")
#                     pygame.quit()
#                     return
#                 elif event.type == pygame.KEYDOWN:
#                     if not game_over:
#                         if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s, pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
#                             last_direction = {pygame.K_UP: 'up', pygame.K_w: 'up', pygame.K_DOWN: 'down', pygame.K_s: 'down',
#                                               pygame.K_LEFT: 'left', pygame.K_a: 'left', pygame.K_RIGHT: 'right', pygame.K_d: 'right'}[event.key]
#                             if not game_started:
#                                 game_started = True
#                                 time_left = time_limit  # Initialize the timer once the game starts
#                                 footer_message = ""
#                             else:
#                                 move_player(last_direction)
#                                 move_bots(pressure)  # Add the pressure argument
#                                 update_grid()
#                                 print_ascii_grid()  # Print ASCII grid to terminal
#                                 asyncio.create_task(taunt_player())  # Call taunt_player asynchronously
#                         elif event.key == pygame.K_ESCAPE:
#                             print("ESC pressed. Exiting game.")
#                             pygame.quit()
#                             return  # Ensure the game quits properly
#                     elif game_over:
#                         if event.key == pygame.K_ESCAPE:
#                             print("ESC pressed. Exiting game.")
#                             pygame.quit()
#                             return  # Ensure the game quits properly
#                         elif event.key == pygame.K_SPACE:
#                             print("SPACE pressed. Restarting game.")
#                             game_over = False
#                             game_started = False
#                             break  # Exit the waiting loop to restart the game

#             # Check if movement is locked or if action message is being displayed
#             if not lock_movement and current_direction == "None":
#                 current_direction = last_direction

#             if game_started and not display_action_message and not fight_mode and use_timer:
#                 time_left -= elapsed_time
#                 if time_left <= 0:
#                     print("Time limit reached. Displaying action message.")
#                     display_action_message = True
#                     action_start_time = pygame.time.get_ticks()
#                     time_left = time_limit  # Reset time for next round

#             # Handle display of action messages and player movement
#             if display_action_message:
#                 current_action_time = pygame.time.get_ticks()
#                 if (current_action_time - action_start_time) / 1000.0 >= action_display_time:
#                     if current_direction != "None":
#                         print(f"Player moving {current_direction} from {player_pos}")
#                         move_player(current_direction)
#                         print(f"Player moved to {player_pos}")
#                         print(f"Bots before moving: {bots}")
#                         move_bots(pressure)  # Add the pressure argument
#                         print(f"Bots after moving: {bots}")
#                         update_grid()
#                         print_ascii_grid()  # Print ASCII grid to terminal
#                     else:
#                         footer_message = "Waiting..."  # Display waiting message
#                         print(footer_message)
#                     current_direction = "None"
#                     display_action_message = False

#             # If in fight mode, process one step of the fight
#             if fight_mode:
#                 fight_step()
#                 print_ascii_grid()  # Print ASCII grid to terminal after fight step

#             # Always draw the grid and handle the stats
#             draw_grid()
#             draw_stats(time_left)
#             draw_footer()
#             pygame.display.flip()

#             # Control frame rate
#             clock.tick(30)

#         if bot_count == 0:
#             end_game_message = "Humans win! Press SPACE for a new game or ESC to exit"
#         else:
#             end_game_message = "Bots win! Press SPACE for a new game or ESC to exit"

#         print(end_game_message)
#         draw_footer()
#         pygame.display.flip()

#         # Wait for user input to restart or exit
#         while game_over:
#             for event in pygame.event.get():
#                 if event.type == pygame.QUIT:
#                     print("Quit event detected. Exiting game.")
#                     pygame.quit()
#                     return
#                 elif event.type == pygame.KEYDOWN:
#                     if event.key == pygame.K_ESCAPE:
#                         print("ESC pressed. Exiting game.")
#                         pygame.quit()
#                         return  # Ensure the game quits properly
#                     elif event.key == pygame.K_SPACE:
#                         print("SPACE pressed. Restarting game.")
#                         game_over = False
#                         break  # Exit the waiting loop to restart the game

# # Initialize game
# update_grid()
# asyncio.run(async_game_loop())


