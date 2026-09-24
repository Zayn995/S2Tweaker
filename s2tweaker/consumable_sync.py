"""Build sparse playback-speed profiles for supported consumable actions."""
from __future__ import annotations

import math


MIN_SPEED = 0.25
MAX_SPEED = 4.0
PROFILE_FIELDS = (
    ("action.consumable.medicine", "consumable_medicine_speed"),
    ("action.consumable.food", "consumable_food_speed"),
    ("action.consumable.drink", "consumable_drink_speed"),
)


def profile_values(settings):
    """Return changed action rates, leaving neutral categories to the game.

    These factors control the native companion's paired action montages. They
    are independent of inventory-action timing and locomotion speed. The
    companion matches exact native use-montage paths. Items reusing those
    animations share the category's speed, including quest or mod variants.
    Missing fields retain the neutral value for older settings objects.
    """
    values = {}
    for key, field in PROFILE_FIELDS:
        value = getattr(settings, field, 1.0)
        if (type(value) not in (int, float)
                or not MIN_SPEED <= value <= MAX_SPEED
                or not math.isfinite(value)):
            raise ValueError(f"Consumable action speed supports 25% to 400%: {field}")
        if not math.isclose(value, 1.0, rel_tol=0.0, abs_tol=1e-9):
            values[key] = value
    return values


def enabled(settings):
    """Whether a validated profile requests a consumable speed change."""
    return bool(profile_values(settings))
