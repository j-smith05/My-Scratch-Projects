"""Shared toolkit for the Terminal Arcade: colors, drawing, sound, title screens,
leaderboards, game-over screens and particle effects."""
import curses
import json
import math
import os
import random
import shutil
import subprocess
import time
from datetime import date
from pathlib import Path

os.environ.setdefault("ESCDELAY", "25")  # make Esc respond instantly

DATA_FILE = Path(__file__).with_name(".arcade_data.json")

RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, ORANGE, GREY = range(1, 10)
QUIT_KEYS = (ord("q"), ord("Q"))
ENTER_KEYS = (10, 13, curses.KEY_ENTER)


# ── Colors & drawing ───────────────────────────────────────────────────────

def init_colors():
    curses.start_color()
    try:
        curses.use_default_colors()
        bg = -1
    except curses.error:
        bg = curses.COLOR_BLACK
    base = [curses.COLOR_RED, curses.COLOR_GREEN, curses.COLOR_YELLOW, curses.COLOR_BLUE,
            curses.COLOR_MAGENTA, curses.COLOR_CYAN, curses.COLOR_WHITE]
    for i, c in enumerate(base, 1):
        curses.init_pair(i, c, bg)
    rich = curses.COLORS >= 256
    curses.init_pair(ORANGE, 208 if rich else curses.COLOR_YELLOW, bg)
    curses.init_pair(GREY, 244 if rich else curses.COLOR_WHITE, bg)
    try:
        curses.curs_set(0)
    except curses.error:
        pass


def color(n, *attrs):
    attr = curses.color_pair(n)
    for a in attrs:
        attr |= a
    return attr


def put(win, y, x, text, attr=0):
    """addstr that clips instead of raising when text runs off-screen."""
    h, w = win.getmaxyx()
    if y < 0 or y >= h or x >= w:
        return
    if x < 0:
        text, x = text[-x:], 0
    text = text[: w - x]
    if not text:
        return
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass  # writing the bottom-right cell raises after succeeding


def center(win, y, text, attr=0):
    put(win, y, (win.getmaxyx()[1] - len(text)) // 2, text, attr)


def box(win, top, left, height, width, attr=0, title=""):
    put(win, top, left, "╭" + "─" * (width - 2) + "╮", attr)
    for y in range(top + 1, top + height - 1):
        put(win, y, left, "│", attr)
        put(win, y, left + width - 1, "│", attr)
    put(win, top + height - 1, left, "╰" + "─" * (width - 2) + "╯", attr)
    if title:
        put(win, top, left + 2, f" {title} ", attr | curses.A_BOLD)


def fill(win, top, left, height, width):
    for y in range(top, top + height):
        put(win, y, left, " " * width)


def message_box(win, lines, attr=0):
    """Draws a centered popup containing `lines` (the first line is bold)."""
    h, w = win.getmaxyx()
    width = max(len(line) for line in lines) + 6
    height = len(lines) + 2
    top, left = (h - height) // 2, (w - width) // 2
    fill(win, top, left, height, width)
    box(win, top, left, height, width, attr)
    for i, line in enumerate(lines):
        put(win, top + 1 + i, left + 3, line.center(width - 6), attr | (curses.A_BOLD if i == 0 else 0))


def flush_input(win):
    win.nodelay(True)
    while win.getch() != -1:
        pass


def wait_key(win, keys, guard=0.0):
    """Blocks until one of `keys` (characters) is pressed; returns it.
    `guard` seconds of input are discarded first so a mid-game keystroke can't skip a screen."""
    if guard:
        time.sleep(guard)
        flush_input(win)
    win.nodelay(False)
    win.timeout(-1)
    while True:
        k = win.getch()
        if k in ENTER_KEYS and "\n" in keys:
            return "\n"
        if 0 <= k < 256 and chr(k).lower() in keys:
            return chr(k).lower()


def too_small(win, min_h, min_w):
    """If the terminal is smaller than min_w x min_h, draws a notice and returns True."""
    h, w = win.getmaxyx()
    if h >= min_h and w >= min_w:
        return False
    win.erase()
    center(win, h // 2 - 1, "Terminal too small!", curses.A_BOLD)
    center(win, h // 2, f"Need {min_w}x{min_h}, have {w}x{h}.")
    center(win, h // 2 + 1, "Make the window bigger, or press q.")
    win.refresh()
    return True


def ensure_size(win, min_h, min_w):
    """Waits for the terminal to be at least min_w x min_h. False if the player quits."""
    win.timeout(200)
    while too_small(win, min_h, min_w):
        if win.getch() in QUIT_KEYS:
            return False
    win.timeout(-1)
    return True


ARROWS = {
    curses.KEY_UP: (-1, 0), curses.KEY_DOWN: (1, 0), curses.KEY_LEFT: (0, -1), curses.KEY_RIGHT: (0, 1),
    ord("w"): (-1, 0), ord("s"): (1, 0), ord("a"): (0, -1), ord("d"): (0, 1),
    ord("W"): (-1, 0), ord("S"): (1, 0), ord("A"): (0, -1), ord("D"): (0, 1),
}


def fmt_time(seconds):
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


# ── Saved data: scores, settings, play counts ─────────────────────────────

def load_data():
    try:
        data = json.loads(DATA_FILE.read_text())
    except (OSError, ValueError):
        data = {}
    for key in ("scores", "settings", "plays"):
        if not isinstance(data.get(key), dict):
            data[key] = {}
    return data


def save_data(data):
    try:
        tmp = DATA_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(DATA_FILE)
    except OSError:
        pass


def setting(key, default=None):
    return load_data()["settings"].get(key, default)


def set_setting(key, value):
    data = load_data()
    data["settings"][key] = value
    save_data(data)


# ── Sound ──────────────────────────────────────────────────────────────────

SOUND_DIR = Path("/System/Library/Sounds")
EFFECTS = {  # effect name -> (macOS system sound, volume)
    "select": ("Tink", 0.4), "move": ("Tink", 0.25), "start": ("Blow", 0.5),
    "eat": ("Pop", 0.6), "power": ("Glass", 0.6), "bonus": ("Ping", 0.6),
    "crash": ("Basso", 0.7), "lose": ("Sosumi", 0.6), "win": ("Hero", 0.6), "record": ("Hero", 0.7),
    "lock": ("Tink", 0.35), "drop": ("Pop", 0.4), "clear": ("Glass", 0.6), "tetris": ("Hero", 0.6),
    "levelup": ("Ping", 0.6), "hold": ("Morse", 0.4),
    "shoot": ("Tink", 0.2), "kill": ("Bottle", 0.45), "hit": ("Basso", 0.7), "ufo": ("Submarine", 0.5),
    "boss": ("Funk", 0.5), "bossdown": ("Hero", 0.7),
    "dig": ("Tink", 0.35), "flag": ("Morse", 0.4), "cascade": ("Pop", 0.5), "boom": ("Basso", 0.8),
    "merge": ("Pop", 0.45), "bigmerge": ("Glass", 0.55), "undo": ("Morse", 0.35),
    "zap": ("Pop", 0.45), "error": ("Funk", 0.3), "miss": ("Basso", 0.5), "combo": ("Ping", 0.5),
}


class Sound:
    def __init__(self):
        self.enabled = bool(setting("sound", True))
        self.afplay = shutil.which("afplay")
        self.procs = []
        self.last = {}

    def play(self, name):
        if not self.enabled:
            return
        now = time.time()
        if now - self.last.get(name, 0) < 0.05:
            return
        self.last[name] = now
        self.procs = [p for p in self.procs if p.poll() is None]
        if len(self.procs) >= 4:
            return
        file, volume = EFFECTS.get(name, (name, 0.5))
        path = SOUND_DIR / f"{file}.aiff"
        if self.afplay and path.exists():
            self.procs.append(subprocess.Popen([self.afplay, "-v", str(volume), str(path)],
                                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        else:
            try:
                curses.beep()
            except curses.error:
                pass

    def toggle(self):
        self.enabled = not self.enabled
        set_setting("sound", self.enabled)
        self.play("select")

    @property
    def label(self):
        return f"v sound {'on' if self.enabled else 'off'}"


sound = Sound()


# ── Big block-letter font ──────────────────────────────────────────────────

FONT = {
    "A": ("▄▀█", "█▀█"), "B": ("█▄▄", "█▄█"), "C": ("█▀▀", "█▄▄"), "D": ("█▀▄", "█▄▀"), "E": ("█▀▀", "██▄"),
    "F": ("█▀▀", "█▀ "), "G": ("█▀▀", "█▄█"), "H": ("█ █", "█▀█"), "I": ("█", "█"), "J": ("  █", "█▄█"),
    "K": ("█▄▀", "█ █"), "L": ("█  ", "█▄▄"), "M": ("█▀▄▀█", "█ ▀ █"), "N": ("█▄ █", "█ ▀█"),
    "O": ("█▀█", "█▄█"), "P": ("█▀█", "█▀▀"), "Q": ("█▀█", "▀▀█"), "R": ("█▀█", "█▀▄"), "S": ("█▀▀", "▄▄█"),
    "T": ("▀█▀", " █ "), "U": ("█ █", "█▄█"), "V": ("█ █", "▀▄▀"), "W": ("█ █ █", "▀▄▀▄▀"),
    "X": ("▀▄▀", "█ █"), "Y": ("█▄█", " █ "), "Z": ("▀▀█", "█▄▄"), "0": ("█▀█", "█▄█"), "2": ("▀▀█", "█▄▄"),
    "4": ("█ █", "▀▀█"), "8": ("█▄█", "█▄█"), " ": ("  ", "  "), "!": ("█", "▄"),
}


def big_text(text):
    glyphs = [FONT.get(ch, FONT[" "]) for ch in text.upper()]
    return [" ".join(g[0] for g in glyphs), " ".join(g[1] for g in glyphs)]


def draw_logo(win, y, text, col, t):
    """Big text with a white shine sweeping across it."""
    lines = big_text(text)
    width = len(lines[0])
    x0 = (win.getmaxyx()[1] - width) // 2
    shine = int((t * 30) % (width + 30)) - 10
    for row, line in enumerate(lines):
        for i, ch in enumerate(line):
            if ch != " ":
                lit = abs(i - shine - row) < 3
                put(win, y + row, x0 + i, ch, color(WHITE if lit else col, curses.A_BOLD))


# ── Leaderboards ───────────────────────────────────────────────────────────

BOARD_SIZE = 10


class Board:
    """Describes one leaderboard: its storage key, sort order and number format."""

    def __init__(self, key, title, lower_is_better=False, fmt=str, label="Score"):
        self.key, self.title, self.lower, self.fmt, self.label = key, title, lower_is_better, fmt, label

    def entries(self):
        raw = load_data()["scores"].get(self.key, [])
        if isinstance(raw, (int, float)):  # very old single-number format
            raw = [{"name": "???", "score": raw, "date": ""}]
        return sorted(raw, key=lambda e: e["score"], reverse=not self.lower)[:BOARD_SIZE]

    def best(self):
        top = self.entries()
        return top[0]["score"] if top else None

    def qualifies(self, score):
        top = self.entries()
        if len(top) < BOARD_SIZE:
            return True
        return score < top[-1]["score"] if self.lower else score > top[-1]["score"]

    def add(self, name, score, note=""):
        """Adds an entry and returns its 0-based rank (None if it didn't make the top 10)."""
        data = load_data()
        entry = {"name": name, "score": score, "date": date.today().isoformat(), "note": note}
        entries = self.entries() + [entry]
        entries.sort(key=lambda e: e["score"], reverse=not self.lower)
        entries = entries[:BOARD_SIZE]
        data["scores"][self.key] = entries
        save_data(data)
        for i, e in enumerate(entries):
            if e is entry:
                return i
        return None

    def best_text(self):
        top = self.entries()
        return f"{self.fmt(top[0]['score'])} by {top[0]['name']}" if top else "no record yet"


def draw_leaderboard(win, y, board, highlight=None, rows=BOARD_SIZE):
    entries = board.entries()
    center(win, y, f"── {board.title} · TOP {rows} ──", color(CYAN, curses.A_BOLD))
    for i in range(rows):
        if i < len(entries):
            e = entries[i]
            note = e.get("note", "")
            line = f"{i + 1:>2}. {e['name']:<3}  {board.fmt(e['score']):>9}  {note:<10} {e.get('date', ''):>10}"
            attr = color(YELLOW, curses.A_BOLD | curses.A_REVERSE) if i == highlight else color(WHITE)
        else:
            line = f"{i + 1:>2}. ---  {'·' * 9}  {'':<10} {'':>10}"
            attr = color(GREY, curses.A_DIM)
        center(win, y + 1 + i, line, attr)
    return rows + 1


def show_leaderboard(win, board):
    win.erase()
    h, _ = win.getmaxyx()
    rows = max(3, min(BOARD_SIZE, h - 6))
    draw_leaderboard(win, max(1, (h - rows - 4) // 2), board, rows=rows)
    center(win, min(h - 1, (h - rows - 4) // 2 + rows + 3), "press any key", color(GREY, curses.A_DIM))
    win.refresh()
    win.nodelay(False)
    win.getch()


INITIAL_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "


def enter_initials(win, headline):
    letters = list((setting("initials", "AAA") + "AAA")[:3])
    pos = 0
    flush_input(win)
    win.nodelay(False)
    win.timeout(-1)
    while True:
        h, w = win.getmaxyx()
        win.erase()
        y = max(1, h // 2 - 6)
        draw_logo(win, y, "NEW RECORD", YELLOW, time.time())
        center(win, y + 3, headline, color(WHITE, curses.A_BOLD))
        center(win, y + 5, "ENTER YOUR INITIALS", color(CYAN, curses.A_BOLD))
        x0 = (w - 17) // 2
        for i, ch in enumerate(letters):
            attr = color(YELLOW, curses.A_BOLD | (curses.A_REVERSE if i == pos else 0))
            put(win, y + 7, x0 + i * 6, "▲" if i == pos else " ", color(GREY))
            put(win, y + 8, x0 + i * 6 - 1, f" {ch} ", attr)
            put(win, y + 9, x0 + i * 6, "▼" if i == pos else " ", color(GREY))
        center(win, y + 11, "type letters or ↑↓ · ←→ move · Enter done", color(GREY, curses.A_DIM))
        win.refresh()
        k = win.getch()
        if k in ENTER_KEYS:
            name = "".join(letters).strip() or "???"
            set_setting("initials", "".join(letters))
            return name
        if k in (curses.KEY_UP, curses.KEY_DOWN):
            step = -1 if k == curses.KEY_UP else 1
            letters[pos] = INITIAL_CHARS[(INITIAL_CHARS.index(letters[pos]) + step) % len(INITIAL_CHARS)]
            sound.play("move")
        elif k == curses.KEY_LEFT:
            pos = max(0, pos - 1)
        elif k == curses.KEY_RIGHT:
            pos = min(2, pos + 1)
        elif k in (curses.KEY_BACKSPACE, 127, 8):
            pos = max(0, pos - 1)
        elif 0 <= k < 256 and chr(k).upper() in INITIAL_CHARS.strip():
            letters[pos] = chr(k).upper()
            sound.play("move")
            pos = min(2, pos + 1)


# ── Title & game-over screens ──────────────────────────────────────────────

def title_screen(win, logo, logo_color, tagline, controls, options=(), board_for=None, settings_key=None):
    """Animated title screen.

    options: list of (label, [choices]) the player can change with ←→.
    board_for(choice_indices) -> Board shown as the current high score.
    Returns the chosen option indices (list), or None if the player quit.
    """
    saved = setting(settings_key, []) if settings_key else []
    choice = [saved[i] if i < len(saved) and saved[i] < len(opts) else 0 for i, (_, opts) in enumerate(options)]
    row = 0
    win.timeout(60)
    start = time.time()
    while True:
        t = time.time() - start
        h, w = win.getmaxyx()
        win.erase()
        height = 8 + len(options) * 2 + len(controls)
        y = max(0, (h - height) // 2 - 1)
        draw_logo(win, y, logo, logo_color, t)
        center(win, y + 3, tagline, color(GREY))
        y += 5
        for i, (label, opts) in enumerate(options):
            selected = i == row
            text = f"{label}:  ◀ {opts[choice[i]]:^14} ▶"
            center(win, y, text, color(YELLOW if selected else WHITE, curses.A_BOLD if selected else 0))
            y += 2
        board = board_for(choice) if board_for else None
        if board:
            center(win, y, f"HIGH SCORE  {board.best_text()}", color(CYAN, curses.A_BOLD))
            y += 2
        key_w = max((len(k) for k, _ in controls), default=0)
        desc_w = max((len(d) for _, d in controls), default=0)
        x0 = (w - key_w - desc_w - 3) // 2
        for k, d in controls:
            put(win, y, x0, k.rjust(key_w), color(YELLOW))
            put(win, y, x0 + key_w + 3, d, color(GREY))
            y += 1
        y += 1
        if int(t * 2) % 2 == 0:
            center(win, y, "▶  PRESS ENTER TO START  ◀", color(GREEN, curses.A_BOLD))
        hints = (["↑↓ ←→ options"] if options else []) + (["l leaderboard"] if board else []) + [sound.label, "q quit"]
        center(win, h - 1, " · ".join(hints), color(GREY, curses.A_DIM))
        win.refresh()

        k = win.getch()
        if k == -1:
            continue
        if k in QUIT_KEYS or k == 27:
            return None
        if k in ENTER_KEYS or k == ord(" "):
            if settings_key:
                set_setting(settings_key, choice)
            sound.play("start")
            flush_input(win)
            return choice
        if k in (ord("v"), ord("V")):
            sound.toggle()
        elif k in (ord("l"), ord("L")) and board:
            show_leaderboard(win, board)
            win.timeout(60)
        elif options and k in (curses.KEY_UP, curses.KEY_DOWN):
            row = (row + (1 if k == curses.KEY_DOWN else -1)) % len(options)
            sound.play("move")
        elif options and k in (curses.KEY_LEFT, curses.KEY_RIGHT):
            n = len(options[row][1])
            choice[row] = (choice[row] + (1 if k == curses.KEY_RIGHT else -1)) % n
            sound.play("move")


def game_over(win, board, score, stats, title="GAME OVER", keys="rq", key_help="r play again · q back to title",
              note="", won=False):
    """Records the score (asking for initials if it makes the top 10), then shows
    stats, how it compares to the record, and the leaderboard. Returns the key pressed.
    Pass score=None when the round doesn't count (e.g. a lost Minesweeper game)."""
    prev_best = board.best()
    rank = None
    time.sleep(0.4)
    flush_input(win)
    if score is not None and (score or board.lower) and board.qualifies(score):
        is_best = prev_best is None or (score < prev_best if board.lower else score > prev_best)
        sound.play("record" if is_best else "bonus")
        headline = f"{board.label}: {board.fmt(score)}" + ("  ·  #1 ALL-TIME!" if is_best else "")
        rank = board.add(enter_initials(win, headline), score, note)
    else:
        sound.play("win" if won else "lose")

    win.erase()
    h, w = win.getmaxyx()
    lb_rows = max(0, min(BOARD_SIZE, h - 12 - (len(stats) + 1) // 2))
    y = max(0, (h - (11 + lb_rows + (len(stats) + 1) // 2)) // 2)
    draw_logo(win, y, title, GREEN if won else RED, 0)
    y += 3
    if score is not None:
        center(win, y, f"{board.label.upper()}  {board.fmt(score)}", color(WHITE, curses.A_BOLD))
        y += 1
        if rank is None and prev_best is None:
            line, col = "Score some points to get on the board!", GREY
        elif prev_best is None:
            line, col = "First score on the board!", YELLOW
        elif (score < prev_best) if board.lower else (score > prev_best):
            line, col = f"★ NEW RECORD! Beat the old best by {board.fmt(abs(score - prev_best))} ★", YELLOW
        elif score == prev_best:
            line, col = "Tied the all-time record!", YELLOW
        else:
            line, col = f"{board.fmt(abs(score - prev_best))} short of the record ({board.fmt(prev_best)})", GREY
        center(win, y, line, color(col, curses.A_BOLD))
        y += 1
    y += 1
    for i in range(0, len(stats), 2):
        pair = stats[i:i + 2]
        center(win, y, "     ".join(f"{label}: {value}" for label, value in pair), color(CYAN))
        y += 1
    y += 1
    if lb_rows >= 3:
        y += draw_leaderboard(win, y, board, highlight=rank, rows=lb_rows) + 1
    center(win, min(h - 1, y), key_help, color(GREEN, curses.A_BOLD))
    win.refresh()
    return wait_key(win, keys, guard=0.3)


# ── Particles ──────────────────────────────────────────────────────────────

class Particles:
    def __init__(self):
        self.items = []

    def burst(self, y, x, n=10, colors=(YELLOW,), chars="*+·•'", speed=(5, 14), life=(0.25, 0.6),
              gravity=0.0, angle=(0, 360)):
        now = time.time()
        for _ in range(n):
            a = math.radians(random.uniform(*angle))
            v = random.uniform(*speed)
            self.items.append([float(y), float(x), -math.sin(a) * v * 0.5, math.cos(a) * v,
                               now + random.uniform(*life), random.choice(chars), random.choice(colors), gravity])

    def update(self, dt):
        now = time.time()
        for p in self.items:
            p[2] += p[7] * dt
            p[0] += p[2] * dt
            p[1] += p[3] * dt
        self.items = [p for p in self.items if p[4] > now]

    def draw(self, win, oy=0, ox=0):
        for y, x, _, _, _, ch, col, _ in self.items:
            put(win, oy + int(round(y)), ox + int(round(x)), ch, color(col, curses.A_BOLD))

    def __bool__(self):
        return bool(self.items)


def run(main):
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
