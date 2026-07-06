"""Goblin Slayer: Realms of the Fallen — launcher.

Run with:  python main.py

A complete action platformer: three hand-authored SVG realms with scrolling parallax
scenery, waves of goblin-kin, a boss per realm with fully randomised attack patterns,
coins/gems, consumables, permanent relics, lives, and an upgrade shop that visibly
evolves your knight.  All artwork is generated procedurally as SVG (goblinslayer/art.py).

Window is resizable and F11 toggles fullscreen — the game scales to fit any size.
"""
import sys

import pygame

from goblinslayer.game import Game


def main():
    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:
        pass  # keep running even without an audio device
    try:
        Game().run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    sys.exit(main())
