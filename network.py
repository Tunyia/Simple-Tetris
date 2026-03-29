import socket
import threading
import json

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

# SERVER
def start_server(on_connected, on_status):
    global role
    role = "host"
    print("HOST")
    def run():
        global server_socket, conn, running
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.bind(("0.0.0.0", 12345))
            server_socket.listen(1)

            conn, _ = server_socket.accept()
            running = True

            start_receive_thread()

            on_connected()
        except:
            on_status("Server stopped")
    threading.Thread(target=run, daemon=True).start()

# CLIENT
def start_client(ip, on_success, on_fail):
    global role
    role = "client"
    print("CLIENT")
    def run():
        global client_socket, conn, running
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(3)
            client_socket.connect((ip, 12345))

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


def receive_loop():
    global opponent_grid, incoming_garbage, running, opponent_piece, opponent_effects_but_in_network

    buffer = ""
    while running:
        try:
            data = conn.recv(4096).decode()
            if not data:
                break

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

                elif packet["type"] == "garbage":
                    incoming_garbage += packet["amount"]

                elif packet["type"] == "message":
                    print("Received message:", packet["message"])

                elif packet["type"] == "hard_drop":
                    opponent_effects_but_in_network.append(packet)
        except:
            break

# STOP
def stop():
    global running, server_socket, client_socket, conn

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