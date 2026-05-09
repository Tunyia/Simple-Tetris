"""
TCP relay to the lobby server after match_ready: same JSON game protocol as LAN,
wrapped as {"type": "relay", "payload": <inner dict>}.
"""

import json
import queue
import socket
import threading
from typing import Any, Dict, List, Optional


class ServerRelayNetwork:
    """Game-compatible transport: poll() / send_data() like NetworkManager."""

    def __init__(self, conn: socket.socket) -> None:
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._incoming: queue.Queue = queue.Queue()

        self.conn: Optional[socket.socket] = conn
        self.server_socket = None
        self.role = "relay"
        self.listen_port = None

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
        self.peer_display_name: Optional[str] = None
        self._shutdown_requested = False

    def start_recv_thread(self) -> None:
        self._stop_event.clear()
        self.running = True
        self.opponent_disconnected = False
        with self._lock:
            if self.conn:
                self.conn.settimeout(0.5)
        threading.Thread(target=self._receive_loop, name="relay-rx", daemon=True).start()

    def _drain_incoming(self) -> None:
        while True:
            try:
                self._incoming.get_nowait()
            except queue.Empty:
                break

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
                if not isinstance(packet, dict):
                    continue
                if packet.get("type") == "relay":
                    inner = packet.get("payload")
                    if isinstance(inner, dict):
                        self._incoming.put(inner)
                elif packet.get("type") == "match_ready":
                    pass
                elif packet.get("type") == "games":
                    pass

        with self._lock:
            self.running = False

    def send_data(self, data: Dict[str, Any]) -> bool:
        wrapped = {"type": "relay", "payload": data}
        line = json.dumps(wrapped) + "\n"
        payload = line.encode("utf-8")
        with self._lock:
            if self._stop_event.is_set() or not self.conn or not self.running:
                return False
            try:
                self.conn.sendall(payload)
                return True
            except (OSError, BrokenPipeError, ConnectionResetError) as e:
                print(f"[RELAY] send error: {e}")
                self.running = False
                self.opponent_disconnected = True
                return False

    def poll(self) -> None:
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
            self.peer_display_name = None
            return

        if p_type in ("rematch", "start_game", "disconnect"):
            print(f"[RELAY] packet: {packet}")

        if p_type == "state":
            raw = packet.get("name")
            if isinstance(raw, str):
                name = raw.strip()
                if name:
                    self.peer_display_name = name[:32]
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
        elif p_type == "player_name":
            raw = packet.get("name")
            if isinstance(raw, str):
                name = raw.strip()
                if name:
                    self.peer_display_name = name[:32]

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
        self._shutdown_requested = True
        self._stop_event.set()
        with self._lock:
            self.running = False
            if self.conn:
                try:
                    self.conn.close()
                except OSError:
                    pass
                self.conn = None
        self.peer_display_name = None
        self._drain_incoming()
