# neural net wars 0.14.06
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# https://github.com/FlyingFathead/neural-net-wars/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import pygame
import random
import pyttsx3
import asyncio
import threading

class TTSManager:
    def __init__(self):
        self.tts_engine = pyttsx3.init()
        self.cue = None
        self.lock = threading.Lock()
        self.is_playing = False

    def _speak(self, text):
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()
        self.is_playing = False

    def play_taunt(self, taunt):
        with self.lock:
            if not self.is_playing:
                self.cue = taunt
                self.is_playing = True
                threading.Thread(target=self._speak, args=(taunt,)).start()

    async def check_and_play(self):
        while True:
            await asyncio.sleep(0.1)
            with self.lock:
                if self.cue and not self.is_playing:
                    self.is_playing = True
                    threading.Thread(target=self._speak, args=(self.cue,)).start()
                    self.cue = None

tts_manager = TTSManager()

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
EMPTY_CHAR = ' '
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

async def taunt_player():
    taunt = random.choice(taunts)
    global footer_message
    footer_message = taunt
    tts_manager.play_taunt(taunt)

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

def send_game_state_to_llm(grid, bots, player_pos):
    game_state = {
        "grid": grid,
        "bots": [{ "id": bot["id"], "pos": bot["pos"] } for bot in bots],
        "player_pos": player_pos
    }
    # For illustration, we mock the response
    # response = requests.post(LLM_API_URL, json=game_state)
    # return response.json()  # Assuming the LLM returns a JSON response with bot commands
    # Mocked response
    return {"bot_commands": ["down" for _ in bots]}

def move_bots():
    global game_over, bot_count, fight_mode

    if fight_mode:
        return

    # Get bot commands from LLM
    llm_response = send_game_state_to_llm(grid, bots, player_pos)
    bot_commands = llm_response["bot_commands"]

    for i, bot in enumerate(bots):
        old_pos = bot["pos"].copy()
        if bot_commands[i] == 'down':
            bot["pos"][0] += 1
        elif bot_commands[i] == 'up':
            bot["pos"][0] -= 1
        elif bot_commands[i] == 'left':
            bot["pos"][1] -= 1
        elif bot_commands[i] == 'right':
            bot["pos"][1] += 1

        # Ensure bot stays within bounds
        bot["pos"][0] = max(0, min(bot["pos"][0], height - 1))
        bot["pos"][1] = max(0, min(bot["pos"][1], width - 1))

        if bot["pos"] == player_pos:
            print(f"Bot {bot['id']} collided with the player at {bot['pos']}. Initiating fight.")
            fight_mode = True
            current_fight_bot = bot
            break

        print(f"Bot {bot['id']} moved from {old_pos} to {bot['pos']}")

    bots[:] = [bot for bot in bots if bot["pos"][0] < height and bot_hitpoints[bot["id"]] > 0]
    bot_count = len(bots)

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
    asyncio.create_task(tts_manager.check_and_play())  # Run TTSManager check in the background
    while True:
        reset_game_state()  # Reset game state for each new game
        update_grid()  # Update grid after resetting the game state
        last_update_time = pygame.time.get_ticks()
        action_start_time = 0

        while not game_over:
            current_time = pygame.time.get_ticks()
            elapsed_time = (current_time - last_update_time) / 1000.0  # Convert to seconds
            last_update_time = current_time

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
                                move_bots()
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
                        move_bots()
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
