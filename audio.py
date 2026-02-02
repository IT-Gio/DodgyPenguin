import pygame
from utils import resource_path
import os

MASTER_VOL = 1.0
MUSIC_VOL = 0.10
SFX_VOL = 1.0

sound_start_game = None
sound_high_score = None
sound_pickup = None
sound_game_over = None
sound_spawn = None

def asset_path(file):
    """Return the path to a file inside the assets folder."""
    return resource_path(os.path.join("assets", file))

def init_audio():
    global sound_start_game, sound_high_score, sound_pickup, sound_game_over, sound_spawn

    pygame.mixer.init()

    # Load SFX
    sound_start_game = pygame.mixer.Sound(asset_path("music/start_game.wav"))
    sound_high_score = pygame.mixer.Sound(asset_path("music/high_score.wav"))
    sound_pickup = pygame.mixer.Sound(asset_path("music/pickup.wav"))
    sound_game_over = pygame.mixer.Sound(asset_path("music/game_over.wav"))
    sound_spawn = pygame.mixer.Sound(asset_path("music/spawn_item.mp3"))  # quieter later

    # Load background music
    bg_music = asset_path("music/theme.mp3")
    pygame.mixer.music.load(bg_music)
    pygame.mixer.music.play(-1)

    apply_volumes()

def apply_volumes():
    pygame.mixer.music.set_volume(MASTER_VOL * MUSIC_VOL)

    if sound_start_game:
        sound_start_game.set_volume(MASTER_VOL * SFX_VOL)

    if sound_high_score:
        sound_high_score.set_volume(MASTER_VOL * SFX_VOL)

    if sound_pickup:
        sound_pickup.set_volume(MASTER_VOL * SFX_VOL)

    if sound_game_over:
        sound_game_over.set_volume(MASTER_VOL * SFX_VOL)

    if sound_spawn:
        # ambient / subtle sound → quieter
        sound_spawn.set_volume(MASTER_VOL * SFX_VOL * 0.35)
