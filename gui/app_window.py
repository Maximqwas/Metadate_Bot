import json
import os
import sys
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from bot.runner import BotRunner

def get_resource_path(relative_path: str) -> str:
    """Для работы путей в скомпилированном PyInstaller .exe"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), relative_path)

# Настройка внешнего вида CustomTkinter
ctk.set_appearance_mode("Dark")  # Включаем темную тему
ctk.set_default_color_theme("blue")  # Синие акценты

class AppWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Metadata Bot v2.0")
        self.geometry("700x500")
        self.resizable(False, False)
        
        # Перехват закрытия окна
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.config_path = get_resource_path("bot_config.json")
        self.temp_dir = get_resource_path("temp")
        os.makedirs(self.temp_dir, exist_ok=True)

        self.bot_runner = None

        self._build_ui()
        self._load_config()

    def _build_ui(self):
        # Основной фрейм (отступы)
        self.main_frame = ctk.CTkFrame(self, corner_radius=15, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Заголовок
        self.lbl_title = ctk.CTkLabel(
            self.main_frame, 
            text="Telegram Metadata Bot", 
            font=ctk.CTkFont(family="Inter", size=24, weight="bold")
        )
        self.lbl_title.pack(pady=(0, 20))

        # --- Frame Token ---
        self.frame_token = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.frame_token.pack(fill="x", pady=(0, 15), ipadx=10, ipady=10)

        self.lbl_token = ctk.CTkLabel(self.frame_token, text="Bot Token:", font=ctk.CTkFont(size=14))
        self.lbl_token.pack(side="left", padx=(15, 10))

        self.token_var = tk.StringVar()
        self.token_entry = ctk.CTkEntry(
            self.frame_token, 
            textvariable=self.token_var, 
            show="*", 
            width=300,
            font=ctk.CTkFont(size=14),
            border_width=2,
            corner_radius=8
        )
        self.token_entry.pack(side="left", padx=10)

        # Универсальное исправление работы Ctrl+V (через KeyCode для любой раскладки)
        def on_paste(event):
            # 86 — аппаратный код клавиши V в Windows, 4 — флаг зажатого Control
            if (event.state & 4) and event.keycode == 86:
                try:
                    self.token_entry.insert("insert", self.clipboard_get())
                except Exception:
                    pass
                return "break"
            
        self.token_entry.bind("<Key>", on_paste)

        self.btn_save = ctk.CTkButton(
            self.frame_token, 
            text="Сохранить", 
            command=self._save_config,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            width=100
        )
        self.btn_save.pack(side="left", padx=10)

        # --- Frame API Server ---
        self.frame_api = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.frame_api.pack(fill="x", pady=(0, 15), ipadx=10, ipady=10)

        self.lbl_api = ctk.CTkLabel(self.frame_api, text="Local API (opt):", font=ctk.CTkFont(size=14))
        self.lbl_api.pack(side="left", padx=(15, 10))

        self.api_var = tk.StringVar()
        self.api_entry = ctk.CTkEntry(
            self.frame_api, 
            textvariable=self.api_var, 
            placeholder_text="http://localhost:8081",
            width=300,
            font=ctk.CTkFont(size=14),
            border_width=2,
            corner_radius=8
        )
        self.api_entry.pack(side="left", padx=10)
        
        self.api_entry.bind("<Key>", on_paste)

        # --- Frame Controls ---
        self.frame_ctrl = ctk.CTkFrame(self.main_frame, corner_radius=10, fg_color="transparent")
        self.frame_ctrl.pack(fill="x", pady=(0, 15))

        self.btn_start = ctk.CTkButton(
            self.frame_ctrl, 
            text="▶ Включить", 
            command=self.start_bot,
            fg_color="#28a745", hover_color="#218838",
            font=ctk.CTkFont(size=15, weight="bold"),
            corner_radius=8
        )
        self.btn_start.pack(side="left", padx=(0, 10))

        self.btn_stop = ctk.CTkButton(
            self.frame_ctrl, 
            text="⏹ Отключить", 
            command=self.stop_bot,
            state="disabled",
            fg_color="#dc3545", hover_color="#c82333",
            font=ctk.CTkFont(size=15, weight="bold"),
            corner_radius=8
        )
        self.btn_stop.pack(side="left")

        self.lbl_status = ctk.CTkLabel(
            self.frame_ctrl, 
            text="ОТКЛЮЧЕН", 
            text_color="#dc3545", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.lbl_status.pack(side="right", padx=10)

        # --- Log Text ---
        self.log_area = ctk.CTkTextbox(
            self.main_frame, 
            state="disabled", 
            wrap="word", 
            font=ctk.CTkFont(family="Consolas", size=13),
            corner_radius=10,
            border_width=2
        )
        self.log_area.pack(fill="both", expand=True)

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.token_var.set(config.get("token", ""))
                    self.api_var.set(config.get("local_api_server", ""))
            except Exception as e:
                self.log(f"[ERROR] Ошибка загрузки конфига: {e}")

    def _save_config(self):
        token = self.token_var.get().strip()
        api_server = self.api_var.get().strip()
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"token": token, "local_api_server": api_server}, f)
        self.log("[SYSTEM] Конфиг успешно сохранён.")

    def log(self, message: str):
        # Безопасно обновляем UI из других потоков
        self.after(0, self._append_log, message)

    def _append_log(self, message: str):
        self.log_area.configure(state="normal")
        self.log_area.insert("end", message + "\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    def start_bot(self):
        token = self.token_var.get().strip()
        api_server = self.api_var.get().strip()
        if not token:
            messagebox.showerror("Ошибка", "Введите токен бота!")
            return

        self.bot_runner = BotRunner(
            token=token, 
            temp_dir=self.temp_dir, 
            logger_callback=self.log,
            local_api_server=api_server if api_server else None
        )
        self.bot_runner.start()

        self.btn_start.configure(state="disabled", fg_color="gray")
        self.btn_stop.configure(state="normal", fg_color="#dc3545")
        self.lbl_status.configure(text="АКТИВЕН", text_color="#28a745")

    def stop_bot(self):
        if self.bot_runner:
            self.bot_runner.stop()
        self.btn_start.configure(state="normal", fg_color="#28a745")
        self.btn_stop.configure(state="disabled", fg_color="gray")
        self.lbl_status.configure(text="ОТКЛЮЧЕН", text_color="#dc3545")
        
    def on_closing(self):
        if self.bot_runner and self.bot_runner.is_running:
            self.stop_bot()
        self.destroy()
