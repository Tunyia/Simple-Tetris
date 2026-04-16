import pygame
from menu import choose_mode
from tetris import TetrisGame

while True:
    pygame.init()
    # Открываем меню
    mode_data = choose_mode()

    # 1. Если нажали "Cancel" или закрыли крестиком
    if not mode_data or mode_data["mode"] is None:
        break

    current_mode = mode_data["mode"]
    is_multi = (current_mode != "single")

    # 2. Игровой цикл (обработка реваншей)
    while True:
        game = TetrisGame(multiplayer=is_multi)
        result = game.run()

        if result == "rematch":
            pygame.display.quit()
            continue # внутренний цикл сработает снова, создав новый объект TetrisGame
        else:
            break # менюшка
pygame.quit()