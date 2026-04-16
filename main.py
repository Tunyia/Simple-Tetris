import pygame
import sys
from menu import choose_mode
from tetris import TetrisGame

def main():
    # Инициализируем один раз при старте программы
    pygame.init()

    while True:
        # 1. Открываем меню. Оно заблокирует выполнение, пока не выберем режим.
        mode_data = choose_mode()

        # Если закрыли крестиком
        if not mode_data or mode_data.get("mode") is None:
            break

        current_mode = mode_data["mode"]
        is_multi = (current_mode != "single")
        network = mode_data.get("network")

        # 2. Игровой цикл (обработка реваншей)
        while True:
            # Создаем игру
            game = TetrisGame(multiplayer=is_multi, network_manager=network)
            result = game.run()

            if result == "rematch":
                # Для реванша просто создаем новый объект TetrisGame на следующем круге
                # Окно НЕ закрываем (display.quit не нужен, если экран тот же)
                continue
            else:
                # Если выходим в меню:
                if network:
                    network.stop()
                # Полностью гасим видео-систему перед возвратом в Tkinter
                pygame.display.quit()
                break

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()