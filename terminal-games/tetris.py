#!/usr/bin/env python3
"""TETRIS — stack the blocks, clear the lines, survive the speed-up."""
import curses
import random
import time

from common import (BLUE, CYAN, GREEN, GREY, MAGENTA, ORANGE, QUIT_KEYS, RED, WHITE, YELLOW, Board, box,
                    color, ensure_size, fmt_time, game_over, init_colors, message_box, put, run, sound,
                    title_screen, too_small)

ROWS, COLS = 20, 10
PIECES = {
    "I": (["....", "####", "....", "...."], CYAN),
    "O": (["##", "##"], YELLOW),
    "T": ([".#.", "###", "..."], MAGENTA),
    "S": ([".##", "##.", "..."], GREEN),
    "Z": (["##.", ".##", "..."], RED),
    "J": (["#..", "###", "..."], BLUE),
    "L": (["..#", "###", "..."], ORANGE),
}
LINE_POINTS = [0, 100, 300, 500, 800]
LINE_NAMES = ["", "SINGLE", "DOUBLE", "TRIPLE", "TETRIS!"]
LOCK_DELAY, MAX_LOCK_RESETS = 0.5, 15
START_LEVELS = [str(n) for n in range(1, 16)]
BOARD = Board("tetris", "TETRIS")
NEED_H, NEED_W = 24, 50


def cells(shape):
    return [(r, c) for r, row in enumerate(shape) for c, ch in enumerate(row) if ch == "#"]


def rotate(shape, clockwise=True):
    n = len(shape)
    if clockwise:
        return ["".join(row[i] for row in reversed(shape)) for i in range(n)]
    return ["".join(row[n - 1 - i] for row in shape) for i in range(n)]


class Piece:
    def __init__(self, kind):
        self.kind = kind
        self.shape, self.color = PIECES[kind]
        self.r, self.c = 0, (COLS - len(self.shape[0])) // 2


def play(scr, start_level):
    if not ensure_size(scr, NEED_H, NEED_W):
        return "q"
    board = [[None] * COLS for _ in range(ROWS)]
    bag = []

    def draw_from_bag():
        if not bag:
            bag.extend(random.sample(list(PIECES), len(PIECES)))
        return bag.pop()

    def collides(shape, r, c):
        for dr, dc in cells(shape):
            rr, cc = r + dr, c + dc
            if cc < 0 or cc >= COLS or rr >= ROWS or (rr >= 0 and board[rr][cc]):
                return True
        return False

    def ghost_row(p):
        r = p.r
        while not collides(p.shape, r + 1, p.c):
            r += 1
        return r

    piece, upcoming = Piece(draw_from_bag()), [draw_from_bag() for _ in range(3)]
    held, can_hold = None, True
    score, lines, level = 0, 0, start_level
    pieces_placed, tetrises, combo, best_combo = 0, 0, -1, 0
    lock_started, lock_resets = None, 0
    paused, game_ended = False, False
    callouts = []   # (text, color, until)
    trails = []     # (col, from_row, to_row, until)
    start = time.time()

    def layout():
        h, w = scr.getmaxyx()
        return (h - ROWS - 2) // 2, (w - (COLS * 2 + 2) - 24) // 2

    def callout(text, col, seconds=1.0):
        callouts.append((text, col, time.time() + seconds))

    def spawn_next():
        nonlocal piece, can_hold, lock_started, lock_resets, game_ended
        piece = Piece(upcoming.pop(0))
        upcoming.append(draw_from_bag())
        can_hold, lock_started, lock_resets = True, None, 0
        if collides(piece.shape, piece.r, piece.c):
            game_ended = True

    def lock():
        nonlocal score, lines, level, pieces_placed, tetrises, combo, best_combo, game_ended
        for dr, dc in cells(piece.shape):
            if piece.r + dr < 0:
                game_ended = True
                return
            board[piece.r + dr][piece.c + dc] = piece.color
        pieces_placed += 1
        full = [r for r in range(ROWS) if all(board[r])]
        if full:
            top, left = layout()
            for _ in range(2):  # flash the cleared lines
                for flash in (True, False):
                    for r in full:
                        put(scr, top + 1 + r, left + 1, "██" * COLS,
                            color(WHITE, curses.A_BOLD) if flash else color(board[r][0], curses.A_DIM))
                    scr.refresh()
                    time.sleep(0.045)
            for r in full:
                del board[r]
                board.insert(0, [None] * COLS)
            n = len(full)
            combo += 1
            best_combo = max(best_combo, combo + 1)
            score += LINE_POINTS[n] * level + 50 * combo * level
            lines += n
            if n == 4:
                tetrises += 1
                callout("★ TETRIS! ★", YELLOW, 1.4)
                sound.play("tetris")
            else:
                callout(LINE_NAMES[n], CYAN)
                sound.play("clear")
            if combo >= 1:
                callout(f"COMBO x{combo + 1}", MAGENTA)
            new_level = max(start_level, lines // 10 + 1)
            if new_level > level:
                level = new_level
                callout(f"LEVEL {level}!", GREEN, 1.4)
                sound.play("levelup")
        else:
            combo = -1
            sound.play("lock")
        spawn_next()

    def moved_on_ground():
        """Moving or rotating on the floor buys a little more time (up to a limit)."""
        nonlocal lock_started, lock_resets
        if lock_started is not None and lock_resets < MAX_LOCK_RESETS:
            lock_started = time.time()
            lock_resets += 1

    def try_move(dc):
        if not collides(piece.shape, piece.r, piece.c + dc):
            piece.c += dc
            moved_on_ground()

    def try_rotate(clockwise):
        new = rotate(piece.shape, clockwise)
        for dr, dc in ((0, 0), (0, -1), (0, 1), (0, -2), (0, 2), (-1, 0)):
            if not collides(new, piece.r + dr, piece.c + dc):
                piece.shape, piece.r, piece.c = new, piece.r + dr, piece.c + dc
                moved_on_ground()
                return

    def draw_mini(kind, y, x):
        shape, col = PIECES[kind]
        for dr, dc in cells(shape):
            put(scr, y + dr, x + dc * 2, "██", color(col))

    def draw(now):
        top, left = layout()
        side = left + COLS * 2 + 4
        scr.erase()
        box(scr, top, left, ROWS + 2, COLS * 2 + 2, color(GREY), "TETRIS")
        for r in range(ROWS):
            for c in range(COLS):
                if board[r][c]:
                    put(scr, top + 1 + r, left + 1 + c * 2, "██", color(board[r][c]))
                else:
                    put(scr, top + 1 + r, left + 1 + c * 2, " ·", color(GREY, curses.A_DIM))
        for c, r0, r1, until in trails:
            if until > now:
                for r in range(max(0, r0), r1):
                    put(scr, top + 1 + r, left + 1 + c * 2, "││", color(piece.color, curses.A_DIM))
        g = ghost_row(piece)
        for dr, dc in cells(piece.shape):
            if g + dr >= 0:
                put(scr, top + 1 + g + dr, left + 1 + (piece.c + dc) * 2, "░░", color(piece.color, curses.A_DIM))
        settling = lock_started is not None and int(now * 12) % 2
        for dr, dc in cells(piece.shape):
            if piece.r + dr >= 0:
                put(scr, top + 1 + piece.r + dr, left + 1 + (piece.c + dc) * 2, "▓▓" if settling else "██",
                    color(piece.color, curses.A_BOLD))
        active = [c for c in callouts if c[2] > now]
        for i, (text, col, _) in enumerate(active[-3:]):
            put(scr, top + 7 + i * 2, left + 1 + (COLS * 2 - len(text)) // 2, text,
                color(col, curses.A_BOLD | curses.A_REVERSE))

        put(scr, top, side, "NEXT", color(CYAN, curses.A_BOLD))
        for i, kind in enumerate(upcoming):
            draw_mini(kind, top + 1 + i * 3, side)
        put(scr, top + 10, side, "HOLD (c)", color(CYAN, curses.A_BOLD))
        if held:
            draw_mini(held, top + 11, side)
        best = BOARD.best() or 0
        stats = [("SCORE", score), ("BEST", max(best, score)), ("LINES", lines), ("LEVEL", level)]
        for i, (label, val) in enumerate(stats):
            put(scr, top + 14 + i, side, f"{label:<6}", color(GREY))
            put(scr, top + 14 + i, side + 6, str(val), color(YELLOW, curses.A_BOLD))
        help_lines = ["←→ move   ↑/x z rotate", "↓ soft   space drop", f"p pause  {sound.label}"]
        for i, line in enumerate(help_lines):
            put(scr, top + 19 + i, side, line, color(GREY, curses.A_DIM))

    scr.nodelay(True)
    last_fall = time.time()
    while not game_ended:
        now = time.time()
        if too_small(scr, NEED_H, NEED_W):
            if scr.getch() in QUIT_KEYS:
                return "q"
            time.sleep(0.1)
            last_fall = time.time()
            continue
        key = scr.getch()
        while key != -1 and not game_ended:
            if key in QUIT_KEYS:
                return "q"
            if key == curses.KEY_RESIZE:
                scr.clear()
            elif key in (ord("p"), ord("P")):
                paused = not paused
            elif key in (ord("v"), ord("V")):
                sound.toggle()
            elif not paused:
                if key in (curses.KEY_LEFT, ord("a"), ord("A")):
                    try_move(-1)
                elif key in (curses.KEY_RIGHT, ord("d"), ord("D")):
                    try_move(1)
                elif key in (curses.KEY_UP, ord("w"), ord("W"), ord("x"), ord("X")):
                    try_rotate(True)
                elif key in (ord("z"), ord("Z")):
                    try_rotate(False)
                elif key in (curses.KEY_DOWN, ord("s"), ord("S")):
                    if collides(piece.shape, piece.r + 1, piece.c):
                        lock()
                    else:
                        piece.r += 1
                        score += 1
                        last_fall = time.time()
                elif key == ord(" "):
                    target = ghost_row(piece)
                    for dr, dc in cells(piece.shape):
                        trails.append((piece.c + dc, piece.r + dr, target + dr, now + 0.09))
                    score += (target - piece.r) * 2
                    piece.r = target
                    sound.play("drop")
                    lock()
                    last_fall = time.time()
                elif key in (ord("c"), ord("C")) and can_hold:
                    sound.play("hold")
                    if held is None:
                        held = piece.kind
                        spawn_next()
                    else:
                        held, piece = piece.kind, Piece(held)
                        lock_started, lock_resets = None, 0
                    can_hold = False
            key = scr.getch()
        if game_ended:
            break

        if paused:
            last_fall = now
            if lock_started is not None:
                lock_started = now
        else:
            on_ground = collides(piece.shape, piece.r + 1, piece.c)
            if on_ground:
                if lock_started is None:
                    lock_started = now
                elif now - lock_started >= LOCK_DELAY:
                    lock()
                    last_fall = time.time()
            else:
                lock_started = None
                gravity = max(0.04, 0.8 * 0.85 ** (level - 1))
                if now - last_fall >= gravity:
                    last_fall = now
                    piece.r += 1
        callouts[:] = [c for c in callouts if c[2] > now]
        trails[:] = [t for t in trails if t[3] > now]

        draw(now)
        if paused:
            message_box(scr, ["PAUSED", "p to resume · q quit"], color(YELLOW))
        scr.refresh()
        time.sleep(0.01)

    # ── game over: the stack greys out from the bottom up ──
    sound.play("crash")
    top, left = layout()
    for r in range(ROWS - 1, -1, -1):
        put(scr, top + 1 + r, left + 1, "▓▓" * COLS, color(GREY))
        scr.refresh()
        time.sleep(0.025)
    stats = [("Lines", lines), ("Level", level), ("Tetrises", tetrises), ("Best combo", f"x{best_combo}" if best_combo > 1 else "—"),
             ("Pieces", pieces_placed), ("Time", fmt_time(time.time() - start))]
    return game_over(scr, BOARD, score, stats, note=f"level {level}")


def main(scr):
    init_colors()
    while True:
        choice = title_screen(
            scr, "TETRIS", MAGENTA, "Stack the blocks. Clear the lines. Survive the speed-up.",
            [("← →", "move"), ("↑ / x   z", "rotate ↻ / ↺"), ("↓", "soft drop"), ("space", "hard drop"),
             ("c", "hold piece"), ("p / q", "pause / quit")],
            options=[("Start level", START_LEVELS)], board_for=lambda c: BOARD, settings_key="tetris_options")
        if choice is None:
            return
        while play(scr, choice[0] + 1) == "r":
            pass


if __name__ == "__main__":
    run(main)
