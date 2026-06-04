import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import Canvas, IntVar, StringVar, Tk, messagebox
from tkinter import ttk

try:
    from PIL import Image, ImageDraw, ImageFont, ImageGrab
except Exception:  # pragma: no cover - optional runtime dependency
    Image = None
    ImageDraw = None
    ImageFont = None
    ImageGrab = None


if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "timelog_data.json"
SCREENSHOT_DIR = APP_DIR / "screenshots"


DEFAULT_DATA = {
    "config": {
        "print_min_minutes": 15,
        "print_max_minutes": 25,
    },
    "days": {},
    "current_session_seconds": 0,
}


def deep_copy_default_data():
    return json.loads(json.dumps(DEFAULT_DATA))


def load_data():
    if not DATA_FILE.exists():
        return deep_copy_default_data()

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
    except (json.JSONDecodeError, OSError):
        messagebox.showwarning(
            "Invalid Data",
            "Could not read timelog_data.json. Starting with clean data.",
        )
        return deep_copy_default_data()

    data = deep_copy_default_data()
    data["config"].update(loaded.get("config", {}))
    data["days"].update(loaded.get("days", {}))
    data["current_session_seconds"] = int(loaded.get("current_session_seconds", 0))
    return data


def save_data(data):
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def seconds_to_hms(seconds):
    seconds = int(max(0, seconds))
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def current_day(now):
    return now.date().isoformat()


def month_key_from_day(day_key):
    return day_key[:7]


def ensure_day(data, day_key):
    if day_key not in data["days"]:
        data["days"][day_key] = {
            "seconds": 0,
            "screenshots": [],
            "sessions": [],
        }
    return data["days"][day_key]

  
class TimeLogTracker:
    def __init__(self, root):
        self.root = root
        self.root.title("TimeLog Tracker")
        self.root.geometry("1320x820")
        self.root.minsize(1100, 700)

        SCREENSHOT_DIR.mkdir(exist_ok=True)
        self.data = load_data()
        self.running = False
        self.last_tick = None
        self.session_started_at = None
        self.session_elapsed_seconds = int(self.data.get("current_session_seconds", 0))
        self.next_screenshot_at = None
        self.last_autosave_at = None
        self.selected_date = datetime.now().date()

        self.status_var = StringVar(value="Paused")
        self.total_worked_var = StringVar(value="00:00:00")
        self.session_var = StringVar(value="00:00:00")
        self.next_print_var = StringVar(value="Next screenshot: paused")

        config = self.data["config"]
        self.print_min_var = IntVar(value=int(config["print_min_minutes"]))
        self.print_max_var = IntVar(value=int(config["print_max_minutes"]))

        self.apply_theme()
        self.build_layout()
        self.refresh_all()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(1000, self.tick)

    def apply_theme(self):
        self.colors = {
            "bg": "#0d0f12",
            "panel": "#14161a",
            "panel_2": "#1a1d22",
            "border": "#1f242b",
            "text": "#f5f7fb",
            "muted": "#aeb8c8",
            "accent": "#19b7ff",
            "accent_2": "#00d084",
            "danger": "#ff4d6d",
        }

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("Panel.TFrame", background=self.colors["panel"], borderwidth=0, relief="flat")
        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["text"])
        style.configure("Muted.TLabel", foreground=self.colors["muted"], background=self.colors["bg"])
        style.configure("Panel.TLabel", background=self.colors["panel"], foreground=self.colors["text"])
        style.configure("PanelMuted.TLabel", background=self.colors["panel"], foreground=self.colors["muted"])
        style.configure("Row.TLabel", background=self.colors["panel_2"], foreground=self.colors["text"])
        style.configure("RowAccent.TLabel", background=self.colors["panel_2"], foreground=self.colors["accent"])
        style.configure("SoftRow.TFrame", background=self.colors["panel_2"], borderwidth=0, relief="flat")
        style.configure("Accent.TLabel", background=self.colors["panel"], foreground=self.colors["accent"], font=("Segoe UI", 10, "bold"))
        style.configure("Big.TLabel", background=self.colors["panel"], foreground=self.colors["accent"], font=("Segoe UI", 28, "bold"))
        style.configure("Timer.TLabel", background=self.colors["panel"], foreground=self.colors["text"], font=("Segoe UI", 20, "bold"))
        style.configure("Title.TLabel", background=self.colors["bg"], foreground=self.colors["text"], font=("Segoe UI", 16, "bold"))
        style.configure("TButton", background=self.colors["panel_2"], foreground=self.colors["text"], bordercolor=self.colors["panel_2"], lightcolor=self.colors["panel_2"], darkcolor=self.colors["panel_2"], borderwidth=0, relief="flat", focusthickness=0, focuscolor=self.colors["panel_2"], padding=(12, 8))
        style.map("TButton", background=[("active", "#252a32"), ("pressed", "#20242b")], foreground=[("disabled", "#6d7480")])
        style.configure("Accent.TButton", background=self.colors["accent"], foreground="#081018", font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#49c7ff"), ("pressed", "#0ca4eb")])
        style.configure("Danger.TButton", background="#2a1820", foreground=self.colors["danger"])
        style.configure("TEntry", fieldbackground="#0f1115", foreground=self.colors["text"], insertcolor=self.colors["text"], bordercolor="#0f1115", lightcolor="#0f1115", darkcolor="#0f1115", borderwidth=0, relief="flat")
        style.configure("TCheckbutton", background=self.colors["panel"], foreground=self.colors["text"], indicatorcolor="#0f1115")
        style.map("TCheckbutton", background=[("active", self.colors["panel"])], foreground=[("active", self.colors["text"])])
        style.configure("Vertical.TScrollbar", background=self.colors["panel_2"], troughcolor=self.colors["bg"], bordercolor=self.colors["bg"], arrowcolor=self.colors["muted"], lightcolor=self.colors["panel_2"], darkcolor=self.colors["panel_2"], borderwidth=0, relief="flat")
        style.map("Vertical.TScrollbar", background=[("active", "#252a32"), ("pressed", "#20242b")])

        self.root.configure(bg=self.colors["bg"])
        self.root.option_add("*background", self.colors["bg"])
        self.root.option_add("*foreground", self.colors["text"])
        self.root.option_add("*Entry.background", "#0f1115")
        self.root.option_add("*Entry.foreground", self.colors["text"])

    def build_layout(self):
        shell = ttk.Frame(self.root, padding=18)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(shell, style="Panel.TFrame", padding=16)
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 18))
        ttk.Label(sidebar, text="TIMELOG", foreground=self.colors["accent"], background=self.colors["panel"], font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 18))
        ttk.Button(sidebar, text="Dashboard", command=self.refresh_all).pack(fill="x", pady=4)
        ttk.Button(sidebar, text="Open Screenshots", command=self.open_screenshots_folder).pack(fill="x", pady=4)
        ttk.Button(sidebar, text="Screenshot Now", command=self.take_screenshot).pack(fill="x", pady=4)

        content = ttk.Frame(shell)
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        canvas = Canvas(content, background=self.colors["bg"], highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(content, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        main = ttk.Frame(canvas)
        self.main_window = canvas.create_window((0, 0), window=main, anchor="nw")
        self.scroll_canvas = canvas
        main.bind("<Configure>", self.on_scroll_frame_configure)
        canvas.bind("<Configure>", self.on_scroll_canvas_configure)
        canvas.bind_all("<MouseWheel>", self.on_mousewheel)

        main.columnconfigure(0, weight=1)
        main.rowconfigure(5, weight=1)

        ttk.Label(main, text="TIMELOG TRACKER", style="Title.TLabel").grid(row=0, column=0, pady=(0, 16))

        self.wide_metric_card(main, 1, "Current Session", self.session_var, "Big.TLabel")
        self.wide_metric_card(main, 2, "Total Worked", self.total_worked_var, "Timer.TLabel")

        controls = ttk.Frame(main, style="Panel.TFrame", padding=14)
        controls.grid(row=3, column=0, sticky="ew", pady=20)

        button_bar = ttk.Frame(controls, style="Panel.TFrame")
        button_bar.pack(anchor="center")
        ttk.Button(button_bar, text="START WORK", style="Accent.TButton", command=self.start).pack(side="left", padx=6)
        ttk.Button(button_bar, text="PAUSE", command=self.pause).pack(side="left", padx=6)
        ttk.Button(button_bar, text="RESET SESSION", command=self.reset_session).pack(side="left", padx=6)

        ttk.Label(controls, textvariable=self.status_var, style="PanelMuted.TLabel").pack(anchor="center", pady=(14, 0))
        ttk.Label(controls, textvariable=self.next_print_var, style="PanelMuted.TLabel").pack(anchor="center", pady=(4, 0))

        history_panel = ttk.Frame(main, style="Panel.TFrame", padding=14)
        history_panel.grid(row=4, column=0, sticky="nsew")
        history_panel.columnconfigure(0, weight=1)
        history_panel.rowconfigure(1, weight=1)
        ttk.Label(history_panel, text="Monthly History", style="PanelMuted.TLabel").grid(row=0, column=0, pady=(0, 10))
        self.history_rows = ttk.Frame(history_panel, style="Panel.TFrame")
        self.history_rows.grid(row=1, column=0, sticky="ew")
        self.history_rows.columnconfigure(0, weight=1)


    def wide_metric_card(self, parent, row, label, variable, value_style):
        card = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        card.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        ttk.Label(card, text=label, style="PanelMuted.TLabel").pack()
        ttk.Label(card, textvariable=variable, style=value_style).pack(pady=(16, 12))

    def metric_card(self, parent, column, label, variable, value_style):
        card = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        card.grid(row=0, column=column, sticky="ew", padx=6)
        ttk.Label(card, text=label, style="PanelMuted.TLabel").pack()
        ttk.Label(card, textvariable=variable, style=value_style).pack(pady=(10, 0))

    def on_scroll_frame_configure(self, _event=None):
        self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

    def on_scroll_canvas_configure(self, event):
        self.scroll_canvas.itemconfigure(self.main_window, width=event.width)

    def on_mousewheel(self, event):
        self.scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def save_config(self):
        minimum = max(1, int(self.print_min_var.get()))
        maximum = max(minimum, int(self.print_max_var.get()))
        self.print_min_var.set(minimum)
        self.print_max_var.set(maximum)
        self.data["config"].update(
            {
                "print_min_minutes": minimum,
                "print_max_minutes": maximum,
            }
        )
        save_data(self.data)
        self.schedule_next_screenshot()
        self.refresh_all()

    def start(self):
        if self.running:
            return
        now = datetime.now()
        self.running = True
        self.last_tick = now
        self.session_started_at = now
        self.last_autosave_at = now
        self.status_var.set("Status: running")
        self.schedule_next_screenshot()

    def pause(self):
        if not self.running:
            return
        now = datetime.now()
        self.commit_elapsed(now)
        if self.session_started_at:
            day_key = current_day(now)
            day = ensure_day(self.data, day_key)
            day.setdefault("sessions", []).append(
                {
                    "started_at": self.session_started_at.isoformat(timespec="seconds"),
                    "ended_at": now.isoformat(timespec="seconds"),
                    "seconds": int((now - self.session_started_at).total_seconds()),
                }
            )
        self.running = False
        self.last_tick = None
        self.session_started_at = None
        self.last_autosave_at = None
        self.next_screenshot_at = None
        self.status_var.set("Status: paused")
        self.next_print_var.set("Next screenshot: paused")
        save_data(self.data)
        self.refresh_all()

    def reset_session(self):
        now = datetime.now()
        if self.running:
            self.commit_elapsed(now)
            self.last_tick = now
            self.session_started_at = now
        else:
            self.session_started_at = None
        self.session_elapsed_seconds = 0
        self.data["current_session_seconds"] = 0
        save_data(self.data)
        self.refresh_all()

    def get_current_session_seconds(self, now=None):
        now = now or datetime.now()
        seconds = self.session_elapsed_seconds
        if self.running and self.last_tick:
            seconds += max(0, int((now - self.last_tick).total_seconds()))
        return seconds

    def tick(self):
        if self.running:
            now = datetime.now()
            self.commit_elapsed(now)
            if self.next_screenshot_at and now >= self.next_screenshot_at:
                self.take_screenshot()
                self.schedule_next_screenshot()
            if not self.last_autosave_at or (now - self.last_autosave_at).total_seconds() >= 30:
                save_data(self.data)
                self.last_autosave_at = now
            self.refresh_all()
        self.root.after(1000, self.tick)

    def commit_elapsed(self, now):
        if not self.last_tick:
            self.last_tick = now
            return

        delta = max(0, int((now - self.last_tick).total_seconds()))
        if delta == 0:
            return

        day_key = current_day(now)
        day = ensure_day(self.data, day_key)
        day["seconds"] = int(day.get("seconds", 0)) + delta
        self.session_elapsed_seconds += delta
        self.data["current_session_seconds"] = self.session_elapsed_seconds
        self.last_tick = now

    def schedule_next_screenshot(self):
        if not self.running:
            return
        minimum = int(self.print_min_var.get())
        maximum = int(self.print_max_var.get())
        minutes = random.randint(minimum, maximum)
        self.next_screenshot_at = datetime.now() + timedelta(minutes=minutes)
        self.next_print_var.set(f"Next screenshot: {self.next_screenshot_at.strftime('%H:%M:%S')}")

    def take_screenshot(self):
        now = datetime.now()
        if self.running:
            self.commit_elapsed(now)
        day_key = current_day(now)
        day_folder = SCREENSHOT_DIR / day_key
        day_folder.mkdir(parents=True, exist_ok=True)
        filename = f"raid_{now.strftime('%Y-%m-%d_%H-%M-%S')}.png"
        path = day_folder / filename

        if ImageGrab is None:
            messagebox.showerror(
                "Screenshot Unavailable",
                "Install Pillow to capture screenshots: pip install pillow",
            )
            return

        was_visible = self.root.state() != "withdrawn"
        was_topmost = bool(self.root.attributes("-topmost"))

        try:
            if was_visible:
                self.root.attributes("-topmost", False)
                self.root.withdraw()
                self.root.update_idletasks()
                self.root.update()
                time.sleep(0.35)
            image = ImageGrab.grab(all_screens=True)
            image = self.add_timer_card(image)
            image.save(path)
        except Exception as error:
            messagebox.showerror("Screenshot Error", f"Could not capture screenshot:\n{error}")
            return
        finally:
            if was_visible:
                self.root.deiconify()
                self.root.lift()
                self.root.attributes("-topmost", was_topmost)
                self.root.update_idletasks()

        day = ensure_day(self.data, day_key)
        day.setdefault("screenshots", []).append(
            {
                "created_at": now.isoformat(timespec="seconds"),
                "file": str(path),
            }
        )
        save_data(self.data)
        self.refresh_all()

    def add_timer_card(self, image):
        if Image is None or ImageDraw is None or ImageFont is None:
            return image

        session_seconds = self.get_current_session_seconds()
        timer_text = seconds_to_hms(session_seconds)
        label_text = "CURRENT SESSION"

        image = image.convert("RGBA")
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        label_font = self.load_font(24)
        timer_font = self.load_font(58)
        padding_x = 38
        padding_y = 28
        gap = 6
        radius = 24
        top_margin = 42
        right_margin = 180

        label_box = draw.textbbox((0, 0), label_text, font=label_font)
        timer_box = draw.textbbox((0, 0), timer_text, font=timer_font)
        label_width = label_box[2] - label_box[0]
        label_height = label_box[3] - label_box[1]
        timer_width = timer_box[2] - timer_box[0]
        timer_height = timer_box[3] - timer_box[1]

        card_width = max(label_width, timer_width) + padding_x * 2
        card_height = label_height + timer_height + gap + padding_y * 2
        left = image.width - card_width - right_margin
        top = top_margin
        right = left + card_width
        bottom = top + card_height

        draw.rounded_rectangle(
            (left, top, right, bottom),
            radius=radius,
            fill=(13, 15, 18, 224),
            outline=(25, 183, 255, 130),
            width=1,
        )
        draw.text(
            (left + padding_x, top + padding_y),
            label_text,
            font=label_font,
            fill=(174, 184, 200, 255),
        )
        draw.text(
            (left + padding_x, top + padding_y + label_height + gap),
            timer_text,
            font=timer_font,
            fill=(25, 183, 255, 255),
        )

        return Image.alpha_composite(image, overlay).convert("RGB")

    def load_font(self, size):
        font_paths = [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def refresh_all(self):
        now = datetime.now()
        today_key = current_day(now)
        current_month = month_key_from_day(today_key)
        total_seconds = sum(int(day.get("seconds", 0)) for day in self.data["days"].values())
        session_seconds = self.get_current_session_seconds(now)

        self.total_worked_var.set(seconds_to_hms(total_seconds))
        self.session_var.set(seconds_to_hms(session_seconds))
        self.refresh_history(current_month)

    def refresh_history(self, current_month):
        for child in self.history_rows.winfo_children():
            child.destroy()

        header = ttk.Frame(self.history_rows, style="Panel.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=1)
        header.columnconfigure(2, weight=1)
        ttk.Label(header, text="Date", style="PanelMuted.TLabel").grid(row=0, column=0, sticky="w", padx=12)
        ttk.Label(header, text="Time", style="PanelMuted.TLabel").grid(row=0, column=1, sticky="w", padx=12)
        ttk.Label(header, text="Screenshots", style="PanelMuted.TLabel").grid(row=0, column=2, sticky="w", padx=12)

        row_index = 1
        for day_key in sorted(self.data["days"], reverse=True):
            if month_key_from_day(day_key) != current_month:
                continue
            day = self.data["days"][day_key]
            row = ttk.Frame(self.history_rows, style="SoftRow.TFrame", padding=(12, 10))
            row.grid(row=row_index, column=0, sticky="ew", pady=4)
            row.columnconfigure(0, weight=1)
            row.columnconfigure(1, weight=1)
            row.columnconfigure(2, weight=1)
            ttk.Label(row, text=day_key, style="Row.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(row, text=seconds_to_hms(day.get("seconds", 0)), style="RowAccent.TLabel").grid(row=0, column=1, sticky="w")
            ttk.Label(row, text=str(len(day.get("screenshots", []))), style="Row.TLabel").grid(row=0, column=2, sticky="w")
            row.bind("<Button-1>", lambda _event, selected=day_key: self.select_history_day(selected))
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda _event, selected=day_key: self.select_history_day(selected))
            row_index += 1

    def select_history_day(self, day_key):
        try:
            self.selected_date = datetime.fromisoformat(day_key).date()
        except ValueError:
            pass

    def open_screenshots_folder(self):
        self.open_folder(SCREENSHOT_DIR)

    def open_selected_day_folder(self):
        self.open_folder(SCREENSHOT_DIR / self.selected_date.isoformat())

    def open_folder(self, folder):
        folder.mkdir(parents=True, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(folder)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(folder)], check=False)
        else:
            subprocess.run(["xdg-open", str(folder)], check=False)

    def on_close(self):
        if self.running:
            self.pause()
        self.save_config()
        self.root.destroy()


if __name__ == "__main__":
    root = Tk()
    app = TimeLogTracker(root)
    root.mainloop()
