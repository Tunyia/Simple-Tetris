import sys

import pygame

from menu import choose_mode
from tetris import TetrisGame


def main():
    while True:
        mode_data = choose_mode()

        if not mode_data or mode_data.get("mode") is None:
            break

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

                game = TetrisGame(multiplayer=is_multi, network_manager=network)
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
