#!/usr/bin/env python3
"""TYPING RACER — words race across the screen. Type them before they escape."""
import curses
import random
import time

from common import (CYAN, GREEN, GREY, MAGENTA, RED, WHITE, YELLOW, Board, Particles, box, center, color,
                    ensure_size, fmt_time, game_over, init_colors, message_box, put, run, sound, title_screen,
                    too_small)

PACKS = {
    "Common": """
        the and for are but not you all any can had her was one our out day get has him his how man new now
        old see two way who boy did its let put say she too use cat dog sun run fun big red hot cold fast slow
        jump time year work back call hand high keep last long make most much need open over part play same
        show side take tell turn want well word about after again below could every first found great house
        large learn never other place plant point right small sound spell still study their there these thing
        think three water where which while world write years apple brain cloud dream earth flame ghost heart
        light magic night ocean quest river space storm tiger vivid arrow blaze candy dance frost giant honey
        lemon mango olive piano queen sugar toast amazing balance captain fantasy gravity horizon journey
        kingdom machine rainbow science thunder adventure butterfly champion firework hurricane invisible
        lightning marathon paradise question satellite telescope universe""",
    "Programming": """
        code byte loop bash java ruby rust bug git diff push pull fork merge list dict set map int bool char
        void null true false class array stack queue tree node graph hash cache token parse query index async
        await yield return break while print input output debug build deploy commit branch rebase lambda
        python script server client socket thread binary kernel memory pointer compile runtime variable
        function method object module package library terminal keyboard monitor compiler algorithm recursion
        iterator database framework interface exception refactor container javascript typescript inheritance
        polymorphism encapsulation dependency""",
    "Animals": """
        ant bat cat cow dog elk fox owl pig rat yak bear bird crab deer duck frog goat hawk lion mole mule seal
        swan toad wolf worm bison camel eagle gecko horse hyena koala lemur llama moose mouse otter panda
        rhino shark sheep skunk sloth snake squid tiger whale zebra alpaca beaver badger cheetah dolphin donkey
        ferret gerbil gibbon iguana jaguar lizard monkey ocelot parrot penguin rabbit raccoon salmon toucan
        turtle walrus wombat buffalo chimpanzee crocodile flamingo hedgehog kangaroo leopard lobster mongoose
        octopus ostrich panther pelican platypus porcupine reindeer scorpion squirrel tortoise vulture
        armadillo butterfly chameleon dragonfly salamander""",
    "Hard words": """
        rhythm psyche quartz zephyr sphinx jinx knack gnome wreath crypt fjord glyph nymph lymph xylophone
        onomatopoeia bureaucracy conscience entrepreneur fluorescent guarantee hierarchy idiosyncrasy
        juxtaposition kaleidoscope labyrinth mischievous necessary occurrence questionnaire rhetoric
        surveillance threshold unanimous vacuum worcestershire acquiesce bourgeois cacophony definitely
        embarrass foreign gauge harass indict liaison maneuver millennium noticeable pharaoh playwright
        privilege receive rendezvous silhouette sovereign subtle synonym twelfth weird yacht zucchini""",
}
PACK_NAMES = list(PACKS)
MODES = ["Classic", "Practice 60s"]
BOARDS = {"Classic": Board("typing", "TYPING RACER · CLASSIC"),
          "Practice 60s": Board("typing-practice", "TYPING RACER · 60s PRACTICE", fmt=lambda s: f"{s} wpm",
                                label="Speed")}
LIVES, PRACTICE_SECONDS = 3, 60


def play(scr, mode, pack):
    if not ensure_size(scr, 20, 60):
        return "q"
    practice = MODES[mode] == "Practice 60s"
    words_pool = sorted(set(PACKS[PACK_NAMES[pack]].split()), key=len)
    board = BOARDS[MODES[mode]]

    words = []  # dicts: text, x (float), lane
    typed = ""
    score, lives, streak, best_streak, words_done, missed = 0, LIVES, 0, 0, 0, 0
    correct_keys, total_keys = 0, 0
    error_flash = 0.0
    lasers = []      # (y0, x0, y1, x1, until)
    callouts = []    # (text, color, until)
    particles = Particles()
    spawn_timer, paused = 0.0, False

    for n in ("3", "2", "1", "GO!"):
        h, w = scr.getmaxyx()
        scr.erase()
        center(scr, h // 2 - 3, f"T Y P I N G   R A C E R  ·  {MODES[mode]}", color(CYAN, curses.A_BOLD))
        center(scr, h // 2, n, color(YELLOW if n != "GO!" else GREEN, curses.A_BOLD))
        center(scr, h // 2 + 2, f"{PACK_NAMES[pack]} words · type them before they reach the right edge",
               color(GREY))
        scr.refresh()
        sound.play("start" if n == "GO!" else "select")
        time.sleep(0.6)

    scr.nodelay(True)
    start = last = time.time()
    paused_total = 0.0
    while True:
        now = time.time()
        dt, last = min(now - last, 0.1), now
        h, w = scr.getmaxyx()
        if too_small(scr, 20, 60):
            if scr.getch() == 27:
                return "q"
            time.sleep(0.1)
            paused_total += time.time() - now
            last = time.time()
            continue
        lanes = list(range(3, h - 5))
        play_time = max(1.0, now - start - paused_total)
        if practice and play_time >= PRACTICE_SECONDS:
            break
        level = 1 + words_done // 10
        speed = 4.5 + level * 1.0                     # columns per second
        spawn_every = max(0.55, 2.0 - level * 0.15)   # seconds between words
        input_y, input_x = h - 3, 4

        # ── input ──
        key = scr.getch()
        while key != -1:
            if key == curses.KEY_RESIZE:
                scr.clear()
            elif key == 27:  # Esc
                paused = not paused
            elif paused:
                if key in (ord("q"), ord("Q")):
                    return "q"
                if key in (ord("v"), ord("V")):
                    sound.toggle()
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                typed = typed[:-1]
            elif key in (21, 23):  # ctrl-u / ctrl-w clear
                typed = ""
            elif 32 < key < 127:
                ch = chr(key).lower()
                total_keys += 1
                candidate = typed + ch
                if any(wd["text"].startswith(candidate) for wd in words):
                    typed = candidate
                    correct_keys += 1
                    done = [wd for wd in words if wd["text"] == typed]
                    if done:
                        target = max(done, key=lambda wd: wd["x"])  # the closest to escaping
                        words.remove(target)
                        streak += 1
                        best_streak = max(best_streak, streak)
                        words_done += 1
                        score += len(target["text"]) * 10 * (1 + streak // 5)
                        ty, tx = target["lane"], int(target["x"]) + len(target["text"]) // 2
                        lasers.append((input_y, input_x + len(typed), ty, tx, now + 0.15))
                        particles.burst(ty, tx, 12, colors=(GREEN, YELLOW, CYAN, WHITE))
                        if streak % 5 == 0:
                            callouts.append((f"x{1 + streak // 5} COMBO!", MAGENTA, now + 1.2))
                            sound.play("combo")
                        else:
                            sound.play("zap")
                        typed = ""
                else:
                    streak = 0
                    error_flash = now + 0.15
                    sound.play("error")
            key = scr.getch()
        if paused:
            paused_total += dt
            dt = 0

        # ── world ──
        spawn_timer -= dt
        if spawn_timer <= 0 and not paused:
            spawn_timer = spawn_every
            max_len = 4 + level
            on_screen = {x["text"] for x in words}
            pool = [wd for wd in words_pool if len(wd) <= max_len and wd not in on_screen] or \
                [wd for wd in words_pool if wd not in on_screen]
            free_lanes = [y for y in lanes if all(x["lane"] != y or x["x"] > 12 for x in words)]
            if pool and free_lanes:
                text = random.choice(pool)
                words.append({"text": text, "x": float(-len(text)), "lane": random.choice(free_lanes)})
        for wd in words[:]:
            wd["lane"] = min(wd["lane"], lanes[-1])  # keep words on screen after a resize
            wd["x"] += speed * dt
            if wd["x"] + len(wd["text"]) >= w - 2:
                words.remove(wd)
                missed += 1
                streak = 0
                error_flash = now + 0.3
                particles.burst(wd["lane"], w - 3, 8, colors=(RED,), angle=(90, 270))
                sound.play("miss")
                if not practice:
                    lives -= 1
                if typed and not any(x["text"].startswith(typed) for x in words):
                    typed = ""
        if lives <= 0:
            break
        particles.update(dt)
        lasers[:] = [l for l in lasers if l[4] > now]
        callouts[:] = [c for c in callouts if c[2] > now]

        # ── draw ──
        scr.erase()
        wpm = (correct_keys / 5) / (play_time / 60)
        acc = 100 * correct_keys / total_keys if total_keys else 100
        if practice:
            hud = f" PRACTICE · {max(0, PRACTICE_SECONDS - play_time):4.1f}s left   WPM {wpm:.0f}   ACC {acc:.0f}%   WORDS {words_done}"
        else:
            hud = f" SCORE {score}   WPM {wpm:.0f}   ACC {acc:.0f}%   STREAK {streak}   LVL {level}"
        put(scr, 0, 0, hud, color(CYAN, curses.A_BOLD))
        if not practice:
            put(scr, 0, w - LIVES * 2 - 1, "♥ " * lives + "♡ " * (LIVES - lives), color(RED, curses.A_BOLD))
        else:
            filled = int((w - 2) * min(1.0, play_time / PRACTICE_SECONDS))
            put(scr, 1, 0, "━" * filled, color(GREEN, curses.A_BOLD))
        put(scr, 1, 0 if not practice else int((w - 2) * min(1.0, play_time / PRACTICE_SECONDS)),
            "─" * w, color(GREY, curses.A_DIM))
        for y in lanes:
            put(scr, y, w - 2, "▐", color(RED, curses.A_DIM))
        for y0, x0, y1, x1, until in lasers:
            steps = max(abs(y1 - y0), abs(x1 - x0), 1)
            for i in range(0, steps, 2):
                put(scr, round(y0 + (y1 - y0) * i / steps), round(x0 + (x1 - x0) * i / steps), "•",
                    color(CYAN if i % 4 else MAGENTA, curses.A_BOLD))
        for wd in words:
            x, text = int(wd["x"]), wd["text"]
            danger = (wd["x"] + len(text)) / (w - 2)
            base = color(RED, curses.A_BOLD) if danger > 0.8 else color(YELLOW) if danger > 0.6 else color(WHITE)
            if typed and text.startswith(typed):
                put(scr, wd["lane"], x, typed, color(GREEN, curses.A_BOLD | curses.A_UNDERLINE))
                put(scr, wd["lane"], x + len(typed), text[len(typed):], base)
            else:
                put(scr, wd["lane"], x, text, base)
        particles.draw(scr)
        for i, (text, col, _) in enumerate(callouts[-2:]):
            center(scr, 3 + i, f" {text} ", color(col, curses.A_BOLD | curses.A_REVERSE))
        flash = error_flash > now
        box(scr, h - 4, 0, 3, w, color(RED if flash else MAGENTA))
        put(scr, input_y, 2, "› " + typed + "█", color(RED if flash else GREEN, curses.A_BOLD))
        if streak >= 5:
            put(scr, input_y, w - 16, f"x{1 + streak // 5} COMBO!", color(MAGENTA, curses.A_BOLD))
        put(scr, h - 1, 0, f" type to zap words · backspace fix · Esc pause / quit · {PACK_NAMES[pack]} words",
            color(GREY, curses.A_DIM))
        if paused:
            message_box(scr, ["PAUSED", f"Esc resume · {sound.label} · q quit"], color(YELLOW))
        scr.refresh()
        time.sleep(0.015)

    elapsed = max(1.0, time.time() - start - paused_total)
    if practice:
        elapsed = PRACTICE_SECONDS
    wpm = round((correct_keys / 5) / (elapsed / 60))
    acc = f"{100 * correct_keys / total_keys:.0f}%" if total_keys else "—"
    stats = [("WPM", wpm), ("Accuracy", acc), ("Words", words_done), ("Missed", missed),
             ("Best streak", best_streak), ("Time", fmt_time(elapsed))]
    final = wpm if practice else score
    return game_over(scr, board, final, stats, title="TIME" if practice else "GAME OVER",
                     note=PACK_NAMES[pack].split()[0].lower(), won=practice)


def main(scr):
    init_colors()
    while True:
        choice = title_screen(
            scr, "TYPING RACER", CYAN, "Words race across the screen. Type them before they escape.",
            [("letters", "type a word to zap it"), ("backspace / ctrl-u", "fix a letter / clear"),
             ("5-word streak", "raises your combo multiplier"), ("Esc", "pause (q there to quit)")],
            options=[("Mode", MODES), ("Words", PACK_NAMES)], board_for=lambda c: BOARDS[MODES[c[0]]],
            settings_key="typing_options")
        if choice is None:
            return
        while play(scr, *choice) == "r":
            pass


if __name__ == "__main__":
    run(main)
