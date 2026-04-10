import socket
import threading
import json

HOST = "0.0.0.0"
PORT = 5555

games = []  # список игр
game_id_counter = 1

clients = []

def broadcast_games():
    data = json.dumps({
        "type": "games",
        "games": games
    }).encode() + b"\n"

    for c in clients:
        try:
            c.sendall(data)
        except:
            pass

def handle_client(conn):
    global game_id_counter
    clients.append(conn)
    conn.settimeout(10)
    buffer = ""
    while True:
        try:
            data = conn.recv(4096)
            if not data:
                break  # Разрываем цикл, клиент отключился
            buffer += data.decode()
            while "\n" in buffer:
                msg, buffer = buffer.split("\n", 1)
                packet = json.loads(msg)
                if packet["type"] == "create_game":
                    game = {
                        "id": game_id_counter,
                        "name": packet["name"],
                        "players": 1
                    }
                    game_id_counter += 1
                    games.append(game)

                    broadcast_games()
                elif packet["type"] == "join_game":
                    game_id = packet["id"]
                    for g in games:
                        if g["id"] == game_id and g["players"] == 1:
                            g["players"] = 2
                            break
                    broadcast_games()

                elif packet["type"] == "get_games":
                    conn.sendall(json.dumps({
                        "type": "games",
                        "games": games
                    }).encode() + b"\n")
        except socket.timeout:
            continue
        except Exception as e:
            print("Client disconnected:", e)
            break
    clients.remove(conn)
    conn.close()


def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()

    print(f"Server started on port {PORT}")

    while True:
        conn, addr = s.accept()
        print("Client connected:", addr)
        threading.Thread(target=handle_client, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    start_server()
