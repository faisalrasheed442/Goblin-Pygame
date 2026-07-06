"""Reusable UI widgets and HUD rendering."""
from __future__ import annotations

import pygame

from . import art
from .config import (WIDTH, HEIGHT, WHITE, BLACK, PANEL, PANEL_LIGHT, GOLD, RED, GREEN,
                     GEM, COIN, HP_BACK, HP_FILL, GREY)

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
            col = (60, 62, 74)
        elif self.hover:
            col = tuple(min(255, c + 30) for c in self.color)
        pygame.draw.rect(surf, col, self.rect, border_radius=10)
        pygame.draw.rect(surf, (0, 0, 0), self.rect, 3, border_radius=10)
        tc = WHITE if self.enabled else GREY
        if self.sub:
            text(surf, self.label, (self.rect.centerx, self.rect.centery - 12),
                 24, tc, center=True)
            text(surf, self.sub, (self.rect.centerx, self.rect.centery + 12),
                 16, (210, 214, 224) if self.enabled else GREY, center=True, bold=False)
        else:
            text(surf, self.label, self.rect.center, 26, tc, center=True)

    def clicked(self, pos):
        return self.enabled and self.rect.collidepoint(pos)


def draw_hud(surf, player, prog, stage_name, wave_text):
    # health bar
    panel_rect = pygame.Rect(14, 12, 300, 66)
    panel(surf, panel_rect, alpha=170)
    text(surf, "HP", (26, 20), 18, WHITE)
    bar(surf, 60, 22, 240, 16, player.hp / player.max_hp, HP_BACK, HP_FILL)
    text(surf, f"{max(0, int(player.hp))}/{int(player.max_hp)}", (60 + 240 + 8 - 60, 40), 15,
         (230, 200, 205), bold=False)
    # coins & gems
    ci = art.scaled_by_height("coin", 26)
    surf.blit(ci, (26, 46))
    text(surf, str(prog.coins), (56, 48), 22, COIN)
    gi = art.scaled_by_height("gem", 26)
    surf.blit(gi, (150, 46))
    text(surf, str(prog.gems), (180, 48), 22, GEM)

    # stage / wave (top-centre)
    text(surf, stage_name, (WIDTH // 2, 24), 26, WHITE, center=True)
    text(surf, wave_text, (WIDTH // 2, 52), 18, GOLD, center=True, bold=False)


def draw_boss_bar(surf, boss):
    w = 560
    x = WIDTH // 2 - w // 2
    y = 92
    text(surf, boss.name, (WIDTH // 2, y - 6), 22, (255, 210, 210), center=True)
    bar(surf, x, y + 14, w, 18, boss.hp / boss.max_hp, (46, 16, 20), (232, 74, 74), radius=8)
