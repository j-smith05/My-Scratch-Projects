# 🕹️ Terminal Arcade

Six classic games that run right in your terminal, with title screens, sound effects,
animations, top-10 leaderboards and a starfield arcade menu. They're pure Python using only
the standard library (`curses`), so there's nothing to install, and no API keys or accounts.

```
▄▀█ █▀█ █▀▀ ▄▀█ █▀▄ █▀▀
█▀█ █▀▄ █▄▄ █▀█ █▄▀ ██▄
```

## Quick start

```bash
cd terminal-games
python3 arcade.py
```

Use **↑ / ↓** to pick a game and **Enter** to play. When you quit a game you land back in the
menu, which shows each game's record, how often you've played it, and which one you played last.
Press **s** for a stats page with every record in one place.

You can also run any game directly:

```bash
python3 snake.py
python3 tetris.py
python3 invaders.py
python3 minesweeper.py
python3 game2048.py
python3 typing_racer.py
```

**Requirements:** Python 3.8+ on macOS or Linux, and a terminal at least **80×24**. You can
resize the window mid-game and everything re-centers. If it gets too small, the game pauses
and tells you how big to make it.

---

## How every game works

- **Title screen:** each game opens with an animated logo, its controls, the current
  record, and any options (mode, difficulty, start level…). Use **↑↓** to pick an option and
  **←→** to change it. Your choices are remembered for next time.
- **Sound:** short effects play using macOS's built-in system sounds. Press **v** anywhere
  to turn sound on or off; the setting is saved. On Linux, the games use the terminal bell instead.
- **Leaderboards:** every game keeps a **top 10**. Make the list and you get an arcade-style
  **ENTER YOUR INITIALS** screen (type letters, or use ↑↓ to cycle; it remembers your last
  initials). Press **l** on a title screen to see the full board.
- **Game-over screen:** your score, how it compares with the record ("NEW RECORD! Beat the old
  best by 120" or "340 short of the record"), stats for the round, and the leaderboard with
  your entry highlighted.
- **q** always takes you back one step: from a game to its title screen, and from the title
  screen to the arcade menu.

---

## The games

### 🐍 Snake — `snake.py`
Eat food, grow longer, and don't crash. You speed up as you eat.

- **Modes:** *Classic* (walls kill), *Wrap-around* (go off one edge, come back on the other),
  *Obstacles* (random wall blocks). Each mode has its own leaderboard.
- **Red** squares are food (+10, worth more as you grow).
- **◆◆ Gold** appears now and then: +75 and extra growth, but it vanishes after 5 seconds.
- **Blue** power-up: **slow-mo** for 6 seconds.
- **Purple** power-up: **ghost mode** for 6 seconds. Pass through walls, obstacles and yourself.
- Crashing shakes the screen and the snake fades away tail-first.

| Key | Action |
|---|---|
| Arrows / WASD | Steer |
| `p` or Space | Pause |
| `v` / `q` | Sound / Quit |

### 🧱 Tetris — `tetris.py`
Stack falling blocks and clear full lines. Every 10 lines the level goes up and pieces fall faster.

- **Start level** picker on the title screen (1–15) for a faster start.
- **Lock delay:** a piece that touches down shimmers for half a second, so you can still
  slide or rotate it into place (just like modern Tetris).
- **Ghost piece**, **3-piece preview** and **hold**.
- **Callouts** like *SINGLE*, *DOUBLE*, *TRIPLE*, **★ TETRIS! ★**, *COMBO x3* and *LEVEL 5!*.
- Scoring: 1 / 2 / 3 / 4 lines = 100 / 300 / 500 / 800 × level, plus combo bonuses for clearing
  on back-to-back pieces. Soft and hard drops add a few points each.

| Key | Action |
|---|---|
| ← → (or `a` `d`) | Move |
| ↑ / `x` / `w` | Rotate clockwise |
| `z` | Rotate counter-clockwise |
| ↓ / `s` | Soft drop |
| Space | Hard drop |
| `c` | Hold piece |
| `p` / `v` / `q` | Pause / Sound / Quit |

### 👾 Space Invaders — `invaders.py`
Defend Earth from waves of descending aliens. They speed up as their numbers shrink, and each
new wave starts faster and lower.

- **Smooth movement:** tap an arrow for a precise nudge, or hold it to glide.
- Aliens are worth **10 / 20 / 30** points (bottom → top rows) and burst into particles when hit.
- The **mystery ship** `<=O=>` crosses the top now and then for 50–300 bonus points.
- **Boss fight every 5th wave:** a giant mothership with a health bar that sweeps the screen
  firing triple shots. Beat it for **1000+ points and an extra life** (up to 5).
- **Shields** absorb fire from both sides and crumble as they take hits.
- You start with **3 lives**. If the aliens reach your row, it's game over.

| Key | Action |
|---|---|
| ← → (or `a` `d`) | Move (hold to glide) |
| Space / ↑ | Fire |
| `p` / `v` / `q` | Pause / Sound / Quit |

### 💣 Minesweeper — `minesweeper.py`
Reveal every safe square without hitting a mine. Numbers tell you how many mines touch that square.

- **Difficulty** on the title screen: Easy (9×9, 10 mines), Medium (16×16, 40), Hard (30×16, 99).
  Each has its own **best times** leaderboard.
- Your **first dig is always safe**.
- **The face:** `(^_^)` normally, `(°o°)` while you dig, `(x_x)` when you lose, `(⌐■_■)` when you
  win. Click it to start a new game.
- **Flags and question marks:** `f` or right-click cycles a square through ▲ flag → `?` → clear.
- **Chording:** dig a number that already has the right count of flags around it to clear
  all its other neighbors at once.
- Winning sets off **confetti**. Losing reveals the mines one by one, starting from the one you hit.

| Key | Action |
|---|---|
| Arrows / WASD / hjkl | Move cursor |
| Space / Enter / left-click | Dig |
| `f` / right-click | Flag → ? → clear |
| `?` | Toggle a question mark |
| `r` / `v` / `q` | Restart / Sound / Quit |

### 🔢 2048 — `game2048.py`
Slide all the tiles in one direction. Matching tiles merge into their sum. Reach **2048**,
then keep going if you like.

- **Boards:** *Classic 4×4* or *Big 5×5* (more room, bigger scores). Each has its own leaderboard.
- **Animated:** tiles slide into place, merged tiles pop, new tiles grow in, and a `+points`
  popup flashes next to your score.
- **Undo** up to 20 moves, even after you run out of moves.
- Ending or restarting a game asks for confirmation first, so a stray key can't wipe a good run.

| Key | Action |
|---|---|
| Arrows / WASD | Slide |
| `u` | Undo |
| `r` | Restart (not scored) |
| `q` | End the game and score it |
| `v` | Sound on/off |

### ⌨️ Typing Racer — `typing_racer.py`
Words race across the screen from left to right. Type a word to zap it before it reaches the
red line on the right.

- **Modes:**
  - *Classic*: 3 lives, getting faster with every 10 words. Scored by points.
  - *Practice 60s*: no lives, just a 60-second timer. Scored by **words per minute**.
- **Word packs:** *Common*, *Programming*, *Animals* and *Hard words*.
- Each zapped word fires a **laser** from your cursor and bursts apart.
- Words turn **yellow**, then **red**, as they near the edge.
- Every 5 words in a row without a mistake raises your **combo multiplier**.
- Live stats: score, **WPM**, accuracy, streak and level.

| Key | Action |
|---|---|
| Letters | Type |
| Backspace | Fix a letter |
| Ctrl-U | Clear what you've typed |
| Esc | Pause (then `v` for sound, `q` to quit) |

---

## Saved data

Everything (leaderboards, settings, play counts and your last-used initials) is saved
automatically to `.arcade_data.json` in this folder. To reset everything, delete that file:

```bash
rm .arcade_data.json
```

## Files

| File | What it is |
|---|---|
| `arcade.py` | The launcher menu: starfield, records, play counts, stats page |
| `snake.py`, `tetris.py`, `invaders.py`, `minesweeper.py`, `game2048.py`, `typing_racer.py` | The games |
| `common.py` | Shared toolkit: colors, drawing, sound, the block-letter font, title screens, leaderboards, game-over screens and particle effects |

## Troubleshooting

- **"Terminal too small!"** Make the window bigger (at least 80×24), or zoom out with ⌘ −.
- **No sound:** press `v` to make sure it's on. Sounds use the built-in `afplay` on macOS, and
  other systems fall back to the terminal bell (which some terminals silence).
- **Colors look off:** most modern terminals support 256 colors. If yours doesn't, the games
  fall back to the basic 8 colors.
- **Mouse doesn't work in Minesweeper:** some terminals don't pass clicks through. The
  keyboard controls always work.
- **Holding an arrow in Space Invaders feels jerky:** the glide follows your keyboard's key-repeat
  speed. Turning up "Key repeat rate" in System Settings → Keyboard makes it smoother.
