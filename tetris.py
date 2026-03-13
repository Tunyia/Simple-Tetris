import pygame
import sys
import copy
import random
print("Tetris by Tunya")

pygame.init()

WIDTH = 300
HEIGHT = 600
CELL = 30

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tetris")

clock = pygame.time.Clock()

ROWS = HEIGHT // CELL
COLS = WIDTH // CELL

grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]

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

def draw_grid():
    for y in range(ROWS):
        for x in range(COLS):
            rect = pygame.Rect(x*CELL, y*CELL, CELL, CELL)
            pygame.draw.rect(screen, (40,40,40), rect, 1)

class Piece:
    def __init__(self):
        self.shape = copy.deepcopy(get_next_shape())
        self.x = COLS // 2
        self.y = 0

def draw_piece(piece):
    for y, row in enumerate(piece.shape):
        for x, cell in enumerate(row):
            if cell:
                rect = pygame.Rect(
                    (piece.x + x)*CELL,
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

def draw_blocks(grid):
    for y in range(ROWS):
        for x in range(COLS):
            if grid[y][x]:
                rect = pygame.Rect(x*CELL, y*CELL, CELL, CELL)
                pygame.draw.rect(screen, (255,100,100), rect)
                if y in clearing_lines:
                    pygame.draw.rect(screen, (255, 255, 255), rect)
                else:
                    pygame.draw.rect(screen, (255, 100, 100), rect)

def rotate(shape):
    return [list(row) for row in zip(*shape[::-1])]

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
        self.timer = 0.3

    def update(self, dt):
        self.timer -= dt

    def draw(self, screen):
        alpha = int(255 * (self.timer / 0.15))
        surf = pygame.Surface((CELL, CELL))
        surf.set_alpha(alpha)
        surf.fill((180,180,180))

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
            for ty in range(self.start_y, self.end_y):
                screen.blit(
                    surf,
                    ((self.piece.x + x) * CELL,
                     (ty + bottom_y) * CELL)
                )

def get_ghost_y(piece, grid):
    ghost_y = piece.y

    while True:
        if not valid_move(piece, grid, dy=(ghost_y - piece.y) + 1):
            break
        ghost_y += 1

    return ghost_y

def draw_ghost(piece, grid):
    ghost_y = get_ghost_y(piece, grid)

    for y, row in enumerate(piece.shape):
        for x, cell in enumerate(row):
            if cell:
                rect = pygame.Rect(
                    (piece.x + x)*CELL,
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
font = pygame.font.SysFont("Arial", 24)
clearing_lines = [] #вспышка
clear_timer = 0
clear_duration = 0.2
popups = [] #эффект добавления очков
hard_drop_effects = [] #эффект падения блока
while True:
    dt = clock.tick(60) / 1000
    fall_time += dt

    if clear_timer > 0:
        clear_timer -= dt
        if clear_timer <= 0:
            for line in clearing_lines:
                del grid[line]
                grid.insert(0, [0] * COLS)
            points = score_table.get(len(clearing_lines), 0)
            score += points

            popups.append(
                ScorePopup(10 + len(f"Score: {score}") * 10, 10, f"+{points}")
            )

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
                new_shape = rotate(piece.shape)
                old_shape = piece.shape
                piece.shape = new_shape
                if not valid_move(piece, grid):
                    piece.shape = old_shape
                else:
                    lock_timer = 0

            if event.key == pygame.K_c and can_hold: #удерживание фигуры
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
                #score += drop_distance * 2

                place_piece(piece, grid) #сразу фиксация

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

    for effect in hard_drop_effects:
        effect.update(dt)
    hard_drop_effects = [e for e in hard_drop_effects if e.timer > 0]
    for effect in hard_drop_effects:
        effect.draw(screen)

    draw_blocks(grid)
    draw_ghost(piece, grid)
    draw_piece(piece)
    draw_grid()

    score_text = font.render(f"Score: {score}", True, (255, 255, 255))
    screen.blit(score_text, (10, 10))

    for popup in popups:
        popup.update(dt)
    popups = [p for p in popups if p.timer > 0]
    for popup in popups:
        popup.draw(screen)

    draw_preview_box(WIDTH - 50, 40)
    if held_piece:
        draw_mini_piece(held_piece, WIDTH - 50, 40)
    hold_text = font.render("Hold:", True, (255, 255, 255))
    screen.blit(hold_text, (WIDTH - 55, 10))

    for i, p in enumerate(next_queue):
        draw_preview_box(WIDTH - 50, 115+i*45)
        draw_mini_piece(p, WIDTH - 50, 115 + i*45)
    hold_text = font.render("Next:", True, (255, 255, 255))
    screen.blit(hold_text, (WIDTH - 55, 30+55))

    pygame.display.update()
    clock.tick(60)
