"""Game entities: the hero, enemies, bosses, projectiles, pickups and particles.

Physics model (shared): each body tracks a float position (top-left), velocity and
an ``on_ground`` flag.  Gravity is integrated every frame; horizontal motion is
driven by AI or input.  Collision is resolved against the ground line and a list of
one-way platforms (you land on them from above, pass through from below).

Entities never touch pygame drawing state beyond blitting sprites, and they report
back to the game via the lightweight ``ctx`` object passed into ``update`` — this is
how they spawn projectiles, particles and pickups without importing the game module.
"""
from __future__ import annotations

import math
import random

import pygame

from . import art
from .config import (GRAVITY, GROUND_Y, TERMINAL_VY, WIDTH, HEIGHT, PLAYER,
                     ENEMIES, BOSSES, RED, WHITE, COIN, GEM, GREEN)


# ---------------------------------------------------------------------------
# Particles & floating text
# ---------------------------------------------------------------------------
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "grav")

    def __init__(self, x, y, vx, vy, life, color, size, grav=0.25):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = size
        self.grav = grav

    def update(self):
        self.vy += self.grav
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        return self.life > 0

    def draw(self, s):
        a = max(0.0, self.life / self.max_life)
        r = max(1, int(self.size * a))
        col = (*self.color, int(255 * a))
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, col, (r, r), r)
        s.blit(surf, (self.x - r, self.y - r))


class FloatingText:
    def __init__(self, x, y, text, color, size=24):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = 45
        self.font = _get_font(size)

    def update(self):
        self.y -= 1.1
        self.life -= 1
        return self.life > 0

    def draw(self, s):
        a = max(0, min(255, int(255 * self.life / 45)))
        img = self.font.render(self.text, True, self.color)
        img.set_alpha(a)
        s.blit(img, (self.x - img.get_width() // 2, self.y))


_font_cache: dict[int, pygame.font.Font] = {}


def _get_font(size, bold=True):
    key = size * 10 + int(bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont("gotham,arialrounded,arial", size, bold=bold)
    return _font_cache[key]


def burst(ctx, x, y, color, n=10, speed=4, size=5, life=26, grav=0.25):
    for _ in range(n):
        a = random.uniform(0, math.tau)
        v = random.uniform(0.4, 1.0) * speed
        ctx.particles.append(Particle(x, y, math.cos(a) * v, math.sin(a) * v - 1,
                                      random.randint(life - 8, life + 8), color, size, grav))


# ---------------------------------------------------------------------------
# Pickups (coins / gems / hearts)
# ---------------------------------------------------------------------------
class Pickup:
    def __init__(self, x, y, kind):
        self.x, self.y = x, y
        self.kind = kind             # "coin" | "gem" | "heart"
        self.vx = random.uniform(-2.2, 2.2)
        self.vy = random.uniform(-7, -3)
        self.on_ground = False
        self.t = random.uniform(0, math.tau)
        self.collected = False
        self.magnet = False
        size = {"coin": 22, "gem": 26, "heart": 26}[kind]
        self.img = art.scaled_by_height(kind, size)
        self.r = size // 2

    def update(self, ctx):
        p = ctx.player
        cx, cy = self.x, self.y
        pcx, pcy = p.x + p.w / 2, p.y + p.h / 2
        dist = math.hypot(pcx - cx, pcy - cy)
        if dist < 120:
            self.magnet = True
        if self.magnet:
            ang = math.atan2(pcy - cy, pcx - cx)
            self.x += math.cos(ang) * 8
            self.y += math.sin(ang) * 8
        else:
            self.vy = min(self.vy + GRAVITY, TERMINAL_VY)
            self.x += self.vx
            self.y += self.vy
            floor = GROUND_Y - self.r
            if self.y >= floor:
                self.y = floor
                self.vy = 0
                self.vx *= 0.7
        self.t += 0.15
        if dist < 26:
            self.collected = True
        return not self.collected

    def draw(self, s):
        bob = math.sin(self.t) * 3
        s.blit(self.img, (self.x - self.img.get_width() / 2, self.y - self.img.get_height() / 2 + bob))


# ---------------------------------------------------------------------------
# Projectiles
# ---------------------------------------------------------------------------
class Projectile:
    def __init__(self, x, y, vx, vy, damage, sprite_name, size, friendly, spin=False):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.damage = damage
        self.friendly = friendly
        self.spin = spin
        self.angle = 0
        self.img = art.scaled_by_height(sprite_name, size)
        self.r = size // 2
        self.life = 240

    def update(self, ctx):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.spin:
            self.angle = (self.angle + 12) % 360
        return (self.life > 0 and -40 < self.x < WIDTH + 40 and -60 < self.y < HEIGHT + 40)

    @property
    def rect(self):
        return pygame.Rect(self.x - self.r, self.y - self.r, self.r * 2, self.r * 2)

    def draw(self, s):
        img = self.img
        if self.spin:
            img = pygame.transform.rotate(self.img, self.angle)
        elif self.vx < 0:
            img = pygame.transform.flip(self.img, True, False)
        s.blit(img, (self.x - img.get_width() / 2, self.y - img.get_height() / 2))


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
class Player:
    def __init__(self, stats):
        self.w = PLAYER["width"]
        self.h = PLAYER["height"]
        self.x = 120
        self.y = GROUND_Y - self.h
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = True
        self.facing = 1
        self.stats = stats                 # dict from progression (already includes upgrades)
        self.hp = stats["max_hp"]
        self.max_hp = stats["max_hp"]
        self.fire_cd = 0
        self.melee_cd = 0
        self.iframes = 0
        self.anim = 0.0
        self.moving = False
        self.slash_timer = 0
        self.squash = 1.0
        self.tier = stats.get("tier", 0)

    # -- combat state -------------------------------------------------------
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    @property
    def hitbox(self):
        return pygame.Rect(int(self.x + 8), int(self.y + 6), self.w - 16, self.h - 8)

    def take_damage(self, dmg, src_x, ctx):
        if self.iframes > 0:
            return
        self.hp -= dmg
        self.iframes = PLAYER["iframes"]
        self.vx = 7 if self.x > src_x else -7
        self.vy = -6
        ctx.add_text(self.x + self.w / 2, self.y, f"-{dmg}", RED)
        burst(ctx, self.x + self.w / 2, self.y + self.h / 2, RED, 12, 5)
        ctx.shake(8)
        ctx.play("hit")

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    # -- input / update -----------------------------------------------------
    def handle_input(self, keys, ctx):
        sp = self.stats["speed"]
        self.moving = False
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        if left and not right:
            self.vx = -sp
            self.facing = -1
            self.moving = True
        elif right and not left:
            self.vx = sp
            self.facing = 1
            self.moving = True
        else:
            self.vx *= 0.6 if self.on_ground else 0.9
        jump = keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]
        if jump and self.on_ground:
            self.vy = -self.stats["jump_v"]
            self.on_ground = False
            burst(ctx, self.x + self.w / 2, self.y + self.h, (200, 200, 200), 6, 2.5, 3, 16, 0.15)
        if keys[pygame.K_j] or keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]:
            self.shoot(ctx)
        if keys[pygame.K_k] or keys[pygame.K_l]:
            self.melee(ctx)

    def shoot(self, ctx):
        if self.fire_cd > 0:
            return
        self.fire_cd = int(self.stats["fire_cooldown"])
        bx = self.x + (self.w if self.facing > 0 else 0)
        by = self.y + self.h * 0.42
        ctx.player_shots.append(
            Projectile(bx, by, 12 * self.facing, 0, self.stats["damage"], "bolt", 26, True))
        ctx.play("bullet")
        burst(ctx, bx, by, (150, 220, 255), 4, 2.5, 3, 12, 0)

    def melee(self, ctx):
        if self.melee_cd > 0:
            return
        self.melee_cd = PLAYER["melee_cooldown"]
        self.slash_timer = 12
        reach = pygame.Rect(0, 0, 70, 70)
        if self.facing > 0:
            reach.midleft = (self.x + self.w - 6, self.y + self.h / 2)
        else:
            reach.midright = (self.x + 6, self.y + self.h / 2)
        ctx.register_melee(reach, self.stats["melee_damage"])

    def update(self, ctx):
        self.fire_cd = max(0, self.fire_cd - 1)
        self.melee_cd = max(0, self.melee_cd - 1)
        self.iframes = max(0, self.iframes - 1)
        self.slash_timer = max(0, self.slash_timer - 1)

        # physics
        self.vy = min(self.vy + GRAVITY, TERMINAL_VY)
        self.x += self.vx
        self.y += self.vy
        # arena bounds
        self.x = max(0, min(WIDTH - self.w, self.x))

        # ground + platform collision
        self.on_ground = False
        feet = self.y + self.h
        if feet >= GROUND_Y and self.vy >= 0:
            self.y = GROUND_Y - self.h
            self.vy = 0
            if not self.on_ground:
                self.squash = 0.82
            self.on_ground = True
        for plat in ctx.platforms:
            if self.vy >= 0 and self.rect.centerx > plat.left and self.rect.centerx < plat.right:
                prev_feet = feet - self.vy
                if prev_feet <= plat.top + 6 and feet >= plat.top:
                    self.y = plat.top - self.h
                    self.vy = 0
                    self.on_ground = True

        # anim
        if self.moving and self.on_ground:
            self.anim += 0.25
        else:
            self.anim += 0.08
        self.squash += (1.0 - self.squash) * 0.25

    def draw(self, s):
        name = ["hero", "hero_t1", "hero_t2"][min(self.tier, 2)]
        base = art.scaled_by_height(name, self.h + 14)
        # bob & squash
        bob = math.sin(self.anim) * (3 if self.moving else 1.5)
        sw = int(base.get_width() / self.squash)
        sh = int(base.get_height() * self.squash)
        img = pygame.transform.smoothscale(base, (sw, sh))
        if self.facing < 0:
            img = pygame.transform.flip(img, True, False)
        # upgrade aura
        if self.tier > 0:
            aura_col = [(0, 0, 0), (255, 200, 90), (150, 210, 255)][self.tier]
            glow = pygame.Surface((sw + 24, sh + 24), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (*aura_col, 60), glow.get_rect())
            s.blit(glow, (self.x + self.w / 2 - glow.get_width() / 2,
                          self.y + self.h / 2 - glow.get_height() / 2 + bob))
        # flashing when invulnerable
        if self.iframes % 8 < 4 or self.iframes == 0:
            ox = self.x + self.w / 2 - img.get_width() / 2
            oy = self.y + self.h - img.get_height() + bob
            s.blit(img, (ox, oy))
        # slash effect
        if self.slash_timer > 0:
            sl = art.scaled_by_height("slash", 80)
            if self.facing < 0:
                sl = pygame.transform.flip(sl, True, False)
            sl = sl.copy()
            sl.set_alpha(int(255 * self.slash_timer / 12))
            fx = self.x + self.w - 10 if self.facing > 0 else self.x - sl.get_width() + 10
            s.blit(sl, (fx, self.y + self.h / 2 - sl.get_height() / 2))


# ---------------------------------------------------------------------------
# Enemies
# ---------------------------------------------------------------------------
class Enemy:
    def __init__(self, kind, x, stage_index=0, palette=None):
        cfg = ENEMIES[kind]
        self.kind = kind
        self.role = cfg["kind"]
        self.w, self.h = cfg["w"], cfg["h"]
        hp_scale = 1 + stage_index * 0.18
        dmg_scale = 1 + stage_index * 0.12
        self.max_hp = int(cfg["hp"] * hp_scale)
        self.hp = self.max_hp
        self.speed = cfg["speed"]
        self.damage = int(cfg["damage"] * dmg_scale)
        self.coins = cfg["coins"]
        self.x = x
        self.y = (GROUND_Y - self.h) if self.role != "flyer" else random.randint(120, 260)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = self.role != "flyer"
        self.facing = -1
        self.anim = random.uniform(0, 10)
        self.attack_cd = random.randint(40, 90)
        self.hit_flash = 0
        self.dead = False
        self.sprite = kind
        self.base_y = self.y

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    @property
    def hitbox(self):
        return pygame.Rect(int(self.x + 4), int(self.y + 3), self.w - 8, self.h - 6)

    def take_damage(self, dmg, ctx, kx=0):
        self.hp -= dmg
        self.hit_flash = 6
        self.vx += kx
        ctx.add_text(self.x + self.w / 2, self.y - 6, str(dmg), WHITE, 20)
        burst(ctx, self.x + self.w / 2, self.y + self.h / 2, (255, 220, 120), 6, 4)
        if self.hp <= 0:
            self.die(ctx)

    def die(self, ctx):
        self.dead = True
        burst(ctx, self.x + self.w / 2, self.y + self.h / 2, (120, 200, 80), 18, 6, 6, 30)
        for _ in range(random.randint(2, 4)):
            ctx.pickups.append(Pickup(self.x + self.w / 2, self.y + self.h / 2, "coin"))
        if random.random() < 0.15:
            ctx.pickups.append(Pickup(self.x + self.w / 2, self.y + self.h / 2, "heart"))
        ctx.on_enemy_killed(self)

    def update(self, ctx):
        self.hit_flash = max(0, self.hit_flash - 1)
        self.attack_cd = max(0, self.attack_cd - 1)
        p = ctx.player
        pcx = p.x + p.w / 2
        self.facing = -1 if pcx < self.x + self.w / 2 else 1

        if self.role == "melee":
            self._ai_melee(ctx, pcx)
        elif self.role == "ranged":
            self._ai_ranged(ctx, pcx, p)
        elif self.role == "flyer":
            self._ai_flyer(ctx, p)

        # gravity for grounded enemies
        if self.role != "flyer":
            self.vy = min(self.vy + GRAVITY, TERMINAL_VY)
            self.y += self.vy
            if self.y + self.h >= GROUND_Y:
                self.y = GROUND_Y - self.h
                self.vy = 0
                self.on_ground = True
        self.x += self.vx
        self.x = max(-20, min(WIDTH - self.w + 20, self.x))
        self.vx *= 0.8 if self.role != "flyer" else 0.9
        self.anim += 0.2

        # contact damage
        if self.hitbox.colliderect(p.hitbox):
            p.take_damage(self.damage, self.x + self.w / 2, ctx)

    def _ai_melee(self, ctx, pcx):
        d = pcx - (self.x + self.w / 2)
        if abs(d) > 40:
            self.vx += math.copysign(self.speed * 0.5, d)
            self.vx = max(-self.speed, min(self.speed, self.vx))

    def _ai_ranged(self, ctx, pcx, p):
        d = pcx - (self.x + self.w / 2)
        # keep a standoff distance
        if abs(d) < 220:
            self.vx -= math.copysign(self.speed * 0.4, d)
        elif abs(d) > 320:
            self.vx += math.copysign(self.speed * 0.4, d)
        self.vx = max(-self.speed, min(self.speed, self.vx))
        if self.attack_cd == 0 and abs(d) < 420:
            self.attack_cd = random.randint(90, 140)
            ang = math.atan2((p.y + p.h / 2) - (self.y + self.h / 2), d)
            spd = 6.5
            ctx.enemy_shots.append(
                Projectile(self.x + self.w / 2, self.y + self.h / 2,
                           math.cos(ang) * spd, math.sin(ang) * spd, self.damage,
                           "arrow", 20, False))

    def _ai_flyer(self, ctx, p):
        tx = p.x + p.w / 2
        ty = p.y + p.h / 2 - 20
        ang = math.atan2(ty - (self.y + self.h / 2), tx - (self.x + self.w / 2))
        self.vx += math.cos(ang) * 0.25
        self.vy += math.sin(ang) * 0.2 + math.sin(self.anim) * 0.15
        self.vx = max(-self.speed, min(self.speed, self.vx))
        self.vy = max(-self.speed, min(self.speed, self.vy))
        self.y += self.vy
        self.y = max(60, min(GROUND_Y - self.h, self.y))

    def draw(self, s):
        img = art.scaled_by_height(self.sprite, self.h)
        if self.facing > 0:
            img = pygame.transform.flip(img, True, False)
        bob = math.sin(self.anim) * (2 if self.role != "flyer" else 4)
        if self.hit_flash > 0:
            img = img.copy()
            flash = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            flash.fill((255, 255, 255, 150))
            img.blit(flash, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        s.blit(img, (self.x + self.w / 2 - img.get_width() / 2, self.y + bob))
        self._draw_hp(s)

    def _draw_hp(self, s):
        if self.hp >= self.max_hp:
            return
        w = self.w
        x, y = self.x + self.w / 2 - w / 2, self.y - 10
        pygame.draw.rect(s, (30, 12, 16), (x, y, w, 5), border_radius=2)
        pygame.draw.rect(s, (86, 214, 120), (x, y, w * max(0, self.hp / self.max_hp), 5),
                         border_radius=2)


# ---------------------------------------------------------------------------
# Bosses
# ---------------------------------------------------------------------------
class Boss:
    def __init__(self, key, stage_index=0):
        cfg = BOSSES[key]
        self.key = key
        self.w, self.h = cfg["w"], cfg["h"]
        self.max_hp = cfg["hp"]
        self.hp = self.max_hp
        self.speed = cfg["speed"]
        self.damage = cfg["damage"]
        self.coins = cfg["coins"]
        self.gems = cfg["gems"]
        self.x = WIDTH - self.w - 60
        self.y = GROUND_Y - self.h
        self.vx = 0.0
        self.vy = 0.0
        self.facing = -1
        self.anim = 0.0
        self.hit_flash = 0
        self.dead = False
        self.state = "idle"
        self.state_t = 90
        self.attack_cd = 120
        self.sprite = "boss_" + key
        self.name = {"warlord": "Grukk the Warlord",
                     "embermaw": "Embermaw, the Ashborn",
                     "frostking": "The Goblin King"}[key]
        self.intro = 90

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    @property
    def hitbox(self):
        return pygame.Rect(int(self.x + 12), int(self.y + 10), self.w - 24, self.h - 16)

    def take_damage(self, dmg, ctx, kx=0):
        if self.intro > 0:
            return
        self.hp -= dmg
        self.hit_flash = 5
        ctx.add_text(self.x + self.w / 2, self.y - 4, str(dmg), WHITE, 22)
        burst(ctx, self.x + random.randint(0, self.w), self.y + random.randint(20, self.h),
              (255, 200, 120), 5, 4)
        if self.hp <= 0:
            self.die(ctx)

    def die(self, ctx):
        self.dead = True
        ctx.shake(24)
        for _ in range(40):
            burst(ctx, self.x + random.randint(0, self.w), self.y + random.randint(0, self.h),
                  (255, 180, 90), 6, 7, 40)
        for _ in range(int(self.coins // 8)):
            ctx.pickups.append(Pickup(self.x + random.randint(10, self.w - 10),
                                      self.y + self.h / 2, "coin"))
        for _ in range(self.gems):
            ctx.pickups.append(Pickup(self.x + self.w / 2 + random.randint(-30, 30),
                                      self.y + self.h / 2, "gem"))
        ctx.on_boss_killed(self)

    def update(self, ctx):
        self.hit_flash = max(0, self.hit_flash - 1)
        self.anim += 0.12
        p = ctx.player
        if self.intro > 0:
            self.intro -= 1
            return
        pcx = p.x + p.w / 2
        self.facing = -1 if pcx < self.x + self.w / 2 else 1
        self.state_t -= 1

        dispatch = {"warlord": self._ai_warlord,
                    "embermaw": self._ai_embermaw,
                    "frostking": self._ai_frostking}
        dispatch[self.key](ctx, p, pcx)

        # gravity / ground for grounded bosses
        if self.key != "embermaw":
            self.vy = min(self.vy + GRAVITY, TERMINAL_VY)
            self.y += self.vy
            if self.y + self.h >= GROUND_Y:
                self.y = GROUND_Y - self.h
                self.vy = 0
        self.x += self.vx
        self.x = max(0, min(WIDTH - self.w, self.x))
        self.vx *= 0.9

        if self.hitbox.colliderect(p.hitbox):
            p.take_damage(self.damage, self.x + self.w / 2, ctx)

    # ---- boss AIs ---------------------------------------------------------
    def _ai_warlord(self, ctx, p, pcx):
        d = pcx - (self.x + self.w / 2)
        if self.state == "idle":
            self.vx += math.copysign(self.speed * 0.4, d)
            self.vx = max(-self.speed, min(self.speed, self.vx))
            if self.state_t <= 0:
                self.state = random.choice(["charge", "slam", "charge"])
                self.state_t = 60
        elif self.state == "charge":
            self.vx += math.copysign(0.8, d)
            self.vx = max(-self.speed * 2.6, min(self.speed * 2.6, self.vx))
            if self.state_t <= 0:
                self.state, self.state_t = "idle", 90
        elif self.state == "slam":
            if self.vy == 0 and self.y + self.h >= GROUND_Y - 1:
                self.vy = -14
            if self.state_t <= 0 and self.y + self.h >= GROUND_Y - 1:
                ctx.shake(14)
                for i in (-1, 1):
                    ctx.enemy_shots.append(Projectile(
                        self.x + self.w / 2, GROUND_Y - 20, 7 * i, -2, self.damage,
                        "fireball", 30, False, spin=True))
                self.state, self.state_t = "idle", 90

    def _ai_embermaw(self, ctx, p, pcx):
        # hovers, bobbing, and rains fireballs
        target_y = 140 + math.sin(self.anim * 0.6) * 40
        self.y += (target_y - self.y) * 0.04
        d = pcx - (self.x + self.w / 2)
        self.x += math.copysign(min(abs(d) * 0.02, self.speed), d)
        self.attack_cd -= 1
        if self.attack_cd <= 0:
            self.attack_cd = 70
            if self.state == "idle":
                self.state, self.state_t = "volley", 3
        if self.state == "volley" and self.state_t >= 0 and self.attack_cd % 10 == 0:
            ang = math.atan2((p.y) - self.y, (p.x) - self.x)
            for off in (-0.25, 0, 0.25):
                ctx.enemy_shots.append(Projectile(
                    self.x + self.w / 2, self.y + self.h * 0.7,
                    math.cos(ang + off) * 6, math.sin(ang + off) * 6 + 1.5,
                    self.damage, "fireball", 34, False, spin=True))
            self.state = "idle"

    def _ai_frostking(self, ctx, p, pcx):
        d = pcx - (self.x + self.w / 2)
        if self.state == "idle":
            self.vx += math.copysign(self.speed * 0.3, d)
            self.vx = max(-self.speed, min(self.speed, self.vx))
            if self.state_t <= 0:
                self.state = random.choice(["spread", "rain", "spread"])
                self.state_t = 40
        elif self.state == "spread":
            if self.state_t == 20:
                for k in range(-3, 4):
                    ang = math.radians(180 + k * 14) if self.facing < 0 else math.radians(k * 14)
                    ctx.enemy_shots.append(Projectile(
                        self.x + self.w / 2, self.y + self.h * 0.4,
                        math.cos(ang) * 6, math.sin(ang) * 6, self.damage, "shard", 26, False, spin=True))
            if self.state_t <= 0:
                self.state, self.state_t = "idle", 80
        elif self.state == "rain":
            if self.state_t % 8 == 0:
                rx = random.randint(40, WIDTH - 40)
                ctx.enemy_shots.append(Projectile(rx, -20, 0, 7, self.damage, "shard", 26, False, spin=True))
            if self.state_t <= 0:
                self.state, self.state_t = "idle", 80

    def draw(self, s):
        img = art.scaled_by_height(self.sprite, self.h)
        if self.facing > 0:
            img = pygame.transform.flip(img, True, False)
        bob = math.sin(self.anim) * (5 if self.key == "embermaw" else 2)
        if self.intro > 0 and self.intro % 8 < 4:
            img = img.copy(); img.set_alpha(150)
        if self.hit_flash > 0:
            img = img.copy()
            flash = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            flash.fill((255, 255, 255, 150))
            img.blit(flash, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        s.blit(img, (self.x + self.w / 2 - img.get_width() / 2, self.y + bob))
