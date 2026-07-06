"""Game state machine, main loop and the runtime context shared with entities.

The :class:`Game` object *is* the ``ctx`` handed to every entity's ``update`` call:
it owns the live lists (enemies, projectiles, pickups, particles) and exposes the
small API entities use to affect the world (spawn text, shake/flash the camera,
play a sound, register a melee hit, report a kill).

Rendering is resolution-independent: everything is drawn to a fixed logical canvas
(config.WIDTH x HEIGHT) which is then scaled to fit any window size — resizable or
fullscreen (F11) — with letterboxing.
"""
from __future__ import annotations

import math
import os
import random

import pygame

from . import art, ui
from .background import ParallaxBackground
from .config import (WIDTH, HEIGHT, FPS, TITLE as CAPTION, GROUND_Y, STAGES, UPGRADES,
                     CONSUMABLES, EQUIPMENT, LIVES_START, CHARGE_PER_KILL,
                     CHARGE_PER_SECOND, WHITE, GOLD, COIN, GEM, RED, GREEN, BLUE,
                     PURPLE, ORANGE, PANEL_LIGHT, BLACK)
from .entities import (Player, Enemy, Boss, Projectile, Pickup, Particle,
                       FloatingText, burst)
from .progression import Progression
from . import paths
from . import __version__

SOUND_DIR = paths.resource("Game")

# Game states
TITLE, STORY, PLAYING, SHOP, PAUSE, GAMEOVER, VICTORY = range(7)
BUTTON_STATES = (TITLE, SHOP, GAMEOVER, VICTORY)


def _gradient_rect(surf, rect, top, bottom):
    x, y, w, h = rect
    strip = pygame.Surface((1, h))
    for i in range(h):
        t = i / max(1, h - 1)
        strip.set_at((0, i), (int(top[0] + (bottom[0] - top[0]) * t),
                              int(top[1] + (bottom[1] - top[1]) * t),
                              int(top[2] + (bottom[2] - top[2]) * t)))
    surf.blit(pygame.transform.scale(strip, (w, h)), (x, y))


class Game:
    def __init__(self):
        # --- display / responsive scaling ---
        self.fullscreen = False
        self.win_size = (WIDTH, HEIGHT)
        self.window = pygame.display.set_mode(self.win_size, pygame.RESIZABLE)
        pygame.display.set_caption(CAPTION)
        self.canvas = pygame.Surface((WIDTH, HEIGHT))       # logical frame
        self.world = pygame.Surface((WIDTH, HEIGHT))        # world layer (for shake)
        self.view = (1.0, 0, 0)                             # (scale, offx, offy)

        self.clock = pygame.time.Clock()
        self.prog = Progression.load()
        self.state = TITLE
        self.running = True
        self.muted = False

        # runtime world
        self.player: Player | None = None
        self.enemies: list[Enemy] = []
        self.boss: Boss | None = None
        self.player_shots: list[Projectile] = []
        self.enemy_shots: list[Projectile] = []
        self.pickups: list[Pickup] = []
        self.particles: list[Particle] = []
        self.texts: list[FloatingText] = []
        self.platforms: list[pygame.Rect] = []
        self.bg: ParallaxBackground | None = None

        self.lives = LIVES_START
        self.stage_index = 0
        self.wave_index = 0
        self.wave_queue: list[dict] = []
        self.boss_pending = False
        self.spawn_timer = 0
        self.behavior = "normal"
        self.hazard_timer = 120
        self.shake_amt = 0.0
        self.flash_t = 0
        self.charge_trickle = CHARGE_PER_SECOND / FPS
        self.stage_colors = ((74, 130, 74), (30, 62, 36))
        self.buttons: list[ui.Button] = []
        self.stage_name = ""
        self.story_text = ""

        self._load_sounds()
        art.generate_all()

    # ------------------------------------------------------------------ audio
    def _load_sounds(self):
        self.sounds = {}
        self.have_audio = pygame.mixer.get_init() is not None
        if not self.have_audio:
            return
        for key, fn in (("bullet", "bullet.wav"), ("hit", "hit.wav")):
            try:
                snd = pygame.mixer.Sound(os.path.join(SOUND_DIR, fn))
                snd.set_volume(0.3 if key == "bullet" else 0.5)
                self.sounds[key] = snd
            except (pygame.error, FileNotFoundError):
                pass
        try:
            pygame.mixer.music.load(os.path.join(SOUND_DIR, "music.mp3"))
            pygame.mixer.music.set_volume(0.32)
            pygame.mixer.music.play(-1)
        except (pygame.error, FileNotFoundError):
            pass

    def play(self, key):
        if not self.muted and key in self.sounds:
            self.sounds[key].play()

    # ---------------------------------------------------------- ctx entity API
    def add_text(self, x, y, s, color, size=22):
        self.texts.append(FloatingText(x, y, s, color, size))

    def shake(self, amount):
        self.shake_amt = min(26, self.shake_amt + amount)

    def flash(self, frames):
        self.flash_t = max(self.flash_t, frames)

    def register_melee(self, reach, damage):
        burst(self, reach.centerx, reach.centery, (200, 230, 255), 6, 4, 4, 12, 0)
        for e in self.enemies:
            if not e.dead and e.hitbox.colliderect(reach):
                e.take_damage(damage, self, kx=(7 if reach.centerx < e.x else -7))
                self.player.on_deal_damage(damage)
        if self.boss and not self.boss.dead and self.boss.hitbox.colliderect(reach):
            self.boss.take_damage(damage, self)
            self.player.on_deal_damage(damage)

    def on_enemy_killed(self, enemy):
        if self.player:
            self.player.add_charge(CHARGE_PER_KILL)

    def on_boss_killed(self, boss):
        pass

    # ------------------------------------------------------- stage management
    def new_game(self, from_continue=False):
        self.lives = LIVES_START
        if not from_continue:
            self.prog.stage = 0
        self.stage_index = self.prog.stage if from_continue else 0
        self.start_stage(self.stage_index)

    def start_stage(self, index):
        self.stage_index = index
        cfg = STAGES[index]
        self.stage_colors = (cfg["ground_top"], cfg["ground_bot"])
        self.behavior = cfg["behavior"]
        self.bg = ParallaxBackground(cfg["bg"], cfg["ambient"])
        self.player = Player(self.prog.stats())
        if self.behavior == "ice":
            self.player.friction = 0.93        # slippery floor
        for lst in (self.enemies, self.player_shots, self.enemy_shots,
                    self.pickups, self.particles, self.texts):
            lst.clear()
        self.boss = None
        self.boss_pending = False
        self.wave_queue = list(cfg["waves"])
        self.wave_index = 0
        self.spawn_timer = 40
        self.hazard_timer = 180
        self.platforms = self._platforms_for(index)
        self.state = STORY
        self.story_text = cfg["story"]
        self.stage_name = cfg["name"]
        self.buttons = []

    def _platforms_for(self, index):
        layouts = [
            [pygame.Rect(320, 470, 200, 20), pygame.Rect(760, 410, 220, 20)],
            [pygame.Rect(200, 460, 200, 20), pygame.Rect(560, 400, 220, 20),
             pygame.Rect(940, 470, 200, 20)],
            [pygame.Rect(280, 470, 210, 20), pygame.Rect(650, 405, 230, 20),
             pygame.Rect(980, 475, 200, 20)],
        ]
        return layouts[min(index, len(layouts) - 1)]

    def spawn_wave(self):
        if not self.wave_queue:
            return
        wave = self.wave_queue.pop(0)
        self.wave_index += 1
        if self.wave_index > 1 and self.player:      # small heal between waves
            self.player.heal(8)
        for kind, count in wave.items():
            for _ in range(count):
                if kind == "bat":
                    x = random.randint(60, WIDTH - 120)
                else:
                    x = -50 if random.random() < 0.5 else WIDTH + 20
                self.enemies.append(Enemy(kind, x, self.stage_index))

    def spawn_boss(self):
        self.boss = Boss(STAGES[self.stage_index]["boss"], self.stage_index)
        self.boss_pending = False

    # --------------------------------------------------------------- main loop
    def run(self):
        # CI/smoke hook: GOBLIN_SMOKE=<frames> runs headlessly then exits cleanly,
        # so a build can be verified without a display or human input.
        smoke = os.environ.get("GOBLIN_SMOKE")
        smoke_frames = int(smoke) if smoke and smoke.isdigit() else (150 if smoke else 0)
        frame = 0
        while self.running:
            self.clock.tick(FPS)
            self.handle_events()
            self.update()
            self.draw()
            frame += 1
            if smoke_frames and frame >= smoke_frames:
                self.running = False
        self.prog.save()

    def _to_logical(self, pos):
        scale, offx, offy = self.view
        return ((pos[0] - offx) / scale, (pos[1] - offy) / scale)

    def handle_events(self):
        mouse = self._to_logical(pygame.mouse.get_pos())
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.VIDEORESIZE and not self.fullscreen:
                self.win_size = (max(640, ev.w), max(360, ev.h))
                self.window = pygame.display.set_mode(self.win_size, pygame.RESIZABLE)
            elif ev.type == pygame.KEYDOWN:
                self._keydown(ev.key)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.state in BUTTON_STATES:
                    self._click(self._to_logical(ev.pos))
        if self.state in BUTTON_STATES:
            for b in self.buttons:
                b.update(mouse)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self.win_size = self.window.get_size()
        else:
            self.win_size = (WIDTH, HEIGHT)
            self.window = pygame.display.set_mode(self.win_size, pygame.RESIZABLE)

    def _keydown(self, key):
        if key == pygame.K_F11:
            self.toggle_fullscreen()
            return
        if key == pygame.K_m:
            self.muted = not self.muted
            if self.have_audio:
                pygame.mixer.music.set_volume(0.0 if self.muted else 0.32)
        if self.state == TITLE:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.new_game(False)
        elif self.state == STORY:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.state = PLAYING
        elif self.state == PLAYING:
            if key in (pygame.K_ESCAPE, pygame.K_p):
                self.state = PAUSE
            elif key in (pygame.K_e, pygame.K_q, pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_f):
                self.player.use_super(self)
            elif key == pygame.K_1:
                self.use_consumable("potion")
            elif key == pygame.K_2:
                self.use_consumable("shield")
            elif key == pygame.K_3:
                self.use_consumable("berserk")
        elif self.state == PAUSE:
            if key in (pygame.K_ESCAPE, pygame.K_p):
                self.state = PLAYING
        elif self.state in (GAMEOVER, VICTORY):
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self._to_title()

    def _click(self, pos):
        for b in self.buttons:
            if b.clicked(pos):
                b.action()
                return

    def use_consumable(self, key):
        if not self.player or self.prog.stock.get(key, 0) <= 0:
            return
        self.prog.use_consumable(key)
        px, py = self.player.x + self.player.w / 2, self.player.y
        if key == "potion":
            self.player.heal(45)
            self.add_text(px, py, "+45", GREEN, 22)
        elif key == "shield":
            self.player.start_shield(5 * FPS)
            self.add_text(px, py, "SHIELD", BLUE, 22)
        elif key == "berserk":
            self.player.start_berserk(7 * FPS)
            self.add_text(px, py, "RAGE", ORANGE, 22)
        self.play("bullet")

    # --------------------------------------------------------- update dispatch
    def update(self):
        self.shake_amt *= 0.85
        self.flash_t = max(0, self.flash_t - 1)
        if self.state == TITLE and not self.buttons:
            self.build_title_buttons()
        if self.bg:
            bias = abs(self.player.vx) * 0.15 if (self.state == PLAYING and self.player) else 0.0
            self.bg.update(bias)
        if self.state == PLAYING:
            self.update_playing()
        elif self.state == SHOP and not self.buttons:
            self.build_shop_buttons()

    def update_playing(self):
        p = self.player
        keys = pygame.key.get_pressed()
        p.handle_input(keys, self)
        p.update(self)

        # spawning waves -> boss
        if self.wave_queue or self.enemies:
            if not self.enemies and self.spawn_timer <= 0 and self.wave_queue:
                self.spawn_wave()
                self.spawn_timer = 24
            self.spawn_timer -= 1
        elif not self.boss and not self.boss_pending:
            self.boss_pending = True
            self.spawn_timer = 48
        if self.boss_pending:
            self.spawn_timer -= 1
            if self.spawn_timer <= 0:
                self.spawn_boss()

        # stage hazard: meteor rain in the Ember Wastes
        if self.behavior == "meteors":
            self.hazard_timer -= 1
            if self.hazard_timer <= 0:
                self.hazard_timer = random.randint(90, 170)
                for _ in range(random.randint(1, 3)):
                    rx = random.randint(40, WIDTH - 40)
                    self.enemy_shots.append(Projectile(rx, -20, random.uniform(-1, 1), 6,
                                                       14, "fireball", 30, False,
                                                       spin=True, gravity=0.06))

        for e in self.enemies:
            e.update(self)
        self.enemies = [e for e in self.enemies if not e.dead]

        if self.boss:
            self.boss.update(self)

        self._update_shots()

        alive = []
        for pk in self.pickups:
            if pk.update(self):
                alive.append(pk)
            else:
                self._collect(pk)
        self.pickups = alive

        self.particles = [pt for pt in self.particles if pt.update()]
        self.texts = [t for t in self.texts if t.update()]

        if p.hp <= 0:
            self.on_player_death()
        if self.boss and self.boss.dead:
            self.on_stage_complete()

    def _update_shots(self):
        p = self.player
        keep = []
        for b in self.player_shots:
            alive = b.update(self)
            hit = False
            for e in self.enemies:
                if not e.dead and b.rect.colliderect(e.hitbox):
                    e.take_damage(b.damage, self, kx=(3 if b.vx > 0 else -3))
                    p.on_deal_damage(b.damage)
                    hit = True
                    break
            if not hit and self.boss and not self.boss.dead and b.rect.colliderect(self.boss.hitbox):
                self.boss.take_damage(b.damage, self)
                p.on_deal_damage(b.damage)
                hit = True
            if alive and not hit:
                keep.append(b)
            elif hit:
                burst(self, b.x, b.y, (150, 220, 255), 5, 3, 3, 10, 0)
        self.player_shots = keep

        keep = []
        for b in self.enemy_shots:
            alive = b.update(self)
            if alive and b.rect.colliderect(p.hitbox):
                p.take_damage(b.damage, b.x, self)
                burst(self, b.x, b.y, (255, 160, 90), 6, 4)
                continue
            if alive:
                keep.append(b)
        self.enemy_shots = keep

    def _collect(self, pk):
        if pk.kind == "coin":
            self.prog.add_coins(5)
            self.add_text(pk.x, pk.y - 10, "+5", COIN, 18)
        elif pk.kind == "gem":
            self.prog.add_gems(1)
            self.add_text(pk.x, pk.y - 10, "+1 gem", GEM, 20)
        elif pk.kind == "heart":
            self.player.heal(18)
            self.add_text(pk.x, pk.y - 10, "+18", GREEN, 18)

    # ---------------------------------------------------- state transitions
    def on_player_death(self):
        self.lives -= 1
        if self.lives > 0:
            # respawn
            p = self.player
            p.hp = p.max_hp
            p.x, p.y = 160, GROUND_Y - p.h
            p.vx = p.vy = 0
            p.iframes = 2 * FPS
            p.shield_t = p.berserk_t = 0
            self.enemy_shots.clear()
            self.add_text(WIDTH // 2, HEIGHT // 2 - 40, f"{self.lives} LIVES LEFT", RED, 34)
            self.flash(8)
        else:
            self.prog.save()
            self.state = GAMEOVER
            self.build_gameover_buttons()

    def on_stage_complete(self):
        self.boss = None
        self.player_shots.clear()
        self.enemy_shots.clear()
        self.prog.best_stage = max(self.prog.best_stage, self.stage_index)
        self.prog.stage = min(len(STAGES) - 1, self.stage_index + 1)
        self.prog.save()
        if self.stage_index >= len(STAGES) - 1:
            self.state = VICTORY
            self.build_victory_buttons()
        else:
            self.state = SHOP
            self.buttons = []

    def next_stage_from_shop(self):
        self.start_stage(self.stage_index + 1)
        self.buttons = []

    # ----------------------------------------------------- button builders
    def _mk(self, rect, label, action, sub="", color=PANEL_LIGHT, enabled=True):
        b = ui.Button(rect, label, sub, color, enabled)
        b.action = action
        return b

    def build_title_buttons(self):
        cx = WIDTH // 2
        self.buttons = [self._mk((cx - 150, 470, 300, 56), "NEW GAME",
                                 lambda: self.new_game(False), color=(70, 110, 180))]
        if self.prog.stage > 0:
            self.buttons.append(self._mk((cx - 150, 538, 300, 50), "CONTINUE",
                                         lambda: self.new_game(True),
                                         sub=f"Realm {self.prog.stage + 1}", color=(60, 130, 90)))
        self.buttons.append(self._mk((cx - 150, 598, 300, 42), "RESET PROGRESS",
                                     self.reset_progress, color=(120, 60, 70)))

    def reset_progress(self):
        Progression.clear_save()
        self.prog = Progression()
        self.build_title_buttons()

    def build_shop_buttons(self):
        self.buttons = []
        # upgrades: 3x2 grid on the left
        keys = list(UPGRADES.keys())
        bw, bh, gap = 250, 82, 16
        gx, gy = 70, 190
        for i, k in enumerate(keys):
            rect = (gx + (i % 3) * (bw + gap), gy + (i // 3) * (bh + gap), bw, bh)
            self.buttons.append(self._upgrade_btn(rect, k))
        # consumables: row
        cw = 250
        cy = 400
        for i, k in enumerate(CONSUMABLES):
            rect = (gx + i * (cw + gap), cy, cw, 74)
            self.buttons.append(self._consumable_btn(rect, k))
        # relics: row
        rw = 250
        ry = 496
        for i, k in enumerate(EQUIPMENT):
            rect = (gx + i * (rw + gap), ry, rw, 74)
            self.buttons.append(self._relic_btn(rect, k))
        self.buttons.append(self._mk((WIDTH // 2 - 170, 600, 340, 54),
                                     "ENTER NEXT REALM", self.next_stage_from_shop,
                                     color=(70, 130, 90)))

    def _upgrade_btn(self, rect, key):
        label = UPGRADES[key][0]
        lvl = self.prog.levels[key]
        maxed = self.prog.is_maxed(key)
        cost = self.prog.cost(key)
        sub = "MAX" if maxed else f"Lv{lvl} • {UPGRADES[key][1]} • {cost}c"
        color = (60, 100, 150) if self.prog.can_buy(key) else (56, 60, 76)
        b = ui.Button(rect, label, sub, color, enabled=not maxed)
        b.action = lambda k=key: (self.prog.buy(k) and self.play("bullet"),
                                  self.build_shop_buttons())
        return b

    def _consumable_btn(self, rect, key):
        label, desc, cost, hot = CONSUMABLES[key]
        have = self.prog.stock[key]
        sub = f"{desc} • {cost}c • have {have}"
        color = (110, 80, 60) if self.prog.coins >= cost else (56, 60, 76)
        b = ui.Button(rect, f"{label} [{hot}]", sub, color, enabled=self.prog.coins >= cost)
        b.action = lambda k=key: (self.prog.buy_consumable(k) and self.play("bullet"),
                                  self.build_shop_buttons())
        return b

    def _relic_btn(self, rect, key):
        label, desc, cost = EQUIPMENT[key]
        owned = self.prog.has(key)
        sub = "OWNED" if owned else f"{desc} • {cost} gems"
        color = (70, 110, 70) if owned else ((90, 70, 120) if self.prog.gems >= cost else (56, 60, 76))
        b = ui.Button(rect, label, sub, color, enabled=(not owned and self.prog.gems >= cost))
        b.action = lambda k=key: (self.prog.buy_relic(k) and self.play("bullet"),
                                  self.build_shop_buttons())
        return b

    def build_gameover_buttons(self):
        self.buttons = [self._mk((WIDTH // 2 - 150, 470, 300, 54),
                                 "RETURN TO TITLE", self._to_title, color=(90, 70, 90))]

    def build_victory_buttons(self):
        self.buttons = [self._mk((WIDTH // 2 - 150, 520, 300, 54),
                                 "RETURN TO TITLE", self._to_title, color=(70, 120, 100))]

    def _to_title(self):
        self.state = TITLE
        self.build_title_buttons()

    # ---------------------------------------------------------------- render
    def draw(self):
        if self.state in (PLAYING, PAUSE, SHOP):
            self.draw_world()
        elif self.state == STORY and self.bg:
            self.bg.draw(self.world)
            self.canvas.blit(self.world, (0, 0))
        else:
            self.canvas.fill((14, 18, 30))
            if self.bg:
                self.bg.draw(self.canvas)

        if self.state in (PLAYING, PAUSE, SHOP):
            dx = random.uniform(-self.shake_amt, self.shake_amt)
            dy = random.uniform(-self.shake_amt, self.shake_amt)
            self.canvas.fill(BLACK)
            self.canvas.blit(self.world, (dx, dy))

        # overlays
        if self.state == TITLE:
            self.draw_title()
        elif self.state == STORY:
            self.draw_story()
        elif self.state == PLAYING:
            self.draw_hud()
        elif self.state == PAUSE:
            self.draw_hud(); self.draw_pause()
        elif self.state == SHOP:
            self.draw_shop()
        elif self.state == GAMEOVER:
            self.draw_gameover()
        elif self.state == VICTORY:
            self.draw_victory()

        if self.state in BUTTON_STATES:
            for b in self.buttons:
                b.draw(self.canvas)

        if self.flash_t > 0:
            fl = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            fl.fill((255, 255, 255, min(200, self.flash_t * 22)))
            self.canvas.blit(fl, (0, 0))

        self._present()

    def _present(self):
        win_w, win_h = self.window.get_size()
        scale = min(win_w / WIDTH, win_h / HEIGHT)
        sw, sh = int(WIDTH * scale), int(HEIGHT * scale)
        offx, offy = (win_w - sw) // 2, (win_h - sh) // 2
        self.view = (scale, offx, offy)
        self.window.fill(BLACK)
        self.window.blit(pygame.transform.smoothscale(self.canvas, (sw, sh)), (offx, offy))
        pygame.display.flip()

    def draw_world(self):
        s = self.world
        self.bg.draw(s)
        self.bg.draw_ambient(s)
        _gradient_rect(s, (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y),
                       self.stage_colors[0], self.stage_colors[1])
        pygame.draw.line(s, tuple(min(255, c + 40) for c in self.stage_colors[0]),
                         (0, GROUND_Y), (WIDTH, GROUND_Y), 3)
        for plat in self.platforms:
            pygame.draw.rect(s, self.stage_colors[1], plat, border_radius=6)
            pygame.draw.rect(s, tuple(min(255, c + 40) for c in self.stage_colors[0]),
                             pygame.Rect(plat.x, plat.y, plat.w, 6), border_radius=6)
        for pk in self.pickups:
            pk.draw(s)
        for e in self.enemies:
            e.draw(s)
        if self.boss:
            self.boss.draw(s)
        if self.player:
            self.player.draw(s)
        for b in self.player_shots:
            b.draw(s)
        for b in self.enemy_shots:
            b.draw(s)
        for pt in self.particles:
            pt.draw(s)
        for t in self.texts:
            t.draw(s)

    def draw_hud(self):
        if not self.player:
            return
        if self.boss and not self.boss.dead:
            wave_txt = "BOSS BATTLE"
        elif self.wave_queue or self.enemies:
            total = len(STAGES[self.stage_index]["waves"])
            wave_txt = f"Wave {min(self.wave_index, total)}/{total}  •  Enemies {len(self.enemies)}"
        else:
            wave_txt = "The ground trembles..."
        ui.draw_hud(self.canvas, self)
        ui.text(self.canvas, self.stage_name, (WIDTH // 2, 26), 30, WHITE, center=True)
        ui.text(self.canvas, wave_txt, (WIDTH // 2, 60), 20, GOLD, center=True, bold=False)
        if self.boss and not self.boss.dead and self.boss.intro <= 0:
            ui.draw_boss_bar(self.canvas, self.boss)
        # short, unobtrusive hint (bottom-right, clear of the item slots on the left)
        ui.text(self.canvas, "Left-click / J: shoot   •   Esc: pause & controls",
                (WIDTH - 260, HEIGHT - 26), 16, (206, 212, 224), center=True, bold=False)

    def _dim(self, alpha=150):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 14, alpha))
        self.canvas.blit(overlay, (0, 0))

    def draw_title(self):
        self._dim(120)
        ui.text(self.canvas, "GOBLIN SLAYER", (WIDTH // 2, 150), 92, GOLD, center=True)
        ui.text(self.canvas, "Realms of the Fallen", (WIDTH // 2, 224), 38,
                (222, 226, 236), center=True, bold=False)
        hero = art.scaled_by_height(["hero", "hero_t1", "hero_t2"][self.prog.tier()], 160)
        self.canvas.blit(hero, (WIDTH // 2 - hero.get_width() // 2, 280))
        ui.text(self.canvas, f"Coins {self.prog.coins}   Gems {self.prog.gems}   •   Knight Tier {self.prog.tier() + 1}",
                (WIDTH // 2, HEIGHT - 26), 20, WHITE, center=True, bold=False)
        ui.text(self.canvas, "M mute • F11 fullscreen", (WIDTH - 130, 20), 15,
                (180, 184, 196), center=True, bold=False)
        ui.text(self.canvas, f"v{__version__}", (16, HEIGHT - 26), 15,
                (150, 156, 170), bold=False)

    def draw_story(self):
        self._dim(150)
        rect = pygame.Rect(WIDTH // 2 - 400, 210, 800, 300)
        ui.panel(self.canvas, rect)
        ui.text(self.canvas, self.stage_name, (WIDTH // 2, 250), 48, GOLD, center=True)
        y = 320
        for line in self.story_text.split("\n"):
            ui.text(self.canvas, line, (WIDTH // 2, y), 24, WHITE, center=True, bold=False)
            y += 38
        ui.text(self.canvas, "Press ENTER to begin", (WIDTH // 2, 470), 22,
                (200, 230, 255), center=True)

    def draw_pause(self):
        self._dim(170)
        ui.text(self.canvas, "PAUSED", (WIDTH // 2, 120), 72, WHITE, center=True)
        rect = pygame.Rect(WIDTH // 2 - 320, 190, 640, 360)
        ui.panel(self.canvas, rect)
        ui.text(self.canvas, "CONTROLS", (WIDTH // 2, 224), 30, GOLD, center=True)
        rows = [
            ("Move", "A / D  or  Arrow keys"),
            ("Jump", "Space  /  W  /  Up"),
            ("Shoot", "Left-click  /  J"),
            ("Slash (melee)", "Right-click  /  K"),
            ("Super (when charged)", "E  /  Shift  /  F"),
            ("Use Potion / Shield / Rage", "1  /  2  /  3"),
            ("Pause  •  Mute  •  Fullscreen", "Esc  •  M  •  F11"),
        ]
        y = 268
        for label, keysd in rows:
            ui.text(self.canvas, label, (WIDTH // 2 - 290, y), 21, WHITE, bold=False)
            ui.text(self.canvas, keysd, (WIDTH // 2 + 30, y), 21, (170, 210, 255), bold=True)
            y += 40
        ui.text(self.canvas, "Press Esc to resume", (WIDTH // 2, 566), 22,
                (200, 230, 255), center=True)

    def draw_shop(self):
        self._dim(180)
        ui.text(self.canvas, "REALM CLEARED", (WIDTH // 2, 60), 56, GOLD, center=True)
        ci = art.scaled_by_height("coin", 30); self.canvas.blit(ci, (WIDTH // 2 - 150, 104))
        ui.text(self.canvas, str(self.prog.coins), (WIDTH // 2 - 112, 106), 26, COIN)
        gi = art.scaled_by_height("gem", 30); self.canvas.blit(gi, (WIDTH // 2 + 40, 104))
        ui.text(self.canvas, str(self.prog.gems), (WIDTH // 2 + 78, 106), 26, GEM)
        ui.text(self.canvas, "UPGRADES (coins)", (76, 166), 20, (200, 220, 255))
        ui.text(self.canvas, "CONSUMABLES (coins)", (76, 378), 20, (255, 210, 160))
        ui.text(self.canvas, "RELICS — permanent (gems)", (76, 474), 20, (200, 180, 255))

    def draw_gameover(self):
        self._dim(180)
        ui.text(self.canvas, "YOU HAVE FALLEN", (WIDTH // 2, 260), 74, RED, center=True)
        ui.text(self.canvas, f"You reached {STAGES[self.stage_index]['name']}",
                (WIDTH // 2, 340), 26, WHITE, center=True, bold=False)
        ui.text(self.canvas, "Coins, upgrades and relics are kept. Try again!",
                (WIDTH // 2, 384), 22, (210, 214, 224), center=True, bold=False)

    def draw_victory(self):
        self._dim(180)
        ui.text(self.canvas, "VICTORY!", (WIDTH // 2, 190), 92, GOLD, center=True)
        for i, line in enumerate([
                "The Goblin King is slain and the Aether Crystals reclaimed.",
                "Aethermoor rises from the ashes — and you are its legend.",
                f"Gems collected: {self.prog.gems}   •   Knight Tier {self.prog.tier() + 1}"]):
            ui.text(self.canvas, line, (WIDTH // 2, 300 + i * 44), 24, WHITE, center=True, bold=False)
