#!/usr/bin/env python3
"""MINESWEEPER — clear the field without touching a mine. Keyboard or mouse."""
import curses
import random
import time

from common import (ARROWS, BLUE, CYAN, GREEN, GREY, MAGENTA, ORANGE, QUIT_KEYS, RED, WHITE, YELLOW, Board,
                    Particles, box, center, color, ensure_size, game_over, init_colors, put, run, sound,
                    title_screen, too_small)

LEVELS = [("Easy", 9, 9, 10), ("Medium", 16, 16, 40), ("Hard", 16, 30, 99)]
BOARDS = [Board(f"minesweeper-{name.lower()}", f"MINESWEEPER · {name.upper()}", lower_is_better=True,
                fmt=lambda s: f"{s}s", label="Time") for name, *_ in LEVELS]
NUMBER_COLORS = {1: BLUE, 2: GREEN, 3: RED, 4: MAGENTA, 5: ORANGE, 6: CYAN, 7: WHITE, 8: GREY}
VIM_KEYS = {ord("k"): (-1, 0), ord("j"): (1, 0), ord("h"): (0, -1), ord("l"): (0, 1)}
FACES = {"happy": "(^_^)", "worried": "(°o°)", "dead": "(x_x)", "cool": "(⌐■_■)"}


def play(scr, level):
    name, rows, cols, n_mines = LEVELS[level]
    need_h, need_w = rows + 7, max(cols * 2 + 5, 26)
    if not ensure_size(scr, need_h, need_w):
        return "q"

    mines, revealed, flags, marks = set(), set(), set(), set()
    counts = {}
    cur = [rows // 2, cols // 2]
    started = finished_at = None
    state, exploded = "playing", None
    worried_until = 0.0
    particles = Particles()

    def layout():
        h, w = scr.getmaxyx()
        return (h - rows - 5) // 2 + 2, (w - cols * 2 - 3) // 2

    def neighbors(r, c):
        return [(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                if (dr or dc) and 0 <= r + dr < rows and 0 <= c + dc < cols]

    def place_mines(safe):
        forbidden = {safe, *neighbors(*safe)}
        options = [(r, c) for r in range(rows) for c in range(cols) if (r, c) not in forbidden]
        mines.update(random.sample(options, n_mines))
        for r in range(rows):
            for c in range(cols):
                counts[(r, c)] = sum(n in mines for n in neighbors(r, c))

    def reveal(cell):
        nonlocal state, exploded, started
        if cell in flags or cell in revealed:
            return
        if not mines:
            place_mines(cell)
            started = time.time()
        if cell in mines:
            state, exploded = "lost", cell
            return
        before = len(revealed)
        stack = [cell]
        while stack:
            cur_cell = stack.pop()
            if cur_cell in revealed or cur_cell in flags:
                continue
            revealed.add(cur_cell)
            marks.discard(cur_cell)
            if counts[cur_cell] == 0:
                stack.extend(n for n in neighbors(*cur_cell) if n not in revealed)
        sound.play("cascade" if len(revealed) - before > 8 else "dig")

    def chord(cell):
        if cell in revealed and counts[cell] and sum(n in flags for n in neighbors(*cell)) == counts[cell]:
            for n in neighbors(*cell):
                if state == "playing":
                    reveal(n)

    def act(cell, flag):
        nonlocal worried_until
        if state != "playing":
            return
        if flag:
            if cell in revealed:
                return
            if cell in flags:          # flag → question mark
                flags.discard(cell)
                marks.add(cell)
            elif cell in marks:        # question mark → nothing
                marks.discard(cell)
            else:                      # nothing → flag
                flags.add(cell)
            sound.play("flag")
        else:
            worried_until = time.time() + 0.3
            if cell in revealed:
                chord(cell)
            else:
                reveal(cell)

    def draw(now, show_mines=None):
        top, left = layout()
        scr.erase()
        elapsed = int((finished_at or now) - started) if started else 0
        face = {"lost": "dead", "won": "cool"}.get(state, "worried" if worried_until > now else "happy")
        center(scr, top - 2, f"MINESWEEPER · {name}", color(WHITE, curses.A_BOLD))
        put(scr, top - 1, left + 1, f"▲ {n_mines - len(flags)}", color(RED, curses.A_BOLD))
        face_text = FACES[face]
        put(scr, top - 1, left + (cols * 2 + 3 - len(face_text)) // 2, face_text,
            color(YELLOW, curses.A_BOLD | curses.A_REVERSE))
        put(scr, top - 1, left + cols * 2 - 4, f"⏱ {elapsed:>3}", color(CYAN, curses.A_BOLD))
        box(scr, top, left, rows + 2, cols * 2 + 3, color(GREY))
        shown = mines if show_mines is None else show_mines
        for r in range(rows):
            for c in range(cols):
                cell = (r, c)
                if state == "lost" and cell in shown and cell not in flags:
                    glyph, attr = "*", color(RED, curses.A_BOLD | (curses.A_REVERSE if cell == exploded else 0))
                elif state == "lost" and show_mines is None and cell in flags and cell not in mines:
                    glyph, attr = "x", color(MAGENTA, curses.A_BOLD)
                elif cell in flags:
                    glyph, attr = "▲", color(RED if state != "won" else GREEN, curses.A_BOLD)
                elif cell in marks:
                    glyph, attr = "?", color(YELLOW, curses.A_BOLD)
                elif cell in revealed:
                    n = counts[cell]
                    glyph, attr = (str(n), color(NUMBER_COLORS[n], curses.A_BOLD)) if n else ("·", color(GREY, curses.A_DIM))
                else:
                    glyph, attr = "■", color(GREY)
                if [r, c] == cur and state == "playing":
                    attr |= curses.A_REVERSE
                put(scr, top + 1 + r, left + 2 + c * 2, glyph, attr)
        particles.draw(scr)
        center(scr, top + rows + 2, f"arrows/WASD/hjkl move · space dig · f flag/? · r restart · {sound.label} · q quit",
               color(GREY, curses.A_DIM))
        center(scr, top + rows + 3, "mouse: left-click dig · right-click flag · click the face to restart",
               color(GREY, curses.A_DIM))
        return top, left

    curses.mousemask(curses.ALL_MOUSE_EVENTS)
    curses.mouseinterval(0)
    scr.timeout(100)

    while True:
        now = time.time()
        if state == "playing" and mines and len(revealed) == rows * cols - n_mines:
            state = "won"
            flags.update(mines)
            marks.clear()
        if state != "playing":
            finished_at = finished_at or now
            break
        if too_small(scr, need_h, need_w):
            if scr.getch() in QUIT_KEYS:
                return "q"
            continue
        top, left = draw(now)
        scr.refresh()

        key = scr.getch()
        if key == -1:
            continue
        if key in QUIT_KEYS:
            return "q"
        if key == curses.KEY_RESIZE:
            scr.clear()
        elif key in (ord("r"), ord("R")):
            return "r"
        elif key in (ord("v"), ord("V")):
            sound.toggle()
        elif (move := ARROWS.get(key) or VIM_KEYS.get(key)):
            cur[0] = (cur[0] + move[0]) % rows
            cur[1] = (cur[1] + move[1]) % cols
        elif key in (ord(" "), 10, 13, curses.KEY_ENTER):
            act(tuple(cur), flag=False)
        elif key in (ord("f"), ord("F")):
            act(tuple(cur), flag=True)
        elif key == ord("?"):
            cell = tuple(cur)
            if cell not in revealed:
                flags.discard(cell)
                marks.symmetric_difference_update({cell})
        elif key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()
            except curses.error:
                continue
            pressed = bstate & (curses.BUTTON1_PRESSED | curses.BUTTON1_CLICKED)
            face_x = left + (cols * 2 + 3 - 6) // 2
            if my == top - 1 and face_x <= mx < face_x + 6 and pressed:
                return "r"
            r, c = my - top - 1, (mx - left - 2) // 2
            if 0 <= r < rows and 0 <= c < cols:
                cur[:] = [r, c]
                if pressed:
                    act((r, c), flag=False)
                elif bstate & (curses.BUTTON3_PRESSED | curses.BUTTON3_CLICKED):
                    act((r, c), flag=True)

    elapsed = int(finished_at - started)
    explored = f"{100 * len(revealed) // (rows * cols - n_mines)}%"
    if state == "won":
        # confetti!
        h, w = scr.getmaxyx()
        top, left = layout()
        colors_ = (RED, YELLOW, GREEN, CYAN, MAGENTA, BLUE)
        for i in range(6):
            particles.burst(top - 1, left + (cols * 2) * i // 5, 14, colors=colors_, chars="*•◆▪+",
                            speed=(4, 14), life=(1.2, 2.0), gravity=14, angle=(20, 160))
        sound.play("win")
        last = time.time()
        while particles:
            now = time.time()
            particles.update(now - last)
            last = now
            draw(now)
            scr.refresh()
            time.sleep(0.02)
        stats = [("Board", f"{cols}x{rows}"), ("Mines", n_mines), ("Flags used", len(flags))]
        return game_over(scr, BOARDS[level], elapsed, stats, title="CLEARED", won=True, keys="rmq",
                         key_help="r play again · m change difficulty · q back to title", note=name.lower())
    # boom: reveal the mines one by one
    sound.play("boom")
    hidden_mines = sorted(mines - flags, key=lambda m: abs(m[0] - exploded[0]) + abs(m[1] - exploded[1]))
    delay = min(0.04, 1.0 / max(1, len(hidden_mines)))
    for i in range(1, len(hidden_mines) + 1):
        draw(time.time(), show_mines=set(hidden_mines[:i]))
        scr.refresh()
        time.sleep(delay)
    draw(time.time())
    scr.refresh()
    time.sleep(0.8)
    stats = [("Time", f"{elapsed}s"), ("Field cleared", explored), ("Flags placed", len(flags))]
    return game_over(scr, BOARDS[level], None, stats, title="BOOM", keys="rmq",
                     key_help="r try again · m change difficulty · q back to title")


def main(scr):
    init_colors()
    while True:
        choice = title_screen(
            scr, "MINESWEEPER", RED, "Clear the field. The numbers count neighboring mines.",
            [("arrows / WASD / hjkl", "move"), ("space / click", "dig"), ("f / right-click", "flag → ? → clear"),
             ("dig a number", "clears around it when flagged"), ("r / q", "restart / quit")],
            options=[("Difficulty", [f"{n} {c}x{r}" for n, r, c, _ in LEVELS])],
            board_for=lambda c: BOARDS[c[0]], settings_key="minesweeper_options")
        if choice is None:
            return
        while play(scr, choice[0]) == "r":
            pass


if __name__ == "__main__":
    run(main)
