"""Importing the page modules registers their @rx.page routes."""

from . import admin, configuration, consent, ecommerce, events, home

__all__ = ["admin", "configuration", "consent", "ecommerce", "events", "home"]
