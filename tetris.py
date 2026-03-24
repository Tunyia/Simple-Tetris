import pygame
import sys
import copy
import random
print("Tetris by Tunya")

CELL = 30
WIDTH = 300
HEIGHT = 600

ROWS = HEIGHT // CELL
COLS = WIDTH // CELL

screen = None
clock = None
font = None

clearing_lines = []
next_queue = []

SHAPES = [
    [[1,1,1,1]],

    [[1,1],
     [1,1]],

    [[0,1,0],
     [1,1,1]],

    [[1,1,0],
     [0,1,1]],

    [[0,1,1],
     [1,1,0]],

    [[1,0,0],
     [1,1,1]],

    [[0,0,1],
     [1,1,1]]
]

bag = []
def get_next_shape():
    global bag
    if not bag:
        bag = SHAPES.copy()
        random.shuffle(bag)
    return bag.pop()

def draw_grid(offset_x=0):
    for y in range(ROWS):
        for x in range(COLS):
            rect = pygame.Rect(offset_x + x*CELL, y*CELL, CELL, CELL)
            pygame.draw.rect(screen, (40,40,40), rect, 1)

class Piece:
    def __init__(self):
        self.shape = copy.deepcopy(get_next_shape())
        self.x = COLS // 2
        self.y = 0

def draw_piece(piece, offset_x=0):
    for y, row in enumerate(piece.shape):
        for x, cell in enumerate(row):
            if cell:
                rect = pygame.Rect(
                    offset_x + (piece.x + x)*CELL,
                    (piece.y + y)*CELL,
                    CELL,
                    CELL
                )
                pygame.draw.rect(screen, (0,200,255), rect)

def valid_move(piece, grid, dx=0, dy=0):
    for y, row in enumerate(piece.shape):
        for x, cell in enumerate(row):
            if cell:
                new_x = piece.x + x + dx
                new_y = piece.y + y + dy

                if new_x < 0 or new_x >= COLS or new_y >= ROWS:
                    return False

                if new_y >= 0 and grid[new_y][new_x]:
                    return False
    return True

def place_piece(piece, grid):
    for y, row in enumerate(piece.shape):
        for x, cell in enumerate(row):
            if cell:
                grid[piece.y + y][piece.x + x] = 1

def clear_lines(grid):
    new_grid = [row for row in grid if not all(row)]
    lines_cleared = ROWS - len(new_grid)

    for _ in range(lines_cleared):
        new_grid.insert(0, [0]*COLS)

    return new_grid, lines_cleared

def draw_blocks(grid, offset_x=0):
    for y in range(ROWS):
        for x in range(COLS):
            cell = grid[y][x]
            if cell:
                rect = pygame.Rect(offset_x + x*CELL, y*CELL, CELL, CELL)
                if cell == 1: # Цвет блока
                    color = (255, 100, 100)  # обычные блоки
                elif cell == 2:
                    color = (120, 120, 120)  # мусор серый
                if y in clearing_lines: # эффект свечения для очищаемых линий
                    glow_color = (255, 255, 255)
                    pygame.draw.rect(screen, glow_color, rect)
                else:
                    pygame.draw.rect(screen, color, rect)

def rotate(shape):
    return [list(row) for row in zip(*shape[::-1])]

def rotate_with_kick(piece, grid):
    new_shape = rotate(piece.shape)
    kicks = [
        (0,0),
        (-1,0),
        (1,0),
        (-2,0),
        (2,0),
        (0,-1)
    ]

    old_shape = piece.shape
    for dx, dy in kicks:
        piece.shape = new_shape
        if valid_move(piece, grid, dx=dx, dy=dy):
            piece.x += dx
            piece.y += dy
            return
    piece.shape = old_shape

class ScorePopup:
    def __init__(self, x, y, text):
        self.x = x
        self.y = y
        self.text = text
        self.timer = 1.0

    def update(self, dt):
        self.timer -= dt

    def draw(self, screen):
        alpha = int(255 * self.timer)
        surf = font.render(self.text, True, (255,255,0))
        surf.set_alpha(alpha)
        screen.blit(surf, (self.x, self.y))

class HardDropEffect:
    def __init__(self, piece, start_y, end_y):
        self.piece = copy.deepcopy(piece)
        self.start_y = start_y
        self.end_y = end_y
        self.max_timer = 0.3
        self.timer = self.max_timer

    def update(self, dt):
        self.timer -= dt

    def draw(self, screen, offset_x=0):
        alpha_factor = self.timer / self.max_timer
        shape = self.piece.shape
        width = len(shape[0])
        height = len(shape)

        for x in range(width):
            bottom_y = None
            for y in reversed(range(height)):
                if shape[y][x]:
                    bottom_y = y
                    break
            if bottom_y is None:
                continue

            distance = self.end_y - self.start_y
            for i, ty in enumerate(range(self.start_y, self.end_y)):
                fade = i / max(distance, 1)
                alpha = int(255 * fade * alpha_factor)

                surf = pygame.Surface((CELL, CELL))
                surf.set_alpha(alpha)
                surf.fill((220, 220, 220))

                screen.blit(
                    surf,
                    ((self.piece.x + x) * CELL + offset_x,
                     (ty + bottom_y) * CELL)
                )

def get_ghost_y(piece, grid):
    ghost_y = piece.y

    while True:
        if not valid_move(piece, grid, dy=(ghost_y - piece.y) + 1):
            break
        ghost_y += 1

    return ghost_y

def draw_ghost(piece, grid, offset_x=0):
    ghost_y = get_ghost_y(piece, grid)
    for y, row in enumerate(piece.shape):
        for x, cell in enumerate(row):
            if cell:
                rect = pygame.Rect(
                    offset_x + (piece.x + x)*CELL,
                    (ghost_y + y)*CELL,
                    CELL,
                    CELL
                )
                pygame.draw.rect(screen, (100,100,100), rect, 2)

def draw_mini_piece(piece, x_offset, y_offset):
    size = CELL // 3

    shape = piece.shape
    width = len(shape[0])
    height = len(shape)

    box_size = 4 * size  # стандартное поле 4x4

    offset_x = (box_size - width * size) // 2
    offset_y = (box_size - height * size) // 2

    for y, row in enumerate(shape):
        for x, cell in enumerate(row):
            if cell:
                rect = pygame.Rect(
                    x_offset + offset_x + x * size,
                    y_offset + offset_y + y * size,
                    size,
                    size
                )
                pygame.draw.rect(screen, (255,255,255), rect)

def draw_preview_box(x, y):
    size = CELL // 3
    box = pygame.Rect(x, y, size*4, size*4)
    pygame.draw.rect(screen, (120,120,120), box, 2)

def find_full_lines(grid):
    lines = []
    for i, row in enumerate(grid):
        if all(row):
            lines.append(i)
    return lines

def get_next_piece():
    global next_queue
    p = next_queue.pop(0)
    next_queue.append(Piece())
    return p

def draw_opponent_grid(grid, offset_x):
    for y in range(ROWS):
        for x in range(COLS):
            cell = grid[y][x]
            if cell:
                rect = pygame.Rect(offset_x + x * CELL, y * CELL, CELL, CELL)
                if cell == 1:
                    color = (100, 100, 255)  # обычные блоки
                elif cell == 2:
                    color = (120, 120, 120)  # мусор (серый)
                else:
                    color = (64, 64, 64)
                pygame.draw.rect(screen, color, rect)

def run_game(multiplayer=False):
    global screen, clock, font
    global ROWS, COLS, WIDTH, HEIGHT
    global clearing_lines, next_queue

    pygame.init()
    clock = pygame.time.Clock()

    grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]
    if multiplayer:
        opponent_grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        WIDTH = WIDTH * 2 + 80  # 2 поля + пространство под интерфейс

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("simple-Tetris")
    font = pygame.font.SysFont("Arial", 24)

    held_piece = None #удерживание
    can_hold = True

    score_table = { #сколько очков за сколько линий
        1:100,
        2:300,
        3:500,
        4:800
    }
    next_queue = [Piece() for _ in range(3)]
    piece = Piece()
    fall_time = 0
    fall_speed = 0.25 #скорость падения
    score = 0 #счёт
    clearing_lines = [] #вспышка
    clear_timer = 0
    clear_duration = 0.2
    popups = [] #эффект добавления очков
    hard_drop_effects = [] #эффект падения блока

    while True:
        dt = clock.tick(60) / 1000
        fall_time += dt

        # обработка удаления линий
        if clear_timer > 0:
            clear_timer -= dt
            if clear_timer <= 0:
                for line in clearing_lines:
                    del grid[line]
                    grid.insert(0, [0] * COLS)
                points = score_table.get(len(clearing_lines), 0)
                score += points

                if multiplayer:
                    popups.append(ScorePopup(10+300+80 + len(f"Score: {score}") * 10, 10, f"+{points}"))
                else:
                    popups.append(ScorePopup(10 + len(f"Score: {score}") * 10, 10, f"+{points}"))

                clearing_lines = []

        # события
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            fall_speed = 0.25
            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_LEFT:
                    if valid_move(piece, grid, dx=-1):
                        piece.x -= 1

                if event.key == pygame.K_RIGHT:
                    if valid_move(piece, grid, dx=1):
                        piece.x += 1

                if event.key == pygame.K_DOWN:
                    if valid_move(piece, grid, dy=1):
                        fall_speed = 0.05

                if event.key == pygame.K_UP:
                    rotate_with_kick(piece, grid)

                if event.key == pygame.K_c and can_hold:  # удерживание фигуры
                    if held_piece is None:
                        held_piece = copy.deepcopy(piece)
                        piece = Piece()
                    else:
                        held_piece, piece = piece, held_piece
                        piece.x = COLS // 2
                        piece.y = 0
                    can_hold = False

                if event.key == pygame.K_SPACE:
                    drop_distance = get_ghost_y(piece, grid) - piece.y

                    start_y = piece.y
                    end_y = piece.y + drop_distance
                    hard_drop_effects.append(
                        HardDropEffect(piece, start_y, end_y)
                    )

                    piece.y += drop_distance

                    place_piece(piece, grid)  # сразу фиксация

                    lines = find_full_lines(grid)
                    if lines:
                        clearing_lines = lines
                        clear_timer = clear_duration

                    can_hold = True
                    piece = get_next_piece()

        # падение фигуры
        if fall_time > fall_speed:
            if valid_move(piece, grid, dy=1):
                piece.y += 1
            else:
                place_piece(piece, grid)

                lines = find_full_lines(grid)
                if lines:
                    clearing_lines = lines
                    clear_timer = clear_duration

                can_hold = True
                piece = get_next_piece()

                if not valid_move(piece, grid):
                    print("GAME OVER")
                    pygame.quit()
                    sys.exit()

            fall_time = 0

        # рисование
        screen.fill((0, 0, 0))

        player_offset_x = 0 if not multiplayer else COLS * CELL + 80

        # эффекты
        for effect in hard_drop_effects:
            effect.update(dt)
        hard_drop_effects = [e for e in hard_drop_effects if e.timer > 0]
        for effect in hard_drop_effects:
            effect.draw(screen, offset_x=player_offset_x)

        # мультиплеер рисуем opponent_grid слева
        if multiplayer:
            #draw_blocks(opponent_grid, offset_x=0)
            draw_opponent_grid(opponent_grid, 0)
            draw_grid(offset_x=0)

        # игровое поле игрока справа
        draw_blocks(grid, offset_x=player_offset_x)
        draw_ghost(piece, grid, offset_x=player_offset_x)
        draw_piece(piece, offset_x=player_offset_x)
        draw_grid(offset_x=player_offset_x)

        # интерфейс
        if multiplayer:
            ui_offset_x = player_offset_x
        else:
            ui_offset_x = COLS * CELL + 20  # немного отступаем от поля

        score_text = font.render(f"Score: {score}", True, (255, 255, 255))
        if multiplayer:
            screen.blit(score_text, (10+300+80, 10))
        else:
            screen.blit(score_text, (10, 10))

        for popup in popups:
            popup.update(dt)
        popups = [p for p in popups if p.timer > 0]
        for popup in popups:
            popup.draw(screen)

        # Hold
        draw_preview_box(WIDTH - 50, 40)
        if held_piece:
            draw_mini_piece(held_piece, WIDTH - 50, 40)
        hold_text = font.render("Hold:", True, (255, 255, 255))
        screen.blit(hold_text, (WIDTH - 55, 10))

        # Next
        for i, p in enumerate(next_queue):
            draw_preview_box(WIDTH - 50, 115 + i * 45)
            draw_mini_piece(p, WIDTH - 50, 115 + i * 45)
        next_text = font.render("Next:", True, (255, 255, 255))
        screen.blit(next_text, (WIDTH - 55, 30 + 55))

        pygame.display.update()
        clock.tick(60)