import pygame
import sys
import copy
import random
import os
print("Tetris by Tunya")

# КОНСТАНТЫ
WIDTH, HEIGHT = 300, 600
BASE_WIDTH = 300
CELL = 30
ROWS = HEIGHT // CELL
COLS = WIDTH // CELL

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

# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ И КЛАССЫ
def rotate(shape):
    return [list(row) for row in zip(*shape[::-1])]

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

def get_ghost_y(piece, grid):
    ghost_y = piece.y

    while True:
        if not valid_move(piece, grid, dy=(ghost_y - piece.y) + 1):
            break
        ghost_y += 1

    return ghost_y

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def place_piece(piece, grid):
    for y, row in enumerate(piece.shape):
        for x, cell in enumerate(row):
            if cell:
                grid[piece.y + y][piece.x + x] = 1

def find_full_lines(grid):
    lines = []
    for i, row in enumerate(grid):
        if all(row):
            lines.append(i)
    return lines

def draw_blocks(screen, grid, offset_x=0, clearing_lines=None):
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

def draw_ghost(screen, piece, grid, offset_x=0):
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

def draw_piece(screen, piece, offset_x=0):
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

def draw_mini_piece(screen, piece, x_offset, y_offset):
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

def draw_preview_box(screen, x, y):
    size = CELL // 3
    box = pygame.Rect(x, y, size*4, size*4)
    pygame.draw.rect(screen, (120,120,120), box, 2)

def draw_opponent_grid(screen, grid, offset_x):
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

def draw_opponent_piece(screen, piece, offset_x):
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

def draw_grid(screen, offset_x=0):
    for y in range(ROWS):
        for x in range(COLS):
            rect = pygame.Rect(offset_x + x*CELL, y*CELL, CELL, CELL)
            pygame.draw.rect(screen, (40,40,40), rect, 1)

class Piece:
    def __init__(self, shape):
        self.shape = shape
        self.x = COLS // 2 - len(self.shape[0]) // 2
        self.y = 0

class ScorePopup:
    def __init__(self, x, y, text):
        self.x = x
        self.y = y
        self.text = text
        self.timer = 1.0

    def update(self, dt):
        self.timer -= dt

    def draw(self, screen, font):
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

# ОСНОВНОЙ КЛАСС ИГРЫ
class TetrisGame:
    def __init__(self, multiplayer=False, network_manager=None):
        # Настройки экрана и ресурсов
        self.game_running = False
        self.multiplayer = multiplayer
        self.network = network_manager
        self.my_name = "Player"
        self.opponent_name = "Opponent"

        self.base_width = 300
        self.height = 600
        self.width = (self.base_width * 2 + 80) if multiplayer else self.base_width

        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("simple-Tetris")

        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 24)
        self.big_font = pygame.font.SysFont("Arial", 48)

        # Загрузка ассетов
        self.images = {
            "back": pygame.transform.scale(pygame.image.load(resource_path("emojes/back.png")).convert_alpha(),
                                           (24, 24)),
            "reload": pygame.transform.scale(pygame.image.load(resource_path("emojes/reload.png")).convert_alpha(),
                                             (24, 24)),
            "warn": pygame.transform.scale(pygame.image.load(resource_path("emojes/warn.png")).convert_alpha(),
                                           (24, 24)),
            "approve": pygame.transform.scale(pygame.image.load(resource_path("emojes/aprove.png")).convert_alpha(),
                                              (24, 24))
        }

        # Игровое состояние
        self.bag = []
        self.next_queue = [Piece(self.get_shape()) for _ in range(3)]
        self.piece = Piece(self.get_shape())

        self.grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        self.piece = Piece(self.get_shape())
        self.next_queue = [Piece(self.get_shape()) for _ in range(3)]
        self.held_piece = None
        self.can_hold = True

        self.score = 0
        self.fall_time = 0
        self.fall_speed = 0.25
        self.game_over = False
        self.winner = None

        # Эффекты и очереди
        self.clearing_lines = []
        self.clear_timer = 0
        self.clear_duration = 0.2
        self.popups = []
        self.hard_drop_effects = []
        self.opponent_effects = []

        # Сетевые флаги
        self.my_ready = False
        self.rematch_triggered = False
        self.network_timer = 0
        self.reset_network_state()

        self.i_am_ready_for_rematch = False
        if self.network:
            self.network.game_should_start = False
        self.start_packet_sent = False

        # Шторка
        self.easing = 15
        self.curtain_y = 0
        self.curtain_opening = True
        self.curtain_closing = False

    def get_shape(self):
        if not self.bag:
            self.bag = copy.deepcopy(SHAPES)
            random.shuffle(self.bag)
        return self.bag.pop()

    def get_next_piece_from_queue(self):
        p = self.next_queue.pop(0)
        self.next_queue.append(Piece(self.get_shape()))
        return p

    def rotate_with_kick(self):
        new_shape = rotate(self.piece.shape) #Получаем новую форму
        kicks = [ # Список смещений для проверки (wall kicks)
            (0, 0),
            (-1, 0),
            (1, 0),
            (-2, 0),
            (2, 0),
            (0, -1)
        ]
        old_shape = self.piece.shape
        old_x = self.piece.x
        old_y = self.piece.y

        for dx, dy in kicks:
            self.piece.shape = new_shape
            # Вызываем внешнюю функцию валидации, передавая ей внутреннюю сетку
            if valid_move(self.piece, self.grid, dx=dx, dy=dy):
                self.piece.x += dx
                self.piece.y += dy
                return  # Успех! Выходим из метода

        self.piece.shape = old_shape
        self.piece.x = old_x
        self.piece.y = old_y

    def reset_network_state(self):
        if self.network:
            self.network.reset_for_rematch()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.network:
                    self.network.send_data({"type": "disconnect"})
                    self.network.stop()
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if not self.game_over:
                    self.handle_game_input(event.key)
                else:
                    self.handle_menu_input(event.key)

    def handle_game_input(self, key):
        self.fall_speed = 0.25
        if key == pygame.K_LEFT and valid_move(self.piece, self.grid, dx=-1):
            self.piece.x -= 1
        elif key == pygame.K_RIGHT and valid_move(self.piece, self.grid, dx=1):
            self.piece.x += 1
        elif key == pygame.K_UP:
            self.rotate_with_kick()
        elif key == pygame.K_c and self.can_hold:
            self.hold_logic()
        elif key == pygame.K_SPACE:
            self.execute_hard_drop()

    def handle_menu_input(self, key):
        if key == pygame.K_RETURN:
            if self.network:
                self.network.send_data({"type": "disconnect"})
                self.network.stop()
            pygame.display.quit()  # Закрываем именно видео-подсистему (окно исчезнет)
            self.game_running = False  # Выходим из цикла run()
        if key == pygame.K_r:
            self.i_am_ready_for_rematch = not self.i_am_ready_for_rematch
            if self.multiplayer and self.network:
                self.network.send_data({
                    "type": "rematch",
                    "ready": self.i_am_ready_for_rematch
                })

    def hold_logic(self):
        if self.held_piece is None:
            self.held_piece = copy.deepcopy(self.piece)
            self.piece = self.get_next_piece_from_queue()
        else:
            self.held_piece, self.piece = self.piece, self.held_piece
            self.piece.x, self.piece.y = COLS // 2, 0
        self.can_hold = False

    def execute_hard_drop(self):
        drop_dist = get_ghost_y(self.piece, self.grid) - self.piece.y
        start_y, end_y = self.piece.y, self.piece.y + drop_dist

        self.hard_drop_effects.append(HardDropEffect(self.piece, start_y, end_y))
        if self.multiplayer and self.network:
            self.network.send_data({
                "type": "hard_drop",
                "x": self.piece.x,
                "shape": self.piece.shape,
                "start_y": start_y,
                "end_y": end_y
            })

        self.piece.y += drop_dist
        place_piece(self.piece, self.grid)
        self.check_lines()
        self.can_hold = True
        self.piece = self.get_next_piece_from_queue()

    def check_lines(self):
        lines = find_full_lines(self.grid)
        if lines:
            self.clearing_lines = lines
            self.clear_timer = self.clear_duration
            if len(lines) >= 2 and self.multiplayer and self.network:
                self.network.send_data({"type": "garbage", "amount": len(lines) - 1})

    def update(self, dt):
        # 0.
        if self.multiplayer and self.network and self.network.opponent_disconnected:
            # Можно вывести уведомление "Оппонент ливнул"
            self.game_running = False
            self.exit_reason = "menu"
            pygame.display.quit()
            return

        # 1. Шторка
        if self.curtain_closing:
            target = 0
            self.curtain_y += (target - self.curtain_y) * self.easing * dt * 1.1
            if abs(self.curtain_y - target) < 2:  # Уменьшили порог до 2 пикселей
                self.curtain_y = target
                return "rematch"
        if self.curtain_opening:
            target = -self.height
            self.curtain_y += (target - self.curtain_y) * self.easing * dt * 1.1
            # Когда шторка почти уехала за экран (выше -HEIGHT + 2)
            if self.curtain_y <= target + 2:
                self.curtain_y = target  # ПРИНУДИТЕЛЬНО прячем её совсем
                self.curtain_opening = False

        # 2. Сеть и мусор
        self.process_network(dt)

        # 3. Логика очистки линий
        if self.clear_timer > 0:
            self.clear_timer -= dt
            if self.clear_timer <= 0:
                self.finalize_line_clear()

        # 4. Гравитация
        if not self.game_over and self.clear_timer <= 0:
            self.fall_time += dt
            if self.fall_time > self.fall_speed:
                self.apply_gravity()
                self.fall_time = 0

        return None

    def apply_gravity(self):
        if valid_move(self.piece, self.grid, dy=1):
            self.piece.y += 1
        else:
            place_piece(self.piece, self.grid)
            self.check_lines()
            self.can_hold = True
            self.piece = self.get_next_piece_from_queue()
            if not valid_move(self.piece, self.grid):
                self.game_over = True
                if self.multiplayer and self.network:
                    self.network.send_data({"type": "game_over"})

    def process_network(self, dt):
        if not self.multiplayer or not self.network:
            return

        self.network.poll()

        self.network_timer += dt
        if self.network.incoming_garbage > 0:
            self.add_garbage(self.network.incoming_garbage)
            self.network.incoming_garbage = 0

        if not self.game_over and self.network_timer >= 0.05:
            self.network.send_data({
                "type": "state", "grid": self.grid, "score": self.score,
                "piece": {"shape": self.piece.shape, "x": self.piece.x, "y": self.piece.y}
            })
            self.network_timer = 0

        while self.network.opponent_effects:
            data = self.network.opponent_effects.pop(0)
            self.opponent_effects.append(create_opponent_effect(data))

        if self.network.opponent_lost:
            self.game_over, self.winner = True, "me"

    def finalize_line_clear(self):
        for line in self.clearing_lines:
            del self.grid[line]
            self.grid.insert(0, [0] * COLS)
        points = {1: 100, 2: 300, 3: 500, 4: 800}.get(len(self.clearing_lines), 0)
        self.score += points

        if self.multiplayer:
            x_pop = 10 + 300 + 80 + len(f"Score: {self.score}") * 10
        else:
            x_pop = 10 + len(f"Score: {self.score}") * 10
        self.popups.append(ScorePopup(x_pop, 10, f"+{points}"))
        self.clearing_lines = []

    def add_garbage(self, count):
        if count <= 0:
            return

        hole_x = random.randint(0, COLS - 1)
        for _ in range(count):
            self.grid.pop(0)
            new_row = [2] * COLS
            new_row[hole_x] = 0
            self.grid.append(new_row)
            self.piece.y -= 1

        if not valid_move(self.piece, self.grid, 0, 0):
            if self.piece.y < 0:
                self.game_over = True

    def draw(self):
        self.screen.fill((0, 0, 0))
        player_off_x = (COLS * CELL + 80) if self.multiplayer else 0

        # 1. Сначала эффекты (самый нижний слой)
        for e in self.hard_drop_effects: e.draw(self.screen, offset_x=player_off_x)
        for e in self.opponent_effects: e.draw(self.screen, offset_x=0, inner=True)

        # 2. Отрисовка поля оппонента (если мультиплеер)
        if self.multiplayer:
            if self.network.opponent_grid:
                draw_opponent_grid(self.screen, self.network.opponent_grid, 0)
                draw_opponent_piece(self.screen, self.network.opponent_piece, 0)
            draw_grid(self.screen, offset_x=0)  # Сетка оппонента

        # 3. Твое поле: ПОРЯДОК ВАЖЕН
        draw_blocks(self.screen, self.grid, offset_x=player_off_x, clearing_lines=self.clearing_lines)
        draw_ghost(self.screen, self.piece, self.grid, offset_x=player_off_x)
        draw_piece(self.screen, self.piece, offset_x=player_off_x)  # Фигура ПОД сеткой
        draw_grid(self.screen, offset_x=player_off_x)  # Сетка ПОВЕРХ фигуры

        # 4. Интерфейс (Score, Hold, Next)
        self.draw_ui(player_off_x)

        if self.game_over: self.draw_overlay()

        # Шторка
        pygame.draw.rect(self.screen, (0, 0, 0), (0, self.curtain_y, self.width, self.height))
        pygame.display.update()

    def draw_ui(self, player_off_x):
        # Координаты для Score как в оригинале
        score_x = (10 + 300 + 80) if self.multiplayer else 10
        score_surf = self.font.render(f"Score: {self.score}", True, (255, 255, 255))
        self.screen.blit(score_surf, (score_x, 10))

        # Текст имен
        name_x = player_off_x + 10 if self.multiplayer else 10
        name_surf = self.font.render(self.my_name, True, (255, 255, 255))
        self.screen.blit(name_surf, (name_x, 34))
        if self.multiplayer:
            opp_surf = self.font.render(self.opponent_name, True, (255, 255, 255))
            self.screen.blit(opp_surf, (10, 34))

        # HOLD (находится справа вверху)
        hold_text = self.font.render("Hold:", True, (255, 255, 255))
        self.screen.blit(hold_text, (self.width - 55, 10))
        draw_preview_box(self.screen, self.width - 50, 40)
        if self.held_piece:
            draw_mini_piece(self.screen, self.held_piece, self.width - 50, 40)

        # NEXT (3 рамки ниже)
        next_text = self.font.render("Next:", True, (255, 255, 255))
        self.screen.blit(next_text, (self.width - 55, 85))  # 30 + 55 из твоего кода
        for i, p in enumerate(self.next_queue):
            box_y = 115 + i * 45
            draw_preview_box(self.screen, self.width - 50, box_y)
            draw_mini_piece(self.screen, p, self.width - 50, box_y)

        # Всплывающие очки
        for p in self.popups:
            p.draw(self.screen, self.font)

    def draw_side_panel(self, title, piece, y, show_text=True):
        if show_text:
            txt = self.font.render(title, True, (255, 255, 255))
            self.screen.blit(txt, (self.width - 55, y - 25 if "Next" in title else y - 30))
        draw_preview_box(self.screen, self.width - 50, y)
        if piece:
            draw_mini_piece(self.screen, piece, self.width - 50, y)

    def draw_overlay(self):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        title_color = (0, 255, 100) if self.winner == "me" else (255, 50, 50)
        title_text = "YOU WIN!" if self.winner == "me" else "GAME OVER"
        title_surf = self.big_font.render(title_text, True, title_color)
        self.screen.blit(title_surf, (self.width // 2 - title_surf.get_width() // 2, self.height // 2 - 100))

        '''score_surf = self.font.render(f"Final Score: {self.score}", True, (255, 255, 255))
        score_rect = score_surf.get_rect(center=(self.width // 2, self.height // 2 + 10))
        self.screen.blit(score_surf, score_rect)'''

        p1 = self.font.render(f"{self.my_name}: {self.score}", True, (255, 255, 255))
        self.screen.blit(p1, (self.width // 2 - p1.get_width() // 2, self.height // 2 - 30))

        if self.multiplayer:
            p2 = self.font.render(f"{self.opponent_name}: {self.network.opponent_score}", True, (255, 255, 255))
            self.screen.blit(p2, (self.width // 2 - p2.get_width() // 2, self.height // 2))

            # Кнопки меню (теперь вызываются вне зависимости от режима игры)
        y_off = self.height // 2 + 50
        self.draw_menu_item("       Press ENTER to menu", "back", y_off)

        # ЛОГИКА РЕВАНША / РЕСТАРТА
        if not self.multiplayer:
            # Одиночная игра
            self.draw_menu_item("       Press R for restart", "reload", y_off + 40)
        else:
            # Мультиплеер: проверяем состояния готовности
            opp_ready = self.network.rematch_ready
            me_ready = self.i_am_ready_for_rematch

            if me_ready and opp_ready:
                self.draw_menu_item("       Starting...", "approve", y_off + 40, (100, 255, 100))

            elif me_ready and not opp_ready:
                self.draw_menu_item("       Waiting for opponent...", "warn", y_off + 40, (255, 200, 100))

            elif not me_ready and opp_ready:
                self.draw_menu_item("       Opponent ready!", "approve", y_off + 40, (100, 255, 100))
                self.draw_menu_item("       Press R for rematch", "reload", y_off + 70)

            else:
                self.draw_menu_item("       Press R for rematch", "reload", y_off + 40)

    def draw_menu_item(self, text, icon_key, y, color=(200, 200, 200)):
        surf = self.font.render(text, True, color)
        x = self.width // 2 - surf.get_width() // 2
        self.screen.blit(surf, (x, y))
        self.screen.blit(self.images[icon_key], (x, y))

    def run(self):
        self.game_running = True
        start_packet_sent = False

        while self.game_running:
            dt = self.clock.tick(60) / 1000.0
            dt = min(dt, 0.05)

            self.handle_events()

            if not self.game_running: break

            if self.game_over:
                if self.multiplayer and self.network:
                    if self.network.opponent_disconnected or not self.network.running:
                        print("[DEBUG] Connection lost during GameOver")
                        return "menu"

                    if self.i_am_ready_for_rematch and self.network.rematch_ready:
                        if not start_packet_sent:
                            print("[DEBUG] Sending start_game packet...")
                            self.network.send_data({"type": "start_game"})
                            start_packet_sent = True

                    if self.network.game_should_start:
                        print("[DEBUG] Conditions met, restarting game!")
                        return "rematch"
                else:
                    if self.i_am_ready_for_rematch:
                        return "rematch"

            self.fall_speed = 0.25
            keys = pygame.key.get_pressed()
            if keys[pygame.K_DOWN]:
                self.fall_speed = 0.05

            # Обновление эффектов
            for e in self.hard_drop_effects: e.update(dt)
            self.hard_drop_effects = [e for e in self.hard_drop_effects if e.timer > 0]
            for e in self.opponent_effects: e.update(dt)
            self.opponent_effects = [e for e in self.opponent_effects if e.timer > 0]
            for p in self.popups: p.update(dt)
            self.popups = [p for p in self.popups if p.timer > 0]

            res = self.update(dt)
            if res: return res

            if (
                self.multiplayer
                and self.network
                and self.i_am_ready_for_rematch
                and self.network.rematch_ready
                and not self.rematch_triggered
            ):
                self.rematch_triggered = True
                self.curtain_closing = True

            self.draw()
            self.clock.tick(60)
        return "menu"

'''if __name__ == "__main__":
    pygame.init()  # Инициализируем pygame

    # Создаем игру.
    # Если хочешь проверить мультиплеер (два поля), поставь True
    game = TetrisGame(multiplayer=False)

    # Запускаем мотор!
    result = game.run()

    print(f"Игра окончена. Результат: {result}")
    pygame.quit()'''

'''def run_game(multiplayer=False):
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

    EASING = 15
    curtain_y = 0  # экран изначально закрыт
    curtain_opening = True
    curtain_closing = False

    while True:
        dt = clock.tick(60) / 1000
        dt = min(dt, 0.05)
        fall_time += dt
        network_timer += dt

        if curtain_closing:
            target = 0
            curtain_y += (target - curtain_y) * EASING * dt * 1.1
            if abs(curtain_y - target) < 15:
                curtain_y = target
                return "rematch"
        if curtain_opening:
            target = -HEIGHT
            curtain_y += (target - curtain_y) * EASING * dt * 1.1
            if abs(curtain_y - target) < 15:
                curtain_y = target
                curtain_opening = False

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
            curtain_closing = True  #return "rematch"

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
                        curtain_closing = True #return "rematch"
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
            emoji_img = pygame.transform.scale( pygame.image.load(resource_path("emojes/back.png")).convert_alpha(), (24, 24))
            screen.blit(emoji_img, (WIDTH // 2 - enter.get_width() // 2, HEIGHT // 2 + 50))

            if not my_ready:
                if multiplayer:
                    txt = small_font.render("       Press R for rematch", True, (200, 200, 200))
                else:
                    txt = small_font.render("       Press R for restart", True, (200, 200, 200))
                screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 + 80))
                emoji_img = pygame.transform.scale(pygame.image.load(resource_path("emojes/reload.png")).convert_alpha(), (24, 24))
                screen.blit(emoji_img, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 + 80))
            else:
                txt = small_font.render("       Waiting for opponent...", True, (255, 200, 100))
                screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 + 80))
                emoji_img = pygame.transform.scale(pygame.image.load(resource_path("emojes/warn.png")).convert_alpha(), (24, 24))
                screen.blit(emoji_img, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 + 80))
            if opponent_ready:
                txt2 = small_font.render("       Opponent ready for rematch!", True, (100, 255, 100))
                screen.blit(txt2, (WIDTH // 2 - txt2.get_width() // 2, HEIGHT // 2 + 110))
                emoji_img = pygame.transform.scale(pygame.image.load(resource_path("emojes/aprove.png")).convert_alpha(), (24, 24))
                screen.blit(emoji_img, (WIDTH // 2 - txt2.get_width() // 2, HEIGHT // 2 + 110))

        curtain = pygame.Rect(0, curtain_y, WIDTH, HEIGHT)
        pygame.draw.rect(screen, (0, 0, 0), curtain)

        pygame.display.update()
        clock.tick(60)'''