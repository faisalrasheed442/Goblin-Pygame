"""Goblin Slayer: Realms of the Fallen — launcher.

Run with:  python main.py

A complete action platformer: three hand-authored SVG realms, waves of goblin-kin,
a boss per realm, coins/gems, and a between-realm upgrade shop that visibly evolves
your knight.  All artwork is generated procedurally as SVG (see goblinslayer/art.py).
"""
import sys

import pygame

from goblinslayer.config import WIDTH, HEIGHT, TITLE
from goblinslayer.game import Game


def main():
    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:
        pass  # keep running even without an audio device

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)
    try:
        Game(screen).run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    sys.exit(main())
