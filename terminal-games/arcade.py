#!/usr/bin/env python3
"""Terminal Arcade — a menu that launches every game in this folder."""
import curses
import random
import subprocess
import sys
import time
from pathlib import Path

import game2048
import invaders
import minesweeper
import snake
import tetris
import typing_racer
from common import (CYAN, GREEN, GREY, MAGENTA, WHITE, YELLOW, center, color, draw_logo, fill, init_colors,
                    load_data, put, run, save_data, sound)

HERE = Path(__file__).parent
GAMES = [  # (file, name, blurb, leaderboards)
    ("snake.py", "Snake", "Eat, grow, go faster. Three modes.", snake.BOARDS),
    ("tetris.py", "Tetris", "Stack blocks, clear lines, survive.", [tetris.BOARD]),
    ("invaders.py", "Space Invaders", "Alien waves, with a boss every 5th.", [invaders.BOARD]),
    ("minesweeper.py", "Minesweeper", "Clear the field. Mouse works too.", minesweeper.BOARDS),
    ("game2048.py", "2048", "Slide and merge your way to 2048.", [b for _, _, b in game2048.SIZES]),
    ("typing_racer.py", "Typing Racer", "Type the words before they escape.", list(typing_racer.BOARDS.values())),
]


class Starfield:
    LAYERS = [(3, ".", GREY), (7, "·", WHITE), (14, "*", CYAN)]  # (speed, char, color)

    def __init__(self):
        self.stars, self.size = [], (0, 0)

    def update(self, win, dt):
        h, w = win.getmaxyx()
        if (h, w) != self.size:
            self.size = (h, w)
            self.stars = [[random.uniform(0, w), random.randrange(h), *random.choice(self.LAYERS)]
                          for _ in range(h * w // 40)]
        for star in self.stars:
            star[0] -= star[2] * dt
            if star[0] < 0:
                star[0], star[1] = w - 1, random.randrange(h)

    def draw(self, win):
        for x, y, speed, ch, col in self.stars:
            put(win, y, int(x), ch, color(col, curses.A_DIM if speed < 5 else 0))


def best_line(boards):
    """The headline record for a game: its first leaderboard's top entry."""
    top = boards[0].entries()
    return f"best {boards[0].fmt(top[0]['score'])} by {top[0]['name']}" if top else "no record yet"


def mode_name(board):
    if "·" not in board.title:
        return "Best"
    part = board.title.split("·")[-1].strip().lower()
    return " ".join(w if w[0].isdigit() else w.capitalize() for w in part.split())


def stats_page(win):
    data = load_data()
    win.timeout(-1)
    win.erase()
    h, w = win.getmaxyx()
    total = sum(data["plays"].get(file, 0) for file, *_ in GAMES)
    lines = sum(len(boards) for *_, boards in GAMES)
    y = max(0, (h - lines - 6) // 2)
    draw_logo(win, y, "STATS", YELLOW, 0)
    center(win, y + 2, f"{total} game{'' if total == 1 else 's'} played", color(CYAN, curses.A_BOLD))
    y += 4
    left = max(0, (w - 72) // 2)
    for file, name, _, boards in GAMES:
        put(win, y, left + 60, f"played {data['plays'].get(file, 0)}x", color(GREY))
        for i, b in enumerate(boards):
            top = b.entries()
            put(win, y, left, name if i == 0 else "", color(YELLOW, curses.A_BOLD))
            put(win, y, left + 16, mode_name(b), color(GREY))
            record = f"{b.fmt(top[0]['score'])}  {top[0]['name']}  {top[0].get('date', '')}" if top else "—"
            put(win, y, left + 32, record, color(WHITE if top else GREY))
            y += 1
    center(win, h - 1, "press any key", color(GREY, curses.A_DIM))
    win.refresh()
    win.getch()


def menu(win, choice):
    init_colors()
    stars = Starfield()
    win.timeout(40)
    start = last = time.time()
    while True:
        now = time.time()
        stars.update(win, now - last)
        last = now
        data = load_data()
        last_played = data["settings"].get("last_played")
        h, w = win.getmaxyx()
        spacing = 3 if h >= 26 else 2
        width = min(w - 2, 70)
        left = (w - width) // 2
        height = 5 + len(GAMES) * spacing
        y = max(0, (h - height - 2) // 2)

        win.erase()
        stars.draw(win)
        fill(win, y, left, height, width)
        draw_logo(win, y, "ARCADE", MAGENTA, now - start)
        center(win, y + 2, "· terminal edition ·", color(GREY))
        for i, (file, name, blurb, boards) in enumerate(GAMES):
            row = y + 4 + i * spacing
            selected = i == choice
            put(win, row, left + 2, f"{'▶ ' if selected else '  '}{name:<15}",
                color(YELLOW if selected else WHITE, curses.A_BOLD))
            put(win, row, left + 20, blurb[: width - 22], color(WHITE if selected else GREY))
            plays = data["plays"].get(file, 0)
            info = best_line(boards) + (f" · played {plays}x" if plays else "")
            put(win, row + 1, left + 20, info[: width - 22], color(CYAN if selected else GREY, curses.A_DIM))
            if file == last_played:
                put(win, row, left + width - 8, "◆ last", color(GREEN))
        hint = f"↑↓ choose · enter play · s stats · {sound.label} · q quit"
        fill(win, y + height, (w - len(hint)) // 2 - 1, 1, len(hint) + 2)
        center(win, y + height, hint, color(GREY))
        win.refresh()

        key = win.getch()
        if key == -1:
            continue
        if key in (ord("q"), ord("Q"), 27):
            return None
        if key in (curses.KEY_UP, ord("k")):
            choice = (choice - 1) % len(GAMES)
            sound.play("move")
        elif key in (curses.KEY_DOWN, ord("j")):
            choice = (choice + 1) % len(GAMES)
            sound.play("move")
        elif key in (ord("s"), ord("S")):
            stats_page(win)
            win.timeout(40)
        elif key in (ord("v"), ord("V")):
            sound.toggle()
        elif key in (10, 13, curses.KEY_ENTER, ord(" ")):
            return choice
        elif ord("1") <= key <= ord(str(len(GAMES))):
            return key - ord("1")


def main():
    data = load_data()
    files = [g[0] for g in GAMES]
    last = data["settings"].get("last_played")
    choice = files.index(last) if last in files else 0
    while True:
        picked = []
        run(lambda scr: picked.append(menu(scr, choice)))
        if not picked or picked[0] is None:
            return
        choice = picked[0]
        file = GAMES[choice][0]
        data = load_data()
        data["plays"][file] = data["plays"].get(file, 0) + 1
        data["settings"]["last_played"] = file
        save_data(data)
        subprocess.run([sys.executable, str(HERE / file)])


if __name__ == "__main__":
    main()
