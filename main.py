from menu import choose_mode
from tetris import run_game

mode_data = choose_mode()

mode = mode_data["mode"]
ip = mode_data["ip"]

if mode == "single":
    run_game(multiplayer=False)

elif mode == "host":
    run_game(multiplayer=True)

elif mode == "join":
    run_game(multiplayer=True)

else:
    print("Exit")
