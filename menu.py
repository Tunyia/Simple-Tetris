import tkinter as tk
import socket
from network import start_server, start_client, stop

def get_local_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return "127.0.0.1"

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
        join_btn.config(state="disabled")

    def enable_buttons():
        single_btn.config(state="normal")
        host_btn.config(state="normal")
        join_btn.config(state="normal")

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
                root,
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
                root,
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
                root,
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
        show_waiting(f"IP: {ip}\nWaiting for player...")
        show_copy(ip)
        show_cancel()

        def on_connected():
            result["mode"] = "host"
            root.after(0, root.destroy)

        def on_status(text):
            root.after(0, lambda: show_waiting(text))

        start_server(on_connected, on_status)

    def set_join():
        ip = ip_entry.get().strip()

        if not ip:
            show_waiting("Enter IP")
            return

        disable_buttons()
        show_waiting("Connecting...")
        show_cancel()

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

        start_client(ip, on_success, on_fail)

    def cancel_action():
        stop()
        enable_buttons()
        clear_waiting()

    # UI
    root = tk.Tk()
    root.title("Tetris")
    root.geometry("200x360")
    root.resizable(False, False)
    root.configure(bg="#0f0f0f")

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

    single_btn = tk.Button(root, text="Single Player", command=set_single, **BTN)
    single_btn.pack(pady=(15, 5))

    host_btn = tk.Button(root, text="Host Game", command=set_host, **BTN)
    host_btn.pack(pady=5)

    tk.Label(root, text="Server IP:", bg="#0f0f0f", fg="white", font=("Arial", 10)).pack(pady=(15, 0))

    ip_entry = tk.Entry(root, font=("Arial", 12), width=20)
    ip_entry.insert(0, "127.0.0.1")
    ip_entry.pack(pady=5)

    join_btn = tk.Button(root, text="Join Game", command=set_join, **BTN)
    join_btn.pack(pady=5)

    root.mainloop()
    return result