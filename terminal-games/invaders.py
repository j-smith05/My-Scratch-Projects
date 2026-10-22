#!/usr/bin/env python3
"""SPACE INVADERS — hold the line against waves of ASCII aliens (and their bosses)."""
import curses
import random
import time

from common import (CYAN, GREEN, GREY, MAGENTA, QUIT_KEYS, RED, WHITE, YELLOW, Board, Particles, box,
                    color, ensure_size, fmt_time, game_over, init_colors, message_box, put, run, sound,
                    title_screen, too_small)

W = 64
ALIEN_COLS, ALIEN_ROWS, SPACING = 9, 5, 6
ALIEN_TYPES = [  # (two animation frames, color, points) for each row, top to bottom
    (("/O\\", "\\O/"), MAGENTA, 30),
    (("{@}", "}@{"), CYAN, 20),
    (("{@}", "}@{"), CYAN, 20),
    (("<=>", ">=<"), GREEN, 10),
    (("<=>", ">=<"), GREEN, 10),
]
BOSS_FRAMES = (
    ["  ▄▄██████▄▄  ", "▄█▀●▀████▀●▀█▄", "▀▀█▄▀▀▀▀▀▀▄█▀▀"],
    ["  ▄▄██████▄▄  ", "▄█▀●▀████▀●▀█▄", " ▀▄▀▀▀▀▀▀▀▀▄▀ "],
)
BOSS_W = len(BOSS_FRAMES[0][0])
SHIELD = ["▄███▄", "█████", "██ ██"]
DAMAGE = "█▓▒░"
BULLET_SPEED, BOMB_SPEED, UFO_SPEED, GLIDE_SPEED = 40.0, 12.0, 14.0, 30.0
MAX_LIVES = 5
BOARD = Board("invaders", "SPACE INVADERS")


def play(scr):
    if not ensure_size(scr, 24, W + 2):
        return "q"
    H = min(scr.getmaxyx()[0] - 4, 30)
    PY, SY = H - 2, H - 6  # player row, shield top row
    need_h, need_w = H + 4, W + 2

    score, lives, wave = 0, 3, 1
    pxf = W / 2 - 1.0
    move_dir, move_until, last_press = 0, 0.0, {-1: 0.0, 1: 0.0}
    shots = hits = kills = bosses = 0
    start = time.time()
    particles = Particles()
    popups = []  # (y, x, text, color, until)
    s = {}       # per-wave state

    def new_wave():
        boss_wave = wave % 5 == 0
        s.clear()
        s.update(
            alive=[[not boss_wave] * ALIEN_COLS for _ in range(ALIEN_ROWS)],
            fx=4, fy=3 + min(wave - 1, 4), fdir=1, frame=0, step_acc=0.0,
            bullet=None, bullet_acc=0.0, bombs=[], ufo=None, ufo_timer=random.uniform(12, 25),
            shields={}, boss=None, quit=False,
        )
        if boss_wave:
            hp = 30 + 15 * (wave // 5 - 1)
            s["boss"] = {"x": W / 2 - BOSS_W / 2, "y": 3, "dir": 1, "hp": hp, "max": hp,
                         "fire": 2.0, "flash": 0.0, "frame": 0, "anim": 0.0}
        for k in range(4):
            sx = int(W * (k + 1) / 5) - 2
            for r, row in enumerate(SHIELD):
                for c, ch in enumerate(row):
                    if ch != " ":
                        s["shields"][(SY + r, sx + c)] = 0 if ch == "█" else -1

    def origin():
        h, w = scr.getmaxyx()
        return (h - H - 4) // 2 + 1, (w - W - 2) // 2

    def at(y, x, text, attr):
        oy, ox = origin()
        put(scr, oy + 1 + y, ox + 1 + x, text, attr)

    def alive_cells():
        return [(i, j) for j in range(ALIEN_ROWS) for i in range(ALIEN_COLS) if s["alive"][j][i]]

    def hit_shield(y, x):
        sh = s["shields"]
        if (y, x) not in sh:
            return False
        sh[(y, x)] = sh[(y, x)] + 1 if sh[(y, x)] >= 0 else 1
        if sh[(y, x)] >= len(DAMAGE):
            del sh[(y, x)]
        return True

    def draw(now, player=True):
        oy, ox = origin()
        px = int(round(pxf))
        scr.erase()
        put(scr, oy - 1, ox, f" SCORE {score:<7} HI {max(BOARD.best() or 0, score):<7} WAVE {wave}",
            color(CYAN, curses.A_BOLD))
        put(scr, oy - 1, ox + W + 1 - MAX_LIVES * 2, ("♥ " * lives).rjust(MAX_LIVES * 2), color(RED, curses.A_BOLD))
        box(scr, oy, ox, H + 2, W + 2, color(GREY), "SPACE INVADERS")
        for (y, x), dmg in s["shields"].items():
            at(y, x, "▄" if dmg == -1 else DAMAGE[dmg], color(GREEN))
        for i, j in alive_cells():
            frames, col, _ = ALIEN_TYPES[j]
            at(s["fy"] + j * 2, s["fx"] + i * SPACING, frames[s["frame"]], color(col, curses.A_BOLD))
        boss = s["boss"]
        if boss:
            attr = color(WHITE, curses.A_BOLD) if boss["flash"] > now else color(RED, curses.A_BOLD)
            for r, line in enumerate(BOSS_FRAMES[boss["frame"]]):
                for c, ch in enumerate(line):
                    if ch != " ":
                        at(boss["y"] + r, int(boss["x"]) + c, ch, attr)
            filled = round(20 * boss["hp"] / boss["max"])
            bar = f"BOSS [{'█' * filled}{'░' * (20 - filled)}]"
            at(1, (W - len(bar)) // 2, bar, color(RED, curses.A_BOLD))
        if s["ufo"]:
            at(1, int(s["ufo"][0]), "<=O=>", color(RED, curses.A_BOLD))
        if s["bullet"]:
            at(s["bullet"][0], s["bullet"][1], "|", color(YELLOW, curses.A_BOLD))
        for b in s["bombs"]:
            at(int(b[0]), b[1], "¦" if int(b[0]) % 2 else "!", color(RED, curses.A_BOLD))
        if player:
            at(PY, px, "/^\\", color(GREEN, curses.A_BOLD))
        at(H - 1, 0, "▔" * W, color(GREEN, curses.A_DIM))
        particles.draw(scr, oy + 1, ox + 1)
        for y, x, text, col, until in popups:
            if until > now:
                at(y, x, text, color(col, curses.A_BOLD))
        put(scr, oy + H + 2, ox, f" ←→ move (hold to glide) · space fire · p pause · {sound.label} · q quit",
            color(GREY, curses.A_DIM))

    def animate(seconds, player=True):
        """Lets particles play out for a moment with the action frozen."""
        end = time.time() + seconds
        last = time.time()
        while time.time() < end:
            now = time.time()
            particles.update(now - last)
            last = now
            draw(now, player)
            scr.refresh()
            time.sleep(0.016)

    def banner(text, seconds):
        draw(time.time())
        message_box(scr, [text], color(YELLOW))
        scr.refresh()
        time.sleep(seconds)
        while (k := scr.getch()) != -1:  # drop keys pressed during the banner, except quit
            if k in QUIT_KEYS:
                s["quit"] = True

    new_wave()
    scr.nodelay(True)
    banner("WAVE 1", 1.0)
    paused = False
    last = time.time()

    while True:
        now = time.time()
        dt, last = min(now - last, 0.1), now
        if too_small(scr, need_h, need_w):
            if scr.getch() in QUIT_KEYS:
                return "q"
            time.sleep(0.1)
            last = time.time()
            continue
        if s.get("quit"):
            return "q"
        key = scr.getch()
        while key != -1:
            if key in QUIT_KEYS:
                return "q"
            if key == curses.KEY_RESIZE:
                scr.clear()
            elif key in (ord("p"), ord("P")):
                paused = not paused
            elif key in (ord("v"), ord("V")):
                sound.toggle()
            elif not paused:
                d = -1 if key in (curses.KEY_LEFT, ord("a"), ord("A")) else \
                    1 if key in (curses.KEY_RIGHT, ord("d"), ord("D")) else 0
                if d:
                    if now - last_press[d] < 0.6:     # key auto-repeat: glide smoothly
                        move_dir, move_until = d, now + 0.15
                    else:                             # a single tap: precise nudge
                        pxf += 2 * d
                        move_dir = 0
                    last_press[d], last_press[-d] = now, 0.0
                elif key in (ord(" "), curses.KEY_UP, ord("w"), ord("W")) and s["bullet"] is None:
                    s["bullet"] = [PY - 1, int(round(pxf)) + 1]
                    s["bullet_acc"] = 0.0
                    shots += 1
                    sound.play("shoot")
            key = scr.getch()
        if paused:
            draw(now)
            message_box(scr, ["PAUSED", "p to resume"], color(YELLOW))
            scr.refresh()
            time.sleep(0.03)
            last = time.time()
            continue

        if move_dir and now < move_until:
            pxf += move_dir * GLIDE_SPEED * dt
        else:
            move_dir = 0
        pxf = max(0.0, min(W - 3.0, pxf))
        px = int(round(pxf))
        particles.update(dt)
        popups[:] = [p for p in popups if p[4] > now]
        cells = alive_cells()
        boss = s["boss"]
        invaded = False

        # ── alien formation ──
        if cells:
            total = ALIEN_COLS * ALIEN_ROWS
            step_interval = max(0.025, (0.03 + 0.6 * len(cells) / total) * 0.88 ** (wave - 1))
            s["step_acc"] += dt
            if s["step_acc"] >= step_interval:
                s["step_acc"] = 0.0
                s["frame"] ^= 1
                xs = [s["fx"] + i * SPACING for i, _ in cells]
                d = s["fdir"]
                if (d > 0 and max(xs) + 3 + d > W) or (d < 0 and min(xs) + d < 0):
                    s["fy"] += 1
                    s["fdir"] = -d
                else:
                    s["fx"] += d
                for i, j in cells:  # aliens chew through shields they touch
                    ay, ax = s["fy"] + j * 2, s["fx"] + i * SPACING
                    for x in range(ax, ax + 3):
                        s["shields"].pop((ay, x), None)
                invaded = max(s["fy"] + j * 2 for _, j in cells) >= PY
            if random.random() < (0.9 + 0.25 * wave) * dt and len(s["bombs"]) < 3 + wave:
                col = random.choice(sorted({i for i, _ in cells}))
                j = max(j for i, j in cells if i == col)
                s["bombs"].append([float(s["fy"] + j * 2 + 1), s["fx"] + col * SPACING + 1])

        # ── boss ──
        if boss:
            boss["x"] += boss["dir"] * (8 + wave * 0.6) * dt
            if boss["x"] <= 0 or boss["x"] >= W - BOSS_W:
                boss["x"] = max(0.0, min(W - BOSS_W, boss["x"]))
                boss["dir"] *= -1
            boss["anim"] += dt
            if boss["anim"] > 0.3:
                boss["anim"], boss["frame"] = 0.0, boss["frame"] ^ 1
            boss["fire"] -= dt
            if boss["fire"] <= 0:
                bx = int(boss["x"])
                for off in (2, BOSS_W // 2, BOSS_W - 3):
                    s["bombs"].append([float(boss["y"] + 3), bx + off])
                boss["fire"] = random.uniform(0.9, 1.6) * max(0.5, 1 - wave * 0.03)

        # ── bombs ──
        player_hit = False
        for b in s["bombs"][:]:
            old = int(b[0])
            b[0] += BOMB_SPEED * dt
            for y in range(old + 1, int(b[0]) + 1):
                if hit_shield(y, b[1]) or y >= H - 1:
                    s["bombs"].remove(b)
                    break
                if y == PY and px <= b[1] < px + 3:
                    s["bombs"].remove(b)
                    player_hit = True
                    break

        # ── player bullet ──
        bullet = s["bullet"]
        if bullet:
            s["bullet_acc"] += dt * BULLET_SPEED
            while bullet and s["bullet_acc"] >= 1:
                s["bullet_acc"] -= 1
                bullet[0] -= 1
                by, bx = bullet
                if by < 1 or hit_shield(by, bx):
                    bullet = None
                    break
                hit = next(((i, j) for i, j in cells if s["fy"] + j * 2 == by
                            and s["fx"] + i * SPACING <= bx < s["fx"] + i * SPACING + 3), None)
                if hit:
                    i, j = hit
                    s["alive"][j][i] = False
                    cells.remove(hit)
                    pts = ALIEN_TYPES[j][2]
                    score += pts
                    hits += 1
                    kills += 1
                    ax = s["fx"] + i * SPACING
                    particles.burst(by, ax + 1, 9, colors=(ALIEN_TYPES[j][1], YELLOW, WHITE))
                    popups.append((by, ax, f"+{pts}", YELLOW, now + 0.4))
                    sound.play("kill")
                    bullet = None
                    break
                if boss and boss["y"] <= by < boss["y"] + 3 and int(boss["x"]) <= bx < int(boss["x"]) + BOSS_W \
                        and BOSS_FRAMES[boss["frame"]][by - boss["y"]][bx - int(boss["x"])] != " ":
                    boss["hp"] -= 1
                    boss["flash"] = now + 0.06
                    hits += 1
                    score += 5
                    particles.burst(by, bx, 5, colors=(RED, YELLOW))
                    sound.play("kill")
                    bullet = None
                    if boss["hp"] <= 0:
                        bonus = 1000 * (wave // 5)
                        score += bonus
                        bosses += 1
                        cx, cy = int(boss["x"]) + BOSS_W // 2, boss["y"] + 1
                        for _ in range(3):
                            particles.burst(cy, cx, 25, colors=(RED, YELLOW, WHITE, MAGENTA), speed=(6, 22),
                                            life=(0.4, 1.0))
                        popups.append((cy, cx - 3, f"+{bonus}", YELLOW, now + 1.5))
                        if lives < MAX_LIVES:
                            lives += 1
                            popups.append((cy + 2, cx - 3, "+1 LIFE", GREEN, now + 1.5))
                        s["boss"] = boss = None
                        sound.play("bossdown")
                    break
                ufo = s["ufo"]
                if ufo and by == 1 and int(ufo[0]) <= bx < int(ufo[0]) + 5:
                    score += ufo[2]
                    hits += 1
                    particles.burst(1, int(ufo[0]) + 2, 14, colors=(RED, YELLOW))
                    popups.append((1, int(ufo[0]), f"+{ufo[2]}", YELLOW, now + 0.9))
                    sound.play("ufo")
                    s["ufo"] = None
                    bullet = None
                    break
                bomb = next((b for b in s["bombs"] if b[1] == bx and abs(int(b[0]) - by) <= 1), None)
                if bomb:
                    s["bombs"].remove(bomb)
                    particles.burst(by, bx, 4, colors=(YELLOW,))
                    bullet = None
                    break
            s["bullet"] = bullet

        # ── mystery ship (not during boss fights) ──
        if not s["boss"] and cells:
            s["ufo_timer"] -= dt
            if s["ufo"] is None and s["ufo_timer"] <= 0:
                going_right = random.random() < 0.5
                s["ufo"] = [0.0 if going_right else W - 5.0, 1 if going_right else -1,
                            random.choice([50, 100, 150, 300])]
                s["ufo_timer"] = random.uniform(15, 30)
            if s["ufo"]:
                s["ufo"][0] += s["ufo"][1] * UFO_SPEED * dt
                if not -1 <= s["ufo"][0] <= W - 4:
                    s["ufo"] = None

        if invaded:
            lives = 0
            player_hit = True
        if player_hit:
            lives = max(0, lives - 1)
            sound.play("hit")
            particles.burst(PY, px + 1, 30, colors=(RED, YELLOW, WHITE), speed=(4, 16), life=(0.3, 0.9))
            animate(0.8, player=False)
            s["bombs"].clear()
            if lives <= 0:
                break
            banner(f"{lives} {'LIFE' if lives == 1 else 'LIVES'} LEFT", 0.9)
            last = time.time()
        if not cells and not s["boss"]:
            if wave % 5 == 0:
                animate(1.2)
            wave += 1
            score += 100 * (wave - 1)
            banner(f"WAVE {wave - 1} CLEARED!  +{100 * (wave - 1)}", 1.2)
            new_wave()
            banner("⚠ BOSS WAVE ⚠" if wave % 5 == 0 else f"WAVE {wave}", 1.0)
            last = time.time()

        draw(now)
        scr.refresh()
        time.sleep(0.012)

    accuracy = f"{100 * hits / shots:.0f}%" if shots else "—"
    stats = [("Waves cleared", wave - 1), ("Aliens destroyed", kills), ("Bosses defeated", bosses),
             ("Accuracy", accuracy), ("Shots fired", shots), ("Time", fmt_time(time.time() - start))]
    return game_over(scr, BOARD, score, stats, note=f"wave {wave}")


def main(scr):
    init_colors()
    while True:
        choice = title_screen(
            scr, "INVADERS", CYAN, "Hold the line. A boss arrives every 5th wave.",
            [("← → / a d", "move (hold to glide)"), ("space / ↑", "fire"), ("/O\\ {@} <=>", "30 / 20 / 10 points"),
             ("<=O=>", "mystery ship, 50-300"), ("boss", "1000+ points and an extra life"),
             ("p / q", "pause / quit")],
            board_for=lambda c: BOARD)
        if choice is None:
            return
        while play(scr) == "r":
            pass


if __name__ == "__main__":
    run(main)
