import socket
import threading
import json
import time

server_socket = None
client_socket = None
conn = None
role = None  # "host" или "client"

running = False

# данные от оппонента
opponent_grid = None
incoming_garbage = 0
opponent_piece = None
opponent_effects_but_in_network = []
opponent_lost = False
rematch_ready = False
opponent_score = 0

# SERVER
def start_server(on_connected, on_status, on_port):
    global role
    role = "host"
    print("HOST")
    def run():
        global server_socket, conn, running
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                server_socket.bind(("0.0.0.0", 12345))
            except:
                server_socket.bind(("0.0.0.0", 0))
            server_socket.listen(1)
            port = server_socket.getsockname()[1]
            on_port(port)  #сообщаем UI

            conn, _ = server_socket.accept()
            running = True

            start_receive_thread()

            on_connected()
        except:
            on_status("Server stopped")
    threading.Thread(target=run, daemon=True).start()

# CLIENT
def start_client(ip, port, on_success, on_fail):
    global role
    role = "client"
    print("CLIENT")
    def run():
        global client_socket, conn, running
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(3)
            client_socket.connect((ip, port))

            conn = client_socket
            running = True

            start_receive_thread()

            on_success()
        except:
            on_fail()
    threading.Thread(target=run, daemon=True).start()

# SEND
def send_data(data):
    global conn
    if not conn:
        return  # не отправляем если нет соединения
    try:
        message = json.dumps(data).encode()
        conn.sendall(message + b"\n")
    except:
        pass

# RECEIVE
def start_receive_thread():
    threading.Thread(target=receive_loop, daemon=True).start()

log_timer = 0
def receive_loop():
    global opponent_grid, incoming_garbage, running, opponent_piece, opponent_effects_but_in_network, \
    opponent_lost, rematch_ready, log_timer
    print(f"{time.strftime("%H:%M:%S", time.localtime())} receive_loop: start!")

    buffer = ""
    while running:
        try:
            log_timer += 1
            if log_timer > 10:
                print(f"{time.strftime("%H:%M:%S", time.localtime())} receive_loop: working")
                log_timer = 0

            data = conn.recv(4096).decode()

            buffer += data
            while "\n" in buffer:
                msg, buffer = buffer.split("\n", 1)
                packet = json.loads(msg)

                if packet["type"] == "grid":
                    opponent_grid = packet["grid"]
                    #print("GRID RECEIVED", len(opponent_grid))

                elif packet["type"] == "state":
                    opponent_grid = packet["grid"]
                    opponent_piece = packet["piece"]
                    opponent_score = packet.get("score", 0)

                elif packet["type"] == "garbage":
                    incoming_garbage += packet["amount"]

                elif packet["type"] == "message":
                    print("Received message:", packet["message"])

                elif packet["type"] == "hard_drop":
                    opponent_effects_but_in_network.append(packet)

                elif packet["type"] == "game_over":
                    opponent_lost = True

                elif packet["type"] == "rematch":
                    rematch_ready = packet.get("ready", False)

                elif packet["type"] == "disconnect":
                    print("Opponent disconnected")
                    running = False
        except Exception as e:
            print(f"receive_loop error: {e}")

# STOP
def stop():
    global running, server_socket, client_socket, conn
    global opponent_grid, incoming_garbage, opponent_piece, opponent_effects_but_in_network
    global rematch_ready

    running = False

    try:
        if conn:
            conn.close()
    except:
        pass

    try:
        if server_socket:
            server_socket.close()
    except:
        pass

    try:
        if client_socket:
            client_socket.close()
    except:
        pass

    # СБРОС СОСТОЯНИЯ
    conn = None
    server_socket = None
    client_socket = None

    opponent_grid = None
    incoming_garbage = 0
    opponent_piece = None
    opponent_effects_but_in_network = []
    rematch_ready = False
