# Goblin Slayer: Realms of the Fallen

A complete action-platformer built with **pygame**. What began as a single static
screen with one goblin is now a full game: three hand-authored realms, waves of
enemies, a unique boss per realm, coins & gems, and a between-realm upgrade shop
that visibly evolves your knight.

**All artwork is generated procedurally as SVG** (see `goblinslayer/art.py`) and
rasterised through pygame's built-in nanosvg loader — there are no external image
files for the characters, enemies, bosses or backgrounds.

![Goblin Slayer](assets/svg/) <!-- art is generated on first run into assets/svg/ -->

## Story

The kingdom of Aethermoor has fallen to the Goblin King's dark legions. You are the
last Ashblade knight. Fight through three corrupted realms — the **Whispering Woods**,
the **Ember Wastes**, and the **Frozen Citadel** — defeat the realm guardians, reclaim
the Aether Crystals, and end the Goblin King himself.

## Features

- **3 realms** with distinct SVG parallax backgrounds, palettes and platform layouts.
- **3 bosses**, each with unique attack patterns (charge & slam, fireball volleys,
  ice spreads & falling icicles) and a health bar.
- **3 enemy archetypes** — melee grunts, ranged archers, and swooping bats — that
  scale in strength each realm.
- **Real platformer physics**: gravity, jump arcs, one-way platforms, knockback and
  invulnerability frames.
- **Rewards & upgrades**: enemies drop coins, hearts and (bosses) gems. Spend coins in
  the shop on six upgrades — damage, fire rate, max HP, speed, melee, and life regen.
- **Visible character progression**: your knight's armour changes tier (blue → crimson
  → violet, with an aura) as you invest in upgrades.
- **Polish**: particle effects, camera shake, floating damage numbers, screen states
  (title, story, pause, shop, game over, victory), music and SFX, and a persistent
  save file (`savegame.json`).

## Controls

| Action | Keys |
| ------ | ---- |
| Move   | `A` / `D` or `←` / `→` |
| Jump   | `W` / `↑` / `Space` |
| Shoot  | `J` / `Ctrl` |
| Slash (melee) | `K` / `L` |
| Pause  | `Esc` / `P` |
| Mute music | `M` |

## Running

```bash
# from the project root
python -m venv venv
venv\Scripts\activate          # Windows  (use: source venv/bin/activate on macOS/Linux)
pip install -r Requirements.txt
python main.py
```

## Regenerating / previewing the art

Every sprite can be regenerated on its own:

```bash
python -m goblinslayer.art      # writes all SVGs to assets/svg/
```

## Project layout

```
main.py                     # launcher
goblinslayer/
    config.py               # all tunables: stats, stages, waves, upgrades, palette
    art.py                  # SVG generation + surface loading/caching
    entities.py             # player, enemies, bosses, projectiles, pickups, particles
    progression.py          # upgrade levels, derived stats, currency, save/load
    ui.py                   # HUD, bars, buttons, panels
    game.py                 # state machine, main loop, runtime context
Game/                       # original audio assets (music, SFX) — reused
assets/svg/                 # generated SVG art (created on first run)
```
