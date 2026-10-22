#!/usr/bin/env python3
"""SNAKE — eat, grow, go faster. Grab power-ups, chase gold, dodge walls."""
import curses
import random
import time
from collections import deque

from common import (ARROWS, BLUE, CYAN, GREEN, GREY, MAGENTA, QUIT_KEYS, RED, YELLOW, Board, box, color,
                    ensure_size, fmt_time, game_over, init_colors, message_box, put, run, sound, title_screen,
                    too_small)

MODES = ["Classic", "Wrap-around", "Obstacles"]
BOARDS = [Board("snake", "SNAKE · CLASSIC"), Board("snake-wrap", "SNAKE · WRAP-AROUND"),
          Board("snake-obstacles", "SNAKE · OBSTACLES")]
POWERS = {"slow": (BLUE, "Slow-mo"), "ghost": (MAGENTA, "Ghost")}
POWER_DURATION, POWER_LIFETIME, GOLD_LIFETIME = 6.0, 8.0, 5.0


def play(scr, mode):
    if not ensure_size(scr, 18, 44):
        return "q"
    h, w = scr.getmaxyx()
    rows, cols = min(h - 5, 24), min((w - 4) // 2, 36)
    need_h, need_w = rows + 5, cols * 2 + 4
    wrap = MODES[mode] == "Wrap-around"

    mid = (rows // 2, cols // 2)
    snake = deque([mid, (mid[0], mid[1] - 1), (mid[0], mid[1] - 2)])
    obstacles = set()
    if MODES[mode] == "Obstacles":
        while len(obstacles) < rows * cols // 30:
            r, c = random.randrange(rows), random.randrange(cols)
            length, horizontal = random.randint(2, 5), random.random() < 0.5
            for i in range(length):
                cell = (r, min(cols - 1, c + i)) if horizontal else (min(rows - 1, r + i), c)
                if abs(cell[0] - mid[0]) > 1:  # keep the starting lane clear
                    obstacles.add(cell)

    heading, pending = (0, 1), deque()
    grow, score, eaten = 0, 0, 0
    powerups_taken, gold_taken = 0, 0
    effects = {}       # power name -> expiry time
    power = None       # (pos, name, disappears_at)
    gold = None        # (pos, disappears_at)
    food = None
    paused = False
    start = time.time()

    def empty_cell():
        taken = set(snake) | obstacles | {food} | ({power[0]} if power else set()) | ({gold[0]} if gold else set())
        free = [(r, c) for r in range(rows) for c in range(cols) if (r, c) not in taken]
        return random.choice(free) if free else None

    food = empty_cell()

    def draw(now, shake=(0, 0), snake_attr=None, segments=None):
        h, w = scr.getmaxyx()
        top = (h - rows - 2) // 2 + 1 + shake[0]
        left = (w - cols * 2 - 2) // 2 + shake[1]
        ghost = effects.get("ghost", 0) > now
        scr.erase()
        status = f" SNAKE · {MODES[mode]}   Score {score}   Length {len(snake)} "
        put(scr, top - 1, left, status, color(GREEN, curses.A_BOLD))
        active = [f"{POWERS[n][1]} {effects[n] - now:.0f}s" for n in POWERS if effects.get(n, 0) > now]
        if active:
            put(scr, top - 1, left + len(status) + 1, "  ".join(active), color(MAGENTA, curses.A_BOLD))
        box(scr, top, left, rows + 2, cols * 2 + 2, color(MAGENTA if ghost else CYAN if wrap else GREY))
        for r in range(rows):
            put(scr, top + 1 + r, left + 1, " ·" * cols, color(GREY, curses.A_DIM))
        for r, c in obstacles:
            put(scr, top + 1 + r, left + 1 + c * 2, "▒▒", color(GREY))
        if food:
            put(scr, top + 1 + food[0], left + 1 + food[1] * 2, "██", color(RED, curses.A_BOLD))
        if power:
            blink = curses.A_BOLD if int(now * 4) % 2 else curses.A_DIM
            put(scr, top + 1 + power[0][0], left + 1 + power[0][1] * 2, "██", color(POWERS[power[1]][0], blink))
        if gold:
            urgent = gold[1] - now < 2
            blink = curses.A_BOLD if int(now * (10 if urgent else 4)) % 2 else curses.A_DIM
            put(scr, top + 1 + gold[0][0], left + 1 + gold[0][1] * 2, "◆◆", color(YELLOW, blink))
        body_attr = snake_attr or (color(CYAN, curses.A_DIM) if ghost else color(GREEN))
        for i, (r, c) in enumerate(snake):
            if segments is not None and i >= segments:
                break
            glyph = "██" if i == 0 else ("░░" if ghost else "▓▓")
            attr = snake_attr or (color(YELLOW, curses.A_BOLD) if i == 0 else body_attr)
            put(scr, top + 1 + r, left + 1 + c * 2, glyph, attr)
        x = left
        for text, col in [("██", RED), (" food ", GREY), ("◆◆", YELLOW), (" gold ", GREY), ("██", BLUE),
                          (" slow ", GREY), ("██", MAGENTA), (f" ghost · p pause · {sound.label} · q quit", GREY)]:
            put(scr, top + rows + 2, x, text, color(col))
            x += len(text)

    scr.nodelay(True)
    last_step = time.time()
    while True:
        now = time.time()
        if too_small(scr, need_h, need_w):
            if scr.getch() in QUIT_KEYS:
                return "q"
            time.sleep(0.1)
            last_step = time.time()
            continue
        key = scr.getch()
        while key != -1:
            if key in QUIT_KEYS:
                return "q"
            if key == curses.KEY_RESIZE:
                scr.clear()
            elif key in (ord("p"), ord("P"), ord(" ")):
                paused = not paused
            elif key in (ord("v"), ord("V")):
                sound.toggle()
            elif key in ARROWS and not paused and len(pending) < 3:
                pending.append(ARROWS[key])
            key = scr.getch()

        slow = effects.get("slow", 0) > now
        ghost = effects.get("ghost", 0) > now
        interval = max(0.045, 0.13 - eaten * 0.003) * (1.8 if slow else 1)

        if paused:
            last_step = now
        elif now - last_step >= interval:
            last_step = now
            while pending:
                d = pending.popleft()
                if d != (-heading[0], -heading[1]):
                    heading = d
                    break
            r, c = snake[0][0] + heading[0], snake[0][1] + heading[1]
            if not (0 <= r < rows and 0 <= c < cols):
                if not (ghost or wrap):
                    break
                r, c = r % rows, c % cols
            body = list(snake) if grow else list(snake)[:-1]
            if ((r, c) in body or (r, c) in obstacles) and not ghost:
                break
            snake.appendleft((r, c))
            if (r, c) == food:
                eaten += 1
                score += 10 + eaten // 5 * 5
                grow += 3
                sound.play("eat")
                food = empty_cell()
                if food is None:
                    break  # filled the board!
                if power is None and random.random() < 0.25:
                    power = (empty_cell(), random.choice(list(POWERS)), now + POWER_LIFETIME)
                if gold is None and random.random() < 0.12:
                    gold = (empty_cell(), now + GOLD_LIFETIME)
            if power and (r, c) == power[0]:
                effects[power[1]] = now + POWER_DURATION
                score += 25
                powerups_taken += 1
                sound.play("power")
                power = None
            if gold and (r, c) == gold[0]:
                score += 75
                grow += 5
                gold_taken += 1
                sound.play("bonus")
                gold = None
            if grow:
                grow -= 1
            else:
                snake.pop()
        if power and power[2] < now:
            power = None
        if gold and gold[1] < now:
            gold = None

        draw(now)
        if paused:
            message_box(scr, ["PAUSED", "p to resume"], color(YELLOW))
        scr.refresh()
        time.sleep(0.008)

    # ── death: shake, then the snake fades from tail to head ──
    sound.play("crash")
    played = time.time() - start
    for i in range(8):
        draw(time.time(), shake=(random.choice((-1, 0, 1)), random.choice((-2, 0, 2))),
             snake_attr=color(RED, curses.A_BOLD) if i % 2 == 0 else color(YELLOW, curses.A_BOLD))
        scr.refresh()
        time.sleep(0.045)
    length = len(snake)
    for n in range(length, -1, -max(1, length // 12)):
        draw(time.time(), snake_attr=color(RED, curses.A_DIM), segments=n)
        scr.refresh()
        time.sleep(0.03)

    stats = [("Length", length), ("Food eaten", eaten), ("Power-ups", powerups_taken),
             ("Gold", gold_taken), ("Time", fmt_time(played))]
    return game_over(scr, BOARDS[mode], score, stats, note=MODES[mode])


def main(scr):
    init_colors()
    while True:
        choice = title_screen(
            scr, "SNAKE", GREEN, "Eat, grow, go faster. Don't bite yourself.",
            [("arrows / WASD", "steer"), ("◆◆ gold", "+75, vanishes fast"), ("██ blue", "slow-mo"),
             ("██ purple", "ghost: pass through anything"), ("p / q", "pause / quit")],
            options=[("Mode", MODES)], board_for=lambda c: BOARDS[c[0]], settings_key="snake_options")
        if choice is None:
            return
        while play(scr, choice[0]) == "r":
            pass


if __name__ == "__main__":
    run(main)
