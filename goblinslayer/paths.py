"""Filesystem paths that work both from source and inside a PyInstaller bundle.

Two kinds of path:

* **resource** — read-only files shipped with the game (the ``Game/`` audio).  When
  frozen these are extracted to PyInstaller's temporary ``sys._MEIPASS`` dir; from
  source they live in the project root.
* **data** — writable files the game creates at runtime (the generated SVG art and
  ``savegame.json``).  When frozen these go to a per-user app folder that is always
  writable (so saves persist between runs, unlike the ephemeral bundle dir); from
  source they live in the project root.
"""
from __future__ import annotations

import os
import sys

FROZEN = getattr(sys, "frozen", False)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resource_root() -> str:
    if FROZEN:
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return _PROJECT_ROOT


def _data_root() -> str:
    if FROZEN:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        d = os.path.join(base, "GoblinSlayer")
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except OSError:
            return os.path.dirname(sys.executable)
    return _PROJECT_ROOT


RESOURCE_ROOT = _resource_root()
DATA_ROOT = _data_root()


def resource(*parts: str) -> str:
    """Path to a bundled, read-only resource shipped with the game."""
    return os.path.join(RESOURCE_ROOT, *parts)


def data(*parts: str) -> str:
    """Path to a writable, persistent data file created at runtime."""
    return os.path.join(DATA_ROOT, *parts)
