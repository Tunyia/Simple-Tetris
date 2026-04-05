import pygame
import sys
import copy
import random
import network
print("Tetris by Tunya")

CELL = 30
WIDTH = 300
HEIGHT = 600
BASE_WIDTH = 300

ROWS = HEIGHT // CELL
COLS = WIDTH // CELL

screen = None
clock = None
font = None

clearing_lines = []
next_queue = []

my_name = "Player"
opponent_name = "Opponent"

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
                pygame.draw.rect(screen, (0,200,255), rect) #(255, 100, 100)

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

    def draw(self, screen, offset_x=0, inner=False):
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
                if inner:
                    surf.fill((215, 155, 215))

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

def draw_opponent_piece(piece, offset_x):
    if not piece:
        return

    shape = piece["shape"]
    px = piece["x"]
    py = piece["y"]

    for y, row in enumerate(shape):
        for x, cell in enumerate(row):
            if cell:
                rect = pygame.Rect(
                    offset_x + (px + x) * CELL,
                    (py + y) * CELL,
                    CELL,
                    CELL
                )
                pygame.draw.rect(screen, (100, 100, 255), rect)

def create_opponent_effect(data):
    fake_piece = type("FakePiece", (), {})()

    fake_piece.shape = data["shape"]
    fake_piece.x = data["x"]
    fake_piece.y = data["start_y"]

    return HardDropEffect(
        fake_piece,
        data["start_y"],
        data["end_y"]
    )

def run_game(multiplayer=False):
    global screen, clock, font
    global ROWS, COLS, WIDTH, HEIGHT
    global clearing_lines, next_queue
    global opponent_effects

    pygame.init()
    clock = pygame.time.Clock()

    grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]
    if multiplayer:
        opponent_grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        WIDTH = BASE_WIDTH * 2 + 80  # 2 поля + пространство под интерфейс
    else:
        WIDTH = BASE_WIDTH
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
    opponent_effects = []
    game_over = False
    winner = None  # "me" / "opponent"
    my_ready = False # сетевые флаги
    opponent_ready = False
    #waiting_for_rematch = False
    network.rematch_ready = False # очистка network-флагов
    rematch_triggered = False

    network.opponent_grid = None
    network.opponent_piece = None
    network.opponent_effects_but_in_network = []
    network.opponent_lost = False
    network.opponent_score = 0
    network_timer = 0

    while True:
        dt = clock.tick(60) / 1000
        dt = min(dt, 0.05)
        fall_time += dt
        network_timer += dt

        if network.incoming_garbage > 0: # завоз входящего мусора
            for _ in range(network.incoming_garbage):
                grid.pop(0)

                hole = random.randint(0, COLS - 1)
                new_row = [2] * COLS
                new_row[hole] = 0

                grid.append(new_row)
            network.incoming_garbage = 0
        if not game_over:
            if network_timer >= 0.05:
                network.send_data({ # отправка своего поля + падающая фигура оппоненту
                    "type": "state",
                    "grid": grid,
                    "piece": {
                        "shape": piece.shape,
                        "x": piece.x,
                        "y": piece.y
                    },
                    "score": score
                })
                network_timer = 0

        # создаём эффекты из сети
        while network.opponent_effects_but_in_network:
            data = network.opponent_effects_but_in_network.pop(0)
            opponent_effects.append(create_opponent_effect(data))

        if network.opponent_lost: # если игра окончена
            game_over = True
            winner = "me"

        if not network.running and multiplayer: #если связь оборвётся
            print("Connection lost")
            pygame.quit()
            network.stop()
            return  # выйти в меню

        opponent_ready = network.rematch_ready

        if my_ready and opponent_ready and not rematch_triggered:
            rematch_triggered = True
            return "rematch"

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
                network.send_data({"type": "disconnect"})
                pygame.quit()
                network.stop()
                sys.exit()

            fall_speed = 0.25
            if event.type == pygame.KEYDOWN:

                if not game_over:
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
                        hard_drop_effects.append( HardDropEffect(piece, start_y, end_y)) #эффект у себя
                        network.send_data({ #эффект свой для врага
                            "type": "hard_drop",
                            "x": piece.x,
                            "shape": piece.shape,
                            "start_y": start_y,
                            "end_y": end_y
                        })
                        piece.y += drop_distance
                        place_piece(piece, grid)  # сразу фиксация

                        lines = find_full_lines(grid)
                        if lines:
                            clearing_lines = lines
                            clear_timer = clear_duration
                            if len(clearing_lines) >= 2: # отправка мусорных линий
                                garbage = len(clearing_lines) - 1
                                network.send_data({
                                    "type": "garbage",
                                    "amount": garbage
                                })

                        can_hold = True
                        piece = get_next_piece()

                if game_over and event.key == pygame.K_RETURN:
                    network.send_data({"type": "disconnect"})
                    pygame.quit()
                    network.stop()
                    return  # выйти из run_game()
                if game_over and event.key == pygame.K_r:
                    if multiplayer:
                        my_ready = not my_ready
                        #waiting_for_rematch = my_ready
                        network.send_data({
                            "type": "rematch",
                            "ready": my_ready
                        })
                        print(f"REMATCH?: {my_ready}")
                    else:
                        return "rematch"
                        print("RESTART")

        if not game_over:
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
                        if len(clearing_lines) >= 2:  # отправка мусорных линий
                            garbage = len(clearing_lines) - 1
                            network.send_data({
                                "type": "garbage",
                                "amount": garbage
                            })

                    can_hold = True
                    piece = get_next_piece()
                    if not valid_move(piece, grid):
                        print("GAME OVER")
                        game_over = True
                        network.send_data({"type": "game_over"})

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

        for effect in opponent_effects:
            effect.update(dt)
        opponent_effects = [e for e in opponent_effects if e.timer > 0]
        for effect in opponent_effects:
            effect.draw(screen, offset_x=0, inner=True)  # ВАЖНО

        # мультиплеер рисуем opponent_grid слева
        if multiplayer:
            if network.opponent_grid:
                draw_opponent_grid(network.opponent_grid, 0)
                draw_opponent_piece(network.opponent_piece, 0)
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

        # для дебага показываем роль
        if multiplayer:
            role_text = "H" if network.role == "host" else "C"
            debug_surf = font.render(role_text, True, (255, 255, 0))
            screen.blit(debug_surf, (0, HEIGHT - 22))

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

        if multiplayer:
            name_text = font.render(my_name, True, (255, 255, 255))
            screen.blit(name_text, (player_offset_x+10, 10+24))

            enemy_name_text = font.render(opponent_name, True, (255, 255, 255))
            screen.blit(enemy_name_text, (10, 10+24))
        else:
            name_text = font.render(my_name, True, (255, 255, 255))
            screen.blit(name_text, (0+10, 10+24))

        if game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(180)
            overlay.fill((0, 0, 0))
            screen.blit(overlay, (0, 0))

            big_font = pygame.font.SysFont("Arial", 48)
            small_font = pygame.font.SysFont("Arial", 24)

            if winner == "me":
                title = big_font.render("YOU WIN!", True, (0, 255, 100))
            else:
                title = big_font.render("GAME OVER", True, (255, 50, 50))

            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 100))

            # имена
            p1 = small_font.render(f"{my_name}: {score}", True, (255, 255, 255))
            screen.blit(p1, (WIDTH // 2 - p1.get_width() // 2, HEIGHT // 2 - 30))

            if multiplayer:
                p2 = small_font.render(f"{opponent_name}: {network.opponent_score}", True, (255, 255, 255))
                screen.blit(p2, (WIDTH // 2 - p2.get_width() // 2, HEIGHT // 2))

            # кнопки
            enter = small_font.render("       Press ENTER to return to menu", True, (200, 200, 200))
            screen.blit(enter, (WIDTH // 2 - enter.get_width() // 2, HEIGHT // 2 + 50))
            emoji_img = pygame.transform.scale( pygame.image.load("emojes/back.png").convert_alpha(), (24, 24))
            screen.blit(emoji_img, (WIDTH // 2 - enter.get_width() // 2, HEIGHT // 2 + 50))

            if not my_ready:
                if multiplayer:
                    txt = small_font.render("       Press R for rematch", True, (200, 200, 200))
                else:
                    txt = small_font.render("       Press R for restart", True, (200, 200, 200))
                screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 + 80))
                emoji_img = pygame.transform.scale(pygame.image.load("emojes/reload.png").convert_alpha(), (24, 24))
                screen.blit(emoji_img, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 + 80))
            else:
                txt = small_font.render("       Waiting for opponent...", True, (255, 200, 100))
                screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 + 80))
                emoji_img = pygame.transform.scale(pygame.image.load("emojes/warn.png").convert_alpha(), (24, 24))
                screen.blit(emoji_img, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 + 80))
            if opponent_ready:
                txt2 = small_font.render("       Opponent ready for rematch!", True, (100, 255, 100))
                screen.blit(txt2, (WIDTH // 2 - txt2.get_width() // 2, HEIGHT // 2 + 110))
                emoji_img = pygame.transform.scale(pygame.image.load("emojes/aprove.png").convert_alpha(), (24, 24))
                screen.blit(emoji_img, (WIDTH // 2 - txt2.get_width() // 2, HEIGHT // 2 + 110))

        pygame.display.update()
        clock.tick(60)