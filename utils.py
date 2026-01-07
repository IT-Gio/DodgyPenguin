import os
import sys
import pygame


# ===============================
# PATH HELPERS
# ===============================

def resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource (works in dev + PyInstaller).
    Use ONLY for read-only assets (images, sounds, fonts, etc).
    """
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_save_path(filename: str) -> str:
    """
    Get a writable save path (macOS-safe, Windows-safe).
    Use for ALL player data files.
    """
    if sys.platform == "darwin":  # macOS
        base = os.path.join(
            os.path.expanduser("~"),
            "Library",
            "Application Support",
            "DodgyPenguin"
        )
    else:  # Windows / Linux
        base = os.path.join(os.path.abspath("."), "saves")

    os.makedirs(base, exist_ok=True)
    return os.path.join(base, filename)


# ===============================
# GENERAL UTILS
# ===============================

def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def circle_rect_overlap(cx, cy, cr, rect: pygame.Rect) -> bool:
    """True if circle intersects rect."""
    closest_x = clamp(cx, rect.left, rect.right)
    closest_y = clamp(cy, rect.top, rect.bottom)
    dx = cx - closest_x
    dy = cy - closest_y
    return (dx * dx + dy * dy) <= (cr * cr)


def calculate_foot_ratio(surface: pygame.Surface) -> float:
    """
    Returns a float (0.0–1.0) indicating where the 'feet' are vertically
    inside the sprite, based on the lowest non-transparent pixel.
    """
    width, height = surface.get_size()
    pixel_array = pygame.surfarray.pixels_alpha(surface)

    lowest_y = 0
    for y in range(height - 1, -1, -1):
        if pixel_array[:, y].max() > 0:
            lowest_y = y
            break

    del pixel_array  # unlock surface
    return lowest_y / height


# ===============================
# SAVE FILE HELPERS
# ===============================

def _load_int(filename: str, default: int = 0) -> int:
    path = get_save_path(filename)
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(str(default))
        return default

    try:
        with open(path, "r") as f:
            return int(f.read().strip())
    except Exception:
        return default


def _save_int(filename: str, value: int):
    path = get_save_path(filename)
    with open(path, "w") as f:
        f.write(str(int(value)))


# ===============================
# GAME DATA (PUBLIC API)
# ===============================

def load_fish_total() -> int:
    return _load_int("fish.txt", 0)


def save_fish_total(n: int):
    _save_int("fish.txt", n)


def load_highscore() -> int:
    return _load_int("highscore.txt", 0)


def save_highscore(score: int):
    _save_int("highscore.txt", score)


def load_owned_skins() -> list[str]:
    path = get_save_path("owned_skins.txt")
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write("default")
        return ["default"]

    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]


def save_owned_skins(skins: list[str]):
    path = get_save_path("owned_skins.txt")
    with open(path, "w") as f:
        f.write("\n".join(skins))
