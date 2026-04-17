import tkinter as tk
import socket
from network import NetworkManager
import threading
import json
import time
import queue

server_conn = None
server_connected = False
server_games = []

def get_local_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return "127.0.0.1:12345"


def choose_mode():
    global server_conn, server_connected
    ui_queue = queue.Queue()
    menu_running = True
    after_id = None  # Переменная для хранения таймера очереди???

    result = {
        "mode": None,
        "ip": "127.0.0.1",
        "port": 12345
    }

    # UI variables
    waiting_label = None
    cancel_btn = None
    copy_btn = None

    root = tk.Tk()
    root.title("Tetris Menu")
    root.geometry("500x360")
    root.resizable(False, False)
    root.configure(bg="#0f0f0f")

    def process_ui_queue():
        nonlocal after_id

        if not menu_running:
            return

        while not ui_queue.empty():
            try:
                func = ui_queue.get_nowait()
                func()
            except:
                pass

        if menu_running:
            after_id = root.after(50, process_ui_queue)
    process_ui_queue()

    # БЕЗОПАСНЫЙ ВЫХОД!! очень важная шняга
    def safe_exit(mode=None, ip="", port=12345):  # Добавим порт в аргументы
        nonlocal menu_running, after_id
        global server_conn, server_connected

        menu_running = False
        result["mode"] = mode
        result["ip"] = ip
        result["port"] = port

        if after_id:
            try:
                root.after_cancel(after_id)
            except:
                pass

        if server_conn:
            try:
                server_conn.close()
            except:
                pass
            server_conn = None
            server_connected = False

        root.quit()

    # Перехватываем нажатие на крестик окна
    root.protocol("WM_DELETE_WINDOW", lambda: safe_exit(None))

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
        if waiting_label: waiting_label.destroy(); waiting_label = None
        if cancel_btn: cancel_btn.destroy(); cancel_btn = None
        if copy_btn: copy_btn.destroy(); copy_btn = None

    def show_waiting(text):
        nonlocal waiting_label
        if waiting_label:
            waiting_label.config(text=text)
        else:
            waiting_label = tk.Label(left_frame, text=text, bg="#0f0f0f", fg="white", font=("Arial", 12))
            waiting_label.pack(pady=0)

    def show_cancel():
        nonlocal cancel_btn
        if not cancel_btn:
            cancel_btn = tk.Button(left_frame, text="Cancel", command=cancel_action, font=("Arial", 12), bg="#444444",
                                   fg="white", width=12, bd=3)
            cancel_btn.pack(pady=5)

    def copy_ip(ip):
        root.clipboard_clear()
        root.clipboard_append(ip)
        root.update()
        show_waiting(f"IP: {ip}\nCopied!")

    def show_copy(ip):
        nonlocal copy_btn
        if not copy_btn:
            copy_btn = tk.Button(left_frame, text="Copy IP", command=lambda: copy_ip(ip), font=("Arial", 12),
                                 bg="#444444", fg="white", width=12, bd=3)
            copy_btn.pack(pady=5)

    # actions
    def set_single():
        safe_exit("single")

    net_manager = NetworkManager()

    def set_host():
        ip = get_local_ip()
        port_holder = {"port": None}

        def on_port(port):
            port_holder["port"] = port
            if menu_running:
                ui_queue.put(lambda: show_waiting(f"IP: {ip}:{port}\nWaiting for player..."))
                ui_queue.put(lambda: show_copy(f"{ip}:{port}"))
                ui_queue.put(show_cancel)
            pass

        def on_connected():
            if menu_running:
                # Передаем данные хоста
                ui_queue.put(lambda: safe_exit("host", ip))

        def on_status(text):
            if menu_running:
                ui_queue.put(lambda: show_waiting(text))

        net_manager.start_server(on_connected, on_status, on_port)

    def set_join():
        ip_text = ip_entry.get().strip()
        if ":" not in ip_text:
            show_waiting("Use IP:PORT")
            return
        ip, port_str = ip_text.split(":")

        def on_success():
            if menu_running:
                ui_queue.put(lambda: safe_exit("join", ip))

        def on_fail():
            if menu_running:
                ui_queue.put(lambda: show_waiting("Failed to connect"))
                ui_queue.put(enable_buttons)

        try:
            net_manager.start_client(ip, int(port_str), on_success, on_fail)
        except ValueError:
            show_waiting("Invalid Port")

    def cancel_action():
        net_manager.stop()
        enable_buttons()
        clear_waiting()

    # СЕТЕВАЯ ЛОГИКА МЕНЮ
    def server_connection_loop():
        global server_conn, server_connected
        while menu_running:
            if not server_connected:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(2)

                    # Теперь safe_exit сможет прервать процесс подключения!
                    server_conn = s

                    s.connect(("127.0.0.1", 5555))
                    s.settimeout(None)

                    server_connected = True
                    if menu_running:
                        ui_queue.put(lambda: update_server_status(True))
                        request_games()
                        threading.Thread(target=server_receive_loop, daemon=True).start()
                except Exception as e:
                    server_connected = False
                    if menu_running:
                        ui_queue.put(lambda: update_server_status(False))

            # Ждем 5 секунд мелкими шагами
            for _ in range(50):
                if not menu_running: return
                time.sleep(0.1)

    def server_receive_loop():
        global server_connected, server_conn
        buffer = ""
        while menu_running and server_connected:
            try:
                data = server_conn.recv(4096)
                if not data:
                    break
                buffer += data.decode()
                while "\n" in buffer:
                    msg, buffer = buffer.split("\n", 1)
                    packet = json.loads(msg)
                    if packet["type"] == "games":
                        server_games[:] = packet["games"]
                        if menu_running:
                            ui_queue.put(refresh_games_list)
            except:
                break

        server_connected = False
        if server_conn:
            try:
                server_conn.close()
            except:
                pass
        server_conn = None
        if menu_running:
            ui_queue.put(lambda: update_server_status(False))

    def request_games():
        if server_conn and server_connected:
            try:
                server_conn.sendall(json.dumps({"type": "get_games"}).encode() + b"\n")
            except:
                pass

    # UI Elements
    main_frame = tk.Frame(root, bg="#0f0f0f")
    main_frame.pack(fill="both", expand=True)

    left_frame = tk.Frame(main_frame, bg="#1a1a1a", width=200)
    left_frame.pack(side="left", fill="y", expand=True)

    right_frame = tk.Frame(main_frame, bg="#1a1a1a", width=300)
    right_frame.pack(side="right", fill="y", expand=True)

    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")

    BTN = {"font": ("Arial", 14), "bg": "#333333", "fg": "white", "activebackground": "#555555",
           "activeforeground": "white", "bd": 3, "width": 16, "height": 1}

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

    tk.Label(right_frame, text="ONLINE", font=("Arial", 16, "bold"), bg="#1a1a1a", fg="white").pack(pady=0)
    tk.Label(right_frame, text="Nickname", bg="#1a1a1a", fg="#cccccc").pack()

    nickname_entry = tk.Entry(right_frame, font=("Arial", 12), justify="center")
    nickname_entry.insert(0, "Player")
    nickname_entry.pack(pady=(0, 0), ipadx=5, ipady=0)

    server_status = tk.Label(right_frame, text="Server: connecting", bg="#1a1a1a", fg="lightgray",
                             font=("Arial", 10, "bold"))
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
        if not server_connected or not server_conn: return
        name = nickname_entry.get().strip()
        if not name: return
        try:
            server_conn.sendall(json.dumps({"type": "create_game", "name": name}).encode() + b"\n")
        except:
            pass

    create_btn = tk.Button(right_frame, text="Create Game", command=create_game, state="disabled", **BTN)
    create_btn.pack(pady=(5, 0))

    tk.Label(right_frame, text="Games", bg="#1a1a1a", fg="white").pack()
    games_listbox = tk.Listbox(right_frame, height=6, font=("Consolas", 8), bg="#222222", fg="white",
                               selectbackground="#444444", borderwidth=4, activestyle="none")
    games_listbox.pack(padx=0, pady=0, fill="x")

    def refresh_games_list():
        games_listbox.delete(0, tk.END)
        for g in server_games:
            text = f"{g['name']:<10}  {g['players']}/2"
            games_listbox.insert(tk.END, text)

    def join_game():
        if not server_connected or not server_conn: return
        selection = games_listbox.curselection()
        if not selection: return
        game = server_games[selection[0]]
        try:
            server_conn.sendall(json.dumps({"type": "join_game", "id": game["id"]}).encode() + b"\n")
        except:
            pass

    join_btn_right = tk.Button(right_frame, text="Join Game", command=join_game, **BTN, state="disabled")
    join_btn_right.pack(pady=(5, 10))

    def on_select(event):
        if games_listbox.curselection():
            join_btn_right.config(state="normal")
        else:
            join_btn_right.config(state="disabled")

    games_listbox.bind("<<ListboxSelect>>", on_select)

    threading.Thread(target=server_connection_loop, daemon=True).start()

    root.mainloop()

    final_ip = "127.0.0.1"
    final_port = 12345

    if result["ip"] and ":" in str(result["ip"]):
        try:
            parts = result["ip"].split(":")
            final_ip = parts[0]
            final_port = int(parts[1])
        except:
            pass
    elif result["ip"]:
        final_ip = result["ip"]

    try:
        root.destroy()
    except Exception as e:
        print(e)
        pass

    # Возвращаем данные. Теперь main.py получит всё, что нужно.
    return {
        "mode": result["mode"],
        "ip": result["ip"],
        "port": result.get("port", 12345),
        "network": net_manager
    }