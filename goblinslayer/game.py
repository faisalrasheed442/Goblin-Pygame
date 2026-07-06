"""Game state machine, main loop and the runtime context shared with entities.

The :class:`Game` object *is* the ``ctx`` handed to every entity's ``update`` call:
it owns all the live lists (enemies, projectiles, pickups, particles) and exposes
the small API entities use to affect the world (spawn text, shake the camera, play a
sound, register a melee hit, report a kill).
"""
from __future__ import annotations

import math
import os
import random

import pygame

from . import art, ui
from .config import (WIDTH, HEIGHT, FPS, TITLE, GROUND_Y, STAGES, UPGRADES,
                     WHITE, GOLD, COIN, GEM, RED, GREEN, BLUE, PURPLE, PANEL_LIGHT,
                     PANEL, BLACK)
from .entities import (Player, Enemy, Boss, Projectile, Pickup, Particle,
                       FloatingText, burst)
from .progression import Progression

SOUND_DIR = os.path.join(os.path.dirname(__file__), "..", "Game")

# Game states
TITLE, STORY, PLAYING, SHOP, PAUSE, GAMEOVER, VICTORY, STAGECLEAR = range(8)

# States whose on-screen buttons should be interactive / drawn.
BUTTON_STATES = (TITLE, SHOP, GAMEOVER, VICTORY)


def _gradient_rect(surf, rect, top, bottom):
    """Fill a rect with a vertical gradient (cheap, cached per (h,top,bottom))."""
    x, y, w, h = rect
    strip = pygame.Surface((1, h))
    for i in range(h):
        t = i / max(1, h - 1)
        col = (int(top[0] + (bottom[0] - top[0]) * t),
               int(top[1] + (bottom[1] - top[1]) * t),
               int(top[2] + (bottom[2] - top[2]) * t))
        strip.set_at((0, i), col)
    surf.blit(pygame.transform.scale(strip, (w, h)), (x, y))


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.prog = Progression.load()
        self.state = TITLE
        self.running = True
        self.muted = False

        # runtime world lists (populated per stage)
        self.player: Player | None = None
        self.enemies: list[Enemy] = []
        self.boss: Boss | None = None
        self.player_shots: list[Projectile] = []
        self.enemy_shots: list[Projectile] = []
        self.pickups: list[Pickup] = []
        self.particles: list[Particle] = []
        self.texts: list[FloatingText] = []
        self.platforms: list[pygame.Rect] = []

        self.stage_index = 0
        self.wave_index = 0
        self.wave_queue: list[dict] = []
        self.boss_pending = False
        self.spawn_timer = 0
        self.shake_amt = 0.0
        self.bg_name = "bg_forest"
        self.stage_colors = ((74, 130, 74), (36, 70, 40))
        self.buttons: list[ui.Button] = []
        self.banner = ""
        self.banner_t = 0
        self.result_stats = {}

        self._load_sounds()
        art.generate_all()   # ensure assets exist on disk

    # ------------------------------------------------------------------
    # audio
    # ------------------------------------------------------------------
    def _load_sounds(self):
        self.sounds = {}
        self.have_audio = pygame.mixer.get_init() is not None
        if not self.have_audio:
            return
        for key, fn in (("bullet", "bullet.wav"), ("hit", "hit.wav")):
            path = os.path.join(SOUND_DIR, fn)
            try:
                snd = pygame.mixer.Sound(path)
                snd.set_volume(0.35 if key == "bullet" else 0.5)
                self.sounds[key] = snd
            except (pygame.error, FileNotFoundError):
                pass
        try:
            pygame.mixer.music.load(os.path.join(SOUND_DIR, "music.mp3"))
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.play(-1)
        except (pygame.error, FileNotFoundError):
            pass

    def play(self, key):
        if not self.muted and key in self.sounds:
            self.sounds[key].play()

    # ------------------------------------------------------------------
    # ctx API used by entities
    # ------------------------------------------------------------------
    def add_text(self, x, y, s, color, size=22):
        self.texts.append(FloatingText(x, y, s, color, size))

    def shake(self, amount):
        self.shake_amt = min(24, self.shake_amt + amount)

    def register_melee(self, reach, damage):
        burst(self, reach.centerx, reach.centery, (200, 230, 255), 6, 4, 4, 12, 0)
        for e in self.enemies:
            if not e.dead and e.hitbox.colliderect(reach):
                kx = 6 if reach.centerx < e.x else -6
                e.take_damage(damage, self, kx)
        if self.boss and not self.boss.dead and self.boss.hitbox.colliderect(reach):
            self.boss.take_damage(damage, self)

    def on_enemy_killed(self, enemy):
        self.prog.add_coins(0)   # coins come from pickups; keep score via kills if desired
        self.banner_pop("+" + str(enemy.coins), COIN)

    def on_boss_killed(self, boss):
        self.banner_pop("BOSS DEFEATED", GOLD)

    def banner_pop(self, txt, color):
        pass  # reserved; floating texts handle feedback

    # ------------------------------------------------------------------
    # stage management
    # ------------------------------------------------------------------
    def new_game(self, from_continue=False):
        if not from_continue:
            # fresh run keeps meta upgrades but restarts at stage 0
            self.prog.stage = 0
        self.stage_index = self.prog.stage if from_continue else 0
        self.start_stage(self.stage_index)

    def start_stage(self, index):
        self.stage_index = index
        cfg = STAGES[index]
        self.bg_name = "bg_" + cfg["bg"]
        self.stage_colors = (cfg["ground_top"], cfg["ground_bot"])
        self.player = Player(self.prog.stats())
        self.enemies.clear(); self.player_shots.clear(); self.enemy_shots.clear()
        self.pickups.clear(); self.particles.clear(); self.texts.clear()
        self.boss = None
        self.boss_pending = False
        self.wave_queue = list(cfg["waves"])
        self.wave_index = 0
        self.spawn_timer = 30
        self.platforms = self._platforms_for(index)
        self.state = STORY
        self.story_text = cfg["story"]
        self.stage_name = cfg["name"]
        self.buttons = []

    def _platforms_for(self, index):
        layouts = [
            [pygame.Rect(250, 360, 150, 16), pygame.Rect(560, 320, 160, 16)],
            [pygame.Rect(150, 350, 140, 16), pygame.Rect(430, 300, 150, 16),
             pygame.Rect(720, 350, 140, 16)],
            [pygame.Rect(210, 350, 150, 16), pygame.Rect(500, 305, 160, 16),
             pygame.Rect(730, 355, 140, 16)],
        ]
        return layouts[min(index, len(layouts) - 1)]

    def spawn_wave(self):
        if not self.wave_queue:
            return
        wave = self.wave_queue.pop(0)
        self.wave_index += 1
        # "Life Font" upgrade: heal between waves
        regen = self.player.stats.get("regen", 0)
        if regen and self.wave_index > 1:
            self.player.heal(regen)
            self.add_text(self.player.x + self.player.w / 2, self.player.y - 10,
                          f"+{int(regen)}", GREEN, 18)
        for kind, count in wave.items():
            for _ in range(count):
                side = random.choice([-1, 1])
                x = -40 if side < 0 else WIDTH + 10
                x = random.randint(40, WIDTH - 80) if kind == "bat" else x
                e = Enemy(kind, x, self.stage_index)
                self.enemies.append(e)

    def spawn_boss(self):
        cfg = STAGES[self.stage_index]
        self.boss = Boss(cfg["boss"], self.stage_index)
        self.boss_pending = False

    # ------------------------------------------------------------------
    # main loop
    # ------------------------------------------------------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS)
            self.handle_events()
            self.update()
            self.draw()
        self.prog.save()

    def handle_events(self):
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.KEYDOWN:
                self._keydown(ev.key)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.state in BUTTON_STATES:
                    self._click(ev.pos)
        if self.state in BUTTON_STATES:
            for b in self.buttons:
                b.update(mouse)

    def _keydown(self, key):
        if key == pygame.K_m:
            self.muted = not self.muted
            if self.have_audio:
                pygame.mixer.music.set_volume(0.0 if self.muted else 0.35)
        if self.state == TITLE:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.new_game(from_continue=False)
        elif self.state == STORY:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.state = PLAYING
        elif self.state == PLAYING:
            if key in (pygame.K_ESCAPE, pygame.K_p):
                self.state = PAUSE
        elif self.state == PAUSE:
            if key in (pygame.K_ESCAPE, pygame.K_p):
                self.state = PLAYING
        elif self.state in (GAMEOVER, VICTORY):
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.state = TITLE
                self.build_title_buttons()

    def _click(self, pos):
        for b in self.buttons:
            if b.clicked(pos):
                b.action() if hasattr(b, "action") else None
                return

    # ------------------------------------------------------------------
    # update dispatch
    # ------------------------------------------------------------------
    def update(self):
        self.shake_amt *= 0.85
        if self.state == TITLE and not self.buttons:
            self.build_title_buttons()
        if self.state == PLAYING:
            self.update_playing()
        elif self.state == SHOP and not self.buttons:
            self.build_shop_buttons()
        self.banner_t = max(0, self.banner_t - 1)

    def update_playing(self):
        p = self.player
        keys = pygame.key.get_pressed()
        p.handle_input(keys, self)
        p.update(self)

        # spawning logic
        if self.wave_queue or self.enemies:
            if not self.enemies and self.spawn_timer <= 0 and self.wave_queue:
                self.spawn_wave()
                self.spawn_timer = 20
            self.spawn_timer -= 1
        elif not self.boss and not self.boss_pending and not self.enemies and not self.wave_queue:
            # all waves cleared -> boss
            self.boss_pending = True
            self.spawn_timer = 40
        if self.boss_pending:
            self.spawn_timer -= 1
            if self.spawn_timer <= 0:
                self.spawn_boss()

        for e in self.enemies:
            e.update(self)
        self.enemies = [e for e in self.enemies if not e.dead]

        if self.boss:
            self.boss.update(self)

        # projectiles
        self._update_shots()

        # pickups
        alive = []
        for pk in self.pickups:
            if pk.update(self):
                alive.append(pk)
            else:
                self._collect(pk)
        self.pickups = alive

        # particles & texts
        self.particles = [pt for pt in self.particles if pt.update()]
        self.texts = [t for t in self.texts if t.update()]

        # regen tick handled at wave clear; passive regen on wave transitions
        # death / clear checks
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
                    e.take_damage(b.damage, self, kx=3 * (1 if b.vx > 0 else -1))
                    hit = True
                    break
            if not hit and self.boss and not self.boss.dead and b.rect.colliderect(self.boss.hitbox):
                self.boss.take_damage(b.damage, self)
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
            self.add_text(pk.x, pk.y - 10, "+1", GEM, 20)
        elif pk.kind == "heart":
            self.player.heal(15)
            self.add_text(pk.x, pk.y - 10, "+15", GREEN, 18)

    # ------------------------------------------------------------------
    # state transitions
    # ------------------------------------------------------------------
    def on_player_death(self):
        self.prog.save()
        self.result_stats = {"stage": self.stage_index}
        self.state = GAMEOVER
        self.buttons = []
        self.build_gameover_buttons()

    def on_stage_complete(self):
        self.boss = None
        # clear transient combat objects so the frozen shop backdrop stays clean
        self.player_shots.clear()
        self.enemy_shots.clear()
        self.prog.stage = min(len(STAGES) - 1, self.stage_index + 1)
        # passive life-font regen reward
        self.prog.save()
        if self.stage_index >= len(STAGES) - 1:
            self.state = VICTORY
            self.buttons = []
            self.build_victory_buttons()
        else:
            self.state = SHOP
            self.buttons = []

    def next_stage_from_shop(self):
        self.start_stage(self.stage_index + 1)
        self.buttons = []

    # ------------------------------------------------------------------
    # button builders (each button gets an .action closure)
    # ------------------------------------------------------------------
    def _mk(self, rect, label, action, sub="", color=PANEL_LIGHT, enabled=True):
        b = ui.Button(rect, label, sub, color, enabled)
        b.action = action
        return b

    def build_title_buttons(self):
        cx = WIDTH // 2
        self.buttons = [
            self._mk((cx - 130, 350, 260, 54), "NEW GAME",
                     lambda: self.new_game(False), color=(70, 110, 180)),
        ]
        if self.prog.stage > 0:
            self.buttons.append(self._mk(
                (cx - 130, 414, 260, 48), "CONTINUE",
                lambda: self.new_game(True),
                sub=f"Realm {self.prog.stage + 1}", color=(60, 130, 90)))
        self.buttons.append(self._mk(
            (cx - 130, 474, 260, 40), "RESET PROGRESS",
            self.reset_progress, color=(120, 60, 70)))

    def reset_progress(self):
        Progression.clear_save()
        self.prog = Progression()
        self.build_title_buttons()

    def build_shop_buttons(self):
        self.buttons = []
        keys = list(UPGRADES.keys())
        cols, rows = 3, 2
        bw, bh = 250, 92
        gap = 20
        gx = (WIDTH - (cols * bw + (cols - 1) * gap)) // 2
        gy = 190
        for i, k in enumerate(keys):
            r = i // cols
            c = i % cols
            rect = (gx + c * (bw + gap), gy + r * (bh + gap), bw, bh)
            self.buttons.append(self._make_upgrade_button(rect, k))
        self.buttons.append(self._mk(
            (WIDTH // 2 - 150, 470, 300, 50), "ENTER NEXT REALM",
            self.next_stage_from_shop, color=(70, 130, 90)))

    def _make_upgrade_button(self, rect, key):
        label, desc, *_ = UPGRADES[key]
        lvl = self.prog.levels[key]
        maxed = self.prog.is_maxed(key)
        cost = self.prog.cost(key)
        sub = "MAX LEVEL" if maxed else f"Lv{lvl}  •  {desc}  •  {cost}c"
        color = (60, 100, 150) if self.prog.can_buy(key) else (56, 60, 76)
        b = ui.Button(rect, label, sub, color, enabled=not maxed)

        def act(k=key):
            if self.prog.buy(k):
                self.play("bullet")
                self.build_shop_buttons()
        b.action = act
        return b

    def build_gameover_buttons(self):
        self.buttons = [self._mk(
            (WIDTH // 2 - 130, 360, 260, 50), "RETURN TO TITLE",
            self._to_title, color=(90, 70, 90))]

    def build_victory_buttons(self):
        self.buttons = [self._mk(
            (WIDTH // 2 - 130, 400, 260, 50), "RETURN TO TITLE",
            self._to_title, color=(70, 120, 100))]

    def _to_title(self):
        self.state = TITLE
        self.build_title_buttons()

    # ------------------------------------------------------------------
    # rendering
    # ------------------------------------------------------------------
    def draw(self):
        if self.state in (PLAYING, PAUSE, SHOP, STAGECLEAR):
            self.draw_world(self.canvas)
        elif self.state == STORY:
            self.canvas.blit(art.sprite(self.bg_name, (WIDTH, HEIGHT)), (0, 0))
        else:
            self.canvas.blit(art.sprite("bg_forest", (WIDTH, HEIGHT)), (0, 0))

        # apply screen shake by blitting canvas offset
        self.screen.fill(BLACK)
        dx = random.uniform(-self.shake_amt, self.shake_amt)
        dy = random.uniform(-self.shake_amt, self.shake_amt)
        self.screen.blit(self.canvas, (dx, dy))

        # overlays drawn straight to screen (unshaken)
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
                b.draw(self.screen)
        pygame.display.flip()

    def draw_world(self, s):
        s.blit(art.sprite(self.bg_name, (WIDTH, HEIGHT)), (0, 0))
        # ground band
        _gradient_rect(s, (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y),
                       self.stage_colors[0], self.stage_colors[1])
        pygame.draw.line(s, tuple(min(255, c + 40) for c in self.stage_colors[0]),
                         (0, GROUND_Y), (WIDTH, GROUND_Y), 3)
        # platforms
        for plat in self.platforms:
            pygame.draw.rect(s, self.stage_colors[1], plat, border_radius=6)
            top = pygame.Rect(plat.x, plat.y, plat.w, 6)
            pygame.draw.rect(s, tuple(min(255, c + 40) for c in self.stage_colors[0]),
                             top, border_radius=6)
        # pickups behind actors
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
            wave_txt = f"Wave {min(self.wave_index, total)}/{total}  •  Enemies: {len(self.enemies)}"
        else:
            wave_txt = "Clearing..."
        ui.draw_hud(self.screen, self.player, self.prog, self.stage_name, wave_txt)
        if self.boss and not self.boss.dead and self.boss.intro <= 0:
            ui.draw_boss_bar(self.screen, self.boss)
        # controls hint
        ui.text(self.screen, "Move: A/D  Jump: W  Shoot: J  Slash: K  Pause: Esc",
                (WIDTH // 2, HEIGHT - 22), 15, (220, 224, 232), center=True, bold=False)

    # ---- menu screens -----------------------------------------------------
    def _dim(self, alpha=150):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 14, alpha))
        self.screen.blit(overlay, (0, 0))

    def draw_title(self):
        self._dim(120)
        ui.text(self.screen, "GOBLIN SLAYER", (WIDTH // 2, 120), 74, GOLD, center=True)
        ui.text(self.screen, "Realms of the Fallen", (WIDTH // 2, 176), 32,
                (220, 224, 235), center=True, bold=False)
        # hero showcase
        hero = art.scaled_by_height(["hero", "hero_t1", "hero_t2"][self.prog.tier()], 118)
        self.screen.blit(hero, (WIDTH // 2 - hero.get_width() // 2, 214))
        ui.text(self.screen, f"Coins {self.prog.coins}   Gems {self.prog.gems}   •   Tier {self.prog.tier() + 1}",
                (WIDTH // 2, HEIGHT - 22), 18, WHITE, center=True, bold=False)
        ui.text(self.screen, "M: mute", (WIDTH - 60, 18), 14,
                (180, 184, 196), center=True, bold=False)

    def draw_story(self):
        self._dim(150)
        panel = pygame.Rect(WIDTH // 2 - 340, 150, 680, 240)
        ui.panel(self.screen, panel)
        ui.text(self.screen, self.stage_name, (WIDTH // 2, 185), 40, GOLD, center=True)
        y = 240
        for line in self.story_text.split("\n"):
            ui.text(self.screen, line, (WIDTH // 2, y), 22, WHITE, center=True, bold=False)
            y += 34
        ui.text(self.screen, "Press ENTER to begin", (WIDTH // 2, 360), 20,
                (200, 230, 255), center=True)

    def draw_pause(self):
        self._dim(150)
        ui.text(self.screen, "PAUSED", (WIDTH // 2, HEIGHT // 2 - 40), 60, WHITE, center=True)
        ui.text(self.screen, "Press Esc to resume  •  M to mute",
                (WIDTH // 2, HEIGHT // 2 + 30), 22, (210, 214, 224), center=True, bold=False)

    def draw_shop(self):
        self._dim(170)
        ui.text(self.screen, "REALM CLEARED", (WIDTH // 2, 70), 52, GOLD, center=True)
        ui.text(self.screen, "Spend your spoils, then march onward.",
                (WIDTH // 2, 120), 22, WHITE, center=True, bold=False)
        # currency
        ci = art.scaled_by_height("coin", 28); self.screen.blit(ci, (WIDTH // 2 - 130, 146))
        ui.text(self.screen, str(self.prog.coins), (WIDTH // 2 - 96, 148), 24, COIN)
        gi = art.scaled_by_height("gem", 28); self.screen.blit(gi, (WIDTH // 2 + 40, 146))
        ui.text(self.screen, str(self.prog.gems), (WIDTH // 2 + 74, 148), 24, GEM)

    def draw_gameover(self):
        self._dim(170)
        ui.text(self.screen, "YOU HAVE FALLEN", (WIDTH // 2, 200), 60, RED, center=True)
        ui.text(self.screen, f"You reached {STAGES[self.result_stats.get('stage', 0)]['name']}",
                (WIDTH // 2, 270), 24, WHITE, center=True, bold=False)
        ui.text(self.screen, "Your coins and upgrades are kept. Try again!",
                (WIDTH // 2, 310), 20, (210, 214, 224), center=True, bold=False)

    def draw_victory(self):
        self._dim(170)
        ui.text(self.screen, "VICTORY!", (WIDTH // 2, 150), 74, GOLD, center=True)
        for i, line in enumerate([
                "The Goblin King is slain and the Aether Crystals reclaimed.",
                "Aethermoor rises from the ashes — and you are its legend.",
                f"Gems collected: {self.prog.gems}"]):
            ui.text(self.screen, line, (WIDTH // 2, 240 + i * 40), 22, WHITE,
                    center=True, bold=False)
