from menu import choose_mode
from tetris import run_game

while True:
    # 1. Открываем меню
    mode_data = choose_mode()

    # Если нажали "Cancel" или закрыли крестиком
    if not mode_data or mode_data["mode"] is None:
        break

    current_mode = mode_data["mode"]

    # 2. Игровой цикл
    while True:
        # запуск игры
        is_multi = (current_mode != "single")
        result = run_game(multiplayer=is_multi)

        # после окончания игры обработка результата
        if result == "rematch":
            continue  # перезапускаем игру (остаемся во внутреннем цикле)
        else:
            break  # выходим из игры (прерываем внутренний цикл -> вернемся в меню)