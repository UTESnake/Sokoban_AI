import copy
import os
import pygame
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk, messagebox, scrolledtext

import assets
from game import Game
from solver import Solve
from algorithm.algo_adversarial import alpha_beta, expectimax, minimax
from algorithm.algo_complex import (
    backtracking_search,
    global_search,
    min_conflict,
    no_observation_search,
    partial_observation_search,
    path_finding,
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
        ("BidirBFS",   "No Obs.",      "◌", "#9582CF"),
        ("Dijkstra",   "Partial",      "◐", "#58B7DC"),
        ("Backtrack",  "Backtrack",    "↵", "#DD4F7D"),
        ("RBFS",       "Path",         "⇢", "#5BC89F"),
        ("GBFS",       "Global",       "⊙", "#FFD64F"),
        ("IDDFS",      "Min Conflict", "▦", "#B563D9"),
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
    ("Level 6", "level6.txt"),
]
LEVEL_FILES = dict(LEVELS)

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
    "BidirBFS": no_observation_search,
    "Dijkstra": partial_observation_search,
    "Backtrack": backtracking_search,
    "RBFS": path_finding,
    "GBFS": global_search,
    "IDDFS": min_conflict,
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
                         bg=parent["bg"], highlightthickness=0, **kw)
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
        self._rounded_rect(3, shadow_h, w-1, h, self.radius, self.shadow, self.shadow)
        self._rounded_rect(0, 0, w-4, body_h, self.radius, color, self.outline, width=2)
        self.create_line(8, 8, w-12, 8, fill=self._shift(color, 18), width=1)
        self.create_line(8, body_h-8, w-12, body_h-8, fill=self._shift(color, -18), width=1)
        if self.selected:
            self._rounded_rect(2, 2, w-6, body_h-2, self.radius, color, "#FFFFFF", width=2)

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
                             fill=BTN_ICON, font=icon_font, anchor="w")
            self.create_text(text_x, center_y, text=self.text,
                             fill=self.fg, font=text_font, anchor="w")
        else:
            self.create_text(w//2 - 2, center_y, text=self.text,
                             fill=self.fg, font=FONT_BTN)

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
        self.win_notified     = False
        self.victory_popup    = None

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
        self.combobox.bind("<<ComboboxSelected>>", lambda _: self.init_game())

        tk.Frame(f, height=1, bg=LINE).pack(fill="x", padx=18, pady=7)

        tk.Label(f, text="ALGORITHMS", font=("Segoe UI", 10, "bold"),
                 bg=BG_PANEL, fg=TEXT_DARK).pack(anchor="w", padx=18, pady=(0, 5))

        self.algo_buttons = {}
        for title, buttons in ALGO_GROUPS:
            self._build_algo_group(f, title, buttons)

        # Start / Stop — rộng hơn theo LEFT_W
        tk.Frame(f, height=1, bg=LINE).pack(fill="x", padx=18, pady=(4, 6))
        RoundedButton(f, text="Start", icon="▶", bg="#6FCFA9", fg=BTN_TEXT,
                      width=LEFT_W - 58, height=38, command=self.init_game
                      ).pack(padx=18, pady=(0, 5))
        RoundedButton(f, text="Stop",  icon="■", bg="#E26087", fg=BTN_TEXT,
                      width=LEFT_W - 58, height=38, command=self.stop_game
                      ).pack(padx=18)

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
        self.root.after(20, self.run_solution)

    # ─────────────────────────────────────────
    #  GAME FRAME — co giãn theo cửa sổ
    # ─────────────────────────────────────────
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

        tk.Label(f, text="PROCESS LOG", font=("Segoe UI", 10, "bold"),
                 bg=BG_PANEL, fg=TEXT_DARK).pack(anchor="w", padx=28, pady=(24, 12))
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

    def init_game(self):
        self._cancel_solution_animation()
        if self.loop_job is not None:
            self.root.after_cancel(self.loop_job)
            self.loop_job = None

        level = self.combobox.get()
        try:
            matrix = self.load_map(level)
        except FileNotFoundError:
            messagebox.showerror("Error", f"Không tìm thấy file map cho {level}")
            return

        assets.load_sprites()

        if not self.game_initialized:
            self.root.update_idletasks()   # đảm bảo frame đã render trước khi lấy ID
            os.environ['SDL_WINDOWID'] = str(self.game_frame.winfo_id())
            if os.name == 'nt':
                os.environ['SDL_VIDEODRIVER'] = 'windib'
            pygame.init()

        self.gameSokoban = Game(matrix, [])
        self.dockList = self.gameSokoban.listDock()
        self.manual_steps = 0
        self.win_notified = False

        # Lấy kích thước frame thực sau khi layout xong
        self.root.update_idletasks()
        fw = self.game_frame.winfo_width()
        fh = self.game_frame.winfo_height()
        gw = fw if fw > 10 else GAME_W
        gh = fh if fh > 10 else GAME_H
        self.screen = pygame.display.set_mode((gw, gh))
        self._gw, self._gh = gw, gh

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
        self.root.focus_set()
        self._game_loop()

    def _prepare_display_map(self, matrix):
        self.gameSokoban = Game(matrix, [])
        self.dockList = self.gameSokoban.listDock()
        self.manual_steps = 0
        self.win_notified = False

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

        # Fill nền toàn screen bằng màu sàn (tránh viền đen xung quanh map)
        self.gameSokoban.fill_screen_with_floor((self._gw, self._gh), self.screen)

        # Render map vào surface tạm đúng kích thước map
        map_w = self._map_surf.get_width()
        map_h = self._map_surf.get_height()
        self.gameSokoban.fill_screen_with_floor((map_w, map_h), self._map_surf)
        self.gameSokoban.print_game(self._map_surf)

        # Blit map_surf vào giữa screen theo offset đã tính
        self.screen.blit(self._map_surf, (self._offset_x, self._offset_y))

        pygame.display.flip()
        self.loop_job = self.root.after(100, self._game_loop)

    def stop_game(self):
        self._cancel_solution_animation()
        self.game_initialized = False
        if self.loop_job is not None:
            self.root.after_cancel(self.loop_job)
            self.loop_job = None
        self._log("Stopped.")

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
            self.solution_var.set(f"Manual steps: {self.manual_steps}")
            if self.gameSokoban.is_completed(self.dockList):
                self._show_win_message(self.manual_steps, "manual")

        return "break"

    def play_solution(self):
        self._log("Playing solution...")

    def step_solution(self):
        self._log("Step.")

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
            matrix = self.load_map(level)
        except FileNotFoundError:
            messagebox.showerror("Error", f"Không tìm thấy file map cho {level}")
            return

        self._log(f"Running {algo}...")
        self.solution_var.set(f"Running {algo}...")
        self.is_solving = True
        self.root.configure(cursor="watch")
        self.root.update_idletasks()

        try:
            result = handler(Solve(copy.deepcopy(matrix)))
        except Exception as exc:
            self._log(f"{algo} error: {exc}")
            messagebox.showerror("Error", f"Lỗi khi chạy {algo}:\n{exc}")
            return
        finally:
            self.is_solving = False
            self.root.configure(cursor="")

        if not result or result == "NoSol":
            self.solution_var.set("No solution found.")
            self._log(f"{algo}: no solution.")
        else:
            self.solution_var.set(result)
            self._log(f"{algo}: found {len(result)} steps.")
            self._start_solution_animation(result, matrix)

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
        else:
            msg = f"Chúc mừng! Thuật toán đã giải xong màn chơi trong {steps} bước."
            self._log(f"Completed by algorithm in {steps} steps.")
        self.solution_var.set(msg)
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
        self._prepare_display_map(copy.deepcopy(matrix))
        self.current_solution = solution
        self.solution_index = 0
        self._log(f"Animating {len(solution)} steps...")
        self.solution_job = self.root.after(ANIMATION_START_DELAY, self._play_next_solution_step)

    def _play_next_solution_step(self):
        if self.solution_index >= len(self.current_solution):
            self.solution_job = None
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
            self.gameSokoban.move(y, x, self.dockList)

        self.solution_index += 1
        self.solution_var.set(
            f"{self.current_solution}  ({self.solution_index}/{len(self.current_solution)})"
        )
        self.solution_job = self.root.after(ANIMATION_STEP_DELAY, self._play_next_solution_step)

    def _cancel_solution_animation(self):
        if self.solution_job is not None:
            self.root.after_cancel(self.solution_job)
            self.solution_job = None
        self.current_solution = ""
        self.solution_index = 0


# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    root = tk.Tk()
    app  = SokobanApp(root)
    root.mainloop()
