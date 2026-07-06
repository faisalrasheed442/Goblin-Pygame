"""Game entities: the hero, enemies, bosses, projectiles, pickups and particles.

Physics model (shared): each body tracks a float position (top-left), velocity and
an ``on_ground`` flag.  Gravity is integrated every frame; horizontal motion is
driven by AI or input.  Collision is resolved against the ground line and a list of
one-way platforms (you land on them from above, pass through from below).

Bosses use a *fully randomised* phase-based AI: every action is chosen at random
from a phase-dependent pool, and every numeric parameter (angles, counts, speeds,
telegraph and recovery times) is randomised each time — so patterns are genuinely
unpredictable rather than a fixed rotation.

Entities affect the world only through the lightweight ``ctx`` (the Game) passed
into ``update`` — spawning projectiles/particles/pickups, shaking the camera, etc.
"""
from __future__ import annotations

import math
import random

import pygame

from . import art
from .config import (GRAVITY, GROUND_Y, TERMINAL_VY, WIDTH, HEIGHT, PLAYER,
                     ENEMIES, BOSSES, RED, WHITE, GREEN, GEM, SHIELD_COL,
                     CHARGE_PER_HIT, CHARGE_PER_KILL, STAGE_HP_SCALE, STAGE_DMG_SCALE)


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
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, int(255 * a)), (r, r), r)
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


def _get_font(size):
    if size not in _font_cache:
        _font_cache[size] = pygame.font.SysFont("gotham,arialrounded,arial", size, bold=True)
    return _font_cache[size]


def burst(ctx, x, y, color, n=10, speed=4, size=5, life=26, grav=0.25):
    for _ in range(n):
        a = random.uniform(0, math.tau)
        v = random.uniform(0.4, 1.0) * speed
        ctx.particles.append(Particle(x, y, math.cos(a) * v, math.sin(a) * v - 1,
                                      random.randint(max(6, life - 8), life + 8), color, size, grav))


def ring(ctx, x, y, color, n=28, speed=9, size=6, life=30):
    for i in range(n):
        a = math.tau * i / n
        ctx.particles.append(Particle(x, y, math.cos(a) * speed, math.sin(a) * speed,
                                      life, color, size, grav=0.0))


# ---------------------------------------------------------------------------
# Pickups (coins / gems / hearts)
# ---------------------------------------------------------------------------
class Pickup:
    def __init__(self, x, y, kind):
        self.x, self.y = x, y
        self.kind = kind
        self.vx = random.uniform(-2.6, 2.6)
        self.vy = random.uniform(-8, -3.5)
        self.t = random.uniform(0, math.tau)
        self.collected = False
        self.magnet = False
        size = {"coin": 24, "gem": 30, "heart": 28}[kind]
        self.img = art.scaled_by_height(kind, size)
        self.r = size // 2

    def update(self, ctx):
        p = ctx.player
        pcx, pcy = p.x + p.w / 2, p.y + p.h / 2
        dist = math.hypot(pcx - self.x, pcy - self.y)
        if dist < 150:
            self.magnet = True
        if self.magnet:
            ang = math.atan2(pcy - self.y, pcx - self.x)
            self.x += math.cos(ang) * 10
            self.y += math.sin(ang) * 10
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
        if dist < 32:
            self.collected = True
        return not self.collected

    def draw(self, s):
        bob = math.sin(self.t) * 3
        s.blit(self.img, (self.x - self.img.get_width() / 2, self.y - self.img.get_height() / 2 + bob))


# ---------------------------------------------------------------------------
# Projectiles
# ---------------------------------------------------------------------------
class Projectile:
    def __init__(self, x, y, vx, vy, damage, sprite_name, size, friendly, spin=False, gravity=0.0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.damage = damage
        self.friendly = friendly
        self.spin = spin
        self.gravity = gravity
        self.angle = 0
        self.img = art.scaled_by_height(sprite_name, size)
        self.r = size // 2
        self.life = 300

    def update(self, ctx):
        if self.gravity:
            self.vy += self.gravity
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.spin:
            self.angle = (self.angle + 12) % 360
        return (self.life > 0 and -60 < self.x < WIDTH + 60 and -80 < self.y < HEIGHT + 60)

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
        self.x = 160
        self.y = GROUND_Y - self.h
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = True
        self.facing = 1
        self.stats = stats
        self.hp = stats["max_hp"]
        self.max_hp = stats["max_hp"]
        self.fire_cd = 0
        self.melee_cd = 0
        self.iframes = 0
        self.anim = 0.0
        self.moving = False
        self.slash_timer = 0
        self.squash = 1.0
        self.recoil = 0.0
        self.tier = stats.get("tier", 0)
        # super meter + buffs
        self.super = 0.0
        self.super_max = stats["super_max"]
        self.shield_t = 0
        self.berserk_t = 0
        self.friction = 0.6          # ground friction (stage behaviour may lower it)

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    @property
    def hitbox(self):
        return pygame.Rect(int(self.x + 10), int(self.y + 8), self.w - 20, self.h - 10)

    @property
    def super_ready(self):
        return self.super >= self.super_max

    # -- combat -------------------------------------------------------------
    def add_charge(self, amount):
        self.super = min(self.super_max, self.super + amount * self.stats.get("charge_mult", 1.0))

    def on_deal_damage(self, dmg):
        self.add_charge(CHARGE_PER_HIT)
        ls = self.stats.get("lifesteal", 0.0)
        if ls:
            self.heal(dmg * ls)

    def take_damage(self, dmg, src_x, ctx):
        if self.iframes > 0:
            return
        if self.shield_t > 0:
            ctx.add_text(self.x + self.w / 2, self.y, "BLOCK", SHIELD_COL, 20)
            burst(ctx, self.x + self.w / 2, self.y + self.h / 2, SHIELD_COL, 10, 5)
            self.iframes = 18
            return
        dmg = int(dmg * (1 - self.stats.get("dmg_reduce", 0.0)))
        self.hp -= dmg
        self.iframes = PLAYER["iframes"]
        self.vx = 9 if self.x > src_x else -9
        self.vy = -7
        ctx.add_text(self.x + self.w / 2, self.y, f"-{dmg}", RED)
        burst(ctx, self.x + self.w / 2, self.y + self.h / 2, RED, 14, 6)
        ctx.shake(9)
        ctx.play("hit")

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def start_shield(self, frames):
        self.shield_t = max(self.shield_t, frames)

    def start_berserk(self, frames):
        self.berserk_t = max(self.berserk_t, frames)

    # -- input / update -----------------------------------------------------
    def handle_input(self, keys, ctx):
        sp = self.stats["speed"]
        self.moving = False
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        accel = sp if self.on_ground else sp * 0.6
        if left and not right:
            self.vx -= accel * (0.5 if abs(self.vx) < sp else 0.2)
            self.vx = max(-sp, self.vx)
            self.facing = -1
            self.moving = True
        elif right and not left:
            self.vx += accel * (0.5 if abs(self.vx) < sp else 0.2)
            self.vx = min(sp, self.vx)
            self.facing = 1
            self.moving = True
        else:
            self.vx *= self.friction if self.on_ground else 0.94
        jump = keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]
        if jump and self.on_ground:
            self.vy = -self.stats["jump_v"]
            self.on_ground = False
            burst(ctx, self.x + self.w / 2, self.y + self.h, (200, 200, 200), 7, 3, 3, 16, 0.15)
        # combat: mouse OR keyboard (left click / J = shoot, right click / K = slash)
        mb = pygame.mouse.get_pressed(3)
        if mb[0] or keys[pygame.K_j] or keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]:
            self.shoot(ctx)
        if mb[2] or keys[pygame.K_k] or keys[pygame.K_l]:
            self.melee(ctx)

    def shoot(self, ctx):
        if self.fire_cd > 0:
            return
        self.fire_cd = int(self.stats["fire_cooldown"])
        dmg = self.stats["damage"] * (1.6 if self.berserk_t > 0 else 1.0)
        bx = self.x + (self.w if self.facing > 0 else 0)
        by = self.y + self.h * 0.40
        ctx.player_shots.append(
            Projectile(bx, by, 15 * self.facing, 0, int(dmg), "bolt", 28, True))
        self.recoil = 3.0 * -self.facing       # subtle kickback for feel
        ctx.play("bullet")
        burst(ctx, bx, by, (150, 220, 255), 5, 3, 3, 12, 0)

    def melee(self, ctx):
        if self.melee_cd > 0:
            return
        self.melee_cd = PLAYER["melee_cooldown"]
        self.slash_timer = 12
        dmg = self.stats["melee_damage"] * (1.6 if self.berserk_t > 0 else 1.0)
        reach = pygame.Rect(0, 0, 92, 92)
        if self.facing > 0:
            reach.midleft = (self.x + self.w - 8, self.y + self.h / 2)
        else:
            reach.midright = (self.x + 8, self.y + self.h / 2)
        ctx.register_melee(reach, int(dmg))

    def use_super(self, ctx):
        if not self.super_ready:
            return False
        self.super = 0.0
        cx, cy = self.x + self.w / 2, self.y + self.h / 2
        dmg = int(self.stats["super_dmg"] * (1.6 if self.berserk_t > 0 else 1.0))
        radius = 320
        ring(ctx, cx, cy, (150, 230, 255), 40, 12, 8, 34)
        ring(ctx, cx, cy, (255, 255, 255), 30, 7, 6, 26)
        ctx.shake(20)
        ctx.flash(10)
        ctx.play("hit")
        ctx.enemy_shots.clear()
        for e in list(ctx.enemies):
            if not e.dead and math.hypot(e.x + e.w / 2 - cx, e.y + e.h / 2 - cy) < radius:
                e.take_damage(dmg, ctx, kx=(8 if e.x > cx else -8))
        if ctx.boss and not ctx.boss.dead:
            if math.hypot(ctx.boss.x + ctx.boss.w / 2 - cx, ctx.boss.y + ctx.boss.h / 2 - cy) < radius + 120:
                ctx.boss.take_damage(dmg, ctx)
        return True

    def update(self, ctx):
        self.fire_cd = max(0, self.fire_cd - 1)
        self.melee_cd = max(0, self.melee_cd - 1)
        self.iframes = max(0, self.iframes - 1)
        self.slash_timer = max(0, self.slash_timer - 1)
        self.shield_t = max(0, self.shield_t - 1)
        self.berserk_t = max(0, self.berserk_t - 1)
        self.recoil *= 0.7
        self.add_charge(ctx.charge_trickle)     # slow passive fill

        # physics
        self.vy = min(self.vy + GRAVITY, TERMINAL_VY)
        self.x += self.vx + self.recoil
        self.y += self.vy
        self.x = max(0, min(WIDTH - self.w, self.x))

        self.on_ground = False
        feet = self.y + self.h
        if feet >= GROUND_Y and self.vy >= 0:
            self.y = GROUND_Y - self.h
            self.vy = 0
            if not self.on_ground:
                self.squash = 0.82
            self.on_ground = True
        for plat in ctx.platforms:
            if self.vy >= 0 and plat.left < self.rect.centerx < plat.right:
                prev_feet = feet - self.vy
                if prev_feet <= plat.top + 8 and feet >= plat.top:
                    self.y = plat.top - self.h
                    self.vy = 0
                    self.on_ground = True

        self.anim += 0.25 if (self.moving and self.on_ground) else 0.08
        self.squash += (1.0 - self.squash) * 0.25

    def draw(self, s):
        name = ["hero", "hero_t1", "hero_t2"][min(self.tier, 2)]
        base = art.scaled_by_height(name, self.h + 16)
        bob = math.sin(self.anim) * (3 if self.moving else 1.5)
        sw = max(1, int(base.get_width() / self.squash))
        sh = max(1, int(base.get_height() * self.squash))
        img = pygame.transform.smoothscale(base, (sw, sh))
        if self.facing < 0:
            img = pygame.transform.flip(img, True, False)
        cx = self.x + self.w / 2
        base_y = self.y + self.h - img.get_height() + bob

        # upgrade / super-ready aura
        aura_col = None
        if self.super_ready:
            aura_col = (150, 230, 255)
        elif self.tier > 0:
            aura_col = [(0, 0, 0), (255, 200, 90), (150, 210, 255)][self.tier]
        if aura_col:
            pulse = 60 + int(30 * (math.sin(self.anim * 2) * 0.5 + 0.5)) if self.super_ready else 55
            glow = pygame.Surface((sw + 30, sh + 30), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (*aura_col, pulse), glow.get_rect())
            s.blit(glow, (cx - glow.get_width() / 2, self.y + self.h / 2 - glow.get_height() / 2 + bob))

        if self.berserk_t > 0:
            img = img.copy()
            tint = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            tint.fill((255, 90, 40, 70))
            img.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        if self.iframes == 0 or self.iframes % 8 < 4:
            s.blit(img, (cx - img.get_width() / 2, base_y))

        if self.slash_timer > 0:
            sl = art.scaled_by_height("slash", 104)
            if self.facing < 0:
                sl = pygame.transform.flip(sl, True, False)
            sl = sl.copy()
            sl.set_alpha(int(255 * self.slash_timer / 12))
            fx = self.x + self.w - 12 if self.facing > 0 else self.x - sl.get_width() + 12
            s.blit(sl, (fx, self.y + self.h / 2 - sl.get_height() / 2))

        if self.shield_t > 0:
            rad = int(self.h * 0.7)
            sh_surf = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            a = 90 if self.shield_t > 40 or self.shield_t % 8 < 4 else 40
            pygame.draw.circle(sh_surf, (*SHIELD_COL, a), (rad, rad), rad, 4)
            pygame.draw.circle(sh_surf, (*SHIELD_COL, a // 3), (rad, rad), rad)
            s.blit(sh_surf, (cx - rad, self.y + self.h / 2 - rad))


# ---------------------------------------------------------------------------
# Enemies
# ---------------------------------------------------------------------------
class Enemy:
    """Enemies with real, telegraphed attacks.

    Melee grunts *approach → wind up → swing* a weapon (an actual attack hitbox that
    only hurts during the swing), then recover — they no longer damage you just by
    touching.  Bats *hover → telegraph → dive*.  Archers loose aimed arrows.
    """
    # melee timing (frames)
    WINDUP, STRIKE, RECOVER, REACH = 20, 11, 30, 62

    def __init__(self, kind, x, stage_index=0):
        cfg = ENEMIES[kind]
        self.kind = kind
        self.role = cfg["kind"]
        self.w, self.h = cfg["w"], cfg["h"]
        self.max_hp = int(cfg["hp"] * (1 + stage_index * STAGE_HP_SCALE))
        self.hp = self.max_hp
        self.speed = cfg["speed"]
        self.damage = int(cfg["damage"] * (1 + stage_index * STAGE_DMG_SCALE))
        self.coins = cfg["coins"]
        self.x = x
        self.y = (GROUND_Y - self.h) if self.role != "flyer" else random.randint(150, 340)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = self.role != "flyer"
        self.facing = -1
        self.anim = random.uniform(0, 10)
        self.hit_flash = 0
        self.dead = False
        self.sprite = kind
        # attack state machine
        self.atk = "move"                 # move | windup | strike | recover
        self.atk_t = random.randint(20, 70)
        self.hit_done = False
        self.lunge = 0.0                  # forward draw offset while attacking

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    @property
    def hitbox(self):
        return pygame.Rect(int(self.x + 6), int(self.y + 4), self.w - 12, self.h - 8)

    def _attack_rect(self):
        """The arc/reach that actually deals damage during a swing or dive."""
        r = pygame.Rect(0, 0, 56, 56)
        if self.facing > 0:
            r.midleft = (self.x + self.w - 8, self.y + self.h * 0.5)
        else:
            r.midright = (self.x + 8, self.y + self.h * 0.5)
        return r

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
        burst(ctx, self.x + self.w / 2, self.y + self.h / 2, (120, 200, 80), 20, 6, 6, 30)
        for _ in range(random.randint(2, 4)):
            ctx.pickups.append(Pickup(self.x + self.w / 2, self.y + self.h / 2, "coin"))
        if random.random() < 0.14:
            ctx.pickups.append(Pickup(self.x + self.w / 2, self.y + self.h / 2, "heart"))
        ctx.on_enemy_killed(self)

    def update(self, ctx):
        self.hit_flash = max(0, self.hit_flash - 1)
        self.atk_t = max(0, self.atk_t - 1)
        self.lunge *= 0.8
        p = ctx.player
        pcx = p.x + p.w / 2
        # face the player, but lock facing during a swing so the arc lands where aimed
        if self.atk in ("move", "recover"):
            self.facing = -1 if pcx < self.x + self.w / 2 else 1

        if self.role == "melee":
            self._ai_melee(ctx, p, pcx)
        elif self.role == "ranged":
            self._ai_ranged(ctx, pcx, p)
        elif self.role == "flyer":
            self._ai_flyer(ctx, p)

        if self.role != "flyer":
            self.vy = min(self.vy + GRAVITY, TERMINAL_VY)
            self.y += self.vy
            if self.y + self.h >= GROUND_Y:
                self.y = GROUND_Y - self.h
                self.vy = 0
        self.x += self.vx
        self.x = max(-30, min(WIDTH - self.w + 30, self.x))
        self.vx *= 0.8 if self.role != "flyer" else 0.9
        self.anim += 0.2

    # -- melee: approach → windup → swing → recover -------------------------
    def _ai_melee(self, ctx, p, pcx):
        d = pcx - (self.x + self.w / 2)
        if self.atk == "move":
            if abs(d) > self.REACH:
                self.vx += math.copysign(self.speed * 0.55, d)
                self.vx = max(-self.speed, min(self.speed, self.vx))
            elif self.atk_t <= 0 and self.on_ground:
                self.atk, self.atk_t, self.hit_done = "windup", self.WINDUP, False
                ctx.add_text(self.x + self.w / 2, self.y - 14, "!", (255, 210, 90), 26)
        elif self.atk == "windup":
            self.vx *= 0.6
            self.lunge = -self.facing * 5          # lean back to telegraph
            if self.atk_t <= 0:
                self.atk, self.atk_t = "strike", self.STRIKE
                self.vx = self.facing * 4          # lunge into the swing
        elif self.atk == "strike":
            self.lunge = self.facing * 10
            if not self.hit_done and self._attack_rect().colliderect(p.hitbox):
                p.take_damage(self.damage, self.x + self.w / 2, ctx)
                burst(ctx, p.x + p.w / 2, p.y + p.h / 2, (255, 160, 90), 8, 5)
                self.hit_done = True
            if self.atk_t <= 0:
                self.atk, self.atk_t = "recover", self.RECOVER
        elif self.atk == "recover":
            self.vx *= 0.7
            if self.atk_t <= 0:
                self.atk, self.atk_t = "move", random.randint(10, 30)

    def _ai_ranged(self, ctx, pcx, p):
        d = pcx - (self.x + self.w / 2)
        if abs(d) < 300:
            self.vx -= math.copysign(self.speed * 0.4, d)
        elif abs(d) > 460:
            self.vx += math.copysign(self.speed * 0.4, d)
        self.vx = max(-self.speed, min(self.speed, self.vx))
        # telegraph the shot with a short draw-back
        if self.atk == "move" and self.atk_t <= 0 and abs(d) < 620:
            self.atk, self.atk_t = "windup", 16
        elif self.atk == "windup":
            self.vx *= 0.4
            self.lunge = -self.facing * 3
            if self.atk_t <= 0:
                ang = math.atan2((p.y + p.h / 2) - (self.y + self.h / 2), d) + random.uniform(-0.06, 0.06)
                spd = 8.0
                ctx.enemy_shots.append(Projectile(
                    self.x + self.w / 2, self.y + self.h / 2,
                    math.cos(ang) * spd, math.sin(ang) * spd, self.damage, "arrow", 22, False))
                self.atk, self.atk_t = "move", random.randint(70, 130)

    def _ai_flyer(self, ctx, p):
        tx, ty = p.x + p.w / 2, p.y + p.h / 2
        cx, cy = self.x + self.w / 2, self.y + self.h / 2
        dist = math.hypot(tx - cx, ty - cy)
        if self.atk == "move":
            # circle above/around the player at a hover altitude
            hover_y = p.y - 90
            self.vx += math.copysign(0.2, tx - cx)
            self.vy += (hover_y - self.y) * 0.02 + math.sin(self.anim) * 0.2
            if self.atk_t <= 0 and dist < 320:
                self.atk, self.atk_t, self.hit_done = "windup", 14, False
                self._dtx, self._dty = tx, ty
        elif self.atk == "windup":
            self.vx *= 0.6; self.vy *= 0.6         # brief pause before the dive
            if self.atk_t <= 0:
                ang = math.atan2(self._dty - cy, self._dtx - cx)
                self.vx = math.cos(ang) * self.speed * 2.6
                self.vy = math.sin(ang) * self.speed * 2.6
                self.atk, self.atk_t = "strike", 16
        elif self.atk == "strike":
            if not self.hit_done and self.hitbox.colliderect(p.hitbox):
                p.take_damage(self.damage, cx, ctx)
                burst(ctx, tx, ty, (255, 160, 90), 8, 5)
                self.hit_done = True
            if self.atk_t <= 0:
                self.atk, self.atk_t = "recover", 26
        elif self.atk == "recover":
            self.vy += -0.25                        # peel back up
            if self.atk_t <= 0:
                self.atk, self.atk_t = "move", random.randint(30, 60)
        self.vx = max(-self.speed * 2.8, min(self.speed * 2.8, self.vx))
        self.vy = max(-self.speed * 2.8, min(self.speed * 2.8, self.vy))
        self.y += self.vy
        self.y = max(70, min(GROUND_Y - self.h, self.y))

    def draw(self, s):
        img = art.scaled_by_height(self.sprite, self.h)
        if self.facing > 0:
            img = pygame.transform.flip(img, True, False)
        bob = math.sin(self.anim) * (2 if self.role != "flyer" else 4)
        # scale-up puff on windup to telegraph the attack
        if self.atk == "windup":
            gw = int(img.get_width() * 1.08)
            gh = int(img.get_height() * 1.08)
            img = pygame.transform.smoothscale(img, (gw, gh))
        if self.hit_flash > 0:
            img = img.copy()
            flash = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            flash.fill((255, 255, 255, 150))
            img.blit(flash, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        ox = self.x + self.w / 2 - img.get_width() / 2 + self.lunge
        s.blit(img, (ox, self.y + self.h - img.get_height() + bob))
        # weapon swing arc during a melee strike
        if self.role == "melee" and self.atk == "strike":
            sl = art.scaled_by_height("eslash", 66)
            if self.facing < 0:
                sl = pygame.transform.flip(sl, True, False)
            sl = sl.copy()
            sl.set_alpha(int(255 * min(1.0, self.atk_t / self.STRIKE + 0.2)))
            fx = self.x + self.w - 14 if self.facing > 0 else self.x - sl.get_width() + 14
            s.blit(sl, (fx, self.y + self.h / 2 - sl.get_height() / 2))
        self._draw_hp(s)

    def _draw_hp(self, s):
        if self.hp >= self.max_hp:
            return
        w = self.w
        x, y = self.x + self.w / 2 - w / 2, self.y - 12
        pygame.draw.rect(s, (30, 12, 16), (x, y, w, 5), border_radius=2)
        pygame.draw.rect(s, (86, 214, 120), (x, y, w * max(0, self.hp / self.max_hp), 5), border_radius=2)


# ---------------------------------------------------------------------------
# Bosses  — randomised, phase-based AI
# ---------------------------------------------------------------------------
class Boss:
    def __init__(self, key, stage_index=0):
        cfg = BOSSES[key]
        self.key = key
        self.w, self.h = cfg["w"], cfg["h"]
        self.max_hp = cfg["hp"]
        self.hp = self.max_hp
        self.base_speed = cfg["speed"]
        self.damage = cfg["damage"]
        self.coins = cfg["coins"]
        self.gems = cfg["gems"]
        self.x = WIDTH - self.w - 90
        self.y = GROUND_Y - self.h
        self.vx = 0.0
        self.vy = 0.0
        self.facing = -1
        self.anim = 0.0
        self.hit_flash = 0
        self.dead = False
        self.sprite = "boss_" + key
        self.name = {"warlord": "Grukk the Warlord",
                     "embermaw": "Embermaw, the Ashborn",
                     "frostking": "The Goblin King"}[key]
        self.intro = 100
        self.phase = 1
        self.mode = "idle"
        self.timer = random.randint(40, 70)
        self.action = None
        self.last_action = None
        self.telegraph = 0
        # attack pools per boss & phase
        self.pools = self._build_pools()

    def _build_pools(self):
        if self.key == "warlord":
            return {1: ["charge", "throw", "slam"],
                    2: ["charge", "throw", "slam", "throw"],
                    3: ["charge", "slam", "throw", "quake"]}
        if self.key == "embermaw":
            return {1: ["volley", "aimed", "dive"],
                    2: ["volley", "aimed", "dive", "rain"],
                    3: ["volley", "rain", "dive", "inferno"]}
        return {1: ["spread", "aimed", "rain"],
                2: ["spread", "aimed", "rain", "teleport"],
                3: ["spread", "rain", "teleport", "blizzard"]}

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    @property
    def hitbox(self):
        return pygame.Rect(int(self.x + 14), int(self.y + 12), self.w - 28, self.h - 18)

    @property
    def speed(self):
        return self.base_speed * (1.0 + 0.18 * (self.phase - 1))

    def take_damage(self, dmg, ctx, kx=0):
        if self.intro > 0:
            return
        self.hp -= dmg
        self.hit_flash = 5
        ctx.add_text(self.x + self.w / 2, self.y - 4, str(dmg), WHITE, 22)
        burst(ctx, self.x + random.randint(0, self.w), self.y + random.randint(20, self.h),
              (255, 200, 120), 5, 4)
        new_phase = 1 + (self.hp < self.max_hp * 0.66) + (self.hp < self.max_hp * 0.33)
        if new_phase > self.phase:
            self.phase = new_phase
            self._enrage(ctx)
        if self.hp <= 0:
            self.die(ctx)

    def _enrage(self, ctx):
        ctx.add_text(self.x + self.w / 2, self.y - 30, "ENRAGED!", (255, 120, 90), 26)
        ring(ctx, self.x + self.w / 2, self.y + self.h / 2, (255, 140, 80), 30, 8, 7, 30)
        ctx.shake(14)
        self.mode = "idle"
        self.timer = 20

    def die(self, ctx):
        self.dead = True
        ctx.shake(26)
        ctx.flash(8)
        for _ in range(48):
            burst(ctx, self.x + random.randint(0, self.w), self.y + random.randint(0, self.h),
                  (255, 180, 90), 6, 7, 40)
        for _ in range(int(self.coins // 8)):
            ctx.pickups.append(Pickup(self.x + random.randint(10, self.w - 10),
                                      self.y + self.h / 2, "coin"))
        for _ in range(self.gems):
            ctx.pickups.append(Pickup(self.x + self.w / 2 + random.randint(-40, 40),
                                      self.y + self.h / 2, "gem"))
        ctx.on_boss_killed(self)

    # ---- main update ------------------------------------------------------
    def update(self, ctx):
        self.hit_flash = max(0, self.hit_flash - 1)
        self.anim += 0.12
        if self.intro > 0:
            self.intro -= 1
            return
        p = ctx.player
        pcx = p.x + p.w / 2
        self.facing = -1 if pcx < self.x + self.w / 2 else 1
        self.timer -= 1

        if self.mode == "idle":
            self._wander(pcx)
            if self.timer <= 0:
                self._choose_action(ctx)
        elif self.mode == "windup":
            self.telegraph += 1
            if self.timer <= 0:
                self._execute(ctx, p, pcx)
                self.mode = "recover"
                self.timer = random.randint(18, 40) - 4 * (self.phase - 1)
        elif self.mode == "recover":
            self.vx *= 0.85
            if self.timer <= 0:
                self.mode = "idle"
                self.timer = max(16, random.randint(34, 70) - 10 * (self.phase - 1))
        elif self.mode == "charge":
            self.vx += math.copysign(1.1, self._charge_dir)
            self.vx = max(-self.speed * 3.0, min(self.speed * 3.0, self.vx))
            if self.timer <= 0:
                self.mode, self.timer = "recover", random.randint(16, 30)
        elif self.mode == "dive":
            self.x += (self._dive_tx - (self.x + self.w / 2)) * 0.12
            self.y += (self._dive_ty - self.y) * 0.12
            if self.timer <= 0:
                self.mode, self.timer = "recover", random.randint(20, 36)

        # physics (flyers ignore ground)
        if self.key != "embermaw":
            self.vy = min(self.vy + GRAVITY, TERMINAL_VY)
            self.y += self.vy
            if self.y + self.h >= GROUND_Y:
                self.y = GROUND_Y - self.h
                self.vy = 0
        else:
            # gentle hover baseline
            if self.mode not in ("dive",):
                self.y += (170 + math.sin(self.anim * 0.6) * 46 - self.y) * 0.04
        self.x += self.vx
        self.x = max(0, min(WIDTH - self.w, self.x))
        self.vx *= 0.9

        if self.hitbox.colliderect(p.hitbox):
            p.take_damage(self.damage, self.x + self.w / 2, ctx)

    def _wander(self, pcx):
        d = pcx - (self.x + self.w / 2)
        # randomly approach or reposition
        self.vx += math.copysign(self.speed * 0.3, d) * random.choice([1, 1, -1])
        self.vx = max(-self.speed, min(self.speed, self.vx))

    def _choose_action(self, ctx):
        pool = self.pools[self.phase]
        action = random.choice(pool)
        # avoid three identical picks in a row (keeps it random but less streaky)
        if action == self.last_action and random.random() < 0.6:
            action = random.choice(pool)
        self.last_action = action
        self.action = action
        # movement actions start immediately; ranged actions telegraph first
        if action == "charge":
            p = ctx.player
            self._charge_dir = 1 if p.x > self.x else -1
            self.mode, self.timer = "charge", random.randint(24, 46)
            ctx.add_text(self.x + self.w / 2, self.y - 20, "!", (255, 200, 80), 30)
        elif action == "dive":
            p = ctx.player
            self._dive_tx = p.x + p.w / 2
            self._dive_ty = p.y + p.h / 2 - 30
            self.mode, self.timer = "dive", random.randint(22, 34)
        else:
            self.telegraph = 0
            self.mode = "windup"
            self.timer = random.randint(10, 22)   # random telegraph time

    # ---- attack execution (all params randomised) -------------------------
    def _execute(self, ctx, p, pcx):
        a = self.action
        cx, cy = self.x + self.w / 2, self.y + self.h * 0.5
        px, py = p.x + p.w / 2, p.y + p.h / 2

        if a == "throw":
            n = random.randint(1, 3) + (self.phase - 1)
            for _ in range(n):
                ang = math.atan2(py - cy, px - cx) + random.uniform(-0.35, 0.35)
                spd = random.uniform(6, 9)
                ctx.enemy_shots.append(Projectile(cx, cy, math.cos(ang) * spd, math.sin(ang) * spd,
                                                  self.damage, "fireball", 30, False, spin=True))
        elif a == "slam" or a == "quake":
            if self.y + self.h < GROUND_Y - 4:
                self.vy = -6
            ctx.shake(16)
            waves = random.randint(2, 4) if a == "quake" else 2
            base = random.uniform(4, 7)
            for i in range(waves):
                for sgn in (-1, 1):
                    ctx.enemy_shots.append(Projectile(
                        cx, GROUND_Y - 24, sgn * (base + i * 1.2), -random.uniform(1, 3),
                        self.damage, "fireball", 28, False, spin=True, gravity=0.15))
        elif a == "volley":
            n = random.randint(4, 6) + (self.phase - 1)
            spread = random.uniform(0.5, 1.1)
            aim = math.atan2(py - cy, px - cx)
            for i in range(n):
                ang = aim + (i / (n - 1) - 0.5) * spread
                spd = random.uniform(5.5, 7.5)
                ctx.enemy_shots.append(Projectile(cx, cy, math.cos(ang) * spd, math.sin(ang) * spd + 1,
                                                  self.damage, "fireball", 30, False, spin=True))
        elif a == "aimed":
            n = random.randint(2, 4) + (self.phase - 1)
            for _ in range(n):
                ang = math.atan2(py - cy, px - cx) + random.uniform(-0.12, 0.12)
                spd = random.uniform(7, 9.5)
                spr = "fireball" if self.key == "embermaw" else "shard"
                ctx.enemy_shots.append(Projectile(cx, cy, math.cos(ang) * spd, math.sin(ang) * spd,
                                                  self.damage, spr, 26, False, spin=True))
        elif a == "rain" or a == "inferno" or a == "blizzard":
            count = {"rain": random.randint(4, 7), "inferno": random.randint(8, 12),
                     "blizzard": random.randint(9, 14)}[a]
            spr = "shard" if self.key == "frostking" else "fireball"
            for _ in range(count):
                rx = random.randint(40, WIDTH - 40)
                ctx.enemy_shots.append(Projectile(rx, -20, random.uniform(-1.5, 1.5),
                                                  random.uniform(6, 9), self.damage, spr, 26,
                                                  False, spin=True, gravity=0.05))
        elif a == "spread":
            n = random.randint(6, 10) + (self.phase - 1)
            off = random.uniform(0, math.tau)
            spd = random.uniform(5.5, 7.5)
            for i in range(n):
                ang = off + math.tau * i / n
                ctx.enemy_shots.append(Projectile(cx, cy, math.cos(ang) * spd, math.sin(ang) * spd,
                                                  self.damage, "shard", 26, False, spin=True))
        elif a == "teleport":
            self.x = random.randint(60, WIDTH - self.w - 60)
            ring(ctx, cx, cy, (150, 210, 255), 22, 7, 6, 24)
            # follow up with a quick aimed shot
            ang = math.atan2(py - (self.y + self.h / 2), px - (self.x + self.w / 2))
            ctx.enemy_shots.append(Projectile(self.x + self.w / 2, self.y + self.h / 2,
                                              math.cos(ang) * 8, math.sin(ang) * 8,
                                              self.damage, "shard", 26, False, spin=True))

    def draw(self, s):
        img = art.scaled_by_height(self.sprite, self.h)
        if self.facing > 0:
            img = pygame.transform.flip(img, True, False)
        bob = math.sin(self.anim) * (6 if self.key == "embermaw" else 2)
        # telegraph flash before an attack
        if self.mode == "windup":
            img = img.copy()
            g = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            a = 80 if (self.telegraph // 3) % 2 == 0 else 20
            g.fill((255, 120, 60, a))
            img.blit(g, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        if self.intro > 0 and self.intro % 8 < 4:
            img = img.copy(); img.set_alpha(150)
        if self.hit_flash > 0:
            img = img.copy()
            fl = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            fl.fill((255, 255, 255, 150))
            img.blit(fl, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        s.blit(img, (self.x + self.w / 2 - img.get_width() / 2, self.y + bob))
