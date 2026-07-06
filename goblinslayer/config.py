"""Global configuration, tunables and colour palette for the game.

Everything a designer might want to balance lives here so gameplay can be tuned
without touching the logic code.
"""

# ----------------------------------------------------------------------------
# Display  (logical resolution — the game renders here, then scales to any window)
# ----------------------------------------------------------------------------
WIDTH = 1280
HEIGHT = 720
FPS = 60
TITLE = "Goblin Slayer: Realms of the Fallen"

GROUND_Y = 620            # y coordinate of the floor line (top of the ground band)
GRAVITY = 0.9             # downward acceleration (px / frame^2)
TERMINAL_VY = 24          # max fall speed

# ----------------------------------------------------------------------------
# Colours (HUD / effects; the art itself is SVG)
# ----------------------------------------------------------------------------
WHITE = (238, 240, 246)
BLACK = (12, 14, 20)
GREY = (120, 128, 140)
DARK = (22, 26, 38)
PANEL = (26, 30, 46)
PANEL_LIGHT = (44, 50, 72)
GOLD = (255, 205, 84)
COIN = (255, 196, 60)
GEM = (120, 220, 255)
RED = (232, 74, 74)
GREEN = (86, 214, 120)
BLUE = (86, 158, 255)
PURPLE = (170, 120, 255)
ORANGE = (255, 150, 70)
HP_BACK = (60, 20, 28)
HP_FILL = (232, 74, 74)
SUPER_FILL = (120, 220, 255)
SHIELD_COL = (120, 200, 255)

# ----------------------------------------------------------------------------
# Player base stats (upgrades add on top of these)
# ----------------------------------------------------------------------------
LIVES_START = 3

PLAYER = {
    "max_hp": 100,
    "speed": 6.0,
    "jump_v": 18.0,
    "damage": 12,
    "fire_cooldown": 18,      # frames between shots
    "melee_cooldown": 26,
    "melee_damage": 26,
    "width": 52,
    "height": 92,
    "iframes": 55,            # invulnerability frames after being hit
    "super_max": 100,         # charge needed for the super attack
    "super_dmg": 140,         # base nova damage
}

# Super charge gained from actions
CHARGE_PER_HIT = 1.2         # per shot that connects
CHARGE_PER_KILL = 14
CHARGE_PER_SECOND = 1.5      # slow passive trickle (per second)

# Upgrade definitions: id -> (label, description, base_cost, cost_growth, max_level, per_level)
UPGRADES = {
    "damage":   ("Sharpened Blade", "+4 shot damage",        40, 1.55, 8, 4),
    "firerate": ("Swift Hands",     "-1.5 frames shot delay", 50, 1.65, 6, 1.5),
    "maxhp":    ("Iron Vigor",      "+25 max health",         45, 1.55, 8, 25),
    "speed":    ("Windstep",        "+0.5 move speed",        55, 1.75, 5, 0.5),
    "melee":    ("Ashblade Fury",   "+12 melee damage",       45, 1.65, 6, 12),
    "super":    ("Aether Surge",    "+18 super damage",       60, 1.7,  6, 18),
}

# Consumables — bought in the shop, used with number keys in battle.
CONSUMABLES = {
    "potion":  ("Health Potion", "Restore 45 HP",          35, "1"),
    "shield":  ("Aegis Charm",   "Absorb damage for 5s",   55, "2"),
    "berserk": ("Rage Draught",  "+60% damage for 7s",     60, "3"),
}

# Equipment / relics — bought with gems, permanent passive bonuses.
EQUIPMENT = {
    "vampiric": ("Vampiric Edge", "10% lifesteal",       2),
    "aethercore": ("Aether Core", "+35% super charge",   3),
    "stoneheart": ("Stoneheart",  "-18% damage taken",   3),
    "swiftboots": ("Swift Boots", "+18% move & jump",    2),
}

# ----------------------------------------------------------------------------
# Realms / stages.
# behavior: per-stage gameplay modifier so each realm plays differently.
# ----------------------------------------------------------------------------
STAGES = [
    {
        "name": "The Whispering Woods",
        "bg": "forest",
        "ground_top": (74, 130, 74),
        "ground_bot": (30, 62, 36),
        "ambient": "fireflies",
        "behavior": "normal",
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
        "ground_bot": (60, 22, 20),
        "ambient": "embers",
        "behavior": "meteors",          # fireballs rain from the sky at random
        "waves": [
            {"grunt": 3, "archer": 2},
            {"grunt": 4, "bat": 3},
            {"grunt": 5, "archer": 2, "bat": 2},
        ],
        "boss": "embermaw",
        "story": "Rivers of fire carve the wastes, and molten hail falls from a\n"
                 "burning sky. The beast Embermaw guards the second crystal.",
    },
    {
        "name": "The Frozen Citadel",
        "bg": "ice",
        "ground_top": (120, 176, 210),
        "ground_bot": (44, 74, 108),
        "ambient": "snow",
        "behavior": "ice",              # slippery ground — momentum carries
        "waves": [
            {"grunt": 4, "archer": 2, "bat": 2},
            {"grunt": 5, "archer": 3, "bat": 3},
            {"grunt": 6, "archer": 3, "bat": 4},
        ],
        "boss": "frostking",
        "story": "At the world's edge stands the Citadel of ice, its floors slick\n"
                 "as glass. The Goblin King waits upon a throne of frost. End it.",
    },
]

# ----------------------------------------------------------------------------
# Enemy archetype stats
# ----------------------------------------------------------------------------
ENEMIES = {
    "grunt":  {"hp": 32,  "speed": 2.0, "damage": 12, "coins": 5,  "w": 54, "h": 66, "kind": "melee"},
    "archer": {"hp": 24,  "speed": 1.4, "damage": 10, "coins": 8,  "w": 54, "h": 68, "kind": "ranged"},
    "bat":    {"hp": 18,  "speed": 3.0, "damage": 8,  "coins": 6,  "w": 52, "h": 44, "kind": "flyer"},
}

BOSSES = {
    "warlord":   {"hp": 480,  "speed": 2.4, "damage": 18, "coins": 130, "gems": 1, "w": 150, "h": 176},
    "embermaw":  {"hp": 760,  "speed": 2.8, "damage": 22, "coins": 190, "gems": 2, "w": 190, "h": 200},
    "frostking": {"hp": 1120, "speed": 3.0, "damage": 26, "coins": 280, "gems": 3, "w": 180, "h": 220},
}

# Difficulty growth applied per stage index (0-based) to enemy hp / damage.
STAGE_HP_SCALE = 0.18
STAGE_DMG_SCALE = 0.12
