import json
import queue
import socket
import threading
from typing import Any, Callable, Dict, List, Optional


class NetworkManager:
    """
    LAN session: accept/connect in a worker thread, recv in a daemon thread.
    All game-visible state is updated from the main thread via poll().
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._incoming = queue.Queue()

        self.conn: Optional[socket.socket] = None
        self.server_socket: Optional[socket.socket] = None
        self.role: Optional[str] = None
        self.listen_port: Optional[int] = None

        self.running = False

        self.opponent_grid = None
        self.opponent_piece = None
        self.opponent_score = 0
        self.opponent_lost = False
        self.opponent_disconnected = False
        self.incoming_garbage = 0
        self.opponent_effects: List[Dict[str, Any]] = []
        self.rematch_ready = False
        self.game_should_start = False

    def _drain_incoming(self) -> None:
        while True:
            try:
                self._incoming.get_nowait()
            except queue.Empty:
                break

    def _close_listen_socket(self) -> None:
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None

    def _close_conn(self) -> None:
        if self.conn:
            try:
                self.conn.close()
            except OSError:
                pass
            self.conn = None

    def _receive_loop(self) -> None:
        buffer = ""
        while not self._stop_event.is_set():
            with self._lock:
                conn = self.conn
            if not conn:
                break
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                self._incoming.put({"type": "__connection_lost__", "reason": "recv_os"})
                break

            if not chunk:
                self._incoming.put({"type": "__connection_lost__", "reason": "peer_closed"})
                break

            try:
                buffer += chunk.decode("utf-8")
            except UnicodeDecodeError:
                self._incoming.put({"type": "__connection_lost__", "reason": "decode"})
                break

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    packet = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(packet, dict):
                    self._incoming.put(packet)

        with self._lock:
            self.running = False

    def _start_receive_thread(self) -> None:
        threading.Thread(target=self._receive_loop, name="net-recv", daemon=True).start()

    def start_server(
        self,
        on_connected: Callable[[], None],
        on_status: Callable[[str], None],
        on_port: Callable[[int], None],
    ) -> None:
        self.role = "host"

        def run() -> None:
            try:
                self._stop_event.clear()
                self._drain_incoming()
                with self._lock:
                    self._close_listen_socket()
                    self._close_conn()
                    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    srv.bind(("0.0.0.0", 0))
                    srv.listen(1)
                    self.server_socket = srv
                    self.listen_port = int(srv.getsockname()[1])

                on_port(self.listen_port)

                conn, _ = srv.accept()

                with self._lock:
                    try:
                        srv.close()
                    except OSError:
                        pass
                    self.server_socket = None
                    conn.settimeout(0.5)
                    self.conn = conn

                self.running = True
                self.opponent_disconnected = False
                self._start_receive_thread()
                on_connected()
            except Exception as e:
                with self._lock:
                    self._close_listen_socket()
                    self._close_conn()
                self.running = False
                on_status(f"Error: {e}")

        threading.Thread(target=run, name="net-host", daemon=True).start()

    def start_client(
        self,
        ip: str,
        port: int,
        on_success: Callable[[], None],
        on_fail: Callable[[], None],
    ) -> None:
        self.role = "client"

        def run() -> None:
            try:
                self._stop_event.clear()
                self._drain_incoming()
                with self._lock:
                    self._close_conn()
                    c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    c.settimeout(10.0)
                    c.connect((ip, port))
                    c.settimeout(0.5)
                    self.conn = c

                self.running = True
                self.opponent_disconnected = False
                self._start_receive_thread()
                on_success()
            except Exception as e:
                with self._lock:
                    self._close_conn()
                self.running = False
                print(f"[CLIENT] Connection failed: {e}")
                on_fail()

        threading.Thread(target=run, name="net-client", daemon=True).start()

    def send_data(self, data: Dict[str, Any]) -> None:
        line = json.dumps(data) + "\n"
        payload = line.encode("utf-8")
        with self._lock:
            if self._stop_event.is_set() or not self.conn or not self.running:
                return
            try:
                self.conn.sendall(payload)
            except (OSError, BrokenPipeError, ConnectionResetError) as e:
                print(f"[NETWORK] send error: {e}")
                self.running = False
                self.opponent_disconnected = True

    def poll(self) -> None:
        """Apply all packets received since last poll (call from the game / UI thread)."""
        while True:
            try:
                packet = self._incoming.get_nowait()
            except queue.Empty:
                break
            self._apply_packet(packet)

    def _apply_packet(self, packet: Dict[str, Any]) -> None:
        p_type = packet.get("type")

        if p_type == "__connection_lost__":
            self.opponent_disconnected = True
            self.running = False
            return

        if p_type in ("rematch", "start_game", "disconnect"):
            print(f"[NETWORK] packet: {packet}")

        if p_type == "state":
            self.opponent_grid = packet.get("grid")
            self.opponent_piece = packet.get("piece")
            self.opponent_score = int(packet.get("score", 0))
        elif p_type == "garbage":
            self.incoming_garbage += int(packet.get("amount", 0))
        elif p_type == "hard_drop":
            self.opponent_effects.append(packet)
        elif p_type == "game_over":
            self.opponent_lost = True
        elif p_type == "rematch":
            self.rematch_ready = bool(packet.get("ready", False))
        elif p_type == "start_game":
            self.game_should_start = True
        elif p_type == "disconnect":
            self.opponent_disconnected = True
            self.running = False

    def reset_for_rematch(self) -> None:
        self._drain_incoming()
        self.opponent_grid = None
        self.opponent_piece = None
        self.opponent_lost = False
        self.opponent_disconnected = False
        self.incoming_garbage = 0
        self.opponent_effects.clear()
        self.rematch_ready = False
        self.game_should_start = False

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            self.running = False
            self._close_listen_socket()
            self._close_conn()
        self._drain_incoming()
