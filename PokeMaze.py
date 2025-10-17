# -*- coding: utf-8 -*-
"""
ASCII PokeMaze++ : faster-paced maze + turn-based battles
Charmander vs roaming enemies, coins, mystery tiles, weather, combo meter, XP/levels, and a Boss fight.

Highlights (new vs previous version):
- Enemies ROAM between turns (feel the pressure).
- Score + Coins to collect on the map.
- Mystery tiles (?) with fun effects (heal, poison, PP+, weather shift, bonus coins, surprise enemy).
- Weather system: Sunny (fire boost), Rain (fire nerf), Fog (more misses), Clear (neutral).
- Combo meter: consecutive hits add bonus damage (and a satisfying "COMBO!" toast).
- XP & Leveling: beat enemies to level up → more max HP and +1 Flamethrower PP on some levels.
- Optional RUN action in battle (50% chance) to disengage and reposition.
- Boss fight spawns after you defeat all regular enemies.
- End-of-run summary with tiny achievements.
- All kept Python 2/3 compatible; tests still pass; no new dependencies required.
- Single-file game with CLI flags (see README below).
"""
from __future__ import print_function

import argparse
import os
import random
import sys
import time
import unittest

# ---------------- Basic constants ----------------
POS_X = 0
POS_Y = 1

HP_BAR_SIZE = 20

DEFAULT_NUM_ENEMIES = 6
DEFAULT_NUM_POTIONS = 4
DEFAULT_NUM_SUPERPOTIONS = 2
DEFAULT_NUM_ANTIDOTES = 2
DEFAULT_NUM_COINS = 8
DEFAULT_NUM_MYSTERY = 4

ASCII_MAP = """\
#############################
                             
     #######         ####    
                             
 ########     #####          
                         ####
                             
####      ############       
                             
#############                 
                      ###### 
                             
                   ####      
                             
#############################\
"""

# ---------------- Logging (quiet mode for tests) ----------------
QUIET = False

def _to_text(x):
    try:
        return str(x)
    except Exception:
        try:
            return repr(x)
        except Exception:
            return "<unprintable>"

def log(*a):
    """Py2/3-safe logging without print kwargs or f-strings."""
    if not QUIET:
        line = " ".join(_to_text(x) for x in a)
        try:
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
        except Exception:
            try:
                print(line)
            except Exception:
                pass

# ---------------- I/O helpers & compatibility ----------------

def is_interactive_stdin():
    try:
        return bool(sys.stdin) and hasattr(sys.stdin, 'isatty') and sys.stdin.isatty()
    except Exception:
        return False

def out(s):
    try:
        sys.stdout.write(s)
        sys.stdout.flush()
    except Exception:
        try:
            sys.stdout.write(s)
        except Exception:
            pass

# DEMO mode
DEMO_MODE = False
_DEMO_STEP_COUNT = 0
_DEMO_MOVE_CHOICES = ['w', 'a', 's', 'd']

def demo_next_key():
    """Return synthetic movement keys and eventually 'q' to end DEMO."""
    global _DEMO_STEP_COUNT
    _DEMO_STEP_COUNT += 1
    if _DEMO_STEP_COUNT > 240:
        return 'q'
    weights = [1, 1, 2, 3]  # w,a,s,d (slight bias to move forward)
    total = sum(weights)
    r = random.randint(1, total)
    acc = 0
    for i, w in enumerate(weights):
        acc += w
        if r <= acc:
            return _DEMO_MOVE_CHOICES[i]
    return 'd'

# Optional readchar
_READCHAR = False
try:
    import readchar  # type: ignore
    _READCHAR = True
except Exception:
    _READCHAR = False

def safe_input(prompt=""):
    """Non-blocking guard for DEMO; otherwise try normal input."""
    if DEMO_MODE:
        return ""
    try:
        # Py2/3 compatibility
        try:
            inp = raw_input  # noqa: F821  # type: ignore
        except NameError:
            inp = input
        return inp(prompt)
    except Exception:
        # If input cannot be read (e.g., non-interactive), just return empty
        return ""

def read_key(prompt=""):
    """
    Read a single key. In DEMO, generate a synthetic move key.
    Otherwise:
      - If readchar is available, use it for single-key input.
      - Else fall back to input() and take the first char.
    If input cannot be read, return empty string (no auto-DEMO).
    """
    if DEMO_MODE:
        return demo_next_key()

    if prompt:
        out(prompt)

    # Single key if available
    if _READCHAR:
        try:
            ch = readchar.readchar()
            if isinstance(ch, bytes):
                try:
                    ch = ch.decode("utf-8", "ignore")
                except Exception:
                    ch = str(ch)
            return ch[:1].lower()
        except Exception:
            pass

    # Fallback to line input
    try:
        try:
            inp = raw_input  # noqa: F821  # type: ignore
        except NameError:
            inp = input
        ch = inp("").strip()
        return ch[:1].lower() if ch else ""
    except Exception:
        # Non-interactive or other error: return empty so the loop can continue
        return ""

def safe_clear():
    """Clear screen with an ANSI fallback."""
    try:
        ret = os.system("cls" if os.name == "nt" else "clear")
        if ret == 0:
            return
    except Exception:
        pass
    out("\033[2J\033[H")

# ---------------- Optional colors ----------------
ENABLE_COLOR = True
CSI = "\033["
RESET = CSI + "0m"
COLORS = {
    "wall": CSI + "90m",
    "player": CSI + "96m",
    "enemy": CSI + "91m",
    "potion": CSI + "92m",
    "coin": CSI + "93m",
    "mystery": CSI + "95m",
    "hud": CSI + "94m",
    "bar_ok": CSI + "32m",
    "bar_mid": CSI + "33m",
    "bar_low": CSI + "31m",
    "status": CSI + "95m",
}

if os.getenv("NO_COLOR") == "1":
    ENABLE_COLOR = False

if os.name == "nt" and ENABLE_COLOR:
    try:
        import colorama  # type: ignore
        colorama.just_fix_windows_console()
    except Exception:
        ENABLE_COLOR = False

def c(text, key):
    if not ENABLE_COLOR:
        return text
    return COLORS.get(key, "") + text + RESET

# ---------------- Map ----------------

def build_map(s):
    """Return (rectangular grid, width, height) with safe padding."""
    rows = s.split("\n")
    maxw = max(len(r) for r in rows)
    grid = [list(r.ljust(maxw)) for r in rows]
    return grid, maxw, len(grid)

obstacle_definition, MAP_WIDTH, MAP_HEIGHT = build_map(ASCII_MAP)

# ---------------- Game content ----------------
# Player BASE (scales with level)
BASE_MAX_HP = 120
char_max_hp = BASE_MAX_HP
current_hp = char_max_hp
flame_pp = 3  # PP for Flamethrower
inventory = {"potion": 0, "superpotion": 0, "antidote": 0}
player_poisoned = False

# Progression / meta
level = 1
xp = 0
xp_to_next = 100
score = 0
steps_taken = 0
enemies_defeated = 0
potions_used = 0
superpotions_used = 0
antidotes_used = 0
total_damage_dealt = 0
total_damage_taken = 0
hit_streak = 0
best_streak = 0

# Player position
my_position = [0, 1]

# Objects on map
# dict: {"type": "enemy"/"potion"/"superpotion"/"antidote"/"coin"/"mystery", ...}
map_objects = []

# Weather system
WEATHER_STATES = ["Clear", "Sunny", "Rain", "Fog"]
weather = {"state": "Clear", "turns": 0}

def set_weather(state=None, turns=None):
    if state is None:
        state = random.choice(WEATHER_STATES)
    if turns is None:
        turns = random.randint(8, 16)
    weather["state"] = state
    weather["turns"] = int(turns)

def tick_weather():
    if weather["turns"] > 0:
        weather["turns"] -= 1
        if weather["turns"] == 0:
            weather["state"] = "Clear"

# Enemies
ENEMIES = {
    "Machop": {
        "hp": 100,
        "attacks": [("Karate Chop", 10, {"miss": 0.05, "crit": 0.12}),
                    ("Low Kick", 12, {"miss": 0.05, "crit": 0.10})],
    },
    "Geodude": {
        "hp": 110,
        "attacks": [("Tackle", 8, {"miss": 0.05, "crit": 0.10}),
                    ("Rock Slide", 14, {"miss": 0.12, "crit": 0.15})],
    },
    "Zubat": {
        "hp": 80,
        "attacks": [("Bite", 6, {"miss": 0.05, "crit": 0.15}),
                    ("Supersonic", 10, {"miss": 0.25, "crit": 0.10})],
    },
    "Onix": {
        "hp": 130,
        "attacks": [("Sharp Rock", 16, {"miss": 0.18, "crit": 0.18}),
                    ("Whip", 9, {"miss": 0.05, "crit": 0.10})],
    },
    "Koffing": {
        "hp": 95,
        "attacks": [("Tackle", 8, {"miss": 0.07, "crit": 0.12}),
                    ("Poison Gas", 0, {"miss": 0.10, "crit": 0.00, "poison": True})],
    },
    "Boss Onix": {
        "hp": 180,
        "attacks": [("Stone Edge", 18, {"miss": 0.15, "crit": 0.20}),
                    ("Earth Shake", 12, {"miss": 0.10, "crit": 0.15})],
    },
}

# ---------------- Game utilities ----------------

def draw_bar(current, total, size=HP_BAR_SIZE):
    current = max(0, min(int(current), int(total or 1)))
    size = int(size) if size else 1
    total = int(total) if total else 1
    filled = int(float(current) * size / float(total))
    empty = size - filled
    ratio = (float(current) / float(total)) if total else 0.0
    if ratio >= 0.6:
        color = "bar_ok"
    elif ratio >= 0.3:
        color = "bar_mid"
    else:
        color = "bar_low"
    return c("[" + ("*" * filled) + (" " * empty) + "]", color) + " ({}/{})".format(current, total)

def all_free_cells():
    """Yield all walkable cells (no wall, not player)."""
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if obstacle_definition[y][x] != "#" and [x, y] != my_position:
                yield [x, y]

def random_free_cell():
    """Pick a random free cell (no wall, not player, not occupied)."""
    free = [cell for cell in all_free_cells()
            if all(obj["pos"] != cell for obj in map_objects)]
    if not free:
        raise RuntimeError("No free cells available")
    return random.choice(free)

def populate_map(num_enemies, num_potions, num_super, num_antidotes, num_coins, num_mystery):
    """Place enemies and items without overlaps."""
    map_objects[:] = []
    free = [cell for cell in all_free_cells()]
    random.shuffle(free)

    def take_cell():
        if not free:
            raise RuntimeError("Not enough free cells")
        return free.pop()

    enemy_names = ["Machop", "Geodude", "Zubat", "Onix", "Koffing"]
    for _ in range(num_enemies):
        name = random.choice(enemy_names)
        map_objects.append({
            "type": "enemy",
            "name": name,
            "hp": ENEMIES[name]["hp"],
            "pos": take_cell(),
        })
    for _ in range(num_potions):
        map_objects.append({"type": "potion", "heal": 25, "pos": take_cell()})
    for _ in range(num_super):
        map_objects.append({"type": "superpotion", "heal": 50, "pos": take_cell()})
    for _ in range(num_antidotes):
        map_objects.append({"type": "antidote", "pos": take_cell()})
    for _ in range(num_coins):
        map_objects.append({"type": "coin", "value": 5, "pos": take_cell()})
    for _ in range(num_mystery):
        map_objects.append({"type": "mystery", "pos": take_cell()})

def occupancy_index():
    """O(1) index for rendering."""
    return {tuple(o["pos"]): o for o in map_objects}

def apply_variance(base, miss=0.05, crit=0.10, crit_mult=1.5):
    """Return damage with miss/crit variance (legacy helper)."""
    r = random.random()
    if r < miss:
        return 0
    if r < miss + crit:
        return int(round(base * crit_mult))
    return base

def roll_damage(base, miss=0.05, crit=0.10, crit_mult=1.5):
    """
    Roll an attack once and return (damage, missed, critical).
    Status-only moves (base==0) apply status only if not missed.
    """
    r = random.random()
    if r < miss:
        return 0, True, False
    critical = (r < miss + crit)
    dmg = int(round(base * (crit_mult if critical else 1.0)))
    return dmg, False, critical

def enemy_turn(enemy):
    """Return (damage, effects, message) for a randomly chosen enemy attack.
       Weather adjustments applied after roll.
    """
    atk_name, base, params = random.choice(ENEMIES[enemy["name"]]["attacks"])
    miss_p = params.get("miss", 0.05)
    crit_p = params.get("crit", 0.10)
    dmg, missed, critical = roll_damage(base, miss_p, crit_p, 1.5)

    # Weather tweaks (affect final damage or miss message)
    if not missed:
        if weather["state"] == "Fog":
            # 30% softer hits in the fog
            dmg = int(round(dmg * 0.7))
        # Sunny/Rain don't affect enemy by default

    effects = {}
    if params.get("poison") and not missed:
        effects["poison"] = True

    if missed:
        msg = "%s used %s (missed)" % (enemy["name"], atk_name)
    else:
        if base > 0:
            extra = " (CRIT!)" if critical else ""
            msg = "%s used %s (-%d HP)%s" % (enemy["name"], atk_name, dmg, extra)
        else:
            msg = "%s used %s (status)" % (enemy["name"], atk_name)
    return dmg, effects, msg

def use_item(kind):
    """Apply item effects to the player. Return True if used."""
    global current_hp, player_poisoned, inventory, potions_used, superpotions_used, antidotes_used
    if kind == "potion":
        if inventory["potion"] > 0:
            inventory["potion"] -= 1
            potions_used += 1
            heal = 25
            before = current_hp
            current_hp = min(char_max_hp, current_hp + heal)
            log("Used Potion (+%d). HP: %d/%d" % (current_hp - before, current_hp, char_max_hp))
            return True
        log("You have no Potions left.")
        return False
    if kind == "superpotion":
        if inventory["superpotion"] > 0:
            inventory["superpotion"] -= 1
            superpotions_used += 1
            heal = 50
            before = current_hp
            current_hp = min(char_max_hp, current_hp + heal)
            log("Used Super Potion (+%d). HP: %d/%d" % (current_hp - before, current_hp, char_max_hp))
            return True
        log("You have no Super Potions left.")
        return False
    if kind == "antidote":
        if inventory["antidote"] > 0:
            if player_poisoned:
                inventory["antidote"] -= 1
                antidotes_used += 1
                player_poisoned = False
                log("Used Antidote. You are no longer poisoned!")
                return True
            else:
                log("You are not poisoned.")
                return False
        log("You have no Antidotes left.")
        return False
    return False

def get_player_choice(enemy_name):
    """Return action: A/L/N/P/U/D/R. DEMO auto-selects; otherwise read from input."""
    global flame_pp, player_poisoned
    if DEMO_MODE:
        # very light-weight demo logic
        if player_poisoned and inventory.get("antidote", 0) > 0 and random.random() < 0.75:
            return 'D'
        if current_hp <= int(0.35 * char_max_hp):
            if inventory.get("superpotion", 0) > 0 and random.random() < 0.7:
                return 'U'
            if inventory.get("potion", 0) > 0 and random.random() < 0.8:
                return 'P'
        if flame_pp > 0 and random.random() < 0.66:
            return 'L'
        return 'A' if random.random() < 0.85 else 'N'

    while True:
        log("\nAction:")
        log("  [A] Ember (-10)   [L] Flamethrower (-12, PP left: %d)" % flame_pp)
        log("  [N] Nothing       [P] Potion (+25)  [U] Super Potion (+50)  [D] Antidote  [R] Run (50%%)")
        choice = safe_input("> ")
        if not choice:
            # Empty input: default to 'A' to keep the game moving
            return 'A'
        choice = choice.strip().upper()[:1]
        if choice in {'A', 'L', 'N', 'P', 'U', 'D', 'R'}:
            return choice

def add_xp(n):
    """Award XP; handle level-ups with small bonuses."""
    global xp, level, xp_to_next, char_max_hp, current_hp, flame_pp
    xp += int(n)
    leveled = False
    while xp >= xp_to_next:
        xp -= xp_to_next
        level += 1
        xp_to_next = int(round(xp_to_next * 1.25))
        # Level bonuses
        old_max = char_max_hp
        char_max_hp += 10
        current_hp = min(char_max_hp, current_hp + 10)
        if level % 2 == 0:
            flame_pp += 1
        log(c("LEVEL UP! → Lv.%d  Max HP %d→%d, Flamethrower PP:%d" % (level, old_max, char_max_hp, flame_pp), "status"))
        leveled = True
    return leveled

def player_turn(enemy):
    """Process the player's action. Return (damage_dealt, escaped_bool)."""
    global current_hp, flame_pp, player_poisoned, hit_streak, best_streak
    global total_damage_dealt, total_damage_taken

    # Poison tick
    if player_poisoned:
        dmg = 5
        current_hp = max(0, current_hp - dmg)
        total_damage_taken += dmg
        log(c("Poison hurts you! (-5)", "status"))

    choice = get_player_choice(enemy["name"])
    dmg = 0
    escaped = False

    # Base moves with simple weather + combo bonuses
    def _apply_bonuses(base_dmg):
        # Level scaling
        base = base_dmg + (level - 1)  # tiny ramp
        # Weather
        if weather["state"] == "Sunny":
            base += 2
        elif weather["state"] == "Rain":
            base = max(0, base - 2)
        # Combo
        combo_bonus = max(0, min(8, 2 * max(0, hit_streak - 1)))
        return base + combo_bonus, combo_bonus

    if choice == 'A':
        base, combo_bonus = _apply_bonuses(10)
        roll = apply_variance(base, miss=0.06 if weather["state"] == "Fog" else 0.05, crit=0.13)
        dmg = roll
        if dmg > 0:
            hit_streak += 1
            best_streak = max(best_streak, hit_streak)
            if combo_bonus > 0:
                log(c("COMBO +%d!" % combo_bonus, "status"))
            log("Charmander used Ember! " + ("(-%d enemy HP)" % dmg))
        else:
            hit_streak = 0
            log("Charmander used Ember! (missed)")
    elif choice == 'L':
        if flame_pp > 0:
            flame_pp -= 1
            base, combo_bonus = _apply_bonuses(12)
            roll = apply_variance(base, miss=0.08 if weather["state"] != "Fog" else 0.10, crit=0.16)
            dmg = roll
            if dmg > 0:
                hit_streak += 1
                best_streak = max(best_streak, hit_streak)
                if combo_bonus > 0:
                    log(c("COMBO +%d!" % combo_bonus, "status"))
                log("Charmander used Flamethrower! " + ("(-%d enemy HP)" % dmg))
            else:
                hit_streak = 0
                log("Charmander used Flamethrower! (missed)")
        else:
            hit_streak = 0
            log("No PP left for Flamethrower. You lose the turn!")
    elif choice == 'N':
        hit_streak = 0
        log("Charmander does nothing…")
    elif choice == 'P':
        used = use_item("potion")
        if not used:
            log("You lose the turn.")
        hit_streak = 0
    elif choice == 'U':
        used = use_item("superpotion")
        if not used:
            log("You lose the turn.")
        hit_streak = 0
    elif choice == 'D':
        used = use_item("antidote")
        if not used:
            log("You lose the turn.")
        hit_streak = 0
    elif choice == 'R':
        # 50% chance to run away
        if random.random() < 0.5:
            log(c("You successfully ran away!", "status"))
            escaped = True
        else:
            log("You failed to escape!")
        hit_streak = 0

    total_damage_dealt += max(0, int(dmg))
    return dmg, escaped

def draw_map():
    """Draw HUD + map."""
    enemies_left = sum(1 for o in map_objects if o["type"] == "enemy")
    hud1 = (c("HP ", "hud") + draw_bar(current_hp, char_max_hp) +
            "  " + c("Pot:%d Sup:%d Ant:%d" % (inventory['potion'], inventory['superpotion'], inventory['antidote']), "hud") +
            "  " + c("Enemies:%d" % enemies_left, "hud") +
            "  " + c("Flame PP:%d" % flame_pp, "hud"))
    if player_poisoned:
        hud1 += "  " + c("[POISONED]", "status")

    hud2 = (c("Lvl:%d  XP:%d/%d  Score:%d  Steps:%d  Combo:%d (best %d)  Weather:%s%s"
           % (level, xp, xp_to_next, score, steps_taken, hit_streak, best_streak,
              weather["state"],
              ("[%d]" % weather["turns"]) if weather["state"] != "Clear" else ""), "hud"))

    log(hud1 + "  " + c("(@=you, E=enemies, $=coins, ?=mystery, *=items)", "hud"))
    log(hud2)

    occ = occupancy_index()

    print("+" + "-" * (MAP_WIDTH * 3) + "+")
    for y in range(MAP_HEIGHT):
        out("|")
        for x in range(MAP_WIDTH):
            pos = (x, y)
            if my_position[POS_X] == x and my_position[POS_Y] == y:
                out(c(" @ ", "player"))
            elif obstacle_definition[y][x] == "#":
                out(c("###", "wall"))
            else:
                obj = occ.get(pos)
                if obj:
                    t = obj.get("type")
                    if t == "enemy":
                        out(c(" E ", "enemy"))
                    elif t in ("potion", "superpotion", "antidote"):
                        out(c(" * ", "potion"))
                    elif t == "coin":
                        out(c(" $ ", "coin"))
                    elif t == "mystery":
                        out(c(" ? ", "mystery"))
                    else:
                        out(" * ")
                else:
                    out("   ")
        out("|\n")
    print("+" + "-" * (MAP_WIDTH * 3) + "+")
    print("Move: w/a/s/d | Help: h | Quit: q")

def print_help():
    log("\n" + c("Help:", "hud"))
    log("  - Move with WASD. @ is you. E are enemies. $ are coins. ? are mystery tiles. * are items.")
    log("  - Items: Potion (+25), Super Potion (+50), Antidote (cures poison).")
    log("  - Defeat all enemies… then face the Boss!")
    log("  - Weather cycles: Sunny (+fire dmg), Rain (-fire dmg), Fog (more misses), Clear (neutral).")
    log("  - In battle:")
    log("      [A] Ember  [L] Flamethrower (limited PP)  [R] Run (50%)")
    log("      [P] Potion  [U] Super Potion  [D] Antidote  [N] Nothing")
    if is_interactive_stdin():
        safe_input("\nPress ENTER to continue…")
    safe_clear()

# ---------------- Enemy movement ----------------

def neighbors4(x, y):
    for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
        yield x+dx, y+dy

def can_walk(x, y):
    if x < 0 or y < 0 or x >= MAP_WIDTH or y >= MAP_HEIGHT:
        return False
    if obstacle_definition[y][x] == "#":
        return False
    if [x, y] == my_position:
        return False
    return True

def move_enemies():
    """Each enemy tries to step randomly to a neighboring free cell (no collisions)."""
    occ = set(tuple(o["pos"]) for o in map_objects if o["type"] == "enemy")
    taken = set(tuple(o["pos"]) for o in map_objects)  # avoid stacking with items for clarity
    new_positions = {}
    for idx, obj in enumerate(map_objects):
        if obj["type"] != "enemy":
            continue
        x, y = obj["pos"]
        candidates = []
        for nx, ny in neighbors4(x, y):
            if can_walk(nx, ny) and (nx, ny) not in taken:
                candidates.append((nx, ny))
        if candidates and random.random() < 0.75:  # 75% chance to roam
            chosen = random.choice(candidates)
            new_positions[idx] = [chosen[0], chosen[1]]
            taken.add(chosen)
        else:
            new_positions[idx] = [x, y]
            taken.add((x, y))
    # commit
    for idx, newp in new_positions.items():
        map_objects[idx]["pos"] = newp

# ---------------- Mystery resolution ----------------

def resolve_mystery():
    """Trigger a random effect for the player."""
    global current_hp, flame_pp, score, player_poisoned
    roll = random.random()
    if roll < 0.20:
        heal = 20
        before = current_hp
        current_hp = min(char_max_hp, current_hp + heal)
        log(c("Mystery healed you +%d!" % (current_hp - before), "status"))
    elif roll < 0.40:
        if not player_poisoned:
            player_poisoned = True
            log(c("Mystery… uh oh, you got poisoned!", "status"))
        else:
            score += 3
            log("Mystery fizzles. Consolation +3 score.")
    elif roll < 0.60:
        flame_pp += 1
        log(c("Mystery granted +1 Flamethrower PP!", "status"))
    elif roll < 0.80:
        bonus = random.randint(5, 15)
        score += bonus
        log(c("Mystery rain of coins! +%d score" % bonus, "status"))
    else:
        # Surprise enemy spawn nearby if possible
        try:
            pos = random_free_cell()
            name = random.choice(["Zubat", "Koffing", "Machop"])
            map_objects.append({"type": "enemy", "name": name, "hp": ENEMIES[name]["hp"], "pos": pos})
            log(c("Mystery spawned a wild %s!" % name, "status"))
        except Exception:
            log("Mystery tried to spawn an enemy, but there is no space.")

# ---------------- Battle loop ----------------

def do_battle(enemy):
    """Battle loop. Return one of: 'win' | 'lose' | 'escape'."""
    global current_hp, player_poisoned, total_damage_taken, enemies_defeated, score
    safe_clear()
    # --- Title line printed before each battle contextually ---
    log(c("The battle begins!", "hud"), "(Charmander vs %s)" % enemy['name'])
    enemy_hp = int(enemy["hp"])
    base_hp = enemy_hp

    while enemy_hp > 0 and current_hp > 0:
        # Enemy turn
        log("\nEnemy turn:")
        dmg, effects, msg = enemy_turn(enemy)
        log(msg)
        current_hp = max(0, current_hp - dmg)
        total_damage_taken += dmg
        if effects.get("poison") and not player_poisoned:
            player_poisoned = True
            log(c("You are poisoned!", "status"))

        log("Charmander:", draw_bar(current_hp, char_max_hp))
        log("%s:" % enemy['name'], draw_bar(enemy_hp, base_hp))
        if is_interactive_stdin():
            safe_input("\nPress ENTER to continue…")
        safe_clear()
        if current_hp <= 0:
            break

        # Player turn
        log("Your turn!")
        dmg, escaped = player_turn(enemy)
        if escaped:
            log(c("You fled the battle!", "status"))
            return 'escape'
        enemy_hp = max(0, enemy_hp - dmg)
        log("Charmander:", draw_bar(current_hp, char_max_hp))
        log("%s:" % enemy['name'], draw_bar(enemy_hp, base_hp))
        if is_interactive_stdin():
            safe_input("\nPress ENTER to continue…")
        safe_clear()

    if current_hp <= 0:
        log(c("You lost the battle!", "bar_low"))
        return 'lose'
    log(c("You won the battle!", "bar_ok"))
    # Soft loot
    enemies_defeated += 1
    score_gain = 20
    score += score_gain
    log("You gained +%d score." % score_gain)
    if random.random() < 0.3:
        before = current_hp
        current_hp = min(char_max_hp, current_hp + 10)
        log("You recovered +%d HP." % (current_hp - before))
    if random.random() < 0.2:
        inventory["potion"] += 1
        log("The enemy dropped a Potion (+1).")
    # XP
    gained = random.randint(30, 45)
    log("Gained %d XP." % gained)
    add_xp(gained)
    return 'win'

# ---------------- Main loop ----------------

def title_splash():
    safe_clear()
    banner = [
        " /$$$$$$$           /$$                 /$$      /$$                              ",
        "| $$__  $$         | $$                | $$$    /$$$                              ",
        "| $$  \\ $$ /$$$$$$ | $$   /$$  /$$$$$$ | $$$$  /$$$$  /$$$$$$  /$$$$$$$$  /$$$$$$ ",
        "| $$$$$$$//$$__  $$| $$  /$$/ /$$__  $$| $$ $$/$$ $$ |____  $$|____ /$$/ /$$__  $$",
        "| $$____/| $$  \\ $$| $$$$$$/ | $$$$$$$$| $$  $$$| $$  /$$$$$$$   /$$$$/ | $$$$$$$$",
        "| $$     | $$  | $$| $$_  $$ | $$_____/| $$\\  $ | $$ /$$__  $$  /$$__/  | $$_____/",
        "| $$     |  $$$$$$/| $$ \\  $$|  $$$$$$$| $$ \\/  | $$|  $$$$$$$ /$$$$$$$$|  $$$$$$$",
        "|__/      \\______/ |__/  \\__/ \\_______/|__/     |__/ \\_______/|________/ \\_______/",
        "",
        "                 By FBS with a little help from my friends"
    ]
    for line in banner:
        log(c(line, "hud"))
        time.sleep(0.02 if is_interactive_stdin() else 0)
    if is_interactive_stdin():
        safe_input("\nPress ENTER to start…")
    safe_clear()

def main(args):
    global DEMO_MODE, ENABLE_COLOR, current_hp, flame_pp, player_poisoned
    global inventory, my_position, QUIET, char_max_hp
    global steps_taken, score, hit_streak, best_streak

    if args.no_color:
        os.environ["NO_COLOR"] = "1"
        ENABLE_COLOR = False

    QUIET = False

    # DEMO only if explicitly requested
    DEMO_MODE = bool(args.demo)

    # Difficulty tweaks
    enemies_n = args.enemies
    potions_n = args.potions
    supers_n = args.superpotions
    antidotes_n = args.antidotes
    coins_n = args.coins
    mystery_n = args.mystery
    if args.hard:
        enemies_n = max(1, int(enemies_n * 1.3))
        potions_n = max(0, int(potions_n * 0.6))
        supers_n = max(0, int(supers_n * 0.5))
        antidotes_n = max(0, int(antidotes_n * 0.5))
        coins_n = max(0, int(coins_n * 0.8))
        mystery_n = max(0, int(mystery_n * 1.2))

    # Initial state
    char_max_hp = BASE_MAX_HP
    current_hp = char_max_hp
    flame_pp = 3
    player_poisoned = False
    inventory = {"potion": 0, "superpotion": 0, "antidote": 0}
    my_position = [0, 1]

    # meta reset
    reset_meta()

    # Safer map population (auto-shrink on failure, retry once)
    try:
        populate_map(enemies_n, potions_n, supers_n, antidotes_n, coins_n, mystery_n)
    except RuntimeError:
        shrink = max(1, enemies_n // 4)
        enemies_n = max(1, enemies_n - shrink)
        potions_n = max(0, potions_n - 1)
        supers_n = max(0, supers_n - 1)
        antidotes_n = max(0, antidotes_n - 1)
        coins_n = max(0, coins_n - 1)
        mystery_n = max(0, mystery_n - 1)
        populate_map(enemies_n, potions_n, supers_n, antidotes_n, coins_n, mystery_n)

    boss_spawned = False
    wrap_moves = not args.no_wrap

    if not args.quiet_title:
        title_splash()

    set_weather("Clear", 0)  # start neutral

    end_game = False
    while not end_game:
        draw_map()
        direction = read_key("Move (w/a/s/d, h help, q quit): ")
        new_position = None

        if direction == "w":
            ny = my_position[POS_Y] - 1
            if wrap_moves:
                ny = ny % MAP_HEIGHT
                new_position = [my_position[POS_X], ny]
            elif ny >= 0:
                new_position = [my_position[POS_X], ny]
        elif direction == "s":
            ny = my_position[POS_Y] + 1
            if wrap_moves:
                ny = ny % MAP_HEIGHT
                new_position = [my_position[POS_X], ny]
            elif ny < MAP_HEIGHT:
                new_position = [my_position[POS_X], ny]
        elif direction == "a":
            nx = my_position[POS_X] - 1
            if wrap_moves:
                nx = nx % MAP_WIDTH
                new_position = [nx, my_position[POS_Y]]
            elif nx >= 0:
                new_position = [nx, my_position[POS_Y]]
        elif direction == "d":
            nx = my_position[POS_X] + 1
            if wrap_moves:
                nx = nx % MAP_WIDTH
                new_position = [nx, my_position[POS_Y]]
            elif nx < MAP_WIDTH:
                new_position = [nx, my_position[POS_Y]]
        elif direction == "h":
            print_help()
            continue
        elif direction == "q":
            # Only allow quitting if stdin is interactive AND user confirms.
            if is_interactive_stdin():
                ans = safe_input("Quit? (y/N): ").strip().lower()
                if ans == "y":
                    log("Goodbye!")
                    break
                else:
                    safe_clear()
                    continue
            else:
                # Ignore stray 'q' when stdin is not interactive
                safe_clear()
                continue
        else:
            # Unrecognized/empty input: just redraw and continue
            safe_clear()
            continue

        if new_position:
            if obstacle_definition[new_position[POS_Y]][new_position[POS_X]] != "#":
                steps_taken += 1
                my_position[:] = new_position
                # Object in the cell?
                for obj in list(map_objects):
                    if obj["pos"] == my_position:
                        if obj["type"] == "enemy":
                            result = do_battle(obj)
                            if result == 'win':
                                map_objects.remove(obj)
                                hit_streak = 0  # reset between battles
                            elif result == 'escape':
                                # Nudge the enemy away a bit to avoid immediate re-trigger
                                try:
                                    obj["pos"] = random_free_cell()
                                except Exception:
                                    pass
                                hit_streak = 0
                            else:
                                end_game = True
                                safe_clear()
                                log("You were defeated. Game Over.")
                                summary_screen()
                                return
                        elif obj["type"] == "potion":
                            inventory["potion"] += 1
                            log(c("You found a Potion! (+1)", "potion"))
                            map_objects.remove(obj)
                            if is_interactive_stdin():
                                safe_input("ENTER…")
                        elif obj["type"] == "superpotion":
                            inventory["superpotion"] += 1
                            log(c("You found a Super Potion! (+1)", "potion"))
                            map_objects.remove(obj)
                            if is_interactive_stdin():
                                safe_input("ENTER…")
                        elif obj["type"] == "antidote":
                            inventory["antidote"] += 1
                            log(c("You found an Antidote! (+1)", "potion"))
                            map_objects.remove(obj)
                            if is_interactive_stdin():
                                safe_input("ENTER…")
                        elif obj["type"] == "coin":
                            val = obj.get("value", 5)
                            score += val
                            log(c("You picked up %d coins!" % val, "coin"))
                            map_objects.remove(obj)
                            if is_interactive_stdin():
                                safe_input("ENTER…")
                        elif obj["type"] == "mystery":
                            log(c("You step onto a mysterious tile…", "mystery"))
                            resolve_mystery()
                            map_objects.remove(obj)
                            if is_interactive_stdin():
                                safe_input("ENTER…")
                        break

                # Enemies roam after your move
                move_enemies()

                # Weather countdown
                if steps_taken % 6 == 0 and random.random() < 0.25:
                    # 25% chance to (re-)set a non-clear weather
                    set_weather(random.choice(["Sunny", "Rain", "Fog"]), random.randint(8, 14))
                tick_weather()

            safe_clear()

        # Boss spawn logic
        if not boss_spawned and all(o["type"] != "enemy" for o in map_objects):
            boss_spawned = True
            try:
                pos = random_free_cell()
                map_objects.append({"type": "enemy", "name": "Boss Onix", "hp": ENEMIES["Boss Onix"]["hp"], "pos": pos})
                log(c("The ground trembles… A BOSS appears!", "status"))
            except Exception:
                # If for some reason no space, directly start fight at current pos
                enemy = {"type": "enemy", "name": "Boss Onix", "hp": ENEMIES["Boss Onix"]["hp"], "pos": my_position[:]}
                result = do_battle(enemy)
                if result != 'win':
                    end_game = True
                    safe_clear()
                    log("You were defeated. Game Over.")
                    summary_screen()
                    return

        # Victory?
        if boss_spawned and all((o["type"] != "enemy") for o in map_objects):
            safe_clear()
            log(c("Congratulations! You defeated ALL enemies and the Boss.", "bar_ok"))
            log("The end.")
            summary_screen()
            break

def reset_meta():
    global level, xp, xp_to_next, score, steps_taken, enemies_defeated
    global potions_used, superpotions_used, antidotes_used
    global total_damage_dealt, total_damage_taken, hit_streak, best_streak
    level = 1
    xp = 0
    xp_to_next = 100
    score = 0
    steps_taken = 0
    enemies_defeated = 0
    potions_used = 0
    superpotions_used = 0
    antidotes_used = 0
    total_damage_dealt = 0
    total_damage_taken = 0
    hit_streak = 0
    best_streak = 0

def summary_screen():
    log("")
    log(c("=== RUN SUMMARY ===", "hud"))
    log("Level: %d   XP: %d/%d   Score: %d" % (level, xp, xp_to_next, score))
    log("Enemies defeated:", enemies_defeated)
    log("Steps taken:", steps_taken)
    log("Damage dealt:", total_damage_dealt, "  Damage taken:", total_damage_taken)
    log("Potions used:", potions_used, "Super Potions used:", superpotions_used, "Antidotes used:", antidotes_used)
    log("Best combo streak:", best_streak)
    # tiny achievements
    if best_streak >= 6:
        log(c("Achievement: HOT STREAK (6+ combo)", "status"))
    if enemies_defeated >= 6:
        log(c("Achievement: ROAM SLAYER (6+ foes)", "status"))
    if score >= 100:
        log(c("Achievement: COIN HOARDER (100+)", "status"))
    log(c("===================", "hud"))

# ---------------- Tests (kept intentionally similar) ----------------
class GameTests(unittest.TestCase):
    def setUp(self):
        global ENABLE_COLOR, DEMO_MODE, QUIET, _DEMO_STEP_COUNT
        ENABLE_COLOR = False
        DEMO_MODE = True
        QUIET = True
        _DEMO_STEP_COUNT = 0
        random.seed(1234)

    def test_draw_bar_bounds(self):
        self.assertIn("(0/100)", draw_bar(0, 100))
        self.assertIn("(100/100)", draw_bar(150, 100))
        self.assertIn("(0/100)", draw_bar(-10, 100))

    def test_map_rectangular(self):
        for y in range(MAP_HEIGHT):
            self.assertEqual(len(obstacle_definition[y]), MAP_WIDTH)

    def test_free_cell(self):
        map_objects[:] = []
        map_objects.append({"type": "potion", "heal": 25, "pos": [1, 1]})
        for _ in range(20):
            x, y = random_free_cell()
            self.assertNotEqual([x, y], my_position)
            self.assertTrue(obstacle_definition[y][x] != "#")
            self.assertTrue(all(o["pos"] != [x, y] for o in map_objects))

    def test_populate_counts(self):
        map_objects[:] = []
        # Use original signature subset to preserve expectations; extras default to 0
        populate_map(5, 2, 1, 1, 0, 0)
        enemies = [o for o in map_objects if o["type"] == "enemy"]
        pots = [o for o in map_objects if o["type"] == "potion"]
        sups = [o for o in map_objects if o["type"] == "superpotion"]
        ants = [o for o in map_objects if o["type"] == "antidote"]
        self.assertEqual(len(enemies), 5)
        self.assertEqual(len(pots), 2)
        self.assertEqual(len(sups), 1)
        self.assertEqual(len(ants), 1)
        positions = [tuple(o["pos"]) for o in map_objects]
        self.assertEqual(len(positions), len(set(positions)))

    def test_enemy_turn_damage_range(self):
        e = {"name": "Machop", "hp": 100, "pos": [5, 5], "type": "enemy"}
        zeros = 0
        normals = 0
        for _ in range(60):
            dmg, eff, _msg = enemy_turn(e)
            self.assertTrue(dmg >= 0)
            if dmg == 0:
                zeros += 1
            if dmg >= 10:
                normals += 1
        self.assertTrue(zeros >= 1)
        self.assertTrue(normals >= 1)

    def test_demo_key_valid(self):
        ks = set()
        for _ in range(20):
            ks.add(read_key())
        self.assertTrue(ks.issubset({'w', 'a', 's', 'd', 'q'}))

    def test_antidote_usage(self):
        global player_poisoned, inventory, current_hp
        inventory["antidote"] = 1
        player_poisoned = True
        before = current_hp
        used = use_item("antidote")
        self.assertTrue(used)
        self.assertFalse(player_poisoned)
        self.assertEqual(current_hp, before)

    # Ensure draw_map does not crash in DEMO/QUIET mode
    def test_draw_map_no_crash(self):
        try:
            draw_map()
        except Exception as e:
            self.fail("draw_map raised an exception: %s" % e)

# ---------------- CLI ----------------

def parse_args(argv=None):
    p = argparse.ArgumentParser(description="ASCII PokeMaze++")
    p.add_argument("--test", action="store_true", help="Run tests and exit")
    p.add_argument("--demo", action="store_true", help="Force DEMO (no interactive input)")
    p.add_argument("--seed", type=int, help="RNG seed for reproducibility")
    p.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    p.add_argument("--enemies", type=int, default=DEFAULT_NUM_ENEMIES, help="Number of enemies")
    p.add_argument("--potions", type=int, default=DEFAULT_NUM_POTIONS, help="Number of Potions")
    p.add_argument("--superpotions", type=int, default=DEFAULT_NUM_SUPERPOTIONS, help="Number of Super Potions")
    p.add_argument("--antidotes", type=int, default=DEFAULT_NUM_ANTIDOTES, help="Number of Antidotes")
    p.add_argument("--coins", type=int, default=DEFAULT_NUM_COINS, help="Number of Coins")
    p.add_argument("--mystery", type=int, default=DEFAULT_NUM_MYSTERY, help="Number of Mystery tiles")
    p.add_argument("--hard", action="store_true", help="Hard mode")
    p.add_argument("--no-wrap", action="store_true", help="Disable wrap-around at map borders")
    p.add_argument("--quiet-title", action="store_true", help="Skip splash screen")
    return p.parse_args(argv)

if __name__ == "__main__":
    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)
    if args.test:
        os.environ["NO_COLOR"] = "1"
        try:
            # Ensure tests don't spam title
            args.quiet_title = True
        except Exception:
            pass
        try:
            unittest.main(argv=[sys.argv[0]], exit=False)
        except TypeError:
            unittest.main(argv=[sys.argv[0]])
    else:
        try:
            main(args)
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
