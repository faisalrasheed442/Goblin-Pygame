"""Global configuration, tunables and colour palette for the game.

Everything that a designer might want to tweak lives here so that gameplay can be
balanced without hunting through the logic code.
"""

# ----------------------------------------------------------------------------
# Display
# ----------------------------------------------------------------------------
WIDTH = 960
HEIGHT = 540
FPS = 60
TITLE = "Goblin Slayer: Realms of the Fallen"

GROUND_Y = 470            # y coordinate of the floor line (top of the ground)
GRAVITY = 0.9             # downward acceleration (px / frame^2)
TERMINAL_VY = 22          # max fall speed

# ----------------------------------------------------------------------------
# Colours (used for HUD / effects; art itself is SVG)
# ----------------------------------------------------------------------------
WHITE = (238, 240, 246)
BLACK = (12, 14, 20)
GREY = (120, 128, 140)
DARK = (22, 26, 38)
PANEL = (28, 32, 48)
PANEL_LIGHT = (44, 50, 72)
GOLD = (255, 205, 84)
COIN = (255, 196, 60)
GEM = (120, 220, 255)
RED = (232, 74, 74)
GREEN = (86, 214, 120)
BLUE = (86, 158, 255)
PURPLE = (170, 120, 255)
HP_BACK = (60, 20, 28)
HP_FILL = (232, 74, 74)
XP_FILL = (120, 220, 255)

# ----------------------------------------------------------------------------
# Player base stats (upgrades add on top of these)
# ----------------------------------------------------------------------------
PLAYER = {
    "max_hp": 100,
    "speed": 5.0,
    "jump_v": 16.5,
    "damage": 10,
    "fire_cooldown": 22,      # frames between shots
    "melee_cooldown": 30,
    "melee_damage": 22,
    "width": 44,
    "height": 74,
    "iframes": 60,            # invulnerability frames after being hit
}

# Upgrade definitions: id -> (label, description, base_cost, cost_growth, max_level, per_level)
UPGRADES = {
    "damage":   ("Sharpened Blade", "+4 shot damage",       40, 1.6, 8, 4),
    "firerate": ("Swift Hands",     "-2 frames shot delay",  50, 1.7, 6, 2),
    "maxhp":    ("Iron Vigor",      "+25 max health",        45, 1.6, 8, 25),
    "speed":    ("Windstep",        "+0.6 move speed",       55, 1.8, 5, 0.6),
    "melee":    ("Ashblade Fury",   "+10 melee damage",      45, 1.7, 6, 10),
    "regen":    ("Life Font",       "heal 6 hp per wave",    70, 2.0, 4, 6),
}

# ----------------------------------------------------------------------------
# Realms / stages.  Each realm defines its palette, background key, waves and boss.
# waves: list of dicts describing what spawns.  count scales difficulty.
# ----------------------------------------------------------------------------
STAGES = [
    {
        "name": "The Whispering Woods",
        "bg": "forest",
        "ground_top": (74, 130, 74),
        "ground_bot": (36, 70, 40),
        "waves": [
            {"grunt": 3},
            {"grunt": 3, "archer": 1},
            {"grunt": 4, "bat": 2},
        ],
        "boss": "warlord",
        "story": "The forest that once sang now festers with goblin-kin.\n"
                 "Cut a path to their Warlord and reclaim the first Aether Crystal.",
    },
    {
        "name": "The Ember Wastes",
        "bg": "lava",
        "ground_top": (150, 66, 40),
        "ground_bot": (70, 26, 24),
        "waves": [
            {"grunt": 3, "archer": 2},
            {"grunt": 4, "bat": 3},
            {"grunt": 5, "archer": 2, "bat": 2},
        ],
        "boss": "embermaw",
        "story": "Rivers of fire carve the wastes. The beast Embermaw guards\n"
                 "the second crystal amid the ash. Do not be burned.",
    },
    {
        "name": "The Frozen Citadel",
        "bg": "ice",
        "ground_top": (120, 176, 210),
        "ground_bot": (52, 84, 120),
        "waves": [
            {"grunt": 4, "archer": 2, "bat": 2},
            {"grunt": 5, "archer": 3, "bat": 3},
            {"grunt": 6, "archer": 3, "bat": 4},
        ],
        "boss": "frostking",
        "story": "At the world's edge stands the Citadel of ice, where the\n"
                 "Goblin King himself waits upon a throne of frost. End it.",
    },
]

# ----------------------------------------------------------------------------
# Enemy archetype stats
# ----------------------------------------------------------------------------
ENEMIES = {
    "grunt":  {"hp": 30,  "speed": 1.8, "damage": 12, "coins": 5,  "w": 42, "h": 52, "kind": "melee"},
    "archer": {"hp": 22,  "speed": 1.2, "damage": 10, "coins": 8,  "w": 42, "h": 54, "kind": "ranged"},
    "bat":    {"hp": 16,  "speed": 2.6, "damage": 8,  "coins": 6,  "w": 40, "h": 34, "kind": "flyer"},
}

BOSSES = {
    "warlord":   {"hp": 420,  "speed": 2.2, "damage": 20, "coins": 120, "gems": 1, "w": 120, "h": 140},
    "embermaw":  {"hp": 680,  "speed": 2.6, "damage": 24, "coins": 180, "gems": 2, "w": 150, "h": 150},
    "frostking": {"hp": 1000, "speed": 2.8, "damage": 28, "coins": 260, "gems": 3, "w": 140, "h": 170},
}

# Difficulty growth applied per stage index (0-based) to enemy hp / damage.
STAGE_HP_SCALE = 0.18
STAGE_DMG_SCALE = 0.12
