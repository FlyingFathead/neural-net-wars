# neural net wars v0.12

import pygame
import random

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
human_senior_dmg_image = load_and_resize_image("gfx/neural_net_wars_human_senior_dmg.png", (CELL_SIZE, CELL_SIZE))
human_senior_fire_image = load_and_resize_image("gfx/neural_net_wars_human_senior_fire.png", (CELL_SIZE, CELL_SIZE))
human_senior_image = load_and_resize_image("gfx/neural_net_wars_human_senior.png", (CELL_SIZE, CELL_SIZE))

# Constants
DEFAULT_WIDTH = 12
DEFAULT_HEIGHT = 12
PLAYER_CHAR = '@'
BOT_CHAR = 'b'
EMPTY_CHAR = ' '
# Constants for screen dimensions
STATS_HEIGHT = 60  # Additional height to accommodate stats display
MIN_STATS_WIDTH = 800  # Minimum width required for the stats section
STATS_WIDTH = 200  # Width for the stats display area
MIN_HEIGHT = 600  # Minimum height required for the window

# Game State
width = DEFAULT_WIDTH
height = DEFAULT_HEIGHT
grid = [[EMPTY_CHAR for _ in range(width)] for _ in range(height)]
initial_bots = 10
initial_humans = 1
player_pos = [height - 1, width // 2]
bots = [[0, i * (width // initial_bots)] for i in range(initial_bots)]
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
lock_movement = True
player_hitpoints = 10
bot_hitpoints = [3 for _ in range(initial_bots)]
hit_chance = 0.5  # 50% chance to hit

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
            elif grid[y][x] == BOT_CHAR:
                if robot_image:
                    screen.blit(robot_image, rect.topleft)
                else:
                    pygame.draw.rect(screen, (255, 0, 0), rect)  # Red if no image
            pygame.draw.rect(screen, (255, 255, 255), rect, 1)

def draw_stats(time_left):
    # Prepare and draw the stats text without background fill
    if display_action_message:
        stats_text = f"[ 🚨 ACTION! 🚨 ]\n[ Current move: {current_direction} ]\n[ Bots: {bot_count} ]\n[ Humans: {human_count} ]"
    else:
        stats_text = f"[ Time left: {time_left:.1f} s ]\n[ Current move: {current_direction} ]\n[ Bots: {bot_count} ]\n[ Humans: {human_count} ]"

    stats_text += f"\n[ Player HP: {player_hitpoints} ]"
    for i, hp in enumerate(bot_hitpoints):
        stats_text += f"\n[ Bot {i} HP: {hp} ]"

    y_offset = 10
    for line in stats_text.split('\n'):
        text_surface = font.render(line, True, (255, 255, 255))
        screen.blit(text_surface, (grid_width + 10, y_offset))  # Adjust x, y to align text within stats_area
        y_offset += 30

def move_player(direction):
    global player_pos, grid

    # Clear the previous player position from the grid
    grid[player_pos[0]][player_pos[1]] = EMPTY_CHAR  

    if direction == 'up':
        player_pos[0] = (player_pos[0] - 1) % height if wrap_around else max(0, player_pos[0] - 1)
    elif direction == 'down':
        player_pos[0] = min(height - 1, player_pos[0] + 1)  
    elif direction == 'left':
        player_pos[1] = (player_pos[1] - 1) % width if wrap_around else max(0, player_pos[1] - 1)
    elif direction == 'right':
        player_pos[1] = (player_pos[1] + 1) % width if wrap_around else min(width - 1, player_pos[1] + 1)

    # Update the grid to reflect the new player position
    grid[player_pos[0]][player_pos[1]] = PLAYER_CHAR

def move_bots():
    global game_over, bot_count
    for bot in bots:
        bot[0] += 1
        if bot[0] >= height:
            print(f"Bot reached the bottom of the grid at {bot}. Game over.")
            game_over = True
        elif bot == player_pos:
            print(f"Bot collided with the player at {bot}. Initiating attack.")
            attack(bot)
    bots[:] = [bot for bot in bots if bot[0] < height and bot_hitpoints[bots.index(bot)] > 0]
    bot_count = len(bots)

def attack(bot):
    global player_hitpoints, game_over
    if random.random() < hit_chance:
        print("Bot hit the player!")
        player_hitpoints -= 1
        if player_hitpoints <= 0:
            print("Player is dead. Game over.")
            game_over = True
    if random.random() < hit_chance:
        bot_index = bots.index(bot)
        print(f"Player hit Bot {bot_index}!")
        bot_hitpoints[bot_index] -= 1
        if bot_hitpoints[bot_index] <= 0:
            print(f"Bot {bot_index} is dead.")

def update_grid():
    global game_over, grid
    grid = [[EMPTY_CHAR for _ in range(width)] for _ in range(height)]
    grid[player_pos[0]][player_pos[1]] = PLAYER_CHAR
    for bot in bots:
        if bot[0] < height:
            grid[bot[0]][bot[1]] = BOT_CHAR
        if bot == player_pos:
            print(f"Bot collided with the player in update_grid at {bot}. Game over.")
            game_over = True

def print_ascii_grid():
    print("\n" + "=" * (width * 2 - 1))
    for row in grid:
        print(' '.join(row))
    print("=" * (width * 2 - 1) + "\n")

def game_loop():
    global game_over, current_direction, last_direction, display_action_message
    time_left = time_limit  # Time left in seconds
    last_update_time = pygame.time.get_ticks()
    action_start_time = 0

    while not game_over:
        current_time = pygame.time.get_ticks()
        elapsed_time = (current_time - last_update_time) / 1000.0  # Convert to seconds
        last_update_time = current_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("Quit event detected. Game over.")
                game_over = True
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    last_direction = 'up'
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    last_direction = 'down'
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    last_direction = 'left'
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    last_direction = 'right'
        
        if not lock_movement or current_direction == "None":
            current_direction = last_direction

        if not display_action_message:
            time_left -= elapsed_time
            print(f"Time left for move: {time_left:.2f} seconds")

            if time_left <= 0:
                print("Time limit reached. Displaying action message.")
                display_action_message = True
                action_start_time = pygame.time.get_ticks()
                time_left = 0

        if display_action_message:
            current_action_time = pygame.time.get_ticks()
            if (current_action_time - action_start_time) / 1000.0 < action_display_time:
                pass  # Do nothing, display message
            else:
                if current_direction != "None":
                    print(f"Player moving {current_direction} from {player_pos}")
                    move_player(current_direction)
                    print(f"Player moved to {player_pos}")
                    print(f"Bots before moving: {bots}")
                    move_bots()
                    print(f"Bots after moving: {bots}")
                current_direction = "None"
                time_left = time_limit  # Reset the time_left
                display_action_message = False

        update_grid()
        print_ascii_grid()  # Print ASCII grid to terminal        
        draw_grid()
        draw_stats(time_left)
        pygame.display.flip()

        if game_over:
            break
        clock.tick(30)

# Initialize game
update_grid()
if not game_over:
    game_loop()

if bot_count == 0:
    winner_text = "Humans win!"
else:
    winner_text = "Bots win!"

print(winner_text)
pygame.quit()
print("Game Over!")