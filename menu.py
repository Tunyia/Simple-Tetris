import json
import queue
import socket
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

from network import NetworkManager

_SETTINGS_PATH = Path(__file__).resolve().parent / "player_settings.json"


def load_saved_nickname():
    try:
        if _SETTINGS_PATH.is_file():
            data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                n = str(data.get("nickname", "")).strip()
                if n:
                    return n[:32]
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return "Player"


def save_nickname(nickname):
    try:
        nick = (nickname or "").strip() or "Player"
        _SETTINGS_PATH.write_text(
            json.dumps({"nickname": nick[:32]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass

server_conn = None
server_connected = False
server_games = []


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


def choose_mode():
    global server_conn, server_connected

    ui_queue = queue.Queue()
    menu_running = True
    after_id = None

    result = {
        "mode": None,
        "ip": "127.0.0.1",
        "port": 12345,
        "nickname": "Player",
    }

    waiting_label = None
    waiting_host_row = None

    root = tk.Tk()
    root.title("Tetris Menu")
    root.minsize(500, 400)
    root.geometry("500x400")
    root.resizable(False, False)
    root.configure(bg="#0f0f0f")

    if sys.platform == "darwin":
        try:
            cur = float(root.tk.call("tk", "scaling"))
            root.tk.call("tk", "scaling", max(1.0, cur * 0.95))
        except tk.TclError:
            pass

    net_manager = NetworkManager()

    def process_ui_queue():
        nonlocal after_id

        if not menu_running:
            return

        while True:
            try:
                func = ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                func()
            except tk.TclError:
                pass

        if menu_running:
            after_id = root.after(50, process_ui_queue)

    process_ui_queue()

    def safe_exit(mode=None, ip="", port=12345):
        nonlocal menu_running, after_id
        global server_conn, server_connected

        menu_running = False
        result["mode"] = mode
        result["ip"] = ip
        result["port"] = port

        if mode in (None, "single"):
            net_manager.stop()

        if after_id:
            try:
                root.after_cancel(after_id)
            except tk.TclError:
                pass
            after_id = None

        if server_conn:
            try:
                server_conn.close()
            except OSError:
                pass
            server_conn = None
            server_connected = False

        root.quit()

    root.protocol("WM_DELETE_WINDOW", lambda: safe_exit(None))

    def disable_buttons():
        single_btn.config(state="disabled")
        host_btn.config(state="disabled")
        join_btn_left.config(state="disabled")
        join_btn_right.config(state="disabled")

    def enable_buttons():
        single_btn.config(state="normal")
        host_btn.config(state="normal")
        join_btn_left.config(state="normal")
        join_btn_right.config(state="normal")

    def clear_waiting():
        nonlocal waiting_label, waiting_host_row
        if waiting_label:
            waiting_label.destroy()
            waiting_label = None
        if waiting_host_row:
            waiting_host_row.destroy()
            waiting_host_row = None

    def show_waiting(text):
        nonlocal waiting_label
        if waiting_label:
            waiting_label.config(text=text)
        else:
            waiting_label = tk.Label(
                left_frame,
                text=text,
                bg="#1a1a1a",
                fg="white",
                font=("Arial", 12),
                wraplength=200,
                justify="center",
            )
            waiting_label.pack(pady=0)

    def copy_ip(ip):
        root.clipboard_clear()
        root.clipboard_append(ip)
        root.update_idletasks()
        show_waiting(f"IP: {ip}\nCopied!")

    def show_host_buttons(ip_port):
        nonlocal waiting_host_row
        if waiting_host_row:
            waiting_host_row.destroy()
        waiting_host_row = tk.Frame(left_frame, bg="#1a1a1a")
        waiting_host_row.pack(fill="x", pady=5)
        tk.Button(
            waiting_host_row,
            text="Copy IP",
            command=lambda p=ip_port: copy_ip(p),
            font=("Arial", 12),
            bg="#444444",
            fg="white",
            bd=3,
            height=1,
        ).pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        tk.Button(
            waiting_host_row,
            text="Cancel",
            command=cancel_action,
            font=("Arial", 12),
            bg="#444444",
            fg="white",
            bd=3,
            height=1,
        ).pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))

    def set_single():
        safe_exit("single")

    def set_host():
        ip = get_local_ip()
        disable_buttons()

        def on_port(port):
            if menu_running:
                ui_queue.put(lambda: show_waiting(f"IP: {ip}:{port}\nWaiting for player..."))
                ui_queue.put(lambda: show_host_buttons(f"{ip}:{port}"))

        def on_connected():
            if menu_running:
                p = net_manager.listen_port or 12345
                ui_queue.put(lambda: safe_exit("host", ip, p))

        def on_status(text):
            if menu_running:
                ui_queue.put(lambda: show_waiting(text))
                ui_queue.put(enable_buttons)

        net_manager.start_server(on_connected, on_status, on_port)

    def set_join():
        ip_text = ip_entry.get().strip()
        if ":" not in ip_text:
            show_waiting("Use IP:PORT")
            return
        host_part, port_str = ip_text.rsplit(":", 1)
        disable_buttons()

        def on_success():
            if menu_running:
                try:
                    p = int(port_str)
                except ValueError:
                    p = 12345
                ui_queue.put(lambda: safe_exit("join", host_part.strip(), p))

        def on_fail():
            if menu_running:
                ui_queue.put(lambda: show_waiting("Failed to connect"))
                ui_queue.put(enable_buttons)

        try:
            net_manager.start_client(host_part.strip(), int(port_str), on_success, on_fail)
        except ValueError:
            show_waiting("Invalid Port")
            enable_buttons()

    def cancel_action():
        net_manager.stop()
        enable_buttons()
        clear_waiting()

    def server_connection_loop():
        global server_conn, server_connected
        while menu_running:
            if not server_connected:
                s = None
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(2.0)
                    server_conn = s
                    s.connect(("127.0.0.1", 5555))
                    s.settimeout(30.0)
                    server_connected = True
                    if menu_running:
                        ui_queue.put(lambda: update_server_status(True))
                        request_games()
                        threading.Thread(target=server_receive_loop, name="menu-server-rx", daemon=True).start()
                except OSError:
                    server_connected = False
                    if s:
                        try:
                            s.close()
                        except OSError:
                            pass
                    server_conn = None
                    if menu_running:
                        ui_queue.put(lambda: update_server_status(False))

            for _ in range(50):
                if not menu_running:
                    return
                time.sleep(0.1)

    def server_receive_loop():
        global server_connected, server_conn
        buffer = ""
        while menu_running and server_connected:
            conn = server_conn
            if not conn:
                break
            try:
                data = conn.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8")
                while "\n" in buffer:
                    msg, buffer = buffer.split("\n", 1)
                    msg = msg.strip()
                    if not msg:
                        continue
                    try:
                        packet = json.loads(msg)
                    except json.JSONDecodeError:
                        continue
                    if packet.get("type") == "games":
                        server_games[:] = packet["games"]
                        if menu_running:
                            ui_queue.put(refresh_games_list)
            except (OSError, UnicodeDecodeError):
                break

        server_connected = False
        if server_conn:
            try:
                server_conn.close()
            except OSError:
                pass
        server_conn = None
        if menu_running:
            ui_queue.put(lambda: update_server_status(False))

    def request_games():
        if server_conn and server_connected:
            try:
                server_conn.sendall(json.dumps({"type": "get_games"}).encode("utf-8") + b"\n")
            except OSError:
                pass

    main_frame = tk.Frame(root, bg="#0f0f0f")
    main_frame.pack(fill="both", expand=True)

    nick_bar = tk.Frame(main_frame, bg="#0f0f0f")
    nick_bar.pack(fill="x", padx=12, pady=(10, 6))
    tk.Label(nick_bar, text="Nickname", bg="#0f0f0f", fg="#cccccc", font=("Arial", 10)).pack(
        side=tk.LEFT, padx=(0, 8)
    )
    nickname_entry = tk.Entry(nick_bar, font=("Arial", 12), justify="center")
    nickname_entry.pack(side=tk.LEFT, fill="x", expand=True)
    nickname_entry.insert(0, load_saved_nickname())

    content = tk.Frame(main_frame, bg="#0f0f0f")
    content.pack(fill="both", expand=True)

    left_wrap = tk.Frame(content, bg="#0f0f0f")
    left_wrap.pack(side="left", fill="y", padx=(8, 4), pady=(0, 8))
    tk.Label(left_wrap, text="LOCAL", font=("Arial", 16, "bold"), bg="#0f0f0f", fg="white").pack(
        anchor="w", pady=(0, 4)
    )
    left_frame = tk.Frame(left_wrap, bg="#1a1a1a", width=220, height=330)
    left_frame.pack()
    left_frame.pack_propagate(False)

    right_wrap = tk.Frame(content, bg="#0f0f0f")
    right_wrap.pack(side="right", fill="y", padx=(4, 8), pady=(0, 8))
    tk.Label(right_wrap, text="ONLINE", font=("Arial", 16, "bold"), bg="#0f0f0f", fg="white").pack(
        anchor="w", pady=(0, 4)
    )
    right_frame = tk.Frame(right_wrap, bg="#1a1a1a", width=260, height=330)
    right_frame.pack()
    right_frame.pack_propagate(False)

    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")

    mono_font = ("Menlo", 9) if sys.platform == "darwin" else ("Consolas", 9)

    BTN = {
        "font": ("Arial", 14),
        "bg": "#333333",
        "fg": "white",
        "activebackground": "#555555",
        "activeforeground": "white",
        "bd": 3,
        "width": 14,
        "height": 1,
    }

    single_btn = tk.Button(left_frame, text="Single Player", command=set_single, **BTN)
    single_btn.pack(pady=(12, 5))

    host_btn = tk.Button(left_frame, text="Host Game", command=set_host, **BTN)
    host_btn.pack(pady=5)

    tk.Label(
        left_frame,
        text="Host IP:port (see host screen):",
        bg="#1a1a1a",
        fg="white",
        font=("Arial", 9),
    ).pack(pady=(15, 0))
    ip_entry = tk.Entry(left_frame, font=("Arial", 12), width=18)
    ip_entry.insert(0, "127.0.0.1:")
    ip_entry.pack(pady=5)

    join_btn_left = tk.Button(left_frame, text="Join Game", command=set_join, **BTN)
    join_btn_left.pack(pady=5)

    server_status = tk.Label(
        right_frame,
        text="Server: connecting",
        bg="#1a1a1a",
        fg="lightgray",
        font=("Arial", 10, "bold"),
    )
    server_status.pack(pady=(0, 0))

    def update_server_status(online=True):
        if online:
            server_status.config(text="Server: ● online", fg="lightgreen")
            create_btn.config(state="normal")
        else:
            server_status.config(text="Server: ● offline", fg="red")
            create_btn.config(state="disabled")
            join_btn_right.config(state="disabled")

    def create_game():
        if not server_connected or not server_conn:
            return
        name = (nickname_entry.get().strip() or "Player")[:32]
        try:
            server_conn.sendall(
                json.dumps({"type": "create_game", "name": name}).encode("utf-8") + b"\n"
            )
        except OSError:
            pass

    create_btn = tk.Button(right_frame, text="Create Game", command=create_game, state="disabled", **BTN)
    create_btn.pack(pady=(5, 0))

    tk.Label(right_frame, text="Games", bg="#1a1a1a", fg="white").pack()
    games_listbox = tk.Listbox(
        right_frame,
        height=6,
        font=mono_font,
        bg="#222222",
        fg="white",
        selectbackground="#444444",
        borderwidth=4,
        activestyle="none",
    )
    games_listbox.pack(padx=0, pady=0, fill="x")

    def refresh_games_list():
        games_listbox.delete(0, tk.END)
        for g in server_games:
            text = f"{g['name']:<10}  {g['players']}/2"
            games_listbox.insert(tk.END, text)

    def join_game():
        if not server_connected or not server_conn:
            return
        selection = games_listbox.curselection()
        if not selection:
            return
        game = server_games[selection[0]]
        try:
            server_conn.sendall(
                json.dumps({"type": "join_game", "id": game["id"]}).encode("utf-8") + b"\n"
            )
        except OSError:
            pass

    join_btn_right = tk.Button(right_frame, text="Join Game", command=join_game, **BTN, state="disabled")
    join_btn_right.pack(pady=(5, 10))

    def on_select(_event):
        if games_listbox.curselection():
            join_btn_right.config(state="normal")
        else:
            join_btn_right.config(state="disabled")

    games_listbox.bind("<<ListboxSelect>>", on_select)

    threading.Thread(target=server_connection_loop, name="menu-server-conn", daemon=True).start()

    root.mainloop()

    nickname_out = result.get("nickname", "Player")
    try:
        nickname_out = (nickname_entry.get().strip() or "Player")[:32]
    except tk.TclError:
        pass

    window_pos = None
    try:
        root.update_idletasks()
        window_pos = (root.winfo_rootx(), root.winfo_rooty())
    except tk.TclError:
        pass

    try:
        root.destroy()
    except tk.TclError:
        pass

    save_nickname(nickname_out)

    return {
        "mode": result["mode"],
        "ip": result["ip"],
        "port": result.get("port", 12345),
        "network": net_manager,
        "nickname": nickname_out,
        "window_pos": window_pos,
    }
