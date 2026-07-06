"""Player progression: upgrade levels, derived stats, currency and save/load.

Kept separate from the live entities so the meta-progression (what you've bought in
the shop) persists between runs and cleanly feeds a fresh :class:`Player` each stage.
"""
from __future__ import annotations

import json
import math
import os

from .config import PLAYER, UPGRADES

SAVE_PATH = os.path.join(os.path.dirname(__file__), "..", "savegame.json")
SAVE_PATH = os.path.normpath(SAVE_PATH)


class Progression:
    def __init__(self):
        self.coins = 0
        self.gems = 0
        self.levels = {k: 0 for k in UPGRADES}
        self.stage = 0            # highest stage reached (for continue)

    # -- currency -----------------------------------------------------------
    def add_coins(self, n):
        self.coins += n

    def add_gems(self, n):
        self.gems += n

    # -- upgrades -----------------------------------------------------------
    def cost(self, key):
        label, desc, base, growth, max_lvl, per = UPGRADES[key]
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

    # -- derived combat stats ----------------------------------------------
    def stats(self):
        lv = self.levels
        s = {
            "max_hp": PLAYER["max_hp"] + lv["maxhp"] * UPGRADES["maxhp"][5],
            "speed": PLAYER["speed"] + lv["speed"] * UPGRADES["speed"][5],
            "jump_v": PLAYER["jump_v"],
            "damage": PLAYER["damage"] + lv["damage"] * UPGRADES["damage"][5],
            "fire_cooldown": max(6, PLAYER["fire_cooldown"] - lv["firerate"] * UPGRADES["firerate"][5]),
            "melee_damage": PLAYER["melee_damage"] + lv["melee"] * UPGRADES["melee"][5],
            "regen": lv["regen"] * UPGRADES["regen"][5],
        }
        s["tier"] = self.tier()
        return s

    def tier(self):
        total = sum(self.levels.values())
        if total >= 16:
            return 2
        if total >= 6:
            return 1
        return 0

    # -- persistence --------------------------------------------------------
    def to_dict(self):
        return {"coins": self.coins, "gems": self.gems,
                "levels": self.levels, "stage": self.stage}

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
            for k in p.levels:
                p.levels[k] = int(data.get("levels", {}).get(k, 0))
        except (OSError, ValueError, KeyError):
            pass
        return p

    @staticmethod
    def clear_save():
        try:
            os.remove(SAVE_PATH)
        except OSError:
            pass
