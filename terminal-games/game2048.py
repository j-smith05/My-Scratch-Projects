#!/usr/bin/env python3
"""2048 — slide the tiles, merge the numbers, reach 2048 (and keep going)."""
import curses
import random
import time

from common import (ARROWS, CYAN, GREEN, GREY, QUIT_KEYS, YELLOW, Board, box, color, ensure_size,
                    fmt_time, game_over, init_colors, message_box, put, run, sound, title_screen, too_small,
                    wait_key)

SIZES = [("Classic 4x4", 4, Board("2048", "2048 · CLASSIC")), ("Big 5x5", 5, Board("2048-big", "2048 · BIG BOARD"))]
TILE_W = 8  # 7 columns of tile + 1 column gap
# value: (256-color background, 256-color text, 8-color fallback background)
TILE_STYLES = {
    0: (239, 239, curses.COLOR_BLACK), 2: (254, 236, curses.COLOR_WHITE), 4: (223, 236, curses.COLOR_WHITE),
    8: (215, 231, curses.COLOR_YELLOW), 16: (209, 231, curses.COLOR_YELLOW), 32: (203, 231, curses.COLOR_RED),
    64: (196, 231, curses.COLOR_RED), 128: (227, 236, curses.COLOR_GREEN), 256: (221, 236, curses.COLOR_GREEN),
    512: (220, 236, curses.COLOR_CYAN), 1024: (214, 231, curses.COLOR_BLUE), 2048: (178, 231, curses.COLOR_MAGENTA),
}
BIG_STYLE = (93, 231, curses.COLOR_MAGENTA)  # anything past 2048
SLIDE_FRAMES = 5


def init_tile_colors():
    rich = curses.COLORS >= 256
    for i, value in enumerate(list(TILE_STYLES) + ["big"]):
        bg, fg, basic = TILE_STYLES.get(value, BIG_STYLE)
        if rich:
            curses.init_pair(20 + i, fg, bg)
        else:
            curses.init_pair(20 + i, curses.COLOR_BLACK if basic == curses.COLOR_WHITE else curses.COLOR_WHITE, basic)


def tile_attr(value):
    keys = list(TILE_STYLES)
    idx = keys.index(value) if value in TILE_STYLES else len(keys)
    return curses.color_pair(20 + idx) | (curses.A_BOLD if value else 0)


def slide_line(line):
    """Slides one line toward index 0. Returns (new_line, points, merged_indices, moves)
    where moves is a list of (from_index, to_index, value_before_merge)."""
    tiles = [(i, v) for i, v in enumerate(line) if v]
    out, points, merged, moves = [], 0, [], []
    k = 0
    while k < len(tiles):
        i, v = tiles[k]
        dest = len(out)
        if k + 1 < len(tiles) and tiles[k + 1][1] == v:
            out.append(v * 2)
            points += v * 2
            merged.append(dest)
            moves += [(i, dest, v), (tiles[k + 1][0], dest, v)]
            k += 2
        else:
            out.append(v)
            moves.append((i, dest, v))
            k += 1
    return out + [0] * (len(line) - len(out)), points, merged, moves


def move(grid, direction):
    """direction is (dr, dc). Returns (new_grid, points, merged_cells, moves)."""
    n = len(grid)
    new = [[0] * n for _ in range(n)]
    points, merged_cells, all_moves = 0, set(), []
    for k in range(n):
        # Coordinates of line k, ordered from the edge the tiles slide toward.
        if direction == (0, -1):
            coords = [(k, i) for i in range(n)]
        elif direction == (0, 1):
            coords = [(k, n - 1 - i) for i in range(n)]
        elif direction == (-1, 0):
            coords = [(i, k) for i in range(n)]
        else:
            coords = [(n - 1 - i, k) for i in range(n)]
        line, pts, merged, moves = slide_line([grid[r][c] for r, c in coords])
        points += pts
        for (r, c), v in zip(coords, line):
            new[r][c] = v
        merged_cells.update(coords[i] for i in merged)
        all_moves += [(coords[a], coords[b], v) for a, b, v in moves]
    return new, points, merged_cells, all_moves


def spawn(grid):
    n = len(grid)
    empty = [(r, c) for r in range(n) for c in range(n) if not grid[r][c]]
    if not empty:
        return None
    r, c = random.choice(empty)
    grid[r][c] = 4 if random.random() < 0.1 else 2
    return (r, c)


def can_move(grid):
    return any(move(grid, d)[0] != grid for d in ((0, 1), (0, -1), (1, 0), (-1, 0)))


def play(scr, size):
    label, n, board = SIZES[size]
    if not ensure_size(scr, n * 3 + 5, n * TILE_W + 5):
        return "q"
    th = 4 if scr.getmaxyx()[0] >= n * 4 + 5 else 3   # tile height incl. 1-row gap
    need_h, need_w = n * th + 5, n * TILE_W + 5

    grid = [[0] * n for _ in range(n)]
    spawn(grid)
    spawn(grid)
    score, history, won_shown = 0, [], False
    moves_made, merges, undos = 0, 0, 0
    gain, gain_until = 0, 0.0
    start = time.time()

    def layout():
        h, w = scr.getmaxyx()
        y0 = (h - (n * th + 5)) // 2
        return y0, (w - (n * TILE_W + 3)) // 2

    def tile_pos(r, c):
        y0, bx = layout()
        return y0 + 3 + r * th, bx + 2 + c * TILE_W

    def draw_tile(y, x, value, pop=False, small=False):
        attr = tile_attr(value)
        content_h, width = th - 1, TILE_W - 1
        text = str(value) if value else ""
        mid = (content_h - 1) // 2
        if small:
            put(scr, y + mid, x + 2, text.center(3), attr)
            return
        if pop:
            x, width = x - 1, width + 2
        for dy in range(content_h):
            put(scr, y + dy, x, text.center(width) if dy == mid else " " * width, attr)

    def draw_frame(now):
        y0, bx = layout()
        scr.erase()
        put(scr, y0, bx, "2048", color(YELLOW, curses.A_BOLD))
        put(scr, y0, bx + 6, f"SCORE {score}", color(CYAN, curses.A_BOLD))
        if gain_until > now:
            put(scr, y0, bx + 13 + len(str(score)), f"+{gain}", color(GREEN, curses.A_BOLD))
        best = f"BEST {max(board.best() or 0, score)}"
        put(scr, y0, bx + n * TILE_W + 3 - len(best), best, color(GREY, curses.A_BOLD))
        box(scr, y0 + 1, bx, n * th + 3, n * TILE_W + 3, color(GREY))
        for r in range(n):
            for c in range(n):
                draw_tile(*tile_pos(r, c), 0)
        put(scr, y0 + n * th + 4, bx, f"arrows/WASD slide · u undo · r restart · {sound.label} · q end",
            color(GREY, curses.A_DIM))

    def draw_grid(now, pop=(), small=()):
        draw_frame(now)
        for r in range(n):
            for c in range(n):
                if grid[r][c]:
                    draw_tile(*tile_pos(r, c), grid[r][c], pop=(r, c) in pop, small=(r, c) in small)

    def animate_slide(moves):
        for f in range(1, SLIDE_FRAMES + 1):
            t = 1 - (1 - f / SLIDE_FRAMES) ** 2  # ease out
            draw_frame(time.time())
            for (r0, c0), (r1, c1), v in moves:
                y0, x0 = tile_pos(r0, c0)
                y1, x1 = tile_pos(r1, c1)
                draw_tile(round(y0 + (y1 - y0) * t), round(x0 + (x1 - x0) * t), v)
            scr.refresh()
            time.sleep(0.014)

    def confirm(question):
        draw_grid(time.time())
        message_box(scr, [question, "", "y: yes   any other key: keep playing"], color(YELLOW))
        scr.refresh()
        scr.timeout(-1)
        return scr.getch() in (ord("y"), ord("Y"))

    def finish(title="GAME OVER"):
        biggest = max(max(row) for row in grid)
        stats = [("Biggest tile", biggest), ("Moves", moves_made), ("Merges", merges), ("Undos", undos),
                 ("Board", label), ("Time", fmt_time(time.time() - start))]
        return game_over(scr, board, score, stats, title=title, note=f"tile {biggest}", won=biggest >= 2048)

    fresh = set()
    while True:
        now = time.time()
        scr.timeout(150)
        if too_small(scr, need_h, need_w):
            if scr.getch() in QUIT_KEYS:
                return "q"
            continue
        draw_grid(now)
        biggest = max(max(row) for row in grid)
        if biggest >= 2048 and not won_shown:
            won_shown = True
            sound.play("win")
            message_box(scr, ["★ YOU REACHED 2048! ★", "", "c: keep going   q: finish here"], color(YELLOW))
            scr.refresh()
            if wait_key(scr, "cq") == "q":
                return finish("YOU WIN")
            continue
        if not can_move(grid):
            sound.play("lose")
            message_box(scr, ["NO MOVES LEFT", "", "u: undo   enter: finish"], color(YELLOW))
            scr.refresh()
            if wait_key(scr, "u\n") == "\n":
                return finish()
            key = ord("u")
        else:
            scr.refresh()
            key = scr.getch()

        if key == -1:
            continue
        if key == curses.KEY_RESIZE:
            scr.clear()
        elif key in QUIT_KEYS:
            if confirm("End this game?"):
                return finish()
        elif key in (ord("r"), ord("R")):
            if confirm("Restart? This game won't be scored."):
                return "r"
        elif key in (ord("v"), ord("V")):
            sound.toggle()
        elif key in (ord("u"), ord("U")):
            if history:
                grid, score = history.pop()
                undos += 1
                sound.play("undo")
        elif key in ARROWS:
            new, points, merged_cells, moves = move(grid, ARROWS[key])
            if new == grid:
                continue
            history = (history + [([row[:] for row in grid], score)])[-20:]
            animate_slide(moves)
            grid, score = new, score + points
            moves_made += 1
            merges += len(merged_cells)
            if points:
                gain, gain_until = points, time.time() + 0.6
                sound.play("bigmerge" if max(grid[r][c] for r, c in merged_cells) >= 128 else "merge")
            pos = spawn(grid)
            fresh = {pos} if pos else set()
            draw_grid(time.time(), pop=merged_cells, small=fresh)
            scr.refresh()
            time.sleep(0.06)


def main(scr):
    init_colors()
    init_tile_colors()
    while True:
        choice = title_screen(
            scr, "2048", YELLOW, "Slide the tiles. Merge the numbers. Reach 2048.",
            [("arrows / WASD", "slide every tile"), ("u", "undo (up to 20 moves)"), ("r", "restart"),
             ("q", "end the game and score it")],
            options=[("Board", [s[0] for s in SIZES])], board_for=lambda c: SIZES[c[0]][2],
            settings_key="2048_options")
        if choice is None:
            return
        while play(scr, choice[0]) == "r":
            pass


if __name__ == "__main__":
    run(main)
