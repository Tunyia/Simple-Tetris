import socket
import threading
import json
import time


class NetworkManager:
    def __init__(self):
        self.conn = None
        self.server_socket = None
        self.role = None
        self.running = False
        self.game_should_start = False  # Добавили инициализацию

        # Состояние оппонента
        self.opponent_grid = None
        self.opponent_piece = None
        self.opponent_score = 0
        self.opponent_lost = False
        self.opponent_disconnected = False
        self.incoming_garbage = 0
        self.opponent_effects = []
        self.rematch_ready = False

    def start_server(self, on_connected, on_status, on_port):
        self.role = "host"

        def run():
            try:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.bind(("0.0.0.0", 12345))  # Или 0 для авто-порта
                self.server_socket.listen(1)
                on_port(self.server_socket.getsockname()[1])

                self.conn, _ = self.server_socket.accept()
                self.running = True
                self.start_receive_thread()
                on_connected()
            except Exception as e:
                on_status(f"Error: {e}")

        threading.Thread(target=run, daemon=True).start()

    def start_client(self, ip, port, on_success, on_fail):
        self.role = "client"

        def run():
            try:
                self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.conn.settimeout(5)
                self.conn.connect((ip, port))
                self.running = True
                self.start_receive_thread()
                on_success()
            except Exception as e:
                print(e)
                on_fail()

        threading.Thread(target=run, daemon=True).start()

    def send_data(self, data):
        if not self.conn or not self.running:
            return
        try:
            message = json.dumps(data) + "\n"
            self.conn.sendall(message.encode())
        except (OSError, BrokenPipeError, ConnectionResetError) as e:
            print(f"[NETWORK] Error sending data: {e}")
            self.running = False
            self.opponent_disconnected = True  # Этот флаг мы проверим в игре

    def start_receive_thread(self):
        threading.Thread(target=self.receive_loop, daemon=True).start()

    def receive_loop(self):
        buffer = ""
        while self.running:
            try:
                # Читаем данные
                data = self.conn.recv(4096).decode()
                if not data:
                    print("[NETWORK] Connection closed by peer")
                    break

                buffer += data
                while "\n" in buffer:
                    msg, buffer = buffer.split("\n", 1)
                    if not msg.strip(): continue
                    packet = json.loads(msg)
                    self.parse_packet(packet)
            except socket.timeout:
                # !!!если данных нет 5 секунд, мы просто уходим на новый круг цикла, а не закрываем соединение.
                continue
            except Exception as e:
                print(f"[NETWORK] Receive error: {e}")
                break
        self.stop()
        self.opponent_disconnected = True

    def parse_packet(self, packet):
        p_type = packet.get("type")

        # Логика обработки
        if p_type == "state":
            self.opponent_grid = packet.get("grid")
            self.opponent_piece = packet.get("piece")
            self.opponent_score = packet.get("score", 0)
        elif p_type == "garbage":
            self.incoming_garbage += packet.get("amount", 0)
        elif p_type == "hard_drop":
            self.opponent_effects.append(packet)
        elif p_type == "game_over":
            self.opponent_lost = True
        elif p_type == "rematch":
            self.rematch_ready = packet.get("ready", False)
        elif p_type == "start_game":
            print("[NETWORK] Start game signal received!")
            self.game_should_start = True  # ТЕПЕРЬ ФЛАГ ПОДНИМАЕТСЯ
        elif p_type == "disconnect":
            self.opponent_disconnected = True
            self.running = False

    def reset_for_rematch(self):
        self.opponent_grid = None
        self.opponent_piece = None
        self.opponent_lost = False
        self.opponent_disconnected = False
        self.incoming_garbage = 0
        self.opponent_effects = []
        self.rematch_ready = False
        self.game_should_start = False  # Сбрасываем для следующего раза

    def stop(self):
        self.running = False
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        self.conn = None