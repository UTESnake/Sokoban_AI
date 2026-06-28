import copy
import os
import time
from collections import deque
import pygame
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk, messagebox, scrolledtext

import assets
from game import Game
from solver import Solve
from algorithm.algo_adversarial import alpha_beta, expectimax, minimax
from algorithm.common import apply_step, box_toDock, heuristic, validMove, worker_toBox
from algorithm.algo_complex import (
    ac3_search,
    and_or_search,
    backtracking_search,
    min_conflict_search,
    partially_observable_search,
    search_with_no_observation,
)
from algorithm.algo_infor import astar_search, greedy_search, ida_star_search
from algorithm.algo_local import beam_search, simple_hill_climbing, simulated_annealing_search
from algorithm.algo_uninfor import bfs_search, dfs_search, ids_search


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ══════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════
BG_MAIN  = "#F0F4FF"
BG_PANEL = "#FFFFFF"
ACCENT   = "#5B5BD6"
BTN_TEXT = "#56617D"
BTN_ICON = "#465277"
BTN_SHADOW = "#CBD7E7"
LINE = "#DDE3F0"
TEXT_DARK = "#303846"

# Pygame surface — vừa màn hình hơn, map vẫn được căn giữa
GAME_W, GAME_H = 640, 640
GAME_MIN_W, GAME_MIN_H = 520, 520

# Panel widths follow the reference layout.
LEFT_W = 430
RIGHT_W = 330
ANIMATION_START_DELAY = 450
ANIMATION_STEP_DELAY = 420

# 18 thuật toán — key cũ được giữ, label/icon/màu đổi theo ảnh mẫu
ALGO_GROUPS = [
    ("Tìm kiếm không thông tin", [
        ("BFS",        "BFS",          "●", "#93DDBB"),
        ("DFS1",       "DFS",          "◆", "#B563D9"),
        ("IDS",        "IDS",          "▤", "#61B5D8"),
    ]),
    ("Tìm kiếm có thông tin", [
        ("Astar",      "A*",           "★", "#F07351"),
        ("SMAstar",    "IDA*",         "✦", "#9380C9"),
        ("Greedy",     "Greedy",       "◎", "#FFD64F"),
    ]),
    ("Tìm kiếm cục bộ", [
        ("HillClimb",  "Simple Hill",  "▲", "#5BC89F"),
        ("BeamSearch", "Beam",         "➤", "#F07351"),
        ("SimAnneal",  "Annealing",    "∿", "#54AED3"),
    ]),
    ("Tìm kiếm trong môi trường phức tạp", [
        ("AndOr",       "AND-OR",         "◇", "#9582CF"),
        ("NoObs",       "No Observation", "◌", "#58B7DC"),
        ("PartialObs",  "Partial Obs.",   "◐", "#5BC89F"),
        ("Backtrack",   "Backtracking",   "↵", "#DD4F7D"),
        ("MinConflict", "Min-Conflict",   "▦", "#FFD64F"),
        ("AC3",         "AC-3",           "≋", "#B563D9"),
    ]),
    ("Tìm kiếm đối kháng", [
        ("UCS",        "Minimax",      "♜", "#9582CF"),
        ("BFS2",       "Alpha-Beta",   "αβ", "#58B7DC"),
        ("DFS2",       "Expectimax",   "◈", "#5BC89F"),
    ]),
]

LEVELS = [
    ("Level 1 - Uninformed", "level1_uninformed.txt"),
    ("Level 2 - Informed", "level2_informed.txt"),
    ("Level 3 - Local", "level3_local.txt"),
    ("Level 4 - Complex", "level4_complex.txt"),
    ("Level 5 - Adversarial", "level5_adversarial.txt"),
]
LEVEL_FILES = dict(LEVELS)
OBSERVATION_ALGOS = {"NoObs", "PartialObs"}
LEVEL_OBSERVATION_UNKNOWN_CELLS = {
    "Level 4 - Complex": (
        (2, 5), (3, 5),
        (5, 4), (5, 5), (5, 6), (6, 4),
    ),
}

LEVEL_PROFILES = {
    "Level 1 - Uninformed": {
        "title": "Không thông tin",
        "description": "So sánh cách duyệt rộng, duyệt sâu và sâu dần khi không dùng heuristic.",
        "accent": "#61B5D8",
        "algorithms": ("BFS", "DFS1", "IDS"),
    },
    "Level 2 - Informed": {
        "title": "Có thông tin",
        "description": "Hai kiện hàng và các ngõ cụt làm nổi bật vai trò của hàm heuristic.",
        "accent": "#F07351",
        "algorithms": ("Astar", "SMAstar", "Greedy"),
    },
    "Level 3 - Local": {
        "title": "Tìm kiếm cục bộ",
        "description": "Nhiều lựa chọn gần nhau giúp thấy khác biệt giữa Hill, Beam và Annealing.",
        "accent": "#5BC89F",
        "algorithms": ("HillClimb", "BeamSearch", "SimAnneal"),
    },
    "Level 4 - Complex": {
        "title": "Môi trường phức tạp",
        "description": "So sánh tìm kiếm bất định, quan sát hạn chế và các kỹ thuật thỏa mãn ràng buộc.",
        "accent": "#9582CF",
        "algorithms": (
            "AndOr", "NoObs", "PartialObs",
            "Backtrack", "MinConflict", "AC3"),
    },
    "Level 5 - Adversarial": {
        "title": "Tìm kiếm đối kháng",
        "description": "Đối thủ E đóng vai trò vật cản, tạo tình huống so sánh các chiến lược đối kháng.",
        "accent": "#DD4F7D",
        "algorithms": ("UCS", "BFS2", "DFS2"),
    },
}

ALGO_TO_LEVEL = {
    algorithm: level
    for level, profile in LEVEL_PROFILES.items()
    for algorithm in profile["algorithms"]
}

ALGO_VISUALS = {
    key: {"label": label, "color": color}
    for _group, buttons in ALGO_GROUPS
    for key, label, _icon, color in buttons
}

ALGORITHM_HANDLERS = {
    "BFS": bfs_search,
    "DFS1": dfs_search,
    "IDS": ids_search,
    "Astar": astar_search,
    "SMAstar": ida_star_search,
    "Greedy": greedy_search,
    "HillClimb": simple_hill_climbing,
    "BeamSearch": beam_search,
    "SimAnneal": simulated_annealing_search,
    "AndOr": and_or_search,
    "NoObs": search_with_no_observation,
    "PartialObs": partially_observable_search,
    "Backtrack": backtracking_search,
    "MinConflict": min_conflict_search,
    "AC3": ac3_search,
    "UCS": minimax,
    "BFS2": alpha_beta,
    "DFS2": expectimax,
}

FONT_BOLD  = ("Segoe UI", 10, "bold")
FONT_BTN   = ("Segoe UI",  9, "bold")
FONT_BTN_SMALL = ("Segoe UI", 8, "bold")
FONT_BTN_TINY = ("Segoe UI", 7, "bold")
FONT_ICON = ("Segoe UI Symbol", 11, "bold")
FONT_MONO  = ("Consolas",  10)
FONT_TITLE = ("Segoe UI", 13, "bold")


# ══════════════════════════════════════════════════════════════
#  ROUNDED BUTTON
# ══════════════════════════════════════════════════════════════
class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, bg, fg, command=None,
                 radius=8, width=120, height=36, icon="", **kw):
        super().__init__(parent, width=width, height=height,
                         bg=parent["bg"], highlightthickness=0,
                         cursor="hand2", **kw)
        self.command   = command
        self.bg_normal = bg
        self.bg_hover  = self._shift(bg, 16)
        self.bg_active = self._shift(bg, -8)
        self.fg        = fg
        self.radius    = radius
        self.text      = text
        self.icon      = icon
        self.selected  = False
        self.outline   = self._shift(bg, -26)
        self.shadow    = self._shift(bg, -42)
        self._draw(self.bg_normal)
        self.bind("<Enter>",    lambda _: self._draw(self.bg_hover))
        self.bind("<Leave>",    lambda _: self._draw(self.bg_normal))
        self.bind("<Button-1>", lambda _: self._click())

    def _shift(self, c, amt):
        c = c.lstrip("#")
        r, g, b = (max(0, min(255, int(c[i:i+2], 16) + amt)) for i in (0, 2, 4))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _draw(self, color):
        self.delete("all")
        w, h = int(self["width"]), int(self["height"])
        shadow_h = 4
        body_h = h - shadow_h

        if self.selected:
            body_color = self._shift(color, -10)
            border_color = self._shift(self.bg_normal, -58)
            shadow_color = self._shift(self.bg_normal, -70)
            text_color = "#FFFFFF"
            icon_color = "#FFFFFF"

            # Trạng thái chọn: nổi cao, một viền đậm duy nhất và ánh sáng nhẹ.
            self._rounded_rect(
                3, shadow_h + 1, w - 1, h, self.radius,
                shadow_color, shadow_color)
            self._rounded_rect(
                1, 0, w - 5, body_h - 1, self.radius,
                body_color, border_color, width=3)
            self.create_line(
                10, 5, w - 16, 5,
                fill=self._shift(body_color, 35), width=2)

            # Chấm chọn nhỏ thay cho khung trắng kép cũ.
            badge_x, badge_y = w - 13, 7
            self.create_oval(
                badge_x - 5, badge_y - 5, badge_x + 5, badge_y + 5,
                fill="#FFFFFF", outline=border_color, width=1)
            self.create_oval(
                badge_x - 2, badge_y - 2, badge_x + 2, badge_y + 2,
                fill=border_color, outline="")
        else:
            body_color = color
            text_color = self.fg
            icon_color = BTN_ICON
            self._rounded_rect(
                3, shadow_h, w - 1, h, self.radius,
                self.shadow, self.shadow)
            self._rounded_rect(
                0, 0, w - 4, body_h, self.radius,
                body_color, self.outline, width=2)
            self.create_line(
                8, 8, w - 12, 8,
                fill=self._shift(body_color, 18), width=1)
            self.create_line(
                8, body_h - 8, w - 12, body_h - 8,
                fill=self._shift(body_color, -18), width=1)

        center_y = body_h // 2
        if self.icon:
            text_font = self._fit_text_font(w)
            icon_font = FONT_ICON
            icon_w = tkfont.Font(font=icon_font).measure(self.icon)
            text_w = tkfont.Font(font=text_font).measure(self.text)
            gap = 9
            content_w = icon_w + gap + text_w
            start_x = max(10, ((w - 4) - content_w) // 2)
            icon_x = start_x
            text_x = icon_x + icon_w + gap
            self.create_text(icon_x, center_y, text=self.icon,
                             fill=icon_color, font=icon_font, anchor="w")
            self.create_text(text_x, center_y, text=self.text,
                             fill=text_color, font=text_font, anchor="w")
        else:
            self.create_text(w//2 - 2, center_y, text=self.text,
                             fill=text_color, font=FONT_BTN)

    def _fit_text_font(self, width):
        usable = max(40, width - 34)
        for font in (FONT_BTN, FONT_BTN_SMALL, FONT_BTN_TINY):
            if tkfont.Font(font=font).measure(self.text) <= usable:
                return font
        return FONT_BTN_TINY

    def _rounded_rect(self, x1, y1, x2, y2, radius, fill, outline, width=1):
        radius = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
        self.create_arc(x1, y1, x1+2*radius, y1+2*radius,
                        start=90, extent=90, fill=fill, outline=outline, width=width)
        self.create_arc(x2-2*radius, y1, x2, y1+2*radius,
                        start=0, extent=90, fill=fill, outline=outline, width=width)
        self.create_arc(x1, y2-2*radius, x1+2*radius, y2,
                        start=180, extent=90, fill=fill, outline=outline, width=width)
        self.create_arc(x2-2*radius, y2-2*radius, x2, y2,
                        start=270, extent=90, fill=fill, outline=outline, width=width)
        self.create_rectangle(x1+radius, y1, x2-radius, y2,
                              fill=fill, outline=outline, width=width)
        self.create_rectangle(x1, y1+radius, x2, y2-radius,
                              fill=fill, outline=outline, width=width)

    def _click(self):
        self._draw(self.bg_active)
        if self.command:
            self.command()

    def set_selected(self, selected: bool):
        self.selected = selected
        self._draw(self.bg_normal)

    def set_content(self, text=None, icon=None, bg=None):
        if text is not None:
            self.text = text
        if icon is not None:
            self.icon = icon
        if bg is not None:
            self.bg_normal = bg
            self.bg_hover = self._shift(bg, 16)
            self.bg_active = self._shift(bg, -8)
            self.outline = self._shift(bg, -26)
            self.shadow = self._shift(bg, -42)
        self._draw(self.bg_normal)


# ══════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════
class SokobanApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sokoban Solver")
        self.root.configure(bg=BG_MAIN)
        self.root.resizable(True, True)

        self.selected_algo    = tk.StringVar(value="")
        self.solution_var     = tk.StringVar(value="No solution yet...")
        self.game_initialized = False
        self.loop_job         = None
        self.resize_job       = None
        self.manual_steps     = 0
        self.is_solving       = False
        self.solution_job     = None
        self.current_solution = ""
        self.solution_index   = 0
        self.solution_paused  = False
        self.win_notified     = False
        self.victory_popup    = None
        self.comparison_results = {}
        self.competitor_position = None
        self.competitor_previous_position = None
        self.competitor_under_tile = " "
        self.competitor_turn_requirements = []
        self.observation_fog_enabled = False
        self.observation_revealed = set()

        # col0=left(fixed), col1=game(expands), col2=log(fixed)
        # row0=main(expands), row1=bottom(fixed)
        root.grid_columnconfigure(0, minsize=LEFT_W, weight=0)
        root.grid_columnconfigure(1, minsize=GAME_MIN_W, weight=1)
        root.grid_columnconfigure(2, minsize=RIGHT_W, weight=0)
        root.grid_rowconfigure(0, weight=1)
        root.grid_rowconfigure(1, minsize=72, weight=0)

        win_w = LEFT_W + GAME_W + RIGHT_W + 44
        win_h = GAME_H + 72 + 36
        root.geometry(f"{win_w}x{win_h}")
        root.minsize(LEFT_W + GAME_MIN_W + RIGHT_W + 44, 700)

        self._build_left_panel()
        self._build_game_frame()
        self._build_right_panel()
        self._build_bottom_panel()
        self._bind_keyboard_controls()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(150, self.init_game)

    # ─────────────────────────────────────────
    #  LEFT PANEL
    # ─────────────────────────────────────────
    def _build_left_panel(self):
        outer = tk.Frame(self.root, bg=BG_PANEL,
                         highlightbackground="#9AA6B6", highlightthickness=1,
                         width=LEFT_W)
        outer.grid(row=0, column=0, sticky="nsew", padx=(10, 6), pady=(10, 6))
        outer.grid_propagate(False)

        self.left_canvas = tk.Canvas(outer, bg=BG_PANEL, highlightthickness=0)
        self.left_canvas.configure(yscrollincrement=18)
        self.left_canvas.pack(side="left", fill="both", expand=True)

        f = tk.Frame(self.left_canvas, bg=BG_PANEL)
        self.left_window = self.left_canvas.create_window((0, 0), window=f, anchor="nw")
        f.bind("<Configure>", self._update_left_scrollregion)
        self.left_canvas.bind("<Configure>", self._resize_left_content)
        outer.bind("<Enter>", lambda _: self.left_canvas.bind_all("<MouseWheel>", self._on_left_mousewheel))
        outer.bind("<Leave>", lambda _: self.left_canvas.unbind_all("<MouseWheel>"))

        title_f = tk.Frame(f, bg=BG_PANEL)
        title_f.pack(pady=(10, 6))
        tk.Label(title_f, text="🎮", font=("Segoe UI Emoji", 12),
                 bg=BG_PANEL, width=2, anchor="center").pack(
                     side="left", padx=(0, 8), pady=(1, 0))
        tk.Label(title_f, text="MY SOKOBAN", font=("Segoe UI", 14, "bold"),
                 bg=BG_PANEL, fg=ACCENT).pack(side="left")
        tk.Frame(f, height=1, bg=LINE).pack(fill="x", padx=18)

        # Level selector
        tk.Label(f, text="LEVEL", font=("Segoe UI", 10, "bold"),
                 bg=BG_PANEL, fg=TEXT_DARK).pack(anchor="w", padx=18, pady=(8, 3))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("M.TCombobox",
                        fieldbackground="#456A86", background="#EEF2FF",
                        foreground="#FFFFFF", bordercolor="#456A86",
                        lightcolor="#456A86", darkcolor="#456A86",
                        arrowcolor=ACCENT, font=("Segoe UI", 11, "bold"))
        self.combobox = ttk.Combobox(
            f, style="M.TCombobox", state="readonly",
            font=("Segoe UI", 11, "bold"),
            values=[label for label, _filename in LEVELS])
        self.combobox.current(0)
        self.combobox.pack(padx=18, fill="x")
        self.combobox.bind("<<ComboboxSelected>>", self._on_level_selected)

        tk.Frame(f, height=1, bg=LINE).pack(fill="x", padx=18, pady=7)

        tk.Label(f, text="ALGORITHMS", font=("Segoe UI", 10, "bold"),
                 bg=BG_PANEL, fg=TEXT_DARK).pack(anchor="w", padx=18, pady=(0, 5))

        self.algo_buttons = {}
        for title, buttons in ALGO_GROUPS:
            self._build_algo_group(f, title, buttons)

        # Restart / Stop — rộng hơn theo LEFT_W
        tk.Frame(f, height=1, bg=LINE).pack(fill="x", padx=18, pady=(4, 6))
        RoundedButton(f, text="Restart", icon="▶", bg="#6FCFA9", fg=BTN_TEXT,
                      width=LEFT_W - 58, height=38, command=self.init_game
                      ).pack(padx=18, pady=(0, 5))
        self.stop_button = RoundedButton(
            f, text="Stop", icon="■", bg="#E26087", fg=BTN_TEXT,
            width=LEFT_W - 58, height=38, command=self.stop_game)
        self.stop_button.pack(padx=18, pady=(0, 8))

    def _update_left_scrollregion(self, _event=None):
        self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))

    def _resize_left_content(self, event):
        self.left_canvas.itemconfigure(self.left_window, width=event.width)

    def _on_left_mousewheel(self, event):
        self.left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_algo_group(self, parent, title, buttons):
        group = tk.Frame(parent, bg="#FCFDFF",
                         highlightbackground=LINE, highlightthickness=1)
        group.pack(fill="x", padx=18, pady=(0, 4))

        tk.Label(group, text=title, font=("Segoe UI", 9, "bold"),
                 bg="#FCFDFF", fg="#6B7280").pack(anchor="w", padx=9, pady=(4, 1))

        btn_area = tk.Frame(group, bg="#FCFDFF")
        btn_area.pack(fill="x", padx=7, pady=(0, 4))

        for i, (key, lbl, icon, bg) in enumerate(buttons):
            row, col = divmod(i, 3)
            btn = RoundedButton(btn_area, text=lbl, icon=icon, bg=bg, fg=BTN_TEXT,
                                width=112, height=32, radius=7,
                                command=lambda k=key: self._select_algo(k))
            btn.grid(row=row, column=col, padx=2, pady=2)
            self.algo_buttons[key] = btn

    def _select_algo(self, key):
        self.selected_algo.set(key)
        for k, btn in self.algo_buttons.items():
            btn.set_selected(k == key)
        target_level = ALGO_TO_LEVEL.get(key)
        if target_level and self.combobox.get() != target_level:
            self.combobox.set(target_level)
        self.init_game()
        self._refresh_level_profile()
        self.root.after(20, self.run_solution)

    def _on_level_selected(self, _event=None):
        self._refresh_level_profile()
        self.init_game()

    def _build_game_frame(self):
        outer = tk.Frame(self.root, bg="#1a1a2e",
                         width=GAME_W + 4, height=GAME_H + 4,
                         highlightbackground="#4A45B9", highlightthickness=2)
        outer.grid(row=0, column=1, sticky="nsew", padx=4, pady=(10, 6))
        outer.grid_propagate(False)

        self.game_frame = tk.Frame(outer, bg="#1a1a2e")
        self.game_frame.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        self.game_frame.bind("<Configure>", self._on_game_frame_resize)

    def _on_game_frame_resize(self, event):
        if event.width < 10 or event.height < 10:
            return
        if self.resize_job is not None:
            self.root.after_cancel(self.resize_job)
        self.resize_job = self.root.after(
            80, lambda w=event.width, h=event.height: self._resize_game_surface(w, h)
        )

    def _resize_game_surface(self, width, height):
        self.resize_job = None
        if not self.game_initialized or not pygame.get_init():
            return
        if getattr(self, "_gw", None) == width and getattr(self, "_gh", None) == height:
            return
        self.screen = pygame.display.set_mode((width, height))
        self._gw, self._gh = width, height
        self._recenter_map()

    def _recenter_map(self):
        if not hasattr(self, "_map_surf"):
            return
        map_w = self._map_surf.get_width()
        map_h = self._map_surf.get_height()
        self._offset_x = max(0, (self._gw - map_w) // 2)
        self._offset_y = max(0, (self._gh - map_h) // 2)

    # ─────────────────────────────────────────
    #  RIGHT PANEL (LOG)
    # ─────────────────────────────────────────
    def _build_right_panel(self):
        f = tk.Frame(self.root, bg=BG_PANEL,
                     highlightbackground="#E4E8F0", highlightthickness=1,
                     width=RIGHT_W)
        f.grid(row=0, column=2, sticky="nsew", padx=(6, 10), pady=(10, 6))
        f.pack_propagate(False)

        tk.Label(f, text="ALGORITHM COMPARISON", font=("Segoe UI", 10, "bold"),
                 bg=BG_PANEL, fg=TEXT_DARK).pack(anchor="w", padx=22, pady=(18, 5))

        self.profile_title_var = tk.StringVar(value="")
        self.profile_description_var = tk.StringVar(value="")
        self.profile_title = tk.Label(
            f, textvariable=self.profile_title_var, font=("Segoe UI", 12, "bold"),
            bg=BG_PANEL, fg=ACCENT, anchor="w")
        self.profile_title.pack(fill="x", padx=22)
        tk.Label(
            f, textvariable=self.profile_description_var, font=("Segoe UI", 8),
            bg=BG_PANEL, fg="#667085", justify="left", anchor="w",
            wraplength=RIGHT_W - 44).pack(fill="x", padx=22, pady=(2, 5))

        self.comparison_canvas = tk.Canvas(
            f, height=202, bg="#F8FAFF", highlightbackground=LINE,
            highlightthickness=1)
        self.comparison_canvas.pack(fill="x", padx=22, pady=(0, 8))
        self.comparison_canvas.bind("<Configure>", lambda _: self._draw_comparison_chart())

        tk.Label(f, text="PROCESS LOG", font=("Segoe UI", 10, "bold"),
                 bg=BG_PANEL, fg=TEXT_DARK).pack(anchor="w", padx=22, pady=(0, 6))
        tk.Frame(f, height=1, bg=LINE).pack(fill="x", padx=22)

        self.log_area = scrolledtext.ScrolledText(
            f, font=("Consolas", 10, "bold"), bg="#FBFAFF", fg="#243143",
            relief="flat", borderwidth=0, wrap="word",
            insertbackground="#243143")
        self.log_area.pack(fill="both", expand=True, padx=22, pady=(10, 12))

        controls = tk.Frame(f, bg=BG_PANEL)
        controls.pack(anchor="center", pady=(0, 16))

        action_box = tk.Frame(controls, bg=BG_PANEL)
        action_box.pack(side="left", anchor="center")
        RoundedButton(action_box, text="Restart", icon="⟲",
                      bg="#FFD64F", fg=BTN_TEXT, width=104, height=36,
                      command=self.reset_game
                      ).pack(pady=(0, 6))
        RoundedButton(action_box, text="Clear", icon="✕",
                      bg="#9D8BD7", fg=BTN_TEXT, width=104, height=36,
                      command=lambda: self.log_area.delete("1.0", tk.END)
                      ).pack()

        move_box = tk.Frame(controls, bg=BG_PANEL)
        move_box.pack(side="left", anchor="center", padx=(18, 0))
        for col in range(3):
            move_box.grid_columnconfigure(col, minsize=38)
        for row in range(2):
            move_box.grid_rowconfigure(row, minsize=38)
        move_buttons = [
            ("▲", 0, 1, -1, 0),
            ("◀", 1, 0, 0, -1),
            ("▼", 1, 1, 1, 0),
            ("▶", 1, 2, 0, 1),
        ]
        for label, row, col, dy, dx in move_buttons:
            RoundedButton(move_box, text=label, bg="#54AED3", fg=BTN_TEXT,
                          width=34, height=34, radius=7,
                          command=lambda y=dy, x=dx: self.manual_move(y, x)
                          ).grid(row=row, column=col, padx=2, pady=2, sticky="nsew")

        self._refresh_level_profile()

    def _refresh_level_profile(self):
        if not hasattr(self, "profile_title_var"):
            return
        level = self.combobox.get()
        profile = LEVEL_PROFILES.get(level)
        if profile is None:
            self.profile_title_var.set("Chế độ tự do")
            self.profile_description_var.set(
                "Chọn một thuật toán để chạy thử trên level này.")
            self.profile_title.configure(fg=ACCENT)
        else:
            self.profile_title_var.set(profile["title"])
            self.profile_description_var.set(profile["description"])
            self.profile_title.configure(fg=profile["accent"])
        self.root.after_idle(self._draw_comparison_chart)

    def _draw_comparison_chart(self):
        if not hasattr(self, "comparison_canvas"):
            return
        canvas = self.comparison_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), RIGHT_W - 44)
        level = self.combobox.get()
        profile = LEVEL_PROFILES.get(level)
        if profile is None:
            canvas.create_text(
                width // 2, 96, text="Chưa có nhóm thuật toán cho level này",
                font=("Segoe UI", 9), fill="#8A94A6")
            return

        algorithms = profile["algorithms"]
        results = self.comparison_results.get(level, {})
        successful = [item for item in results.values() if item.get("status") == "ok"]
        max_steps = max((item["steps"] for item in successful), default=1)
        max_ms = max((item["elapsed_ms"] for item in successful), default=1.0)
        row_height = min(29, 172 // max(1, len(algorithms)))
        top = 24
        label_x = 7
        bar_x = 75
        metric_x = width - 7
        bar_width = max(55, width - bar_x - 92)

        canvas.create_rectangle(8, 8, 20, 12, fill="#54AED3", outline="")
        canvas.create_text(25, 10, text="Bước", anchor="w",
                           font=("Segoe UI", 7, "bold"), fill="#64748B")
        canvas.create_rectangle(76, 8, 88, 12, fill="#9D8BD7", outline="")
        canvas.create_text(93, 10, text="Thời gian", anchor="w",
                           font=("Segoe UI", 7, "bold"), fill="#64748B")

        for index, key in enumerate(algorithms):
            y = top + index * row_height
            visual = ALGO_VISUALS[key]
            result = results.get(key)
            canvas.create_text(
                label_x, y + 7, text=visual["label"], anchor="w",
                font=("Segoe UI", 7, "bold"), fill="#475569")
            canvas.create_rectangle(
                bar_x, y + 1, bar_x + bar_width, y + 6,
                fill="#E7ECF5", outline="")
            canvas.create_rectangle(
                bar_x, y + 9, bar_x + bar_width, y + 14,
                fill="#E7ECF5", outline="")

            if result is None:
                metric = "Chưa chạy"
            elif result["status"] != "ok":
                failed_step = result.get("failed_step")
                metric = f"Fail@{failed_step}" if failed_step is not None else "Thất bại"
                canvas.create_text(
                    metric_x, y + 7, text=metric, anchor="e",
                    font=("Segoe UI", 7, "bold"), fill="#D04F70")
                continue
            else:
                step_width = max(3, int(bar_width * result["steps"] / max_steps))
                time_width = max(3, int(bar_width * result["elapsed_ms"] / max_ms))
                canvas.create_rectangle(
                    bar_x, y + 1, bar_x + step_width, y + 6,
                    fill="#54AED3", outline="")
                canvas.create_rectangle(
                    bar_x, y + 9, bar_x + time_width, y + 14,
                    fill="#9D8BD7", outline="")
                metric_label = result.get("metric_label")
                if metric_label:
                    metric = f'{metric_label} · {result["elapsed_ms"]:.1f}ms'
                else:
                    metric = f'{result["steps"]}b · {result["elapsed_ms"]:.1f}ms'

            canvas.create_text(
                metric_x, y + 7, text=metric, anchor="e",
                font=("Segoe UI", 7, "bold"), fill="#64748B")

    # ─────────────────────────────────────────
    #  BOTTOM BAR
    # ─────────────────────────────────────────
    def _build_bottom_panel(self):
        f = tk.Frame(self.root, bg=BG_PANEL,
                     highlightbackground=LINE, highlightthickness=1)
        f.grid(row=1, column=0, columnspan=3,
               sticky="nsew", padx=10, pady=(0, 10))
        f.grid_columnconfigure(1, weight=1)

        tk.Label(f, text="SOLUTION", font=("Segoe UI", 10, "bold"),
                 bg=BG_PANEL, fg=TEXT_DARK).grid(row=0, column=0, padx=(28, 16), pady=14)

        sol_entry = tk.Entry(
            f, textvariable=self.solution_var,
            font=FONT_MONO, bg="#F6F8FC", fg="#4B5563",
            relief="flat", highlightbackground="#CCD5E5",
            highlightthickness=1, state="readonly")
        sol_entry.grid(row=0, column=1, sticky="ew", padx=0, ipady=10)

    def _bind_keyboard_controls(self):
        key_moves = {
            "<Up>": (-1, 0),
            "<Down>": (1, 0),
            "<Left>": (0, -1),
            "<Right>": (0, 1),
        }
        for key, (dy, dx) in key_moves.items():
            self.root.bind_all(key, lambda event, y=dy, x=dx: self.manual_move(y, x))

    # ─────────────────────────────────────────
    #  GAME LOGIC
    # ─────────────────────────────────────────
    def load_map(self, level):
        filename = LEVEL_FILES.get(level)
        if filename is None:
            filename = f"{level.lower().replace(' ', '')}.txt"
        path = os.path.join(BASE_DIR, "levels", filename)
        with open(path, "r") as fh:
            return [[c for c in line.rstrip('\n')] for line in fh]

    def _map_for_algorithm(self, matrix, algo, level):
        result = copy.deepcopy(matrix)
        if algo not in ("NoObs", "PartialObs"):
            return result

        for row, col in LEVEL_OBSERVATION_UNKNOWN_CELLS.get(level, ()):
            if 0 <= row < len(result) and 0 <= col < len(result[row]):
                if result[row][col] == " ":
                    result[row][col] = "?"
        return result

    def _display_map_for_algorithm(self, matrix, _algo, _level):
        return copy.deepcopy(matrix)

    def init_game(self):
        self._cancel_solution_animation()
        self._set_pause_state(False)
        if self.loop_job is not None:
            self.root.after_cancel(self.loop_job)
            self.loop_job = None

        level = self.combobox.get()
        try:
            matrix = self._display_map_for_algorithm(
                self.load_map(level), self.selected_algo.get(), level)
        except FileNotFoundError:
            messagebox.showerror("Error", f"Không tìm thấy file map cho {level}")
            return

        if not self.game_initialized:
            self.root.update_idletasks()
            os.environ['SDL_WINDOWID'] = str(self.game_frame.winfo_id())
            pygame.init()

        self.gameSokoban = Game(matrix, [])
        self.dockList = self.gameSokoban.listDock()
        self.manual_steps = 0
        self.win_notified = False
        self._reset_observation_fog()

        self.root.update_idletasks()
        fw = self.game_frame.winfo_width()
        fh = self.game_frame.winfo_height()
        gw = fw if fw > 10 else GAME_W
        gh = fh if fh > 10 else GAME_H
        self.screen = pygame.display.set_mode((gw, gh))
        self._gw, self._gh = gw, gh

        assets.load_sprites()

        # Tính kích thước map thực (số cột × tile_w, số hàng × tile_h)
        # Lấy tile size từ assets (sprite đầu tiên), fallback 64
        try:
            tile_w = list(assets.sprites.values())[0].get_width()
            tile_h = list(assets.sprites.values())[0].get_height()
        except Exception:
            tile_w = tile_h = 64
        map_cols = max(len(row) for row in matrix)
        map_rows = len(matrix)
        map_pixel_w = map_cols * tile_w
        map_pixel_h = map_rows * tile_h

        # Surface tạm để render map đúng kích thước, rồi blit vào giữa screen
        self._map_surf = pygame.Surface((map_pixel_w, map_pixel_h))
        self._recenter_map()

        self.game_initialized = True
        self._log(f"{level} loaded. Map {map_cols}x{map_rows} tiles, offset ({self._offset_x},{self._offset_y})")
        self.solution_var.set("No solution yet...")
        self._refresh_level_profile()
        self.root.focus_set()
        self._game_loop()

    def _prepare_display_map(self, matrix):
        self.gameSokoban = Game(matrix, [])
        self.dockList = self.gameSokoban.listDock()
        self.manual_steps = 0
        self.win_notified = False
        self._reset_observation_fog()

        map_cols = max(len(row) for row in matrix)
        map_rows = len(matrix)
        self._map_surf = pygame.Surface((map_cols * 64, map_rows * 64))
        self._recenter_map()

        if not self.game_initialized:
            self.game_initialized = True
            self._game_loop()

    def _game_loop(self):
        if not self.game_initialized:
            return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

        # Observation modes render hidden information through the fog layer.
        if self.observation_fog_enabled:
            self.screen.fill("#080D18")
        else:
            self.gameSokoban.fill_screen_with_floor((self._gw, self._gh), self.screen)

        # Render map vào surface tạm đúng kích thước map
        map_w = self._map_surf.get_width()
        map_h = self._map_surf.get_height()
        self.gameSokoban.fill_screen_with_floor((map_w, map_h), self._map_surf)
        self.gameSokoban.print_game(self._map_surf)
        self._draw_observation_fog(self._map_surf)

        # Blit map_surf vào giữa screen theo offset đã tính
        self.screen.blit(self._map_surf, (self._offset_x, self._offset_y))

        pygame.display.flip()
        self.loop_job = self.root.after(100, self._game_loop)

    def _on_close(self):
        if self.loop_job is not None:
            self.root.after_cancel(self.loop_job)
        pygame.quit()
        self.root.destroy()

    def stop_game(self):
        if not self.current_solution or self.solution_index >= len(self.current_solution):
            self._log("Không có lời giải đang chạy để tạm dừng.")
            return

        if self.solution_paused:
            self._set_pause_state(False)
            self._log(
                f"Continued at step {self.solution_index}/{len(self.current_solution)}.")
            self.solution_job = self.root.after(
                ANIMATION_STEP_DELAY, self._play_next_solution_step)
        else:
            if self.solution_job is not None:
                self.root.after_cancel(self.solution_job)
                self.solution_job = None
            self._set_pause_state(True)
            self._log(
                f"Paused at step {self.solution_index}/{len(self.current_solution)}.")

    def _set_pause_state(self, paused):
        self.solution_paused = paused
        if not hasattr(self, "stop_button"):
            return
        if paused:
            self.stop_button.set_content(
                text="Continue", icon="▶", bg="#6FCFA9")
        else:
            self.stop_button.set_content(
                text="Stop", icon="■", bg="#E26087")

    def manual_move(self, y, x):
        self._cancel_solution_animation()
        if not self.game_initialized or not hasattr(self, "gameSokoban"):
            return "break"

        before = copy.deepcopy(self.gameSokoban.matrix)
        try:
            self.gameSokoban.move(y, x, self.dockList)
        except Exception as exc:
            self._log(f"Move error: {exc}")
            return "break"

        if self.gameSokoban.matrix != before:
            self.manual_steps += 1
            self._reveal_current_observation()
            self.solution_var.set(f"Manual steps: {self.manual_steps}")
            if self.gameSokoban.is_completed(self.dockList):
                self.observation_fog_enabled = False
                self._show_win_message(self.manual_steps, "manual")

        return "break"

    def reset_game(self):
        if self.game_initialized:
            self.init_game()
        self._log("Reset.")

    def run_solution(self):
        if self.is_solving:
            self._log("Một thuật toán đang chạy, hãy chờ hoàn tất.")
            return

        self._cancel_solution_animation()

        algo = self.selected_algo.get()
        if not algo:
            messagebox.showwarning("Chú ý", "Hãy chọn thuật toán trước!")
            return

        handler = ALGORITHM_HANDLERS.get(algo)
        if handler is None:
            messagebox.showerror("Error", f"Chưa khai báo hàm cho thuật toán {algo}")
            return

        level = self.combobox.get()
        try:
            base_matrix = self.load_map(level)
            solver_matrix = self._map_for_algorithm(base_matrix, algo, level)
            display_matrix = self._display_map_for_algorithm(
                base_matrix, algo, level)
        except FileNotFoundError:
            messagebox.showerror("Error", f"Không tìm thấy file map cho {level}")
            return

        self._log(f"Running {algo}...")
        self.solution_var.set(f"Running {algo}...")
        self.is_solving = True
        self.root.configure(cursor="watch")
        self.root.update_idletasks()

        started_at = time.perf_counter()
        try:
            result = handler(Solve(copy.deepcopy(solver_matrix)))
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            self._save_comparison_result(level, algo, "error", 0, elapsed_ms)
            self._log(f"{algo} error: {exc}")
            messagebox.showerror("Error", f"Lỗi khi chạy {algo}:\n{exc}")
            return
        finally:
            self.is_solving = False
            self.root.configure(cursor="")

        elapsed_ms = (time.perf_counter() - started_at) * 1000

        if isinstance(result, dict) and result.get("status") == "success":
            path = result.get("path", "")
            plan_text = result.get("plan_text", path)
            plan_kind = result.get("plan_kind", "path")
            real_steps = result.get("real_steps", len(path))
            display_steps = result.get("display_steps", real_steps)
            metric_label = result.get("metric_label", f"{real_steps}b")

            self._save_comparison_result(
                level,
                algo,
                "ok",
                display_steps,
                elapsed_ms,
                metric_label=metric_label,
                real_steps=real_steps,
            )
            self.solution_var.set(plan_text)
            self._log(
                f"{ALGO_VISUALS.get(algo, {}).get('label', algo)}: tìm được "
                f"{real_steps} bước replay ({plan_kind}); metric={metric_label}; "
                f"thời gian={elapsed_ms:.1f} ms."
            )
            self._log(self._search_formula_note(algo))
            note = result.get("note")
            if note:
                self._log(note)
            self._start_solution_animation(path, display_matrix)
            return

        if isinstance(result, dict) and result.get("status") == "failure":
            failed_path = result.get("path", "")
            path_steps = result.get(
                "path_steps",
                len(failed_path) if isinstance(failed_path, str) else 0
            )
            failed_step = result.get(
                "failed_step",
                result.get("fail_step", path_steps)
            )
            reason = result.get(
                "reason",
                "Thuật toán đã chạy hết nhưng không tìm thấy lời giải."
            )
            node_generated = result.get("node_generated", 0)
            hide_failed_path = result.get("hide_failed_path", False)
            suppress_failure_popup = result.get("suppress_failure_popup", False)

            self._handle_algorithm_failure(
                level=level,
                algo=algo,
                elapsed_ms=elapsed_ms,
                failed_step=failed_step,
                reason=reason,
                node_generated=node_generated,
                failed_path=failed_path,
                path_steps=path_steps,
                hide_failed_path=hide_failed_path,
                suppress_failure_popup=suppress_failure_popup,
            )
            return

        if not result or result == "NoSol":
            self._handle_algorithm_failure(
                level=level,
                algo=algo,
                elapsed_ms=elapsed_ms,
                failed_step=0,
                reason="Thuật toán đã chạy hết nhưng không tìm thấy lời giải.",
                node_generated=0,
                failed_path="",
            )
            return

        self._save_comparison_result(level, algo, "ok", len(result), elapsed_ms)
        self.solution_var.set(result)
        self._log(
            f"{ALGO_VISUALS.get(algo, {}).get('label', algo)}: tìm được "
            f"{len(result)} bước; thời gian={elapsed_ms:.1f} ms.")
        self._log(self._search_formula_note(algo))
        self._start_solution_animation(result, display_matrix)

    def _search_formula_note(self, algo):
        base = (
            "Cách đọc log bước chạy: g(n)=số bước đã đi, "
            "h(n)=box_toDock + worker_toBox, f(n)=g(n)+h(n)."
        )
        if algo == "Astar":
            return base + " A* ưu tiên node có f(n) nhỏ nhất trong frontier."
        if algo == "SMAstar":
            return base + " IDA* dùng f(n) để quyết định đi tiếp hay cắt nhánh theo bound."
        if algo == "Greedy":
            return base + " Greedy ưu tiên h(n) nhỏ, không cộng thêm g(n)."
        if algo in {"BFS", "DFS1", "IDS"}:
            return base + " Nhóm không thông tin dùng g(n)/thứ tự duyệt, h(n) chỉ để bạn quan sát trạng thái còn xa goal bao nhiêu."
        if algo in {"HillClimb", "BeamSearch", "SimAnneal"}:
            return base + " Nhóm cục bộ dùng h(n) làm độ tốt của trạng thái lân cận."
        if algo in {"NoObs", "PartialObs"}:
            return base + " Môi trường quan sát hạn chế chọn action theo belief-state/percept, log vẫn chấm nhánh replay bằng f(n)."
        if algo in {"UCS", "BFS2", "DFS2"}:
            return base + " Tìm kiếm đối kháng còn cộng rủi ro từ MIN/E, nhất là thế gọng kìm và chặn ô đẩy."
        return base

    def _handle_algorithm_failure(
            self, level, algo, elapsed_ms, failed_step, reason,
            node_generated=0, failed_path="", path_steps=None,
            hide_failed_path=False, suppress_failure_popup=False):
        """
        Xử lý kết quả thất bại của thuật toán:
        - Lưu vào biểu đồ so sánh.
        - Ghi log chi tiết.
        - Cập nhật ô SOLUTION.
        - Hiện popup thất bại đẹp giống popup Victory.
        """
        label = ALGO_VISUALS.get(algo, {}).get("label", algo)
        failed_step = failed_step if failed_step is not None else 0
        reason = reason or "Thuật toán đã chạy hết nhưng không tìm thấy lời giải."
        if path_steps is None:
            path_steps = len(failed_path) if isinstance(failed_path, str) else 0

        self._save_comparison_result(
            level, algo, "nosol", 0, elapsed_ms,
            failed_step=failed_step, reason=reason)

        message = f"Thất bại ở bước {failed_step}: {reason}"
        if hide_failed_path:
            self.solution_var.set(f"Kẹt ở bước {failed_step}")
        elif failed_path:
            self.solution_var.set(f"{failed_path}  (kẹt tại bước {path_steps})")
        else:
            self.solution_var.set(message)
        self._log(
            f"{algo}: {message} ({elapsed_ms:.1f} ms, {node_generated} nodes).")
        if failed_path and not hide_failed_path:
            self._log(
                f"SOLUTION trước khi kẹt: {failed_path} ({path_steps} bước)")
        elif failed_path:
            self._log(f"Kẹt ở bước {failed_step}; ẩn path vì quá dài.")

        if suppress_failure_popup:
            self._log("Kết luận được ghi trong SOLUTION; không mở popup vì đây là kết quả dự kiến của bài toán.")
            return

        self._show_failure_dialog(
            algorithm_label=label,
            fail_step=failed_step,
            reason=reason,
            node_generated=node_generated,
            elapsed_ms=elapsed_ms,
            failed_path=failed_path,
        )

    def _show_failure_dialog(
            self, algorithm_label, fail_step, reason,
            node_generated=0, elapsed_ms=0.0, failed_path=""):
        """
        Popup thất bại có giao diện đồng bộ với popup Victory.
        Không dùng messagebox thô nữa.
        """
        if hasattr(self, "failure_popup"):
            try:
                if self.failure_popup is not None and self.failure_popup.winfo_exists():
                    self.failure_popup.lift()
                    return
            except Exception:
                pass

        popup = tk.Toplevel(self.root)
        self.failure_popup = popup
        popup.title("Thất bại")
        popup.configure(bg="#1E2142")
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()

        w, h = 470, 350
        popup.update_idletasks()
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_w = max(self.root.winfo_width(), w)
        root_h = max(self.root.winfo_height(), h)
        x = root_x + (root_w - w) // 2
        y = root_y + (root_h - h) // 2
        popup.geometry(f"{w}x{h}+{x}+{y}")

        canvas = tk.Canvas(popup, width=w, height=h, bg="#1E2142", highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        # Khung chính giống popup Victory
        self._canvas_round_rect(canvas, 18, 18, w - 18, h - 18, 20,
                                fill="#FFFFFF", outline="#E26087", width=3)
        self._canvas_round_rect(canvas, 34, 34, w - 34, h - 34, 16,
                                fill="#F8FBFF", outline="#DDE3F0", width=1)

        # Chấm trang trí
        confetti = [
            (56, 60, "#FFD64F"), (92, 42, "#6FCFA9"), (378, 48, "#F07351"),
            (412, 76, "#58B7DC"), (64, 254, "#B563D9"), (402, 252, "#FFD64F"),
            (112, 292, "#F07351"), (354, 292, "#6FCFA9"),
        ]
        for cx, cy, color in confetti:
            canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                               fill=color, outline="")

        # Icon cảnh báo
        canvas.create_oval(w // 2 - 34, 54, w // 2 + 34, 122,
                           fill="#FFF1F2", outline="#E26087", width=3)
        canvas.create_text(w // 2, 88, text="!", font=("Segoe UI", 34, "bold"),
                           fill="#E26087")

        canvas.create_text(w // 2, 145, text="THẤT BẠI!",
                           font=("Segoe UI", 24, "bold"), fill="#E26087")
        canvas.create_text(w // 2, 178, text="Thuật toán chưa tìm được lời giải",
                           font=("Segoe UI", 12, "bold"), fill=TEXT_DARK)

        canvas.create_text(
            w // 2, 207,
            text=f"{algorithm_label} đã dừng ở bước {fail_step}.",
            font=("Segoe UI", 10, "bold"), fill="#56617D", width=370)

        reason_text = reason or "Không tìm thấy lời giải."
        canvas.create_text(
            w // 2, 238,
            text=f"Lý do: {reason_text}",
            font=("Segoe UI", 9), fill="#56617D", width=380)

        detail_parts = []
        if node_generated:
            detail_parts.append(f"{node_generated} node")
        detail_parts.append(f"{elapsed_ms:.1f} ms")
        detail = " • ".join(detail_parts)

        canvas.create_text(
            w // 2, 270,
            text=f"{algorithm_label} • Fail@{fail_step} • {detail}",
            font=("Segoe UI", 10, "bold"), fill="#B42318", width=390)

        buttons = tk.Frame(canvas, bg="#F8FBFF")
        RoundedButton(buttons, text="Chơi lại", icon="⟲", bg="#FFD64F",
                      fg=BTN_TEXT, width=126, height=38,
                      command=lambda: self._restart_from_failure(popup)
                      ).pack(side="left", padx=6)
        RoundedButton(buttons, text="Đóng", icon="✓", bg="#6FCFA9",
                      fg=BTN_TEXT, width=126, height=38,
                      command=popup.destroy
                      ).pack(side="left", padx=6)
        canvas.create_window(w // 2, 312, window=buttons)

    def _restart_from_failure(self, popup):
        if popup.winfo_exists():
            popup.destroy()
        self.reset_game()

    def _save_comparison_result(
            self, level, algo, status, steps, elapsed_ms,
            failed_step=None, reason=None,
            metric_label=None, real_steps=None):
        item = {
            "status": status,
            "steps": steps,
            "elapsed_ms": elapsed_ms,
        }
        if metric_label is not None:
            item["metric_label"] = metric_label
        if real_steps is not None:
            item["real_steps"] = real_steps
        if failed_step is not None:
            item["failed_step"] = failed_step
        if reason:
            item["reason"] = reason
        self.comparison_results.setdefault(level, {})[algo] = item
        self._draw_comparison_chart()

    def _log(self, msg):
        self.log_area.insert(tk.END, "☑ " + msg + "\n")
        self.log_area.see(tk.END)

    def _show_win_message(self, steps, mode):
        if self.win_notified:
            return
        self.win_notified = True
        if mode == "manual":
            msg = f"Chúc mừng! Bạn đã hoàn thành màn chơi trong {steps} bước."
            self._log(f"Completed manually in {steps} steps.")
            self.solution_var.set(f"Manual steps: {steps}")
        else:
            msg = f"Chúc mừng! Thuật toán đã giải xong màn chơi trong {steps} bước."
            self._log(f"Completed by algorithm in {steps} steps.")
            self.solution_var.set(
                f"{self.current_solution}  ({steps}/{steps})"
            )
        self._show_victory_dialog(msg, steps, mode)

    def _show_victory_dialog(self, message, steps, mode):
        if self.victory_popup is not None and self.victory_popup.winfo_exists():
            self.victory_popup.lift()
            return

        popup = tk.Toplevel(self.root)
        self.victory_popup = popup
        popup.title("Chiến thắng")
        popup.configure(bg="#1E2142")
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()

        w, h = 440, 320
        popup.update_idletasks()
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_w = max(self.root.winfo_width(), w)
        root_h = max(self.root.winfo_height(), h)
        x = root_x + (root_w - w) // 2
        y = root_y + (root_h - h) // 2
        popup.geometry(f"{w}x{h}+{x}+{y}")

        canvas = tk.Canvas(popup, width=w, height=h, bg="#1E2142", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        self._canvas_round_rect(canvas, 18, 18, w - 18, h - 18, 20,
                                fill="#FFFFFF", outline="#6B6BE8", width=3)
        self._canvas_round_rect(canvas, 34, 34, w - 34, h - 34, 16,
                                fill="#F8FBFF", outline="#DDE3F0", width=1)

        confetti = [
            (56, 60, "#FFD64F"), (92, 42, "#6FCFA9"), (350, 48, "#F07351"),
            (388, 76, "#58B7DC"), (64, 238, "#B563D9"), (372, 236, "#FFD64F"),
            (104, 272, "#F07351"), (330, 270, "#6FCFA9"),
        ]
        for cx, cy, color in confetti:
            canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                               fill=color, outline="")

        canvas.create_text(w // 2, 76, text="🏆", font=("Segoe UI Emoji", 40))
        canvas.create_text(w // 2, 122, text="VICTORY!",
                           font=("Segoe UI", 24, "bold"), fill="#5B5BD6")
        canvas.create_text(w // 2, 156, text="Chúc mừng hoàn thành màn chơi",
                           font=("Segoe UI", 12, "bold"), fill=TEXT_DARK)
        canvas.create_text(w // 2, 186, text=message,
                           font=("Segoe UI", 10), fill="#56617D", width=330)

        badge_text = "Bạn tự giải" if mode == "manual" else "Thuật toán giải"
        canvas.create_text(w // 2, 218, text=f"{badge_text} • {steps} bước",
                           font=("Segoe UI", 11, "bold"), fill="#2F6F58")

        buttons = tk.Frame(canvas, bg="#F8FBFF")
        RoundedButton(buttons, text="Chơi lại", icon="⟲", bg="#FFD64F",
                      fg=BTN_TEXT, width=126, height=38,
                      command=lambda: self._restart_from_victory(popup)
                      ).pack(side="left", padx=6)
        RoundedButton(buttons, text="Đóng", icon="✓", bg="#6FCFA9",
                      fg=BTN_TEXT, width=126, height=38,
                      command=popup.destroy
                      ).pack(side="left", padx=6)
        canvas.create_window(w // 2, 270, window=buttons)

    def _restart_from_victory(self, popup):
        if popup.winfo_exists():
            popup.destroy()
        self.reset_game()

    def _canvas_round_rect(self, canvas, x1, y1, x2, y2, radius,
                           fill, outline, width=1):
        radius = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1,
            x2, y1 + radius, x2, y2 - radius, x2, y2,
            x2 - radius, y2, x1 + radius, y2, x1, y2,
            x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        canvas.create_polygon(points, smooth=True, fill=fill,
                              outline=outline, width=width)

    def _start_solution_animation(self, solution, matrix):
        self._cancel_solution_animation()
        self._set_pause_state(False)
        self._prepare_display_map(copy.deepcopy(matrix))
        self.current_solution = solution
        self.solution_index = 0
        self._prepare_competitor_animation(matrix, solution)
        self._log(f"Animating {len(solution)} steps...")
        self.solution_job = self.root.after(ANIMATION_START_DELAY, self._play_next_solution_step)

    def _play_next_solution_step(self):
        if self.solution_paused:
            self.solution_job = None
            return

        if self.solution_index >= len(self.current_solution):
            self.solution_job = None
            self._set_pause_state(False)
            self.observation_fog_enabled = False
            self._log("Animation finished.")
            if self.gameSokoban.is_completed(self.dockList):
                self._show_win_message(len(self.current_solution), "algorithm")
            return

        step = self.current_solution[self.solution_index]
        moves = {
            "U": (-1, 0),
            "D": (1, 0),
            "L": (0, -1),
            "R": (0, 1),
        }
        if step in moves:
            y, x = moves[step]
            decision_context = self._movement_decision_context(
                step, copy.deepcopy(self.gameSokoban.matrix))
            try:
                moved = self.gameSokoban.move(y, x, self.dockList)
            except Exception as exc:
                self.solution_job = None
                self._set_pause_state(True)
                self._log(
                    f"Replay stopped at step {self.solution_index + 1}: {exc}")
                return
            if not moved:
                self.solution_job = None
                self._set_pause_state(True)
                self._log(
                    f"Replay stopped at step {self.solution_index + 1}: "
                    f"action {step} không hợp lệ.")
                return
            self._reveal_current_observation()

        self.solution_index += 1
        if step in moves:
            self._log_movement_decision(step, decision_context)
        self._move_competitor()
        self.solution_var.set(
            f"{self.current_solution}  ({self.solution_index}/{len(self.current_solution)})"
        )
        self.solution_job = self.root.after(ANIMATION_STEP_DELAY, self._play_next_solution_step)

    def _movement_decision_context(self, step, matrix):
        state = self._solve_state_from_matrix(matrix)
        g_next = self.solution_index + 1
        h_before = self._state_h(state)
        candidates = []

        try:
            actions = validMove(state)
        except Exception:
            actions = []

        for action in actions:
            child = copy.deepcopy(state)
            try:
                if not apply_step(child, action):
                    continue
            except Exception:
                continue

            h_value = self._state_h(child)
            candidates.append({
                "action": action,
                "g": g_next,
                "h": h_value,
                "f": g_next + h_value,
                "box_h": self._state_box_h(child),
                "worker_h": self._state_worker_h(child),
            })

        chosen = next(
            (item for item in candidates if item["action"] == step), None)
        return {
            "g_before": self.solution_index,
            "h_before": h_before,
            "chosen": chosen,
            "candidates": candidates,
        }

    def _log_movement_decision(self, step, context):
        chosen = context.get("chosen") if context else None
        candidates = context.get("candidates", []) if context else []
        step_no = self.solution_index
        label = ALGO_VISUALS.get(
            self.selected_algo.get(), {"label": self.selected_algo.get()})["label"]

        if chosen is None:
            self._log(
                f"Bước {step_no}: đi {self._step_name(step)}; không tính được "
                "f/g/h cho action này từ validMove, replay vẫn hợp lệ trên map.")
            return

        rank_f = self._candidate_rank(candidates, step, key="f")
        rank_h = self._candidate_rank(candidates, step, key="h")
        best_f = self._best_candidate(candidates, key="f")
        delta_h = context.get("h_before", 0) - chosen["h"]

        detail = (
            f"Bước {step_no}: {label} chọn {self._step_name(step)} | "
            f"g={self._fmt_cost(chosen['g'])}, "
            f"h={self._fmt_cost(chosen['h'])} "
            f"(box={self._fmt_cost(chosen['box_h'])}, "
            f"worker={self._fmt_cost(chosen['worker_h'])}), "
            f"f={self._fmt_cost(chosen['f'])}."
        )
        reason = self._movement_reason(
            self.selected_algo.get(), step, chosen, best_f, rank_f, rank_h, delta_h)
        self._log(f"{detail} {reason}")

    def _movement_reason(self, algo, step, chosen, best_f, rank_f, rank_h, delta_h):
        delta_text = self._fmt_delta(delta_h)
        if algo == "Astar":
            return (
                f"Lý do: A* so sánh f=g+h; action này xếp #{rank_f} theo f "
                f"trong các nước hợp lệ, h {delta_text}."
            )
        if algo == "SMAstar":
            return (
                f"Lý do: IDA* giữ nhánh khi f không vượt bound hiện tại; "
                f"action này có f={self._fmt_cost(chosen['f'])}, h {delta_text}."
            )
        if algo == "Greedy":
            return (
                f"Lý do: Greedy nhìn h(n); action này xếp #{rank_h} theo h "
                f"và h {delta_text}."
            )
        if algo == "BFS":
            return (
                f"Lý do: BFS lấy node nông nhất trong queue FIFO; g={chosen['g']} "
                f"là độ sâu replay, h {delta_text} chỉ để tham khảo."
            )
        if algo == "DFS1":
            return (
                f"Lý do: DFS đi sâu theo thứ tự sinh trạng thái; bước này tăng "
                f"độ sâu lên g={chosen['g']}, h {delta_text}."
            )
        if algo == "IDS":
            return (
                f"Lý do: IDS chạy DFS theo từng giới hạn độ sâu; bước này nằm "
                f"trong bound hiện tại với g={chosen['g']}, h {delta_text}."
            )
        if algo in {"HillClimb", "BeamSearch", "SimAnneal"}:
            return (
                f"Lý do: tìm kiếm cục bộ ưu tiên trạng thái lân cận có h tốt; "
                f"action này xếp #{rank_h} theo h, h {delta_text}."
            )
        if algo == "NoObs":
            return (
                f"Lý do: No Observation dùng một plan an toàn cho belief-state; "
                f"trên nhánh replay action này có f={self._fmt_cost(chosen['f'])}, h {delta_text}."
            )
        if algo == "PartialObs":
            return (
                f"Lý do: Partial Observation cập nhật percept rồi replan; "
                f"action này giữ nhánh hiện tại với f={self._fmt_cost(chosen['f'])}, h {delta_text}."
            )
        if algo in {"UCS", "BFS2", "DFS2"}:
            return (
                f"Lý do: thuật toán đối kháng chọn đường vừa giảm h vừa tránh MIN/E; "
                f"f replay={self._fmt_cost(chosen['f'])}, đồng thời MIN sẽ tìm thế chặn/gọng kìm."
            )
        if best_f and best_f["action"] == step:
            return f"Lý do: đây là action có f thấp nhất trong các nước hợp lệ; h {delta_text}."
        return (
            f"Lý do: action này thuộc path đã tìm; local-best theo f hiện là "
            f"{self._step_name(best_f['action']) if best_f else 'không có'}, h {delta_text}."
        )

    def _solve_state_from_matrix(self, matrix):
        state = Solve(copy.deepcopy(matrix))
        if hasattr(self, "dockList"):
            state.dockListPosition = list(self.dockList)
        return state

    def _state_h(self, state):
        return self._safe_cost(lambda: heuristic(state))

    def _state_box_h(self, state):
        return self._safe_cost(lambda: box_toDock(state))

    def _state_worker_h(self, state):
        return self._safe_cost(lambda: worker_toBox(state))

    @staticmethod
    def _safe_cost(callback):
        try:
            value = callback()
        except Exception:
            return float("inf")
        return value

    @staticmethod
    def _candidate_rank(candidates, action, key):
        ordered = sorted(candidates, key=lambda item: (item[key], item["action"]))
        for index, item in enumerate(ordered, start=1):
            if item["action"] == action:
                return index
        return len(ordered) + 1

    @staticmethod
    def _best_candidate(candidates, key):
        if not candidates:
            return None
        return min(candidates, key=lambda item: (item[key], item["action"]))

    @staticmethod
    def _fmt_cost(value):
        if value == float("inf"):
            return "inf"
        if isinstance(value, float) and not value.is_integer():
            return f"{value:.1f}"
        return str(int(value))

    @staticmethod
    def _fmt_delta(delta):
        if delta == float("inf") or delta == float("-inf"):
            return "không xác định"
        if delta > 0:
            return f"giảm {SokobanApp._fmt_cost(delta)}"
        if delta < 0:
            return f"tăng {SokobanApp._fmt_cost(abs(delta))}"
        return "không đổi"

    @staticmethod
    def _step_name(step):
        names = {
            "U": "Lên",
            "D": "Xuống",
            "L": "Trái",
            "R": "Phải",
        }
        return f"{names.get(step, step)} ({step})"

    def _reset_observation_fog(self):
        algo = self.selected_algo.get()
        self.observation_fog_enabled = algo in ("NoObs", "PartialObs")
        self.observation_revealed = set()
        self._partialobs_permanent = set()
        if algo == "NoObs":
            self._reveal_current_observation()
            self._log("No Observation: che map bằng blind_box, chỉ lộ vùng quanh worker.")
        elif algo == "PartialObs":
            self._init_partialobs()
            self._reveal_current_observation()
            self._log("Partial Observation: một phần map sáng sẵn, agent quan sát cục bộ quanh worker.")

    def _init_partialobs(self):
        matrix = self.gameSokoban.matrix
        all_open = []
        for r, row_cells in enumerate(matrix):
            for c, ch in enumerate(row_cells):
                if ch in (" ", ".", "@", "$", "*"):
                    all_open.append((r, c))
        half = max(1, len(all_open) // 2)
        self._partialobs_permanent = set(all_open[:half])

    def _observation_cells_around(self, worker, radius=1):
        matrix = self.gameSokoban.matrix
        wr, wc = worker
        observed = set()
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                row, col = wr + dr, wc + dc
                if 0 <= row < len(matrix) and 0 <= col < len(matrix[row]):
                    observed.add((row, col))
        return observed

    def _reveal_unknown_floor_cells(self, cells):
        matrix = self.gameSokoban.matrix
        for row, col in cells:
            if 0 <= row < len(matrix) and 0 <= col < len(matrix[row]):
                if matrix[row][col] == "?":
                    matrix[row][col] = " "

    def _all_map_cells(self):
        matrix = self.gameSokoban.matrix
        return {
            (row, col)
            for row, cells in enumerate(matrix)
            for col, _value in enumerate(cells)
        }

    def _reveal_current_observation(self):
        if not self.observation_fog_enabled or not hasattr(self, "gameSokoban"):
            return
        worker = self.gameSokoban.getPosition()
        if worker is None:
            return

        algo = self.selected_algo.get()
        if algo == "NoObs":
            self.observation_revealed = self._observation_cells_around(
                worker, radius=1)
        elif algo == "PartialObs":
            local_view = self._observation_cells_around(worker, radius=1)
            self._reveal_unknown_floor_cells(local_view)
            self.observation_revealed = (
                self._partialobs_permanent | set(self.dockList) | local_view)

    def _draw_observation_fog(self, surface):
        if not self.observation_fog_enabled:
            return

        algo = self.selected_algo.get()
        fog = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        fog.fill((3, 7, 15, 242))
        for row, col in self.observation_revealed:
            tile_rect = pygame.Rect(col * 64, row * 64, 64, 64)
            fog.fill((0, 0, 0, 0), tile_rect)
            if algo == "PartialObs":
                pygame.draw.rect(
                    fog, (88, 183, 220, 65), tile_rect, width=2)
        surface.blit(fog, (0, 0))

        blind_tile = assets.sprites.get("blind_box")
        if blind_tile is None:
            return

        if algo == "NoObs":
            for row, cells in enumerate(self.gameSokoban.matrix):
                for col, _value in enumerate(cells):
                    if (row, col) in self.observation_revealed:
                        continue
                    surface.blit(blind_tile, (col * 64, row * 64))
            worker_position = self.gameSokoban.getPosition()
            worker_tile = assets.sprites.get("worker")
            if worker_position is not None and worker_tile is not None:
                row, col = worker_position
                surface.blit(worker_tile, (col * 64, row * 64))
        elif algo == "PartialObs":
            for row, cells in enumerate(self.gameSokoban.matrix):
                for col, value in enumerate(cells):
                    if (row, col) in self.observation_revealed:
                        continue
                    if value in (" ", "?", "#"):
                        surface.blit(blind_tile, (col * 64, row * 64))

    def _prepare_competitor_animation(self, matrix, solution):
        self.competitor_position = None
        self.competitor_previous_position = None
        self.competitor_under_tile = " "
        self.competitor_turn_requirements = []

        if self.selected_algo.get() not in {"UCS", "BFS2", "DFS2"}:
            return

        for row, cells in enumerate(matrix):
            for col, value in enumerate(cells):
                if value == "E":
                    self.competitor_position = (row, col)
                    break
            if self.competitor_position is not None:
                break

        if self.competitor_position is None:
            return

        # Dự báo ngắn các ô MAX bắt buộc phải dùng. MIN vẫn được phép cắt
        # đường xa, nhưng không được tự chui vào ngõ cụt khóa cứng lượt kế tiếp.
        preview = Solve(copy.deepcopy(matrix))
        moves = {
            "U": (-1, 0),
            "D": (1, 0),
            "L": (0, -1),
            "R": (0, 1),
        }
        for step in solution:
            required = set()
            worker = preview.workerPosition()
            dy, dx = moves.get(step, (0, 0))
            next_worker = worker[0] + dy, worker[1] + dx
            required.add(next_worker)
            if preview.getMatrixElement(*next_worker) in {"$", "*"}:
                required.add((next_worker[0] + dy, next_worker[1] + dx))
            self.competitor_turn_requirements.append(required)
            preview.move(dy, dx)

        strategy_names = {
            "UCS": "Minimax: MIN chặn vị trí đẩy, đích và hành lang hẹp",
            "BFS2": "Alpha-Beta: MIN dự đoán rồi cắt nhánh phòng thủ yếu",
            "DFS2": "Expectimax: MIN chọn nước cản trở theo xác suất",
        }
        self._log(strategy_names[self.selected_algo.get()])

    def _move_competitor(self):
        if self.competitor_position is None:
            return

        matrix = self.gameSokoban.matrix
        row, col = self.competitor_position
        worker = self.gameSokoban.getPosition()
        if worker is None:
            return

        protected_cells = self._next_player_protected_cells()
        if self.competitor_position in protected_cells:
            # Nếu một ô sắp trở thành bắt buộc cho MAX, MIN phải rời ô đó
            # trước khi lượt tương ứng diễn ra để tránh khóa chết animation.
            escape_targets = self._all_open_cells() - protected_cells
            path = self._competitor_bfs_path(
                self.competitor_position, escape_targets, protected_cells)
            behavior = "guard"
        else:
            target, behavior = self._choose_competitor_target(
                worker, protected_cells)
            if target is None:
                return
            path = self._competitor_bfs_path(
                self.competitor_position, {target}, protected_cells)
        if len(path) < 2:
            return
        next_position = path[1]

        matrix[row][col] = self.competitor_under_tile
        self.competitor_under_tile = matrix[next_position[0]][next_position[1]]
        matrix[next_position[0]][next_position[1]] = "E"
        self.competitor_previous_position = self.competitor_position
        self.competitor_position = next_position

        if self.solution_index % 6 == 1:
            behavior_labels = {
                "pincer": "MIN đang khép gọng kìm quanh người chơi",
                "chase": "MIN đang đuổi người chơi",
                "block": "MIN đang chặn vị trí đứng đẩy thùng",
                "guard": "MIN đang canh đích hoặc hành lang quan trọng",
            }
            self._log(behavior_labels[behavior])

    def _choose_competitor_target(self, worker, protected_cells):
        matrix = self.gameSokoban.matrix

        # 1) Gọng kìm: ép MAX vào phía tường, thùng hoặc hành lang hẹp.
        target = self._select_pincer_target(worker, protected_cells)
        if target is not None:
            return target, "pincer"

        # 2) Nếu có thể áp sát MAX trong vài bước, ưu tiên truy đuổi.
        chase_targets = {
            (worker[0] + dy, worker[1] + dx)
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
            if self._competitor_cell_is_open(
                (worker[0] + dy, worker[1] + dx), protected_cells)
        }
        chase_path = self._competitor_bfs_path(
            self.competitor_position, chase_targets, protected_cells)
        if chase_path and len(chase_path) - 1 <= 4:
            return chase_path[-1], "chase"

        boxes = [
            (row, col)
            for row, cells in enumerate(matrix)
            for col, value in enumerate(cells)
            if value in {"$", "*"}
        ]

        # 3) Chặn ô đứng đẩy thùng — hành vi phù hợp nhất với Sokoban.
        push_stances = {
            position for position in self._important_push_stances(
                boxes, self.dockList)
            if self._competitor_cell_is_open(position, protected_cells)
        }
        target = self._select_reachable_tactical_target(
            push_stances, protected_cells)
        if target is not None:
            return target, "block"

        # 4) Canh đích, đường từ thùng tới đích hoặc nút cổ chai.
        guard_targets = {
            dock for dock in self.dockList
            if self._competitor_cell_is_open(dock, protected_cells)
        }
        for box in boxes:
            for dock in self.dockList:
                guard_targets.update(
                    self._corridor_cells_between(box, dock, protected_cells))
        guard_targets.update(
            position
            for position in self._all_open_cells()
            if self._walkable_neighbor_count(position) <= 2
            and position not in protected_cells
        )
        target = self._select_reachable_tactical_target(
            guard_targets, protected_cells)
        if target is not None:
            return target, "guard"
        return None, "guard"

    def _select_pincer_target(self, worker, protected_cells):
        candidates = {
            (worker[0] + dy, worker[1] + dx)
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
            if self._competitor_cell_is_open(
                (worker[0] + dy, worker[1] + dx), protected_cells)
        }

        choices = []
        for target in candidates:
            path = self._competitor_bfs_path(
                self.competitor_position, {target}, protected_cells)
            if not path:
                continue
            score = self._pincer_pressure_score(target, worker)
            score -= 0.8 * (len(path) - 1)
            choices.append((score, -len(path), target))

        if not choices:
            return None

        choices.sort(reverse=True)
        algo = self.selected_algo.get()
        if algo == "DFS2" and len(choices) > 1:
            top = choices[:min(2, len(choices))]
            return top[self.solution_index % len(top)][2]
        return choices[0][2]

    def _pincer_pressure_score(self, target, worker):
        matrix = self.gameSokoban.matrix
        direction = (target[0] - worker[0], target[1] - worker[1])
        opposite = (worker[0] - direction[0], worker[1] - direction[1])
        opposite_value = self._matrix_value(matrix, opposite)

        score = 42.0
        if opposite_value in {None, "#", "$", "*", "E"}:
            score += 34
        elif self._walkable_neighbor_count(opposite) <= 2:
            score += 14

        escape_cells = self._worker_escape_cells(worker, blocked_by=target)
        score += max(0, 4 - len(escape_cells)) * 13

        boxes = [
            (row, col)
            for row, cells in enumerate(matrix)
            for col, value in enumerate(cells)
            if value in {"$", "*"}
        ]
        if target in self._important_push_stances(boxes, self.dockList):
            score += 18

        if target == self.competitor_previous_position:
            score -= 10
        return score

    def _worker_escape_cells(self, worker, blocked_by=None):
        escape_cells = set()
        matrix = self.gameSokoban.matrix
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            position = (worker[0] + dy, worker[1] + dx)
            if position == blocked_by:
                continue
            value = self._matrix_value(matrix, position)
            if value in {" ", "."}:
                escape_cells.add(position)
        return escape_cells

    def _select_reachable_tactical_target(self, targets, protected_cells):
        choices = []
        for target in targets:
            path = self._competitor_bfs_path(
                self.competitor_position, {target}, protected_cells)
            if not path:
                continue
            score = self._competitor_tactical_score(target)
            choices.append((score, -len(path), target))
        if not choices:
            return None

        choices.sort(reverse=True)
        algo = self.selected_algo.get()
        if algo == "DFS2" and len(choices) > 1:
            # Expectimax: biến thiên giữa các mục tiêu tốt theo xác suất mô phỏng.
            top = choices[:min(3, len(choices))]
            return top[self.solution_index % len(top)][2]
        # Minimax chọn bất lợi lớn nhất; Alpha-Beta cho cùng kết quả nhưng
        # chỉ giữ các nhánh mục tiêu có điểm cao nhất.
        return choices[0][2]

    def _competitor_bfs_path(self, start, targets, protected_cells):
        if not targets:
            return []
        if start in targets:
            return [start]

        queue = deque([start])
        parents = {start: None}
        while queue:
            current = queue.popleft()
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                neighbor = current[0] + dy, current[1] + dx
                if neighbor in parents:
                    continue
                if not self._competitor_cell_is_open(
                        neighbor, protected_cells, allow_current=True):
                    continue
                parents[neighbor] = current
                if neighbor in targets:
                    path = [neighbor]
                    while parents[path[-1]] is not None:
                        path.append(parents[path[-1]])
                    path.reverse()
                    return path
                queue.append(neighbor)
        return []

    def _competitor_cell_is_open(
            self, position, protected_cells, allow_current=False):
        if position in protected_cells:
            return False
        if allow_current and position == self.competitor_position:
            return True
        return self._matrix_value(
            self.gameSokoban.matrix, position) in {" ", "."}

    def _corridor_cells_between(self, start, end, protected_cells):
        path = self._competitor_bfs_path(start, {end}, protected_cells)
        return {
            position for position in path[1:-1]
            if self._walkable_neighbor_count(position) <= 2
        }

    def _all_open_cells(self):
        matrix = self.gameSokoban.matrix
        return {
            (row, col)
            for row, cells in enumerate(matrix)
            for col, value in enumerate(cells)
            if value in {" ", "."}
        }

    def _next_player_protected_cells(self):
        protected = set()
        lookahead_end = min(
            len(self.competitor_turn_requirements),
            self.solution_index + 8)
        for turn in range(self.solution_index, lookahead_end):
            protected.update(self.competitor_turn_requirements[turn])

        worker = self.gameSokoban.getPosition()
        if worker is None or self.solution_index >= len(self.current_solution):
            return protected

        moves = {
            "U": (-1, 0),
            "D": (1, 0),
            "L": (0, -1),
            "R": (0, 1),
        }
        dy, dx = moves.get(self.current_solution[self.solution_index], (0, 0))
        next_worker = worker[0] + dy, worker[1] + dx
        protected.add(next_worker)

        matrix = self.gameSokoban.matrix
        if self._matrix_value(matrix, next_worker) in {"$", "*"}:
            protected.add((next_worker[0] + dy, next_worker[1] + dx))
        return protected

    def _competitor_tactical_score(self, position):
        matrix = self.gameSokoban.matrix
        worker = self.gameSokoban.getPosition()
        boxes = [
            (row, col)
            for row, cells in enumerate(matrix)
            for col, value in enumerate(cells)
            if value in {"$", "*"}
        ]
        docks = list(self.dockList)
        push_stances = self._important_push_stances(boxes, docks)

        score = 0.0
        if worker is not None:
            # Tiến gần để ép MAX đi vòng hoặc tạo nguy cơ bị bắt.
            distance = self._manhattan(position, worker)
            score += 18 / (1 + distance)
            if distance == 1:
                score += 18

        if boxes:
            box_distance = min(self._manhattan(position, box) for box in boxes)
            score += 28 / (1 + box_distance)
        if docks:
            dock_distance = min(self._manhattan(position, dock) for dock in docks)
            score += 20 / (1 + dock_distance)
        if position in push_stances:
            score += 36

        exits = self._walkable_neighbor_count(position)
        if exits <= 2:
            score += 24  # Hành lang hẹp hoặc nút cổ chai.
        if exits == 1:
            score += 10

        # Hạn chế rung qua lại nếu có một ô chiến thuật khác gần tương đương.
        if position == self.competitor_previous_position:
            score -= 8
        return score

    def _important_push_stances(self, boxes, docks):
        positions = set()
        matrix = self.gameSokoban.matrix
        for box in boxes:
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                stance = box[0] - dy, box[1] - dx
                destination = box[0] + dy, box[1] + dx
                if self._matrix_value(matrix, stance) not in {" ", ".", "@", "E"}:
                    continue
                if self._matrix_value(matrix, destination) in {"#", "$", "*", "E"}:
                    continue
                positions.add(stance)
                if destination in docks:
                    positions.add(stance)
        return positions

    def _walkable_neighbor_count(self, position):
        matrix = self.gameSokoban.matrix
        count = 0
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            value = self._matrix_value(
                matrix, (position[0] + dy, position[1] + dx))
            if value not in {None, "#", "$", "*", "E"}:
                count += 1
        return count

    @staticmethod
    def _matrix_value(matrix, position):
        row, col = position
        if row < 0 or row >= len(matrix):
            return None
        if col < 0 or col >= len(matrix[row]):
            return None
        return matrix[row][col]

    @staticmethod
    def _manhattan(first, second):
        return abs(first[0] - second[0]) + abs(first[1] - second[1])

    def _cancel_solution_animation(self):
        if self.solution_job is not None:
            self.root.after_cancel(self.solution_job)
            self.solution_job = None
        self.current_solution = ""
        self.solution_index = 0
        self.competitor_position = None
        self.competitor_previous_position = None
        self.competitor_under_tile = " "
        self.competitor_turn_requirements = []
        self._set_pause_state(False)


# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    root = tk.Tk()
    app  = SokobanApp(root)
    root.mainloop()
