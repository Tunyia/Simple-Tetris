import json
import socket
import threading
from typing import Any, Dict, List

HOST = "0.0.0.0"
PORT = 5555


class LobbyServer:
    """Простое лобби: список игр и рассылка всем подключённым клиентам."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._games: Dict[int, Dict[str, Any]] = {}
        self._next_id = 1
        self._clients_lock = threading.Lock()
        self._clients: List[socket.socket] = []

    def add_client(self, conn: socket.socket) -> None:
        with self._clients_lock:
            self._clients.append(conn)

    def remove_client(self, conn: socket.socket) -> None:
        with self._clients_lock:
            if conn in self._clients:
                self._clients.remove(conn)
        self._drop_games_for(conn)

    def _public_games(self) -> List[dict]:
        with self._lock:
            return [
                {"id": g["id"], "name": g["name"], "players": g["players"]}
                for g in sorted(self._games.values(), key=lambda x: x["id"])
            ]

    def _drop_games_for(self, conn: socket.socket) -> None:
        changed = False
        with self._lock:
            to_del = []
            for gid, g in list(self._games.items()):
                if g["host"] is conn:
                    to_del.append(gid)
                elif g.get("guest") is conn:
                    g["guest"] = None
                    g["players"] = 1
                    changed = True
            for gid in to_del:
                del self._games[gid]
                changed = True
        if changed:
            self._broadcast_games()

    def _broadcast_games(self) -> None:
        payload = json.dumps(
            {"type": "games", "games": self._public_games()},
            ensure_ascii=False,
        ).encode("utf-8") + b"\n"
        with self._clients_lock:
            snapshot = list(self._clients)
        for c in snapshot:
            try:
                c.sendall(payload)
            except OSError:
                pass

    def send_games_to(self, conn: socket.socket) -> None:
        msg = json.dumps(
            {"type": "games", "games": self._public_games()},
            ensure_ascii=False,
        ).encode("utf-8") + b"\n"
        try:
            conn.sendall(msg)
        except OSError:
            pass

    def create_game(self, name: str, conn: socket.socket) -> None:
        with self._lock:
            for gid, g in list(self._games.items()):
                if g["host"] is conn:
                    del self._games[gid]
            gid = self._next_id
            self._next_id += 1
            self._games[gid] = {
                "id": gid,
                "name": (name or "Player")[:64],
                "players": 1,
                "host": conn,
                "guest": None,
            }
        self._broadcast_games()

    def join_game(self, gid: int, conn: socket.socket) -> bool:
        with self._lock:
            g = self._games.get(gid)
            if not g or g["players"] != 1 or g.get("guest") is not None:
                return False
            if g["host"] is conn:
                return False
            g["guest"] = conn
            g["players"] = 2
        self._broadcast_games()
        return True


def handle_client(conn: socket.socket, lobby: LobbyServer) -> None:
    lobby.add_client(conn)
    conn.settimeout(30.0)
    buffer = ""
    try:
        lobby.send_games_to(conn)
        while True:
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                continue
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")
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
                ptype = packet.get("type")
                if ptype == "get_games":
                    lobby.send_games_to(conn)
                elif ptype == "create_game":
                    lobby.create_game(str(packet.get("name", "")), conn)
                elif ptype == "join_game":
                    try:
                        gid = int(packet.get("id"))
                    except (TypeError, ValueError):
                        continue
                    lobby.join_game(gid, conn)
    except (OSError, UnicodeDecodeError):
        pass
    finally:
        lobby.remove_client(conn)
        try:
            conn.close()
        except OSError:
            pass


def main() -> None:
    lobby = LobbyServer()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen()
    print(f"Lobby server listening on {HOST}:{PORT}")
    try:
        while True:
            conn, addr = srv.accept()
            print(f"Client connected: {addr}")
            threading.Thread(target=handle_client, args=(conn, lobby), daemon=True).start()
    except KeyboardInterrupt:
        print("Shutdown")
    finally:
        try:
            srv.close()
        except OSError:
            pass


if __name__ == "__main__":
    main()
