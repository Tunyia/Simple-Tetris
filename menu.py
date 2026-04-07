import tkinter as tk
import socket
from network import start_server, start_client, stop
import threading
import json
import time

server_conn = None
server_connected = False
server_games = []

def get_local_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return "127.0.0.1:12345"

# MENU
def choose_mode():
    result = {
        "mode": None,
        "ip": ""
    }

    #UI state
    waiting_label = None
    cancel_btn = None
    copy_btn = None

    # helpers
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
        nonlocal waiting_label, cancel_btn, copy_btn
        if waiting_label:
            waiting_label.destroy()
            waiting_label = None
        if cancel_btn:
            cancel_btn.destroy()
            cancel_btn = None
        if copy_btn:
            copy_btn.destroy()
            copy_btn = None

    def show_waiting(text):
        nonlocal waiting_label

        if waiting_label:
            waiting_label.config(text=text)
        else:
            waiting_label = tk.Label(
                left_frame,
                text=text,
                bg="#0f0f0f",
                fg="white",
                font=("Arial", 12)
            )
            waiting_label.pack(pady=0)

    def show_cancel():
        nonlocal cancel_btn
        if not cancel_btn:
            cancel_btn = tk.Button(
                left_frame,
                text="Cancel",
                command=cancel_action,
                font=("Arial", 12),
                bg="#444444",
                fg="white",
                width=12,
                bd=3
            )
            cancel_btn.pack(pady=5)

    def copy_ip(ip):
        root.clipboard_clear()
        root.clipboard_append(ip)
        root.update()
        show_waiting(f"IP: {ip}\nCopied!")

    def show_copy(ip):
        nonlocal copy_btn

        if copy_btn:
            copy_btn.config(command=lambda: copy_ip(ip))
        else:
            copy_btn = tk.Button(
                left_frame,
                text="Copy IP",
                command=lambda: copy_ip(ip),
                font=("Arial", 12),
                bg="#444444",
                fg="white",
                width=12,
                bd=3
            )
            copy_btn.pack(pady=5)

    # actions
    def set_single():
        result["mode"] = "single"
        root.destroy()

    def set_host():
        disable_buttons()

        ip = get_local_ip()
        port_holder = {"port": None}
        def on_port(port):
            port_holder["port"] = port  # сохраняем
            root.after(0, lambda: show_waiting(f"IP: {ip}:{port}\nWaiting for player..."))
            root.after(0, lambda: show_copy(f"{ip}:{port}"))
            root.after(0, show_cancel)
        def on_connected():
            result["mode"] = "host"
            result["ip"] = f"{ip}:{port_holder['port']}"  # ← теперь работает
            root.after(0, root.destroy)
        def on_status(text):
            root.after(0, lambda: show_waiting(text))
        start_server(on_connected, on_status, on_port)

    def set_join():
        ip_text = ip_entry.get().strip()

        if ":" not in ip_text:
            show_waiting("Use IP:PORT")
            return

        ip, port = ip_text.split(":")
        port = int(port)

        def on_success():
            result["mode"] = "join"
            result["ip"] = ip
            root.after(0, root.destroy)

        def on_fail():
            def update_ui():
                show_waiting("Failed to connect")
                enable_buttons()
                root.after(3000, clear_waiting)
            root.after(0, update_ui)

        start_client(ip, port, on_success, on_fail)

    def cancel_action():
        stop()
        enable_buttons()
        clear_waiting()
        print("Cancelled")  # для проверки

    def server_connection_loop():
        global server_conn, server_connected
        while True:
            if not server_connected:
                try:
                    print("Trying to connect...")
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect(("127.0.0.1", 5555))
                    s.settimeout(None)  # ВАЖНО! делаем блокирующий сокет обратно

                    server_conn = s
                    server_connected = True

                    root.after(0, lambda: update_server_status(True))

                    threading.Thread(target=server_receive_loop, daemon=True).start()
                    request_games()
                    print("Connected!")
                except Exception as e:
                    print("Connect failed:", e)
                    server_connected = False
                    root.after(0, lambda: update_server_status(False))

            time.sleep(2)

    def server_receive_loop():
        global server_connected, server_conn
        buffer = ""
        while True:
            try:
                data = server_conn.recv(4096)
                if not data:
                    raise Exception("Disconnected")
                buffer += data.decode()
                while "\n" in buffer:
                    msg, buffer = buffer.split("\n", 1)
                    packet = json.loads(msg)
                    if packet["type"] == "games":
                        server_games[:] = packet["games"]
                        root.after(0, refresh_games_list)
            except socket.timeout:
                continue
            except Exception as e:
                print("Receive error:", e)
                server_connected = False
                try:
                    server_conn.close()
                except:
                    pass
                server_conn = None
                root.after(0, lambda: update_server_status(False))
                break

    def request_games():
        if server_conn:
            server_conn.sendall(json.dumps({
                "type": "get_games"
            }).encode() + b"\n")

    # UI
    root = tk.Tk()
    root.title("Tetris")
    root.geometry("500x360")
    root.resizable(False, False)
    root.configure(bg="#0f0f0f")

    #фреймы!!
    main_frame = tk.Frame(root, bg="#0f0f0f")
    main_frame.pack(fill="both", expand=True)

    left_frame = tk.Frame(main_frame, bg="#1a1a1a", width=200)
    left_frame.pack(side="left", fill="y", expand=True)

    right_frame = tk.Frame(main_frame, bg="#1a1a1a", width=300)
    right_frame.pack(side="right", fill="y", expand=True)

    # центр
    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")

    BTN = {
        "font": ("Arial", 14),
        "bg": "#333333",
        "fg": "white",
        "activebackground": "#555555",
        "activeforeground": "white",
        "bd": 3,
        "width": 16,
        "height": 1
    }

    #tk.Label(
    #    root,
    #    text="TETRIS",
    #    font=("Arial", 22, "bold"),
    #    bg="#0f0f0f",
    #    fg="white"
    #).pack(pady=15)

    single_btn = tk.Button(left_frame, text="Single Player", command=set_single, **BTN)
    single_btn.pack(pady=(15, 5))

    host_btn = tk.Button(left_frame, text="Host Game", command=set_host, **BTN)
    host_btn.pack(pady=5)

    tk.Label(left_frame, text="Server IP:", bg="#0f0f0f", fg="white", font=("Arial", 10)).pack(pady=(15, 0))

    ip_entry = tk.Entry(left_frame, font=("Arial", 12), width=20)
    ip_entry.insert(0, "127.0.0.1:12345")
    ip_entry.pack(pady=5)

    join_btn_left = tk.Button(left_frame, text="Join Game", command=set_join, **BTN)
    join_btn_left.pack(pady=5)

    # SERVER UI - right frame
    # Заголовок
    tk.Label(
        right_frame,
        text="ONLINE",
        font=("Arial", 16, "bold"),
        bg="#1a1a1a",
        fg="white"
    ).pack(pady=0)

    # Никнейм
    tk.Label(
        right_frame,
        text="Nickname",
        bg="#1a1a1a",
        fg="#cccccc"
    ).pack()

    nickname_entry = tk.Entry(
        right_frame,
        font=("Arial", 12),
        justify="center"
    )
    nickname_entry.insert(0, "Player")
    nickname_entry.pack(pady=(0, 0), ipadx=5, ipady=0)

    # Статус сервера
    server_status = tk.Label(
        right_frame,
        text="Server: WIP",
        bg="#1a1a1a",
        fg="red",
        font=("Arial", 10, "bold")
    )
    server_status.pack(pady=(0, 0))

    def update_server_status(online=True):
        if online:
            server_status.config(text="Server: online WIP", fg="lightgreen")
        else:
            server_status.config(text="Server: offline WIP", fg="red")
        update_buttons_state()

    def create_game():
        if not server_connected or not server_conn:
            print("No server connection")
            return
        name = nickname_entry.get().strip()
        if not name:
            return
        server_conn.sendall(json.dumps({
            "type": "create_game",
            "name": name
        }).encode() + b"\n")

    create_btn = tk.Button(right_frame,text="Create Game",command=create_game,**BTN)
    create_btn.pack(pady=(5, 0))

    def update_buttons_state():
        if server_connected:
            create_btn.config(state="normal")
        else:
            create_btn.config(state="disabled")
            join_btn_right.config(state="disabled")

    # список игр
    tk.Label(right_frame, text="Games", bg="#1a1a1a", fg="white").pack()

    games_listbox = tk.Listbox(
        right_frame,
        height=6,
        font=("Consolas", 8),
        selectborderwidth=4,
        bg="#222222",
        fg="white",
        selectbackground="#222222",
        borderwidth=4,
        activestyle="none"
    )
    games_listbox.pack(padx=0, pady=0, fill="x")

    # уже не тестовые данные
    def refresh_games_list():
        games_listbox.delete(0, tk.END)
        for g in server_games:
            text = f"{g['name']:<10}  {g['players']}/2"
            games_listbox.insert(tk.END, text)

    # зайти в игру
    def join_game():
        if not server_connected or not server_conn:
            return
        selection = games_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        game = server_games[index]
        server_conn.sendall(json.dumps({
            "type": "join_game",
            "id": game["id"]
        }).encode() + b"\n")

    join_btn_right= tk.Button(right_frame, text="Join Game", command=join_game, **BTN, state="disabled")
    join_btn_right.pack(pady=(5, 10))

    def on_select(event):
        if games_listbox.curselection():
            join_btn_right.config(state="normal")
        else:
            join_btn_right.config(state="disabled")
    games_listbox.bind("<<ListboxSelect>>", on_select)

    threading.Thread(target=server_connection_loop, daemon=True).start()

    root.mainloop()
    return result