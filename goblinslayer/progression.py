"""Player progression: upgrades, currency, consumables, equipment and save/load.

Meta-progression (what you've bought) persists between runs and feeds a fresh
:class:`Player` at the start of each stage.
"""
from __future__ import annotations

import json
import os

from .config import PLAYER, UPGRADES, CONSUMABLES, EQUIPMENT

SAVE_PATH = os.path.join(os.path.dirname(__file__), "..", "savegame.json")
SAVE_PATH = os.path.normpath(SAVE_PATH)


class Progression:
    def __init__(self):
        self.coins = 0
        self.gems = 0
        self.levels = {k: 0 for k in UPGRADES}
        self.stock = {k: 0 for k in CONSUMABLES}      # consumable counts
        self.relics = {k: False for k in EQUIPMENT}   # owned passive relics
        self.stage = 0            # highest stage reached (for continue)
        self.best_stage = 0

    # -- currency -----------------------------------------------------------
    def add_coins(self, n):
        self.coins += n

    def add_gems(self, n):
        self.gems += n

    # -- upgrades -----------------------------------------------------------
    def cost(self, key):
        base, growth, max_lvl = UPGRADES[key][2], UPGRADES[key][3], UPGRADES[key][4]
        lvl = self.levels[key]
        if lvl >= max_lvl:
            return None
        return int(round(base * (growth ** lvl)))

    def can_buy(self, key):
        c = self.cost(key)
        return c is not None and self.coins >= c

    def buy(self, key):
        if not self.can_buy(key):
            return False
        self.coins -= self.cost(key)
        self.levels[key] += 1
        return True

    def is_maxed(self, key):
        return self.levels[key] >= UPGRADES[key][4]

    # -- consumables --------------------------------------------------------
    def consumable_cost(self, key):
        return CONSUMABLES[key][2]

    def buy_consumable(self, key):
        c = self.consumable_cost(key)
        if self.coins < c or self.stock[key] >= 9:
            return False
        self.coins -= c
        self.stock[key] += 1
        return True

    def use_consumable(self, key):
        if self.stock.get(key, 0) > 0:
            self.stock[key] -= 1
            return True
        return False

    # -- equipment / relics -------------------------------------------------
    def relic_cost(self, key):
        return EQUIPMENT[key][2]

    def buy_relic(self, key):
        if self.relics.get(key) or self.gems < self.relic_cost(key):
            return False
        self.gems -= self.relic_cost(key)
        self.relics[key] = True
        return True

    def has(self, relic):
        return self.relics.get(relic, False)

    # -- derived combat stats ----------------------------------------------
    def stats(self):
        lv = self.levels
        speed = PLAYER["speed"] + lv["speed"] * UPGRADES["speed"][5]
        jump = PLAYER["jump_v"]
        if self.has("swiftboots"):
            speed *= 1.18
            jump *= 1.18
        s = {
            "max_hp": PLAYER["max_hp"] + lv["maxhp"] * UPGRADES["maxhp"][5],
            "speed": speed,
            "jump_v": jump,
            "damage": PLAYER["damage"] + lv["damage"] * UPGRADES["damage"][5],
            "fire_cooldown": max(6, PLAYER["fire_cooldown"] - lv["firerate"] * UPGRADES["firerate"][5]),
            "melee_damage": PLAYER["melee_damage"] + lv["melee"] * UPGRADES["melee"][5],
            "super_dmg": PLAYER["super_dmg"] + lv["super"] * UPGRADES["super"][5],
            "super_max": PLAYER["super_max"],
            # equipment passives
            "lifesteal": 0.10 if self.has("vampiric") else 0.0,
            "charge_mult": 1.35 if self.has("aethercore") else 1.0,
            "dmg_reduce": 0.18 if self.has("stoneheart") else 0.0,
            "tier": self.tier(),
        }
        return s

    def tier(self):
        total = sum(self.levels.values()) + sum(self.relics.values()) * 2
        if total >= 18:
            return 2
        if total >= 7:
            return 1
        return 0

    # -- persistence --------------------------------------------------------
    def to_dict(self):
        return {"coins": self.coins, "gems": self.gems, "levels": self.levels,
                "stock": self.stock, "relics": self.relics,
                "stage": self.stage, "best_stage": self.best_stage}

    def save(self):
        try:
            with open(SAVE_PATH, "w", encoding="utf-8") as fh:
                json.dump(self.to_dict(), fh, indent=2)
        except OSError:
            pass

    @classmethod
    def load(cls):
        p = cls()
        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            p.coins = int(data.get("coins", 0))
            p.gems = int(data.get("gems", 0))
            p.stage = int(data.get("stage", 0))
            p.best_stage = int(data.get("best_stage", 0))
            for k in p.levels:
                p.levels[k] = int(data.get("levels", {}).get(k, 0))
            for k in p.stock:
                p.stock[k] = int(data.get("stock", {}).get(k, 0))
            for k in p.relics:
                p.relics[k] = bool(data.get("relics", {}).get(k, False))
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return p

    @staticmethod
    def clear_save():
        try:
            os.remove(SAVE_PATH)
        except OSError:
            pass
