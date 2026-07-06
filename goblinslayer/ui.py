"""Reusable UI widgets and HUD rendering."""
from __future__ import annotations

import math

import pygame

from . import art
from .config import (WIDTH, HEIGHT, WHITE, PANEL, PANEL_LIGHT, GOLD, RED, GREEN,
                     GEM, COIN, HP_BACK, HP_FILL, SUPER_FILL, GREY, CONSUMABLES,
                     FPS)

_fonts: dict[tuple, pygame.font.Font] = {}


def font(size, bold=True):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont("gotham,arialrounded,arial", size, bold=bold)
    return _fonts[key]


def text(surf, s, pos, size=24, color=WHITE, center=False, bold=True, shadow=True):
    img = font(size, bold).render(s, True, color)
    r = img.get_rect()
    if center:
        r.center = pos
    else:
        r.topleft = pos
    if shadow:
        sh = font(size, bold).render(s, True, (0, 0, 0))
        sh.set_alpha(120)
        surf.blit(sh, (r.x + 2, r.y + 2))
    surf.blit(img, r)
    return r


def bar(surf, x, y, w, h, frac, back, fill, border=True, radius=6):
    frac = max(0.0, min(1.0, frac))
    pygame.draw.rect(surf, back, (x, y, w, h), border_radius=radius)
    if frac > 0:
        pygame.draw.rect(surf, fill, (x, y, int(w * frac), h), border_radius=radius)
    if border:
        pygame.draw.rect(surf, (0, 0, 0), (x, y, w, h), 2, border_radius=radius)


def panel(surf, rect, color=PANEL, border=PANEL_LIGHT, radius=14, alpha=235):
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, alpha), s.get_rect(), border_radius=radius)
    pygame.draw.rect(s, (*border, 255), s.get_rect(), 3, border_radius=radius)
    surf.blit(s, rect.topleft)


class Button:
    def __init__(self, rect, label, sub="", color=PANEL_LIGHT, enabled=True):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.sub = sub
        self.color = color
        self.enabled = enabled
        self.hover = False

    def update(self, mouse):
        self.hover = self.rect.collidepoint(mouse) and self.enabled

    def draw(self, surf):
        col = self.color
        if not self.enabled:
            col = (58, 60, 72)
        elif self.hover:
            col = tuple(min(255, c + 30) for c in self.color)
        pygame.draw.rect(surf, col, self.rect, border_radius=10)
        pygame.draw.rect(surf, (0, 0, 0), self.rect, 3, border_radius=10)
        tc = WHITE if self.enabled else GREY
        if self.sub:
            text(surf, self.label, (self.rect.centerx, self.rect.centery - 13), 23, tc, center=True)
            text(surf, self.sub, (self.rect.centerx, self.rect.centery + 13), 15,
                 (214, 218, 228) if self.enabled else GREY, center=True, bold=False)
        else:
            text(surf, self.label, self.rect.center, 26, tc, center=True)

    def clicked(self, pos):
        return self.enabled and self.rect.collidepoint(pos)


def _heart(surf, x, y, size, filled):
    img = art.scaled_by_height("heart", size)
    if not filled:
        img = img.copy()
        img.set_alpha(70)
    surf.blit(img, (x, y))


def draw_hud(surf, game):
    """Full in-battle HUD: health, super meter, currency, lives, consumables, buffs."""
    p = game.player
    prog = game.prog
    # main panel
    panel(surf, pygame.Rect(14, 12, 344, 104), alpha=175)
    text(surf, "HP", (26, 20), 18, WHITE)
    bar(surf, 66, 22, 250, 16, p.hp / p.max_hp, HP_BACK, HP_FILL)
    text(surf, f"{max(0, int(p.hp))}/{int(p.max_hp)}", (322, 22), 14, (230, 200, 205), bold=False)
    text(surf, "SUPER", (26, 46), 15, SUPER_FILL if p.super_ready else (170, 200, 220))
    bar(surf, 66, 48, 250, 12, p.super / p.super_max, (24, 34, 50), SUPER_FILL, radius=5)
    if p.super_ready:
        text(surf, "READY  (E)", (322, 46), 14, SUPER_FILL, bold=True)
    # currency
    ci = art.scaled_by_height("coin", 24); surf.blit(ci, (24, 72))
    text(surf, str(prog.coins), (52, 74), 20, COIN)
    gi = art.scaled_by_height("gem", 24); surf.blit(gi, (150, 72))
    text(surf, str(prog.gems), (178, 74), 20, GEM)

    # lives (hearts, top-left under panel)
    for i in range(max(game.lives, 0)):
        _heart(surf, 20 + i * 30, 122, 26, True)
    text(surf, "LIVES", (20 + max(game.lives, 0) * 30 + 6, 126), 16, (230, 200, 205), bold=False)

    # consumable slots (bottom-left)
    keys = list(CONSUMABLES.keys())
    icons = {"potion": "icon_potion", "shield": "icon_shield", "berserk": "icon_berserk"}
    sx, sy = 20, HEIGHT - 92
    for i, k in enumerate(keys):
        x = sx + i * 96
        r = pygame.Rect(x, sy, 88, 72)
        have = prog.stock[k]
        col = (34, 40, 58) if have > 0 else (28, 30, 40)
        pygame.draw.rect(surf, col, r, border_radius=8)
        pygame.draw.rect(surf, (0, 0, 0), r, 2, border_radius=8)
        icon = art.scaled_by_height(icons[k], 34)
        icon = icon if have > 0 else _fade(icon)
        surf.blit(icon, (x + 8, sy + 8))
        text(surf, f"x{have}", (x + 50, sy + 12), 20, WHITE if have else GREY)
        text(surf, CONSUMABLES[k][3], (x + 50, sy + 44), 16, GOLD if have else GREY, bold=False)

    # active buff timers (left, under the lives row)
    bx = 20
    if p.shield_t > 0:
        r = text(surf, f"SHIELD {p.shield_t // FPS + 1}s", (bx, 156), 18, SUPER_FILL)
        bx = r.right + 16
    if p.berserk_t > 0:
        text(surf, f"RAGE {p.berserk_t // FPS + 1}s", (bx, 156), 18, (255, 140, 80))


def _fade(img):
    img = img.copy()
    img.set_alpha(70)
    return img


def draw_boss_bar(surf, boss):
    w = 720
    x = WIDTH // 2 - w // 2
    y = 100
    text(surf, boss.name, (WIDTH // 2, y - 6), 24, (255, 210, 210), center=True)
    text(surf, f"Phase {boss.phase}/3", (x + w - 44, y - 6), 16, GOLD, bold=False)
    bar(surf, x, y + 16, w, 20, boss.hp / boss.max_hp, (46, 16, 20), (232, 74, 74), radius=8)
