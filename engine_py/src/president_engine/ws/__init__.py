"""
WebSocket server and event handling for the President game.
"""

from .events import *
from .server import app

__all__ = ["app"] 