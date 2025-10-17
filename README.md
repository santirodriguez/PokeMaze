# PokeMaze
a (allegedly! don't be ignorant!) poke snake mix # ASCII PokeMaze++
**A fast-paced ASCII roguelite maze with turn-based Pokémon-style battles.** Play as **Charmander** exploring an ASCII maze: collect coins, pick up items, handle changing weather, build up combos, level up, and face a **Boss fight** at the end. Runs entirely in the terminal — single Python file, no new dependencies.

> Fully compatible with **Python 2 and 3**. Tests included. Works on Linux, macOS, and Windows.

---

## Table of Contents

* [Quick Demo](#quick-demo)
* [Getting Started](#getting-started)
* [Goal](#goal)
* [Controls](#controls)
* [HUD and Map Symbols](#hud-and-map-symbols)
* [Battle System](#battle-system)
* [Weather](#weather)
* [Combo Meter](#combo-meter)
* [XP and Leveling](#xp-and-leveling)
* [Mystery Tiles (?)](#mystery-tiles-)
* [Items](#items)
* [Enemies](#enemies)
* [Boss Fight](#boss-fight)
* [Difficulty & CLI Flags](#difficulty--cli-flags)
* [Usage Examples](#usage-examples)
* [End-of-Run Summary](#end-of-run-summary)
* [Testing](#testing)
* [Compatibility & Optional Dependencies](#compatibility--optional-dependencies)
* [FAQ & Tips](#faq--tips)
* [Credits](#credits)

---

## Quick Demo

Run a non-interactive demo to see how it plays:

```bash
python pokemaze.py --demo --quiet-title
```

For reproducible runs, set a random seed:

```bash
python pokemaze.py --demo --seed 1234
```

---

## Getting Started

1. **Requirements**: Python 2.7+ or any Python 3.x.
2. **Run**:

   ```bash
   python pokemaze.py
   ```
3. (Optional) Disable ANSI colors:

   ```bash
   python pokemaze.py --no-color
   # or export NO_COLOR=1
   ```

---

## Goal

* Explore the maze and **defeat all enemies** to spawn and beat the **Boss Onix**.
* Collect **coins** (`$`) to increase your **Score**.
* Manage your **items**, **Flamethrower PP**, and **HP** carefully.
* Beware of **poison**, **weather effects**, and **roaming enemies** that move after your turn.

---

## Controls

* **Move**: `W A S D`
* **Help**: `h`
* **Quit**: `q` (asks confirmation if interactive)

**In Battle**:

* `A` → **Ember** (base dmg 10)
* `L` → **Flamethrower** (base dmg 12, uses **PP**)
* `R` → **Run** (50% success)
* `P` → **Potion** (+25 HP)
* `U` → **Super Potion** (+50 HP)
* `D` → **Antidote** (cures poison)
* `N` → **Nothing** (skip turn)

---

## HUD and Map Symbols

* **HUD** displays: HP (with bar), inventory (Pot/Sup/Ant), enemies left, PP, Level, XP, Score, Steps, Combo, and Weather.
* **Map symbols**:

  * `@` — you (Charmander)
  * `E` — enemies
  * `$` — coins
  * `?` — mystery tiles
  * `*` — items (Potion / Super Potion / Antidote)
  * `###` — wall

Map wraps around edges unless you disable it with `--no-wrap`.

---

## Battle System

* **Turn-based**: Enemy acts first, then you.
* Attacks have **miss**, **crit**, and **damage variance**.
* **Weather** can alter accuracy or power.
* **Poison** deals damage at the start of your turn.
* **Run** has a 50% escape chance; escaping repositions you safely.

**After winning a battle**:

* Gain +**20 Score**.
* Chance to **recover +10 HP**.
* Chance to **obtain a Potion**.
* Earn **XP** toward leveling up.

---

## Weather

Weather dynamically affects battles and exploration.

| Weather   | Effect                                  |
| --------- | --------------------------------------- |
| **Clear** | Neutral                                 |
| **Sunny** | Boosts Fire damage                      |
| **Rain**  | Reduces Fire damage                     |
| **Fog**   | Higher miss chance, weaker hits overall |

Weather lasts several turns and can reset or change randomly after a few moves.

---

## Combo Meter

* Consecutive hits increase your **combo streak**.
* Each streak adds **bonus damage** (up to +8 max).
* Breaking the streak (miss, skip, or item use) resets it.
* Satisfying “**COMBO!**” message included 😎

---

## XP and Leveling

* Earn XP by defeating enemies.
* On **Level Up**:

  * +10 Max HP (and heal +10 HP)
  * Every **2 levels**, +1 **Flamethrower PP**
* XP requirement grows each level.

---

## Mystery Tiles `?`

Stepping on a `?` triggers a random surprise:

* Heal a bit (+20 HP)
* Get **poisoned** (or small consolation score if already poisoned)
* Gain +1 **Flamethrower PP**
* **Coin rain!** (+5–15 Score)
* Spawn a **surprise enemy** nearby

---

## Items

* **Potion** — heals 25 HP
* **Super Potion** — heals 50 HP
* **Antidote** — cures poison

Displayed as `Pot`, `Sup`, and `Ant` in the HUD. Enemies may drop Potions after battles.

---

## Enemies

Classic Pokémon-style foes with distinct stats:

* **Machop** – balanced
* **Geodude** – tough, strong hits (`Rock Slide`)
* **Zubat** – fragile, high miss/crit
* **Onix** – tanky, varied attacks
* **Koffing** – may poison (`Poison Gas`)

Enemies **roam** between turns, adding constant pressure.

---

## Boss Fight

After all normal enemies are defeated, **Boss Onix** appears with high HP and deadly moves (`Stone Edge`, `Earth Shake`).
If there’s no free space, the boss battle starts immediately at your position.

---

## Difficulty & CLI Flags

Tweak gameplay from the command line:

| Flag               | Description                           | Default |
| ------------------ | ------------------------------------- | ------- |
| `--enemies N`      | Number of enemies                     | 6       |
| `--potions N`      | Number of Potions                     | 4       |
| `--superpotions N` | Super Potions                         | 2       |
| `--antidotes N`    | Antidotes                             | 2       |
| `--coins N`        | Coins                                 | 8       |
| `--mystery N`      | Mystery tiles                         | 4       |
| `--hard`           | Hard mode (more enemies, fewer items) | off     |
| `--no-wrap`        | Disable edge wrapping                 | off     |
| `--no-color`       | Disable ANSI colors                   | off     |
| `--demo`           | Non-interactive demo                  | off     |
| `--seed N`         | RNG seed                              | none    |
| `--quiet-title`    | Skip splash screen                    | off     |
| `--test`           | Run built-in tests                    | off     |

> **Note:** Hard mode scales enemy count and reduces healing items automatically.

---

## Usage Examples

* Normal run (no colors):

  ```bash
  python pokemaze.py --no-color
  ```
* Chaos mode (more enemies + mystery):

  ```bash
  python pokemaze.py --enemies 10 --mystery 8
  ```
* Demo, reproducible seed:

  ```bash
  python pokemaze.py --demo --seed 42 --quiet-title
  ```
* Hard mode without wrap:

  ```bash
  python pokemaze.py --hard --no-wrap
  ```

---

## End-of-Run Summary

After you win or lose, a summary displays:

* Level, XP, and **Score**
* Enemies defeated
* Steps taken
* Damage dealt/taken
* Items used
* **Best combo streak**
* Optional achievements:

  * *HOT STREAK* (6+ combo)
  * *ROAM SLAYER* (6+ foes)
  * *COIN HOARDER* (100+ Score)

---

## Testing

Built-in test suite (no extra dependencies):

```bash
python pokemaze.py --test
```

Tests cover: HP bar, map shape, placement collisions, enemy attack randomness, demo key validity, item usage, and map rendering.

---

## Compatibility & Optional Dependencies

* **No required dependencies**.
* **Optional**:

  * `readchar`: enables single-key input (otherwise falls back to `input()`).
  * `colorama` (Windows): fixes ANSI color support.
* Set `NO_COLOR=1` or `--no-color` for monochrome output.

---

## FAQ & Tips

**Can I run out of Flamethrower PP?**
Yes. Use **Ember** instead, or find `?` tiles that restore +1 PP.

**I’m poisoned, what now?**
Use an **Antidote**. If you don’t have one, heal often and hunt for `*` items.

**Do enemies chase me?**
They don’t pathfind, but they **roam randomly**, sometimes blocking or ambushing you.

**Is wrap-around worth it?**
Yes — it lets you teleport across edges for tactical movement. Disable it with `--no-wrap` for a more constrained experience.

**Can I pause?**
Not formally, but the game waits for input between steps and battles in interactive mode.

---

## Credits

* **ASCII PokeMaze++** — by FBS with community contributions.
