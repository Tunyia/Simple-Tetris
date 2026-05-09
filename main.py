import os
import sys

import pygame

from menu import choose_mode
from tetris import TetrisGame


def main():
    while True:
        mode_data = choose_mode()

        if not mode_data or mode_data.get("mode") is None:
            break

        pos = mode_data.get("window_pos")
        if pos and len(pos) == 2:
            os.environ["SDL_VIDEO_WINDOW_POS"] = f"{int(pos[0])},{int(pos[1])}"
        else:
            os.environ.pop("SDL_VIDEO_WINDOW_POS", None)

        pygame.init()

        current_mode = mode_data["mode"]
        is_multi = current_mode != "single"
        network = mode_data.get("network")

        try:
            while True:
                if is_multi and network:
                    network.poll()
                    if not network.running or network.opponent_disconnected:
                        print("[SYSTEM] Connection lost. Returning to menu...")
                        network.stop()
                        pygame.display.quit()
                        break

                if network:
                    network.reset_for_rematch()

                game = TetrisGame(
                    multiplayer=is_multi,
                    network_manager=network,
                    player_name=mode_data.get("nickname") or "Player",
                )
                result = game.run()

                if result == "rematch":
                    continue

                if network:
                    network.stop()
                pygame.display.quit()
                break
        finally:
            pygame.quit()

    sys.exit(0)


if __name__ == "__main__":
    main()
