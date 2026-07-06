"""Scrolling parallax backgrounds and ambient weather.

Each realm is three SVG layers — a static sky plus a far and a mid layer that scroll
at different speeds — giving real depth and making the world feel alive even when the
hero stands still.  On top, per-realm ambient particles drift (fireflies, rising
embers, falling snow).
"""
from __future__ import annotations

import math
import random

import pygame

from . import art
from .config import WIDTH, HEIGHT, GROUND_Y


class ParallaxBackground:
    def __init__(self, realm: str, ambient: str):
        self.realm = realm
        self.ambient = ambient
        sky, far, mid = art.BG_LAYERS[realm]
        self.sky = art.sprite(sky, (WIDTH, HEIGHT))
        self.far = art.sprite(far, (WIDTH, HEIGHT))
        self.mid = art.sprite(mid, (WIDTH, HEIGHT))
        self.off = 0.0
        self.parts: list[dict] = []
        for _ in range(70):
            self.parts.append(self._new_part(initial=True))

    # -- ambient particles --------------------------------------------------
    def _new_part(self, initial=False):
        if self.ambient == "fireflies":
            return {"x": random.uniform(0, WIDTH), "y": random.uniform(120, GROUND_Y - 20),
                    "vx": random.uniform(-0.4, 0.4), "vy": random.uniform(-0.3, 0.3),
                    "r": random.uniform(1.5, 3.0), "c": (216, 255, 138),
                    "ph": random.uniform(0, math.tau)}
        if self.ambient == "embers":
            y = random.uniform(0, HEIGHT) if initial else HEIGHT + 10
            return {"x": random.uniform(0, WIDTH), "y": y,
                    "vx": random.uniform(-0.5, 0.5), "vy": random.uniform(-1.8, -0.8),
                    "r": random.uniform(1.5, 3.5), "c": (255, 180, 90),
                    "ph": random.uniform(0, math.tau)}
        # snow
        y = random.uniform(0, HEIGHT) if initial else -10
        return {"x": random.uniform(0, WIDTH), "y": y,
                "vx": random.uniform(-0.6, 0.6), "vy": random.uniform(1.0, 2.4),
                "r": random.uniform(1.5, 3.5), "c": (234, 246, 255),
                "ph": random.uniform(0, math.tau)}

    def update(self, scroll_bias=0.0):
        # continuous slow drift + a nudge from player movement for parallax feel
        self.off += 0.6 + scroll_bias
        for p in self.parts:
            p["ph"] += 0.05
            p["x"] += p["vx"] + (math.sin(p["ph"]) * 0.4 if self.ambient != "snow" else 0)
            p["y"] += p["vy"]
            if self.ambient == "fireflies":
                if p["x"] < -10 or p["x"] > WIDTH + 10 or p["y"] < 100 or p["y"] > GROUND_Y:
                    p.update(self._new_part())
            elif self.ambient == "embers":
                if p["y"] < -10:
                    p.update(self._new_part())
            else:  # snow
                if p["y"] > HEIGHT + 10:
                    p.update(self._new_part())
                p["x"] %= WIDTH

    def draw(self, s):
        s.blit(self.sky, (0, 0))
        for layer, spd in ((self.far, 0.3), (self.mid, 0.6)):
            o = int(self.off * spd) % WIDTH
            s.blit(layer, (-o, 0))
            s.blit(layer, (WIDTH - o, 0))

    def draw_ambient(self, s):
        for p in self.parts:
            if self.ambient == "fireflies":
                a = int(120 + 100 * (math.sin(p["ph"]) * 0.5 + 0.5))
            else:
                a = 180
            r = max(1, int(p["r"]))
            surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p["c"], a), (r + 1, r + 1), r)
            s.blit(surf, (p["x"] - r, p["y"] - r))
