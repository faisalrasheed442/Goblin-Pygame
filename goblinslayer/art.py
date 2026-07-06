"""Procedural SVG art generation and surface loading.

Every visible sprite in the game is authored here as an SVG document, written to
``assets/svg/`` and rasterised through pygame's built-in nanosvg loader.  Animation
is handled in the engine via transforms (bob / flip / rotate / scale) so each
character only needs a single, richly detailed still.

Nothing here depends on gameplay, so the art can be regenerated or previewed
independently by running ``python -m goblinslayer.art``.
"""
from __future__ import annotations

import os
import pygame

ASSET_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "svg")
ASSET_DIR = os.path.normpath(ASSET_DIR)

# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _svg(w: int, h: int, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">{body}</svg>'
    )


def _stops(stops):
    # each stop is (offset, color) or (offset, color, opacity)
    out = []
    for s in stops:
        if len(s) == 3:
            o, c, op = s
            out.append(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{op}"/>')
        else:
            o, c = s
            out.append(f'<stop offset="{o}" stop-color="{c}"/>')
    return "".join(out)


def _lin(id_, stops, x1, y1, x2, y2):
    """Linear gradient in absolute (userSpaceOnUse) coordinates.

    nanosvg (pygame's SVG backend) ignores objectBoundingBox gradients and falls
    back to a flat fill, so absolute coordinates are mandatory.
    """
    return (f'<linearGradient id="{id_}" gradientUnits="userSpaceOnUse" '
            f'x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{_stops(stops)}</linearGradient>')


def _rad(id_, stops, cx, cy, r):
    """Radial gradient in absolute (userSpaceOnUse) coordinates."""
    return (f'<radialGradient id="{id_}" gradientUnits="userSpaceOnUse" '
            f'cx="{cx}" cy="{cy}" r="{r}">{_stops(stops)}</radialGradient>')


# ===========================================================================
# HERO
# ===========================================================================

def hero_svg(armor="#4a78ff", armor_dark="#2545b0", cape="#ff5c7a",
             trim="#ffd24a", skin="#f2c9a0", hair="#3a2a44"):
    """Anime knight, facing right, feet at the bottom of a 100x130 canvas."""
    defs = (
        _lin("harmor", [("0", armor), ("1", armor_dark)], 0, 44, 0, 100) +
        _lin("hcape", [("0", cape), ("1", "#a02748")], 0, 34, 0, 110) +
        _lin("hblade", [("0", "#eef4ff"), ("0.5", "#b9c6e6"), ("1", "#8fa0c8")], 92, 40, 83, 72)
    )
    body = f'<defs>{defs}</defs>'
    # cape flowing behind
    body += f'<path d="M46 34 Q20 60 26 110 L40 104 Q44 70 58 44 Z" fill="url(#hcape)"/>'
    # back leg
    body += f'<path d="M44 92 L40 122 Q40 127 46 127 L52 127 L54 96 Z" fill="{armor_dark}"/>'
    body += f'<ellipse cx="46" cy="126" rx="10" ry="4" fill="#20233a"/>'
    # front leg
    body += f'<path d="M58 92 L56 123 Q56 128 62 128 L69 128 L66 94 Z" fill="url(#harmor)"/>'
    body += f'<ellipse cx="63" cy="127" rx="11" ry="4" fill="#20233a"/>'
    # torso armour
    body += (f'<path d="M42 50 Q56 40 70 50 L74 92 Q56 100 38 92 Z" '
             f'fill="url(#harmor)" stroke="{armor_dark}" stroke-width="2"/>')
    # chest emblem
    body += f'<path d="M56 60 L62 72 L56 84 L50 72 Z" fill="{trim}"/>'
    # belt
    body += f'<rect x="40" y="86" width="34" height="6" rx="3" fill="{trim}"/>'
    # back arm
    body += f'<path d="M44 54 Q34 64 40 78 L48 74 Q46 62 52 56 Z" fill="{armor_dark}"/>'
    # head
    body += f'<path d="M46 18 Q46 4 60 4 Q74 4 74 20 Q74 34 60 36 Q48 34 46 22 Z" fill="{hair}"/>'
    body += f'<circle cx="61" cy="24" r="12" fill="{skin}"/>'
    body += f'<path d="M49 20 Q46 6 62 5 Q58 14 58 22 Q52 24 49 20 Z" fill="{hair}"/>'  # fringe
    body += f'<circle cx="66" cy="24" r="2.4" fill="#20263a"/>'  # eye
    body += f'<path d="M62 30 Q66 32 70 30" stroke="#c78b6b" stroke-width="1.4" fill="none"/>'
    # shoulder pauldron
    body += f'<path d="M60 44 Q78 42 78 56 Q70 60 62 54 Z" fill="url(#harmor)" stroke="{armor_dark}" stroke-width="1.5"/>'
    body += f'<circle cx="72" cy="50" r="3" fill="{trim}"/>'
    # sword arm + blade held forward
    body += f'<path d="M64 56 Q80 58 86 70 L82 76 Q72 68 62 66 Z" fill="url(#harmor)"/>'
    body += f'<rect x="80" y="64" width="8" height="8" rx="2" fill="{trim}"/>'          # hilt guard
    body += f'<path d="M92 40 L98 44 L88 72 L83 70 Z" fill="url(#hblade)" stroke="#7d8cb0" stroke-width="0.8"/>'  # blade
    body += f'<circle cx="84" cy="76" r="2.6" fill="{trim}"/>'                          # pommel
    return _svg(100, 130, body)


def slash_svg(color="#bfe3ff"):
    body = f'<defs>{_lin("sl", [("0", "#ffffff"), ("1", color)], 10, 60, 118, 34)}</defs>'
    body += (f'<path d="M10 60 Q70 4 118 34 Q92 46 96 70 Q70 40 30 74 Q18 68 10 60 Z" '
             f'fill="url(#sl)" opacity="0.92"/>')
    body += f'<path d="M22 58 Q66 24 104 42" stroke="#ffffff" stroke-width="4" fill="none" opacity="0.9"/>'
    return _svg(128, 90, body)


# ===========================================================================
# ENEMIES
# ===========================================================================

def grunt_svg(body_col="#5aa02c", dark="#356013", eye="#ffcf3a"):
    d = _lin("gb", [("0", body_col), ("1", dark)], 0, 20, 0, 100)
    b = f'<defs>{d}</defs>'
    # club
    b += f'<path d="M70 40 L92 20 Q98 26 92 32 L74 52 Z" fill="#8a5a30"/>'
    b += f'<circle cx="92" cy="22" r="9" fill="#6b4324"/>'
    # legs
    b += f'<path d="M34 74 L30 96 Q30 100 36 100 L42 100 L44 78 Z" fill="{dark}"/>'
    b += f'<path d="M54 74 L52 96 Q52 100 58 100 L64 100 L64 78 Z" fill="{dark}"/>'
    # body (hunched)
    b += f'<path d="M28 46 Q48 32 70 46 Q74 70 60 82 Q44 88 32 80 Q22 66 28 46 Z" fill="url(#gb)"/>'
    b += f'<path d="M34 60 Q48 66 62 60" stroke="{dark}" stroke-width="2" fill="none"/>'
    # arm to club
    b += f'<path d="M60 52 Q72 46 76 44 L72 54 Q64 58 58 60 Z" fill="{body_col}"/>'
    # head
    b += f'<path d="M34 30 Q44 18 58 24 Q66 30 62 42 Q50 50 38 44 Q30 38 34 30 Z" fill="url(#gb)"/>'
    # ears
    b += f'<path d="M34 30 L22 24 L34 38 Z" fill="{body_col}"/>'
    b += f'<path d="M60 28 L72 20 L62 40 Z" fill="{body_col}"/>'
    # eyes + tusks
    b += f'<circle cx="46" cy="33" r="3" fill="{eye}"/><circle cx="46" cy="33" r="1.2" fill="#000"/>'
    b += f'<circle cx="56" cy="33" r="3" fill="{eye}"/><circle cx="56" cy="33" r="1.2" fill="#000"/>'
    b += f'<path d="M44 44 L42 50 L46 45 Z" fill="#fff"/><path d="M56 44 L58 50 L54 45 Z" fill="#fff"/>'
    return _svg(104, 104, b)


def archer_svg(body_col="#3c8f6a", dark="#1f5a40", eye="#ff5c3a"):
    d = _lin("ab", [("0", body_col), ("1", dark)], 0, 16, 0, 102)
    b = f'<defs>{d}</defs>'
    # bow
    b += f'<path d="M78 18 Q98 52 78 86" stroke="#7a4a24" stroke-width="5" fill="none"/>'
    b += f'<path d="M80 20 L80 84" stroke="#e8e0c8" stroke-width="1.5"/>'
    b += f'<path d="M36 52 L80 52" stroke="#d8d0b8" stroke-width="2"/>'          # arrow
    b += f'<path d="M80 52 L88 49 L88 55 Z" fill="#ccc"/>'
    # legs
    b += f'<path d="M34 74 L30 98 Q30 102 36 102 L42 102 L44 78 Z" fill="{dark}"/>'
    b += f'<path d="M52 74 L50 98 Q50 102 56 102 L62 102 L62 78 Z" fill="{dark}"/>'
    # cloaked body
    b += f'<path d="M26 44 Q46 30 66 44 Q70 68 56 82 Q42 88 30 80 Q20 62 26 44 Z" fill="url(#ab)"/>'
    b += f'<path d="M46 40 L46 82" stroke="{dark}" stroke-width="1.5"/>'
    # hood/head
    b += f'<path d="M32 34 Q46 16 62 32 Q60 46 46 48 Q34 46 32 34 Z" fill="url(#ab)"/>'
    b += f'<path d="M40 36 Q47 30 54 36 L52 42 Q46 44 42 42 Z" fill="#141b16"/>'
    b += f'<circle cx="46" cy="39" r="2.4" fill="{eye}"/>'
    return _svg(96, 108, b)


def bat_svg(body_col="#6a4a8f", dark="#3a2456", eye="#ff3a6a"):
    d = _lin("btb", [("0", body_col), ("1", dark)], 0, 18, 0, 56)
    b = f'<defs>{d}</defs>'
    # wings
    b += f'<path d="M40 34 Q10 12 4 40 Q14 40 18 50 Q28 42 40 46 Z" fill="url(#btb)"/>'
    b += f'<path d="M60 34 Q90 12 96 40 Q86 40 82 50 Q72 42 60 46 Z" fill="url(#btb)"/>'
    b += f'<path d="M40 34 Q22 30 12 44" stroke="{dark}" stroke-width="1.4" fill="none"/>'
    b += f'<path d="M60 34 Q78 30 88 44" stroke="{dark}" stroke-width="1.4" fill="none"/>'
    # body
    b += f'<ellipse cx="50" cy="42" rx="16" ry="14" fill="url(#btb)"/>'
    # ears
    b += f'<path d="M42 30 L38 18 L48 28 Z" fill="{body_col}"/>'
    b += f'<path d="M58 30 L62 18 L52 28 Z" fill="{body_col}"/>'
    # eyes + fangs
    b += f'<circle cx="44" cy="40" r="3" fill="{eye}"/><circle cx="56" cy="40" r="3" fill="{eye}"/>'
    b += f'<path d="M46 50 L44 56 L48 51 Z" fill="#fff"/><path d="M54 50 L56 56 L52 51 Z" fill="#fff"/>'
    return _svg(100, 68, b)


# ===========================================================================
# BOSSES
# ===========================================================================

def boss_warlord_svg():
    d = (_lin("wl", [("0", "#7fbf3a"), ("1", "#3f6d18")], 0, 44, 0, 196) +
         _lin("wlarm", [("0", "#8a6a3a"), ("1", "#4a3418")], 0, 78, 0, 108))
    b = f'<defs>{d}</defs>'
    # huge axe
    b += f'<path d="M150 30 L156 150 L146 150 L140 30 Z" fill="#6b5030"/>'
    b += f'<path d="M120 18 Q170 8 176 46 Q150 40 130 56 Q120 40 120 18 Z" fill="#c8ccd4" stroke="#8a90a0" stroke-width="2"/>'
    # legs
    b += f'<path d="M52 150 L46 190 Q46 196 56 196 L70 196 L72 154 Z" fill="#3f6d18"/>'
    b += f'<path d="M96 150 L94 190 Q94 196 104 196 L118 196 L116 154 Z" fill="#3f6d18"/>'
    # body
    b += f'<path d="M40 78 Q86 54 130 82 Q140 130 116 156 Q84 172 58 156 Q32 128 40 78 Z" fill="url(#wl)" stroke="#2c4d10" stroke-width="3"/>'
    # armour plate
    b += f'<path d="M60 90 Q86 80 112 92 L108 120 Q86 130 64 120 Z" fill="#4a3418" opacity="0.5"/>'
    b += f'<path d="M70 96 L86 128 L102 96" stroke="#2c4d10" stroke-width="3" fill="none"/>'
    # arm holding axe
    b += f'<path d="M112 86 Q140 78 150 96 L142 108 Q122 100 108 102 Z" fill="url(#wl)"/>'
    # head
    b += f'<path d="M56 44 Q86 20 116 44 Q116 70 86 78 Q56 70 56 44 Z" fill="url(#wl)"/>'
    b += f'<path d="M56 44 L34 36 L58 58 Z" fill="#7fbf3a"/>'
    b += f'<path d="M116 44 L138 36 L114 58 Z" fill="#7fbf3a"/>'
    # helmet horns
    b += f'<path d="M60 40 Q52 18 40 14 Q52 26 54 42 Z" fill="#e8e2d0"/>'
    b += f'<path d="M112 40 Q120 18 132 14 Q120 26 118 42 Z" fill="#e8e2d0"/>'
    # eyes
    b += f'<circle cx="76" cy="48" r="5" fill="#ff2a2a"/><circle cx="98" cy="48" r="5" fill="#ff2a2a"/>'
    b += f'<path d="M72 66 L70 76 L76 68 Z" fill="#fff"/><path d="M102 66 L104 76 L98 68 Z" fill="#fff"/>'
    return _svg(190, 200, b)


def boss_embermaw_svg():
    d = (_rad("em", [("0", "#ffd24a"), ("0.5", "#ff6a1e"), ("1", "#8a1e0e")], 90, 90, 70) +
         _lin("emw", [("0", "#ff8a3a"), ("1", "#7a1808")], 0, 20, 0, 96))
    b = f'<defs>{d}</defs>'
    # wings
    b += f'<path d="M60 60 Q6 20 8 90 Q34 74 60 96 Z" fill="url(#emw)" opacity="0.95"/>'
    b += f'<path d="M120 60 Q174 20 172 90 Q146 74 120 96 Z" fill="url(#emw)" opacity="0.95"/>'
    # tail
    b += f'<path d="M120 130 Q160 150 150 110 Q138 128 120 118 Z" fill="url(#emw)"/>'
    # legs
    b += f'<path d="M66 140 L60 176 Q60 182 70 182 L82 182 L84 146 Z" fill="#8a1e0e"/>'
    b += f'<path d="M104 140 L102 176 Q102 182 112 182 L124 182 L122 146 Z" fill="#8a1e0e"/>'
    # body
    b += f'<path d="M56 70 Q90 48 124 72 Q138 116 112 148 Q90 162 68 148 Q44 116 56 70 Z" fill="url(#em)" stroke="#5a1206" stroke-width="3"/>'
    # belly cracks (lava)
    b += f'<path d="M90 84 L86 150" stroke="#ffe07a" stroke-width="3" opacity="0.8"/>'
    b += f'<path d="M78 108 L98 108 M76 128 L100 124" stroke="#ffe07a" stroke-width="2.5" opacity="0.7"/>'
    # head
    b += f'<path d="M62 44 Q90 20 118 44 Q120 70 90 80 Q60 70 62 44 Z" fill="url(#em)"/>'
    # horns
    b += f'<path d="M66 40 Q56 14 44 8 Q58 24 60 44 Z" fill="#2a1008"/>'
    b += f'<path d="M114 40 Q124 14 136 8 Q122 24 120 44 Z" fill="#2a1008"/>'
    # jaw / teeth
    b += f'<path d="M70 66 Q90 82 110 66 L108 74 Q90 86 72 74 Z" fill="#2a1008"/>'
    b += f'<path d="M74 68 L76 76 L80 68 Z M86 70 L88 80 L92 70 Z M98 70 L100 80 L104 70 Z" fill="#fff"/>'
    # eyes
    b += f'<circle cx="78" cy="46" r="6" fill="#fff5c8"/><circle cx="78" cy="46" r="2.6" fill="#000"/>'
    b += f'<circle cx="102" cy="46" r="6" fill="#fff5c8"/><circle cx="102" cy="46" r="2.6" fill="#000"/>'
    return _svg(180, 190, b)


def boss_frostking_svg():
    d = (_lin("fk", [("0", "#bfe6ff"), ("1", "#4a78b0")], 0, 52, 0, 200) +
         _lin("fkr", [("0", "#7a5cff"), ("1", "#2a1e6a")], 0, 70, 0, 200) +
         _lin("fkg", [("0", "#eaf6ff"), ("1", "#7fb0e6")], 0, 8, 0, 40))
    b = f'<defs>{d}</defs>'
    # frozen cape/robe
    b += f'<path d="M46 70 Q86 52 124 70 L134 200 L36 200 Z" fill="url(#fkr)"/>'
    b += f'<path d="M60 90 Q86 100 110 90 L118 196 L52 196 Z" fill="url(#fk)" opacity="0.6"/>'
    # arms with ice staff
    b += f'<path d="M120 84 Q150 78 156 60 L150 30 L146 30 L150 62 Q140 74 116 96 Z" fill="url(#fk)"/>'
    b += f'<path d="M146 22 L154 22 L150 34 Z" fill="url(#fkg)"/>'                 # staff crystal
    b += f'<circle cx="150" cy="20" r="7" fill="url(#fkg)" stroke="#bfe6ff" stroke-width="1.5"/>'
    # head
    b += f'<circle cx="86" cy="52" r="22" fill="#cfe0ef"/>'
    b += f'<circle cx="78" cy="50" r="3" fill="#2a3a6a"/><circle cx="94" cy="50" r="3" fill="#2a3a6a"/>'
    b += f'<path d="M76 62 Q86 68 96 62" stroke="#2a3a6a" stroke-width="2" fill="none"/>'
    # beard
    b += f'<path d="M70 60 Q86 96 102 60 Q94 76 86 88 Q78 76 70 60 Z" fill="#eaf2fb"/>'
    # frozen crown
    b += f'<path d="M62 34 L68 12 L76 30 L86 8 L96 30 L104 12 L110 34 Z" fill="url(#fkg)" stroke="#8fbfe6" stroke-width="1.5"/>'
    b += f'<circle cx="86" cy="20" r="3" fill="#7a5cff"/>'
    return _svg(180, 210, b)


# ===========================================================================
# PROJECTILES / PICKUPS / FX
# ===========================================================================

def bolt_svg(color="#7fd0ff"):
    b = f'<defs>{_rad("bl", [("0", "#ffffff"), ("0.5", color), ("1", color, "0")], 16, 16, 15)}</defs>'
    b += f'<circle cx="16" cy="16" r="15" fill="url(#bl)"/>'
    b += f'<circle cx="16" cy="16" r="6" fill="#ffffff"/>'
    return _svg(32, 32, b)


def arrow_svg():
    b = f'<path d="M2 9 L24 9" stroke="#caa66a" stroke-width="3"/>'
    b += f'<path d="M24 4 L34 9 L24 14 Z" fill="#d8d8d8"/>'
    b += f'<path d="M2 4 L8 9 L2 14 Z" fill="#e05a3a"/>'
    return _svg(36, 18, b)


def fireball_svg():
    b = f'<defs>{_rad("fb", [("0", "#fff3b0"), ("0.4", "#ff8a2a"), ("1", "#c81e0e", "0")], 20, 20, 19)}</defs>'
    b += f'<circle cx="20" cy="20" r="19" fill="url(#fb)"/>'
    b += f'<circle cx="20" cy="20" r="8" fill="#fff0c0"/>'
    return _svg(40, 40, b)


def shard_svg():
    b = f'<defs>{_lin("sh", [("0", "#eaf6ff"), ("1", "#5a9ad6")], 0, 2, 0, 30)}</defs>'
    b += f'<path d="M14 2 L22 16 L14 30 L6 16 Z" fill="url(#sh)" stroke="#bfe6ff" stroke-width="1"/>'
    return _svg(28, 32, b)


def coin_svg():
    b = f'<defs>{_rad("co", [("0", "#fff2a0"), ("0.7", "#ffc632"), ("1", "#c8890e")], 16, 16, 14)}</defs>'
    b += f'<circle cx="16" cy="16" r="14" fill="url(#co)" stroke="#a8720a" stroke-width="1.5"/>'
    b += f'<circle cx="16" cy="16" r="9" fill="none" stroke="#fff0b0" stroke-width="1.5" opacity="0.7"/>'
    b += f'<path d="M13 10 L13 22 M19 10 L19 22 M13 16 L19 16" stroke="#a8720a" stroke-width="1.6"/>'
    return _svg(32, 32, b)


def gem_svg():
    b = f'<defs>{_lin("gm", [("0", "#dff6ff"), ("1", "#3aa0e6")], 0, 2, 0, 30)}</defs>'
    b += f'<path d="M16 2 L28 12 L16 30 L4 12 Z" fill="url(#gm)" stroke="#bfe6ff" stroke-width="1.2"/>'
    b += f'<path d="M4 12 L28 12 M16 2 L16 30 M10 7 L12 12 M22 7 L20 12" stroke="#ffffff" stroke-width="1" opacity="0.6"/>'
    return _svg(32, 32, b)


def heart_svg():
    b = f'<defs>{_rad("ht", [("0", "#ff9db0"), ("1", "#d81e3a")], 16, 12, 16)}</defs>'
    b += f'<path d="M16 28 Q4 18 4 11 Q4 4 10 4 Q14 4 16 9 Q18 4 22 4 Q28 4 28 11 Q28 18 16 28 Z" fill="url(#ht)" stroke="#a01020" stroke-width="1"/>'
    return _svg(32, 32, b)


# ===========================================================================
# ITEM / EFFECT ICONS
# ===========================================================================

def icon_potion_svg():
    b = f'<defs>{_lin("po", [("0", "#ff6a8a"), ("1", "#c81e3a")], 0, 12, 0, 30)}</defs>'
    b += f'<rect x="13" y="2" width="6" height="6" rx="1" fill="#caa"/>'
    b += f'<path d="M12 8 L20 8 L24 18 Q24 30 16 30 Q8 30 8 18 Z" fill="url(#po)" stroke="#7a1020" stroke-width="1.2"/>'
    b += f'<ellipse cx="16" cy="14" rx="5" ry="2" fill="#ffd0dc" opacity="0.7"/>'
    return _svg(32, 32, b)


def icon_shield_svg():
    b = f'<defs>{_lin("sd", [("0", "#bfe6ff"), ("1", "#3a78c8")], 0, 2, 0, 30)}</defs>'
    b += f'<path d="M16 2 L28 7 L28 16 Q28 27 16 31 Q4 27 4 16 L4 7 Z" fill="url(#sd)" stroke="#2a4a7a" stroke-width="1.4"/>'
    b += f'<path d="M16 8 L16 24 M9 14 L23 14" stroke="#eaf6ff" stroke-width="2" opacity="0.8"/>'
    return _svg(32, 32, b)


def icon_berserk_svg():
    b = f'<defs>{_rad("br", [("0", "#ffd24a"), ("1", "#e0401e")], 16, 16, 15)}</defs>'
    b += f'<circle cx="16" cy="16" r="14" fill="url(#br)" stroke="#8a1e0e" stroke-width="1.4"/>'
    b += f'<path d="M12 8 L20 8 L15 15 L20 15 L11 26 L14 16 L10 16 Z" fill="#fff3b0"/>'
    return _svg(32, 32, b)


def icon_relic_svg():
    b = f'<defs>{_lin("rl", [("0", "#f6d98a"), ("1", "#b07a2a")], 0, 2, 0, 30)}</defs>'
    b += f'<circle cx="16" cy="16" r="13" fill="url(#rl)" stroke="#7a5010" stroke-width="1.4"/>'
    b += f'<path d="M16 6 L19 13 L26 13 L20 18 L22 25 L16 21 L10 25 L12 18 L6 13 L13 13 Z" fill="#7a5010"/>'
    return _svg(32, 32, b)


# ===========================================================================
# BACKGROUNDS  (parallax layers, 1280x720; ground band drawn by the engine)
# Layers: sky (static) + far (slow scroll) + mid (faster scroll).  Far/mid keep
# their motifs away from the edges so they tile seamlessly when scrolled.
# ===========================================================================

def sky_forest_svg():
    d = _lin("sky", [("0", "#152a44"), ("0.55", "#2f5a6e"), ("1", "#5c8f5e")], 0, 0, 0, 720)
    b = f'<defs>{d}{_rad("moon", [("0", "#f6ffe8"), ("1", "#f6ffe8", "0")], 1030, 130, 70)}</defs>'
    b += f'<rect width="1280" height="720" fill="url(#sky)"/>'
    b += f'<circle cx="1030" cy="130" r="70" fill="url(#moon)"/><circle cx="1030" cy="130" r="42" fill="#eef7dd"/>'
    for x, y, r in [(160, 90, 2), (360, 70, 2.4), (560, 120, 1.8), (760, 60, 2), (900, 150, 2.2)]:
        b += f'<circle cx="{x}" cy="{y}" r="{r}" fill="#dfeecb" opacity="0.7"/>'
    return _svg(1280, 720, b)


def far_forest_svg():
    b = ''
    b += f'<path d="M0 440 Q320 360 640 430 Q960 500 1280 420 L1280 720 L0 720 Z" fill="#24463f" opacity="0.75"/>'
    for x, s in [(180, 0.9), (520, 0.7), (820, 1.0), (1080, 0.8)]:
        b += (f'<g transform="translate({x},600) scale({s})">'
              f'<rect x="-6" y="-70" width="12" height="80" fill="#16281f"/>'
              f'<path d="M0 -190 L44 -80 L-44 -80 Z" fill="#1a3126" opacity="0.85"/>'
              f'<path d="M0 -140 L36 -55 L-36 -55 Z" fill="#20392b" opacity="0.85"/></g>')
    return _svg(1280, 720, b)


def mid_forest_svg():
    b = ''
    b += f'<path d="M0 560 Q360 500 720 555 Q1000 590 1280 545 L1280 720 L0 720 Z" fill="#173026"/>'
    for x, s in [(120, 1.25), (420, 0.95), (700, 1.35), (980, 1.05), (1180, 0.9)]:
        b += (f'<g transform="translate({x},640) scale({s})">'
              f'<rect x="-7" y="-70" width="14" height="80" fill="#0f1e17"/>'
              f'<path d="M0 -210 L52 -80 L-52 -80 Z" fill="#12281d"/>'
              f'<path d="M0 -160 L44 -55 L-44 -55 Z" fill="#16301f"/>'
              f'<path d="M0 -115 L36 -32 L-36 -32 Z" fill="#1b3a26"/></g>')
    return _svg(1280, 720, b)


def sky_lava_svg():
    d = _lin("lsky", [("0", "#280c12"), ("0.5", "#7a1e12"), ("1", "#c8501c")], 0, 0, 0, 720)
    b = f'<defs>{d}{_rad("sun", [("0", "#ffe08a"), ("1", "#ff6a1e", "0")], 640, 180, 150)}</defs>'
    b += f'<rect width="1280" height="720" fill="url(#lsky)"/>'
    b += f'<circle cx="640" cy="180" r="150" fill="url(#sun)"/><circle cx="640" cy="180" r="60" fill="#ffb03a"/>'
    return _svg(1280, 720, b)


def far_lava_svg():
    b = ''
    b += f'<path d="M120 620 L360 250 L600 620 Z" fill="#3a1810" opacity="0.85"/>'
    b += f'<path d="M720 620 L980 210 L1240 620 Z" fill="#33140d" opacity="0.85"/>'
    b += f'<path d="M940 260 Q980 210 1020 260 Q1000 292 980 272 Q960 292 940 260 Z" fill="#ff7a2a" opacity="0.8"/>'
    b += f'<path d="M0 560 Q320 520 640 555 Q960 590 1280 545 L1280 720 L0 720 Z" fill="#4a1e12" opacity="0.6"/>'
    return _svg(1280, 720, b)


def mid_lava_svg():
    b = f'<defs>{_lin("glow", [("0", "#ff8a3a", "0.8"), ("1", "#ff3a1e", "0.3")], 0, 590, 0, 720)}</defs>'
    b += f'<path d="M0 600 Q360 560 720 600 Q1000 630 1280 590 L1280 720 L0 720 Z" fill="#5a1e10"/>'
    b += f'<path d="M0 640 Q360 610 720 645 Q1000 670 1280 640 L1280 720 L0 720 Z" fill="url(#glow)"/>'
    for x in (200, 520, 860, 1120):
        b += f'<path d="M{x-40} 660 Q{x} 600 {x+40} 660 Z" fill="#2a0e08"/>'
    return _svg(1280, 720, b)


def sky_ice_svg():
    d = _lin("isky", [("0", "#0a1830"), ("0.5", "#284f7e"), ("1", "#a9d2e6")], 0, 0, 0, 720)
    b = f'<defs>{d}{_lin("aur", [("0", "#7fffd4", "0.7"), ("1", "#8f8fff", "0")], 0, 120, 1280, 260)}</defs>'
    b += f'<rect width="1280" height="720" fill="url(#isky)"/>'
    b += f'<path d="M0 140 Q320 70 640 150 Q960 230 1280 120 L1280 240 Q960 320 640 230 Q320 170 0 260 Z" fill="url(#aur)" opacity="0.55"/>'
    for x, y in [(160, 90), (400, 70), (720, 120), (980, 80), (1150, 150), (280, 170), (860, 60)]:
        b += f'<circle cx="{x}" cy="{y}" r="2" fill="#eaf6ff"/>'
    return _svg(1280, 720, b)


def far_ice_svg():
    b = ''
    b += f'<path d="M40 500 L240 260 L440 500 Z" fill="#33547a" opacity="0.8"/>'
    b += f'<path d="M360 520 L640 230 L920 520 Z" fill="#3f608c" opacity="0.85"/>'
    b += f'<path d="M820 510 L1080 300 L1240 510 Z" fill="#33547a" opacity="0.8"/>'
    b += f'<path d="M360 520 L640 230 L720 350 L560 360 Z" fill="#cfe4f4" opacity="0.55"/>'
    return _svg(1280, 720, b)


def mid_ice_svg():
    b = ''
    b += f'<path d="M0 580 Q360 540 720 580 Q1000 610 1280 565 L1280 720 L0 720 Z" fill="#2a4a6e"/>'
    for x, s in [(180, 1.0), (520, 0.8), (900, 1.1), (1150, 0.7)]:
        b += (f'<g transform="translate({x},600) scale({s})">'
              f'<path d="M0 -120 L34 0 L-34 0 Z" fill="#3a5f88"/>'
              f'<path d="M0 -120 L14 -60 L-6 0 L-34 0 Z" fill="#cfe4f4" opacity="0.5"/></g>')
    return _svg(1280, 720, b)


# realm -> (sky, far, mid) layer sprite names
BG_LAYERS = {
    "forest": ("sky_forest", "far_forest", "mid_forest"),
    "lava": ("sky_lava", "far_lava", "mid_lava"),
    "ice": ("sky_ice", "far_ice", "mid_ice"),
}


# ===========================================================================
# Registry + generation + loading
# ===========================================================================

# name -> (generator callable, natural pixel size hint)
_REGISTRY = {
    "hero": hero_svg,
    # Upgrade tiers — the hero's armour visibly evolves as the player grows stronger.
    "hero_t1": lambda: hero_svg(armor="#e0483c", armor_dark="#8a1e18", cape="#ffcf4a",
                                trim="#fff0b0", hair="#2a1a2a"),
    "hero_t2": lambda: hero_svg(armor="#a878ff", armor_dark="#4a2aa0", cape="#5cf0d0",
                                trim="#eaf6ff", hair="#1a1030"),
    "slash": slash_svg,
    "grunt": grunt_svg,
    "archer": archer_svg,
    "bat": bat_svg,
    "boss_warlord": boss_warlord_svg,
    "boss_embermaw": boss_embermaw_svg,
    "boss_frostking": boss_frostking_svg,
    "bolt": bolt_svg,
    "arrow": arrow_svg,
    "fireball": fireball_svg,
    "shard": shard_svg,
    "coin": coin_svg,
    "gem": gem_svg,
    "heart": heart_svg,
    "icon_potion": icon_potion_svg,
    "icon_shield": icon_shield_svg,
    "icon_berserk": icon_berserk_svg,
    "icon_relic": icon_relic_svg,
    "sky_forest": sky_forest_svg,
    "far_forest": far_forest_svg,
    "mid_forest": mid_forest_svg,
    "sky_lava": sky_lava_svg,
    "far_lava": far_lava_svg,
    "mid_lava": mid_lava_svg,
    "sky_ice": sky_ice_svg,
    "far_ice": far_ice_svg,
    "mid_ice": mid_ice_svg,
}


def generate_all(force: bool = False) -> None:
    """Write every SVG document to the assets directory."""
    os.makedirs(ASSET_DIR, exist_ok=True)
    for name, fn in _REGISTRY.items():
        path = os.path.join(ASSET_DIR, name + ".svg")
        if force or not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(fn())


_base_cache: dict[str, pygame.Surface] = {}
_scaled_cache: dict[tuple, pygame.Surface] = {}


def base(name: str) -> pygame.Surface:
    """Load (and cache) a sprite at its natural SVG size."""
    if name not in _base_cache:
        path = os.path.join(ASSET_DIR, name + ".svg")
        if not os.path.exists(path):
            generate_all()
        _base_cache[name] = pygame.image.load(path).convert_alpha()
    return _base_cache[name]


def sprite(name: str, size: tuple[int, int]) -> pygame.Surface:
    """Return a crisp, cached sprite sized to ``size`` (w, h).

    Uses pygame-ce's ``load_sized_svg`` to rasterise the vector art directly at the
    requested resolution (sharp at any scale), falling back to smoothscale.
    """
    key = (name, int(size[0]), int(size[1]))
    if key not in _scaled_cache:
        path = os.path.join(ASSET_DIR, name + ".svg")
        if not os.path.exists(path):
            generate_all()
        try:
            surf = pygame.image.load_sized_svg(path, (key[1], key[2])).convert_alpha()
        except (AttributeError, pygame.error):
            surf = pygame.transform.smoothscale(base(name), (key[1], key[2]))
        _scaled_cache[key] = surf
    return _scaled_cache[key]


def scaled_by_height(name: str, height: int) -> pygame.Surface:
    """Scale preserving the sprite's aspect ratio to a target pixel height."""
    b = base(name)
    ratio = b.get_width() / b.get_height()
    return sprite(name, (int(height * ratio), height))


if __name__ == "__main__":
    # Standalone preview / regeneration entry point.
    generate_all(force=True)
    print(f"Wrote {len(_REGISTRY)} SVG assets to {ASSET_DIR}")
