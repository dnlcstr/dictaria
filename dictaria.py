import os
import sys
import json
import tempfile
import threading
import queue

import numpy as np
import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel

import tkinter as tk
from tkinter import scrolledtext

from pynput import keyboard

# --------------------
# CONFIG
# --------------------

MODEL_SIZE = "medium"      # "small", "medium", "large-v3"
SAMPLE_RATE = 16000
DEVICE_INDEX = None
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

HOTKEY_COMBO = "<cmd>+<shift>+j"
CONFIG_PATH = os.path.expanduser("~/.dictaria_config.json")

MAX_FAVORITES = 5

# language_code, flag, native_name
LANG_DEFS = [
    ("es", "🇪🇸", "Español"),
    ("en", "🇬🇧", "English"),
    ("ja", "🇯🇵", "日本語"),
    ("pt", "🇵🇹", "Português"),
    ("fr", "🇫🇷", "Français"),
    ("it", "🇮🇹", "Italiano"),
    ("de", "🇩🇪", "Deutsch"),
    ("ru", "🇷🇺", "Русский"),
    ("he", "🇮🇱", "עברית"),
    ("ar", "🇸🇦", "العربية"),
    ("zh", "🇨🇳", "中文"),
    ("ko", "🇰🇷", "한국어"),
    ("pl", "🇵🇱", "Polski"),
    ("uk", "🇺🇦", "Українська"),
    ("tr", "🇹🇷", "Türkçe"),
    ("vi", "🇻🇳", "Tiếng Việt"),
    ("id", "🇮🇩", "Bahasa Indonesia"),
    ("hi", "🇮🇳", "हिन्दी"),
    ("bn", "🇧🇩", "বাংলা"),
    ("ur", "🇵🇰", "اُردُو"),
    ("fa", "🇮🇷", "فارسی"),
    ("nl", "🇳🇱", "Nederlands"),
    ("sv", "🇸🇪", "Svenska"),
    ("no", "🇳🇴", "Norsk"),
    ("da", "🇩🇰", "Dansk"),
    ("cs", "🇨🇿", "Čeština"),
    ("el", "🇬🇷", "Ελληνικά"),
    ("ro", "🇷🇴", "Română"),
    ("hu", "🇭🇺", "Magyar"),
]

# system messages (always English; some bilingual)
MSG_SELECT_LANG = "[Please choose a language before recording]"
MSG_NO_AUDIO = "[No useful audio recorded]"
MSG_NO_TEXT = "[No text recognized]"
MSG_FAV_LIMIT = "[Favorites limit reached (5)]"
MSG_LISTENING = "[Listening / Escuchando...]"
MSG_TRANSCRIBING_FMT = "[Transcribing / Transcribiendo ({lang_code})...]"

HELP_TEXT = (
    "Tips: Choose up to 5 favorite languages from the menu, then click a flag above the red button to set the "
    "active language. Press Cmd + Shift + J to start/stop recording while Dictaria is open in the background."
)

# color themes
LIGHT_THEME = {
    "root_bg": "#ffffff",
    "topbar_bg": "#ffffff",
    "topbar_fg": "#222222",
    "card_bg": "#ffffff",
    "border_color": "#dddddd",
    "text_frame_bg": "#f2f2f2",
    "text_box_bg": "#ffffff",
    "text_fg": "#222222",
    "record_idle_fill": "#ff3333",
    "record_idle_outline": "#000000",  # red button in light mode: black border
    "record_active_fill": "#555555",
    "record_active_outline": "#ffffff",
    "record_disabled_fill": "#bbbbbb",
    "record_disabled_outline": "#eeeeee",
    "icon_fg": "#555555",
    "fav_active_bg": "#e0e0e0",
    "fav_active_fg": "#000000",
    "fav_inactive_bg": "#f8f8f8",
    "fav_inactive_fg": "#666666",
}

DARK_THEME = {
    "root_bg": "#101010",
    "topbar_bg": "#151515",
    "topbar_fg": "#f5f5f5",
    "card_bg": "#181818",
    "border_color": "#333333",
    "text_frame_bg": "#202020",
    "text_box_bg": "#111111",
    "text_fg": "#f5f5f5",
    "record_idle_fill": "#ff4444",
    "record_idle_outline": "#ffffff",
    "record_active_fill": "#888888",
    "record_active_outline": "#ffffff",
    "record_disabled_fill": "#444444",
    "record_disabled_outline": "#777777",
    "icon_fg": "#cccccc",
    "fav_active_bg": "#303030",
    "fav_active_fg": "#ffffff",
    "fav_inactive_bg": "#202020",
    "fav_inactive_fg": "#aaaaaa",
}

print(f"Dictaria GUI: model={MODEL_SIZE}, device={DEVICE}, compute_type={COMPUTE_TYPE}")
model = WhisperModel(
    MODEL_SIZE,
    device=DEVICE,
    compute_type=COMPUTE_TYPE,
)

audio_queue = queue.Queue()
recording = False
stream = None


def audio_callback(indata, frames, time, status):
    if status:
        print(status)
    audio_queue.put(indata.copy())


def start_recording():
    global recording, stream
    if recording:
        return
    recording = True
    with audio_queue.mutex:
        audio_queue.queue.clear()
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        callback=audio_callback,
        device=DEVICE_INDEX,
    )
    stream.start()
    print("Recording started.")


def stop_recording():
    global recording, stream
    if not recording:
        return None
    recording = False
    if stream is not None:
        stream.stop()
        stream.close()
        stream = None
    print("Recording stopped.")

    chunks = []
    while not audio_queue.empty():
        chunks.append(audio_queue.get())

    if not chunks:
        return None

    audio = np.concatenate(chunks, axis=0)
    max_level = float(audio.max())
    print(f"Max level: {max_level}")

    if max_level < 0.01:
        print("Input level too low; probably silence or mic misconfigured.")
        return None

    return audio


def transcribe_audio_array(audio, language=None, samplerate=SAMPLE_RATE):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = tmp.name

    sf.write(path, audio, samplerate)

    try:
        kwargs = {
            "beam_size": 1,
            "best_of": 1,
            "temperature": 0,
            "condition_on_previous_text": False,
        }
        if language:
            kwargs["language"] = language

        segments, info = model.transcribe(path, **kwargs)
        textos = [seg.text.strip() for seg in segments]
        return " ".join(textos).strip()
    finally:
        if os.path.exists(path):
            os.remove(path)


def set_macos_dock_icon():
    """
    Try to change Dock icon in macOS using icon.png next to dictaria.py.
    If anything fails, just print and continue.
    """
    if sys.platform != "darwin":
        return

    icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
    if not os.path.exists(icon_path):
        print("No icon.png found next to dictaria.py")
        return

    try:
        from Cocoa import NSApplication, NSImage
        app = NSApplication.sharedApplication()
        img = NSImage.alloc().initByReferencingFile_(icon_path)
        if img is not None:
            app.setApplicationIconImage_(img)
            print("Dock icon set from", icon_path)
        else:
            print("Could not load icon image for Dock")
    except Exception as e:
        print("Could not set macOS Dock icon:", e)


class DictariaApp:
    def __init__(self, root):
        self.root = root

        # config/state
        self.config_path = CONFIG_PATH
        self.max_favorites = MAX_FAVORITES

        self.dark_mode = True
        self.theme = DARK_THEME
        self.favorites = []
        self.active_language = None
        self.show_help = True

        self.lang_vars = {}
        self.lang_info = {code: (flag, name) for code, flag, name in LANG_DEFS}
        self.suppress_menu_callback = False

        self.is_recording = False

        self.load_config()
        self.theme = DARK_THEME if self.dark_mode else LIGHT_THEME

        self.build_ui()
        self.apply_config_to_ui()

    # ---------------- UI BUILD ----------------

    def build_ui(self):
        # window
        self.root.overrideredirect(True)
        self.root.geometry("720x520+200+150")
        self.root.configure(bg=self.theme["root_bg"])
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        # top bar
        self.topbar = tk.Frame(
            self.root,
            bg=self.theme["topbar_bg"],
            height=36,
            highlightthickness=0,
            bd=0,
        )
        self.topbar.pack(fill="x")

        self._drag_x = 0
        self._drag_y = 0
        self.topbar.bind("<ButtonPress-1>", self._start_move)
        self.topbar.bind("<B1-Motion>", self._on_move)

        self.title_label = tk.Label(
            self.topbar,
            text="Dictaria  |  Choose your favorite languages and press Cmd + Shift + J",
            bg=self.theme["topbar_bg"],
            fg=self.theme["topbar_fg"],
            font=("Helvetica", 11),
        )
        self.title_label.pack(side="left", padx=12)

        # theme toggle
        self.theme_btn = tk.Label(
            self.topbar,
            text="☾" if self.dark_mode else "☀︎",
            bg=self.theme["topbar_bg"],
            fg=self.theme["icon_fg"],
            font=("Helvetica", 11),
            cursor="hand2",
        )
        self.theme_btn.pack(side="right", padx=8)
        self.theme_btn.bind("<Button-1>", self.toggle_theme)

        # language menu button
        self.lang_menu_button = tk.Menubutton(
            self.topbar,
            text="Languages ▾",
            bg=self.theme["topbar_bg"],
            fg=self.theme["topbar_fg"],
            font=("Helvetica", 10),
            cursor="hand2",
            relief=tk.FLAT,
            highlightthickness=0,
            bd=0,
        )
        self.lang_menu_button.pack(side="right", padx=10)

        self.lang_menu = tk.Menu(self.lang_menu_button, tearoff=0)
        self.lang_menu_button.configure(menu=self.lang_menu)

        for code, flag, name in LANG_DEFS:
            var = tk.BooleanVar(value=False)
            self.lang_vars[code] = var
            label = f"{flag} {name}"
            self.lang_menu.add_checkbutton(
                label=label,
                onvalue=True,
                offvalue=False,
                variable=var,
                command=lambda c=code: self.on_lang_menu_toggle(c),
            )

        # main card
        self.card_outer = tk.Frame(
            self.root,
            bg=self.theme["root_bg"],
            highlightthickness=0,
            bd=0,
        )
        self.card_outer.pack(expand=True, fill="both", padx=24, pady=24)

        self.card_inner = tk.Frame(
            self.card_outer,
            bg=self.theme["card_bg"],
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme["border_color"],
        )
        self.card_inner.pack(expand=True, fill="both", padx=4, pady=4)

        # favorites row
        self.fav_frame = tk.Frame(
            self.card_inner,
            bg=self.theme["card_bg"],
            bd=0,
            highlightthickness=0,
        )
        self.fav_frame.pack(pady=(10, 4))

        # record button canvas
        self.button_canvas = tk.Canvas(
            self.card_inner,
            width=90,
            height=90,
            bg=self.theme["card_bg"],
            highlightthickness=0,
            bd=0,
        )
        self.button_canvas.pack(pady=12)

        self.record_circle = self.button_canvas.create_oval(
            10, 10, 80, 80,
            fill=self.theme["record_disabled_fill"],
            outline=self.theme["record_disabled_outline"],
            width=4,
        )
        self.button_canvas.bind("<Button-1>", self.on_button_click)

        # separator
        self.separator = tk.Frame(
            self.card_inner,
            height=1,
            bg=self.theme["border_color"],
        )
        self.separator.pack(fill="x", padx=16, pady=8)

        # text frame
        self.text_frame = tk.Frame(
            self.card_inner,
            bg=self.theme["text_frame_bg"],
            bd=0,
            highlightthickness=0,
        )
        self.text_frame.pack(fill="both", expand=True, padx=16, pady=16)

        self.text_box = scrolledtext.ScrolledText(
            self.text_frame,
            wrap=tk.WORD,
            font=("Helvetica", 13),
            bg=self.theme["text_box_bg"],
            fg=self.theme["text_fg"],
            insertbackground=self.theme["text_fg"],
            bd=0,
            relief=tk.FLAT,
        )
        self.text_box.pack(fill="both", expand=True, padx=6, pady=6)
        self.text_box.tag_config(
            "system",
            foreground="#ff5555",
            font=("Helvetica", 10),
        )

        # help panel
        self.help_frame = tk.Frame(
            self.card_inner,
            bg=self.theme["card_bg"],
            bd=0,
            highlightthickness=0,
        )
        self.help_label = tk.Label(
            self.help_frame,
            text=HELP_TEXT,
            bg=self.theme["card_bg"],
            fg=self.theme["text_fg"],
            font=("Helvetica", 9),
            justify="left",
            wraplength=660,
        )
        self.help_label.pack(side="left", padx=8, pady=4)

        self.help_toggle_btn = tk.Label(
            self.help_frame,
            text="[Hide]",
            bg=self.theme["card_bg"],
            fg=self.theme["icon_fg"],
            font=("Helvetica", 9, "underline"),
            cursor="hand2",
        )
        self.help_toggle_btn.pack(side="right", padx=8)
        self.help_toggle_btn.bind("<Button-1>", self.toggle_help_panel)

    # -------------- CONFIG LOAD/SAVE --------------

    def load_config(self):
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        self.dark_mode = (data.get("theme", "dark") == "dark")
        valid_codes = {code for code, _, _ in LANG_DEFS}

        favs = data.get("favorites", [])
        self.favorites = [c for c in favs if c in valid_codes]

        active = data.get("active_language")
        self.active_language = active if active in valid_codes else None

        self.show_help = bool(data.get("show_help", True))

    def save_config(self):
        data = {
            "theme": "dark" if self.dark_mode else "light",
            "favorites": self.favorites,
            "active_language": self.active_language,
            "show_help": self.show_help,
        }
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Could not save config:", e)

    def apply_config_to_ui(self):
        self.theme = DARK_THEME if self.dark_mode else LIGHT_THEME
        self.apply_theme()

        # sync menu checkboxes
        self.suppress_menu_callback = True
        for code, var in self.lang_vars.items():
            var.set(code in self.favorites)
        self.suppress_menu_callback = False

        # fix active language if needed
        if self.active_language not in self.favorites:
            if self.favorites:
                self.active_language = self.favorites[0]
            else:
                self.active_language = None

        self.refresh_favorites_row()
        self.update_record_button()
        self.update_help_visibility()

    # ---------------- WINDOW MOVE ----------------

    def _start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_move(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    # ---------------- THEME ----------------

    def toggle_theme(self, event=None):
        self.dark_mode = not self.dark_mode
        self.theme = DARK_THEME if self.dark_mode else LIGHT_THEME
        self.apply_theme()
        self.update_record_button()
        self.refresh_favorites_row()
        self.save_config()

    def apply_theme(self):
        t = self.theme

        self.root.configure(bg=t["root_bg"])
        self.topbar.configure(bg=t["topbar_bg"])
        self.title_label.configure(bg=t["topbar_bg"], fg=t["topbar_fg"])
        self.theme_btn.configure(
            bg=t["topbar_bg"],
            fg=t["icon_fg"],
            text="☾" if self.dark_mode else "☀︎",
        )

        self.lang_menu_button.configure(
            bg=t["topbar_bg"],
            fg=t["topbar_fg"],
        )

        self.card_outer.configure(bg=t["root_bg"])
        self.card_inner.configure(
            bg=t["card_bg"],
            highlightbackground=t["border_color"],
        )

        self.fav_frame.configure(bg=t["card_bg"])
        self.button_canvas.configure(bg=t["card_bg"])
        self.separator.configure(bg=t["border_color"])

        self.text_frame.configure(bg=t["text_frame_bg"])
        self.text_box.configure(
            bg=t["text_box_bg"],
            fg=t["text_fg"],
            insertbackground=t["text_fg"],
        )

        self.help_frame.configure(bg=t["card_bg"])
        self.help_label.configure(bg=t["card_bg"], fg=t["text_fg"])
        self.help_toggle_btn.configure(bg=t["card_bg"], fg=t["icon_fg"])

    # ---------------- HELP PANEL ----------------

    def toggle_help_panel(self, event=None):
        self.show_help = not self.show_help
        self.update_help_visibility()
        self.save_config()

    def update_help_visibility(self):
        if self.show_help:
            self.help_frame.pack(fill="x", padx=16, pady=(0, 10))
            self.help_toggle_btn.config(text="[Hide]")
        else:
            self.help_toggle_btn.config(text="[Show]")
            self.help_frame.pack_forget()

    # ---------------- LANG MENU / FAVORITES ----------------

    def on_lang_menu_toggle(self, code):
        if self.suppress_menu_callback:
            return

        var = self.lang_vars[code]
        want = var.get()

        if want:
            # add to favorites
            if code in self.favorites:
                return
            if len(self.favorites) >= self.max_favorites:
                self.suppress_menu_callback = True
                var.set(False)
                self.suppress_menu_callback = False
                self.append_system(MSG_FAV_LIMIT)
                return
            self.favorites.append(code)
            if self.active_language is None:
                self.set_active_language(code)
            else:
                self.refresh_favorites_row()
        else:
            # remove from favorites
            if code in self.favorites:
                self.favorites.remove(code)
            if self.active_language == code:
                if self.favorites:
                    self.set_active_language(self.favorites[0])
                else:
                    self.active_language = None
            self.refresh_favorites_row()
            self.update_record_button()

        self.save_config()

    def refresh_favorites_row(self):
        for child in self.fav_frame.winfo_children():
            child.destroy()

        t = self.theme

        for code in self.favorites:
            flag, name = self.lang_info[code]
            is_active = (code == self.active_language)

            bg = t["fav_active_bg"] if is_active else t["fav_inactive_bg"]
            fg = t["fav_active_fg"] if is_active else t["fav_inactive_fg"]

            lbl = tk.Label(
                self.fav_frame,
                text=flag,
                font=("Helvetica", 18),
                bg=bg,
                fg=fg,
                bd=0,
                padx=10,
                pady=4,
                cursor="hand2",
            )
            lbl.pack(side="left", padx=6, pady=4)
            lbl.bind("<Button-1>", lambda e, c=code: self.on_favorite_click(c))

    def on_favorite_click(self, code):
        self.set_active_language(code)
        self.save_config()

    def set_active_language(self, code):
        if code is not None and code not in self.favorites:
            if len(self.favorites) >= self.max_favorites:
                self.append_system(MSG_FAV_LIMIT)
                return
            self.favorites.append(code)

        self.active_language = code

        self.suppress_menu_callback = True
        for c, var in self.lang_vars.items():
            var.set(c in self.favorites)
        self.suppress_menu_callback = False

        self.refresh_favorites_row()
        self.update_record_button()

    # ---------------- RECORD BUTTON ----------------

    def update_record_button(self):
        t = self.theme

        if self.active_language is None:
            fill = t["record_disabled_fill"]
            outline = t["record_disabled_outline"]
        else:
            if self.is_recording:
                fill = t["record_active_fill"]
                outline = t["record_active_outline"]
            else:
                fill = t["record_idle_fill"]
                outline = t["record_idle_outline"]

        # ensure black border for red idle in light mode
        if (not self.dark_mode) and self.active_language is not None and not self.is_recording:
            outline = "#000000"

        self.button_canvas.itemconfig(
            self.record_circle,
            fill=fill,
            outline=outline,
        )

    def on_button_click(self, event):
        self.toggle_record()

    # ---------------- RECORD LOGIC ----------------

    def toggle_record(self):
        if self.active_language is None:
            self.append_system(MSG_SELECT_LANG)
            return

        if not self.is_recording:
            # start recording
            start_recording()
            self.is_recording = True
            self.update_record_button()
            # show "Listening / Escuchando..."
            self.append_system(MSG_LISTENING)
        else:
            # stop and transcribe
            self.is_recording = False
            audio = stop_recording()
            self.update_record_button()

            lang_code = self.active_language

            if audio is None:
                self.append_system(MSG_NO_AUDIO)
                return

            threading.Thread(
                target=self._transcribe_thread,
                args=(audio, lang_code),
                daemon=True,
            ).start()

    def _transcribe_thread(self, audio, lang_code):
        # show "Transcribing / Transcribiendo"
        self.append_system(MSG_TRANSCRIBING_FMT.format(lang_code=lang_code))
        text = transcribe_audio_array(audio, language=lang_code)
        if not text:
            self.append_system(MSG_NO_TEXT)
        else:
            self.append_text(text + "\n")

    # ---------------- TEXT APPEND HELPERS ----------------

    def append_text(self, texto):
        def _():
            self.text_box.insert(tk.END, texto)
            self.text_box.see(tk.END)
        self.root.after(0, _)

    def append_system(self, texto):
        def _():
            self.text_box.insert(tk.END, texto + "\n", "system")
            self.text_box.see(tk.END)
        self.root.after(0, _)


# ---------------- GLOBAL HOTKEY ----------------

def start_hotkey_listener(app: DictariaApp):
    def on_activate():
        print("Hotkey Cmd+Shift+J detected")
        app.toggle_record()

    print(f"Starting global hotkey listener: {HOTKEY_COMBO}")
    hotkeys = keyboard.GlobalHotKeys({
        HOTKEY_COMBO: on_activate,
    })
    hotkeys.daemon = True
    hotkeys.start()


def main():
    root = tk.Tk()
    root.title("Dictaria")
    try:
        root.tk.call("tk", "appname", "Dictaria")
    except Exception:
        pass

    # window icon (Tk)
    icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
    if os.path.exists(icon_path):
        try:
            icon_img = tk.PhotoImage(file=icon_path)
            root.iconphoto(True, icon_img)
            # keep a reference to avoid garbage collection
            root._icon_img = icon_img
        except Exception as e:
            print("Could not set Tk window icon:", e)

    # Dock icon (macOS)
    set_macos_dock_icon()

    app = DictariaApp(root)
    start_hotkey_listener(app)
    root.mainloop()


if __name__ == "__main__":
    main()
