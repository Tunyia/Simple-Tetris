from menu import choose_mode
from tetris import run_game

while True:
    mode_data = choose_mode()

    mode = mode_data["mode"]
    ip = mode_data["ip"]

    if mode is None:
        break  # выход из программы

    while True:
        if mode == "single":
            result = run_game(multiplayer=False)
        elif mode == "host":
            result = run_game(multiplayer=True)
        elif mode == "join":
            result = run_game(multiplayer=True)
        else:
            break

        # обработка результата игры
        if result == "rematch":
            continue  # перезапустить игру

        break  # выйти в меню