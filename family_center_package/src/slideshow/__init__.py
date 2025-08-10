"""
Slideshow module for the Family Center application.

This module provides slideshow functionality for displaying family media,
calendar events, and other content.
"""

from .core import SlideshowEngine
from .pygame_slideshow import PygameSlideshowEngine

__all__ = ["SlideshowEngine", "PygameSlideshowEngine"]
