import pygame
import random
import sys
import os
import math


from utils import resource_path, clamp, load_fish_total, save_fish_total
import audio
from screenwrap import Screen
import player
from player import Penguin, AVAILABLE_SKINS, set_selected_skin

from entities import (
    FishPowerUp, Pebble, MultiplierPowerUp,
    PatchSnowflake, ShovelPowerUp, SnowPatch, Snowball
)

# --------------------------------------------------
# Helpers
# --------------------------------------------------


SKIN_PRICES = {
    "default": 0,
    "otto": 500,
}
from utils import (
    load_owned_skins,
    save_owned_skins,
    load_highscore,
    save_highscore,
)


def draw_centered_text(surface, text, font, color, y_offset=0):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(
        center=(surface.get_width() // 2, surface.get_height() // 2 + y_offset)
    )
    surface.blit(rendered, rect)


def draw_ice_tile_background(surface, tile_img, width, height, scale=5):
    tile_w, tile_h = tile_img.get_size()
    scaled_tile = pygame.transform.scale(tile_img, (tile_w * scale, tile_h * scale))
    sw, sh = scaled_tile.get_size()

    for x in range(0, width, sw):
        for y in range(0, height, sh):
            surface.blit(scaled_tile, (x, y))


def draw_blob_spot(surface, rect: pygame.Rect, alpha=45):
    """
    Draw a dark "preview spot" for the incoming snow patch.
    Not a square: uses an ellipse (blob-like) with soft alpha.
    """
    blob = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    # Ellipse blob (matches patch vibe, avoids square)
    pygame.draw.ellipse(blob, (0, 0, 0, alpha), blob.get_rect())
    surface.blit(blob, rect.topleft)


def draw_center_panel(surface, w, h, alpha=210):
    """
    Semi-transparent centered panel (so GAME OVER doesn't dim the entire background).
    Returns its rect.
    """
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    panel.fill((255, 255, 255, alpha))
    rect = panel.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2))
    surface.blit(panel, rect.topleft)
    return rect


# --------------------------------------------------
# Game states
# --------------------------------------------------

START, PLAYING, GAME_OVER, SKIN_MENU, VOLUME_MENU = range(5)


# --------------------------------------------------
# Main game
# --------------------------------------------------

def run_game():
    pygame.init()
    audio.init_audio()

    WIDTH, HEIGHT = 800, 600
    screen = Screen(WIDTH, HEIGHT)
    clock = pygame.time.Clock()

    FONT = pygame.font.Font(
    resource_path("fonts/pixel.ttf"), 24
    )
    BIG_FONT = pygame.font.Font(
        resource_path("fonts/pixel.ttf"), 48
    )
    

    state = START
    prev_state = START

    highscore = load_highscore()
    
    floor_tile = pygame.image.load(resource_path("bg/floor.png")).convert()

    # -------------------------
    # Load multiplier frames (3x3, 32x32)
    # -------------------------
    sprite_sheet = pygame.image.load(resource_path("powerups/mult.png")).convert_alpha()
    mult_frames = []
    fw, fh = 32, 32
    for r in range(3):
        for c in range(3):
            mult_frames.append(sprite_sheet.subsurface((c * fw, r * fh, fw, fh)))

    # persistent fish total (saved across sessions)
    total_fish = load_fish_total()

    owned_skins = load_owned_skins()


    # -------------------------
    # HUD icons (scaled)
    # -------------------------

    controls_bg = pygame.image.load(
        resource_path("ui/banner_skin.png")
    ).convert_alpha()

    ICON_SIZE_FISH = 48
    ICON_SIZE_PEBBLE = 64

    fish_icon = pygame.image.load(resource_path("powerups/fishy.png")).convert_alpha().subsurface((0, 0, 32, 32))
    fish_icon = pygame.transform.scale(fish_icon, (ICON_SIZE_FISH, ICON_SIZE_FISH))

    pebble_icon = pygame.image.load(resource_path("powerups/pebble.png")).convert_alpha().subsurface((0, 0, 32, 32))
    pebble_icon = pygame.transform.scale(pebble_icon, (ICON_SIZE_PEBBLE, ICON_SIZE_PEBBLE))


    title_bg = pygame.image.load(
        resource_path("ui/title.png")
    ).convert_alpha()

    title_bg = pygame.transform.scale(
        title_bg,
        (int(screen.width * 0.9), int(screen.height / 2 ))
    )


    # --------------------------------------------------
    # Skin preview sprites (walk_down frame 0)
    # --------------------------------------------------
    skin_previews = {}

    for skin in AVAILABLE_SKINS:
        path = resource_path(f"animations/{skin}/walk_down.png")
        sheet = pygame.image.load(path).convert_alpha()

        # take first frame (32x32)
        frame = sheet.subsurface((0, 0, 32, 32))

        # scale to look nice in menu
        frame = pygame.transform.scale(frame, (96, 96))

        skin_previews[skin] = frame


    GO_LOOP_WIDTH = screen.width * 2


    # -------------------------
    # A safe key proxy for GAME_OVER animation
    # (so Penguin.update() can read keys[...] without KeyError)
    # -------------------------
    class KeyProxy:
        def __init__(self, pressed=None):
            self.pressed = pressed or {}

        def __getitem__(self, key):
            return bool(self.pressed.get(key, False))



    # --------------------------------------------------
    # CAMERA (Undertale-style deadzone)
    # --------------------------------------------------
    CAMERA_DEADZONE_W = int(screen.width * 0.55)   # wider
    CAMERA_DEADZONE_H = int(screen.height * 0.45)  # taller

    
    def update_camera(game_data, player):
        cam_x = game_data.get("camera_x", 0.0)
        cam_y = game_data.get("camera_y", 0.0)

        screen_cx = cam_x + screen.width // 2
        screen_cy = cam_y + screen.height // 2

        dz_half_w = CAMERA_DEADZONE_W // 2
        dz_half_h = CAMERA_DEADZONE_H // 2

        # Horizontal deadzone
        if player.world_x < screen_cx - dz_half_w:
            cam_x = player.world_x + dz_half_w - screen.width // 2
        elif player.world_x > screen_cx + dz_half_w:
            cam_x = player.world_x - dz_half_w - screen.width // 2

        # Vertical deadzone
        if player.world_y < screen_cy - dz_half_h:
            cam_y = player.world_y + dz_half_h - screen.height // 2
        elif player.world_y > screen_cy + dz_half_h:
            cam_y = player.world_y - dz_half_h - screen.height // 2

        # Smooth camera motion (important)
        game_data["camera_x"] += (cam_x - game_data["camera_x"]) * 0.12
        game_data["camera_y"] += (cam_y - game_data["camera_y"]) * 0.12



    # -------------------------
    # TUNING (spawn rates / preview)
    # -------------------------
    PATCH_SPAWN_MIN = 2500   # faster patches
    PATCH_SPAWN_MAX = 4500
    PATCH_PREVIEW_MS = 900   # preview time before patch appears
    PATCH_FLAKES_PREVIEW = 45
    PATCH_FLAKES_ACTIVE = 30

    FISH_SPAWN_MS = 3500     # quicker fish
    PEBBLE_SPAWN_MIN = 12000
    PEBBLE_SPAWN_MAX = 20000
    SHOVEL_SPAWN_MS = 35000  # (optional) a bit quicker than 45s

    POWERUP_PREVIEW_MS = 750 # dim circle preview before powerups appear

    # -------------------------
    # Preview drawing (dim circle in world space)
    # -------------------------
    def draw_world_preview_circle(world_x, world_y, radius, alpha, pulse=0.0):
        # convert world -> screen
        sx = int(world_x - game_data["camera_x"])
        sy = int(world_y - game_data["camera_y"])

        r = int(radius + pulse)
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (0, 0, 0, alpha), (r, r), r)
        screen.screen.blit(surf, (sx - r, sy - r))

    # -------------------------
    # Reset / game data
    # -------------------------
    def reset():
        penguin = Penguin(screen)
        penguin.world_x = penguin.x
        penguin.world_y = penguin.y

        return {
            "penguin": penguin,
            "snowballs": [],
            "score": 0,
            "score_timer": 0,
            "spawn_timer": 0,
            "new_high": False,

            "fish": None,
            "fish_timer": 0,
            "spawn_delay_bonus": 0,

            "pebble": None,
            "pebble_timer": 0,
            "shield_count": 0,  # stacks up to 3
            "invincible": False,
            "invincible_timer": 0,
            "show_shield_text": False,
            "shield_text_timer": 0,

            "multiplier_spawn_timer": 0,
            "mult_powerup": None,
            "mult_active": False,
            "mult_timer": 0,

            "shovel": None,
            "shovel_timer": 0,

            "fish_collected": 0,

            "pending_patch_world_rect": None,
            "pending_patch_flakes": [],
            "pending_fish": None,
            "pending_pebble": None,
            "pending_shovel": None,
            "pending_mult": None,
            
        }

    game_data = reset()

    # snow patch system
    snow_patches = []
    patch_snowflakes = []
    next_patch_time = pygame.time.get_ticks() + random.randint(PATCH_SPAWN_MIN, PATCH_SPAWN_MAX)


    # "pre-snowfall" animation before a patch appears
    snowfall_active = False
    snowfall_start_time = 0
    pre_snowflakes = []
    pending_patch_rect = None

    # volume menu selection
    vol_items = ["Master", "Music", "SFX", "Back"]
    vol_index = 0

    # fish save gate (so we save once per game over)
    fish_saved_this_gameover = False

    # -------------------------
    # HUD layout helpers (centered rows)
    # -------------------------
    HUD_X = 10
    SCORE_POS = (10, 10)

    FISH_ROW_Y = 80        # centerline
    PEBBLE_ROW_Y = 140     # centerline
    PEBBLE_SPACING = 12

    # --------------------------------------------------
    # Main loop
    # --------------------------------------------------
    while True:
        dt = clock.tick(60)
        now = pygame.time.get_ticks()

        # ==========================
        # EVENTS (ONLY PLACE INPUT LIVES)
        # ==========================
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.VIDEORESIZE:
                screen.update_size(event.w, event.h)

            if event.type == pygame.KEYDOWN:

                # ---------- GLOBAL ESC ----------
                if event.key == pygame.K_ESCAPE:
                    if state in (SKIN_MENU, VOLUME_MENU):
                        state = prev_state
                    else:
                        pygame.quit()
                        sys.exit()

                # ---------- START ----------
                elif state == START:
                    if event.key == pygame.K_SPACE:
                        audio.sound_start_game.play()
                        state = PLAYING

                    elif event.key == pygame.K_s:
                        audio.sound_pickup.play()
                        prev_state = START
                        state = SKIN_MENU

                    elif event.key == pygame.K_v:
                        audio.sound_pickup.play()
                        prev_state = START
                        state = VOLUME_MENU

                # ---------- GAME OVER ----------
                elif state == GAME_OVER:
                    if event.key == pygame.K_SPACE:
                        game_data = reset()
                        snow_patches.clear()
                        patch_snowflakes.clear()
                        pre_snowflakes.clear()
                        snowfall_active = False
                        pending_patch_rect = None
                        next_patch_time = now + random.randint(8000, 14000)
                        fish_saved_this_gameover = False
                        state = PLAYING

                # ---------- SKIN MENU ----------
                elif state == SKIN_MENU:
                    idx = AVAILABLE_SKINS.index(player.SELECTED_SKIN)

                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        set_selected_skin(AVAILABLE_SKINS[(idx - 1) % len(AVAILABLE_SKINS)])

                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        set_selected_skin(AVAILABLE_SKINS[(idx + 1) % len(AVAILABLE_SKINS)])

                    elif event.key == pygame.K_RETURN:
                        skin = player.SELECTED_SKIN
                        cost = SKIN_PRICES.get(skin, 0)

                        if skin in owned_skins:
                            audio.sound_pickup.play()
                            state = prev_state

                        elif total_fish >= cost:
                            total_fish -= cost
                            save_fish_total(total_fish)
                            owned_skins.add(skin)
                            save_owned_skins(owned_skins)
                            audio.sound_pickup.play()
                            state = prev_state

                # ---------- VOLUME MENU ----------
                elif state == VOLUME_MENU:
                    if event.key == pygame.K_UP:
                        vol_index = (vol_index - 1) % len(vol_items)

                    elif event.key == pygame.K_DOWN:
                        vol_index = (vol_index + 1) % len(vol_items)

                    elif event.key == pygame.K_LEFT:
                        if vol_items[vol_index] == "Master":
                            audio.MASTER_VOL = clamp(audio.MASTER_VOL - 0.05, 0, 1)
                        elif vol_items[vol_index] == "Music":
                            audio.MUSIC_VOL = clamp(audio.MUSIC_VOL - 0.05, 0, 1)
                        elif vol_items[vol_index] == "SFX":
                            audio.SFX_VOL = clamp(audio.SFX_VOL - 0.05, 0, 1)
                        audio.apply_volumes()

                    elif event.key == pygame.K_RIGHT:
                        if vol_items[vol_index] == "Master":
                            audio.MASTER_VOL = clamp(audio.MASTER_VOL + 0.05, 0, 1)
                        elif vol_items[vol_index] == "Music":
                            audio.MUSIC_VOL = clamp(audio.MUSIC_VOL + 0.05, 0, 1)
                        elif vol_items[vol_index] == "SFX":
                            audio.SFX_VOL = clamp(audio.SFX_VOL + 0.05, 0, 1)
                        audio.apply_volumes()

                    elif event.key == pygame.K_RETURN and vol_items[vol_index] == "Back":
                        state = prev_state

        keys = pygame.key.get_pressed()

        # ==========================
        # RENDER + UPDATE
        # ==========================
        draw_ice_tile_background(screen.screen, floor_tile, screen.width, screen.height, scale=5)

        # -------------------------
        # START
        # -------------------------
        if state == START:
            # ---------- TITLE IMAGE (BACKGROUND PLATE) ----------
            title_img = pygame.image.load(
                resource_path("ui/title.png")
            ).convert_alpha()

            # move the sign DOWN a bit
            title_rect = title_img.get_rect(
                center=(screen.width // 2, int(screen.height * 0.5))
            )
            screen.screen.blit(title_img, title_rect)

            # ---------- TITLE TEXT (ON TOP OF SIGN, LOWERED) ----------
            title_text = BIG_FONT.render("Dodgy Penguin", True, (255, 25, 24))
            title_text_rect = title_text.get_rect(
                center=(title_rect.centerx, title_rect.centery - 200)
            )
            screen.screen.blit(title_text, title_text_rect)

            # ---------- MENU TEXT (CLOSER TO TITLE) ----------
            base_y = title_rect.bottom - 300
            line_gap = 30

            draw_centered_text(
                screen.screen,
                "[ SPACE ]  START GAME",
                FONT,
                (20, 162, 18),
                base_y - screen.height // 2
            )

            draw_centered_text(
                screen.screen,
                "[ S ]      SKINS",
                FONT,
                (253, 162, 18),
                base_y - screen.height // 2 + line_gap
            )

            draw_centered_text(
                screen.screen,
                "[ V ]      VOLUME",
                FONT,
                (67, 1, 105),
                base_y - screen.height // 2 + line_gap * 2
            )

            # ---------- TOTAL FISH ----------
            total_fish = load_fish_total()
            draw_centered_text(
                screen.screen,
                f"TOTAL FISH: {total_fish}",
                FONT,
                (0, 100, 200),
                base_y - screen.height // 2 + line_gap * 4
            )

        # -----------------------
        # SKIN MENU
        # -------------------------
        elif state == SKIN_MENU:
            # ---------- COLORS ----------
            UI_BLUE = (20, 60, 120)
            TITLE_COLOR = (253, 162, 18)

            CTRL_FONT = pygame.font.Font(resource_path("fonts/pixel.ttf"), 16)

            # ---------- TITLE ----------
            draw_centered_text(
                screen.screen,
                "SELECT SKIN",
                BIG_FONT,
                TITLE_COLOR,
                -int(screen.height * 0.45)
            )

            # ---------- LAYOUT (MOVED UP) ----------
            cx = screen.width // 2
            cy = screen.height // 2 - int(screen.height * 0.08)

            sprite_size = int(min(screen.width, screen.height) * 0.18)
            spacing = int(sprite_size * 1.7)

            y_sprite = cy - int(sprite_size * 0.15)
            y_name = y_sprite + sprite_size // 2 + 16
            y_status = y_name + 24

            total_width = spacing * (len(AVAILABLE_SKINS) - 1)
            start_x = cx - total_width // 2

            # ---------- SKINS ----------
            for i, skin in enumerate(AVAILABLE_SKINS):
                x = start_x + i * spacing

                selected = (skin == player.SELECTED_SKIN)
                owned = skin in owned_skins
                price = SKIN_PRICES.get(skin, 0)

                preview = pygame.transform.scale(
                    skin_previews[skin],
                    (sprite_size, sprite_size)
                )

                if selected:
                    box = sprite_size + 14
                    pygame.draw.rect(
                        screen.screen,
                        UI_BLUE,
                        pygame.Rect(
                            x - box // 2,
                            y_sprite - box // 2,
                            box,
                            box
                        ),
                        3
                    )

                screen.screen.blit(
                    preview,
                    preview.get_rect(center=(x, y_sprite))
                )

                name = FONT.render(skin.upper(), True, UI_BLUE if selected else (0, 0, 0))
                screen.screen.blit(name, name.get_rect(center=(x, y_name)))

                if owned:
                    owned_txt = FONT.render("OWNED", True, (0, 160, 0))
                    screen.screen.blit(owned_txt, owned_txt.get_rect(center=(x, y_status)))
                else:
                    price_txt = FONT.render(str(price), True, (200, 50, 50))
                    screen.screen.blit(price_txt, price_txt.get_rect(center=(x - 12, y_status)))
                    screen.screen.blit(
                        fish_icon,
                        fish_icon.get_rect(center=(x + 22, y_status))
                    )

            # ---------- TOTAL FISH ----------
            total_fish = load_fish_total()
            total_txt = FONT.render(f"TOTAL FISH: {total_fish}", True, UI_BLUE)
            screen.screen.blit(
                total_txt,
                total_txt.get_rect(center=(cx, screen.height * 0.60))
            )

            # ---------- CONTROLS PANEL ----------
            panel_width = 650
            panel_height = 200

            panel = pygame.transform.scale(controls_bg, (panel_width, panel_height))
            panel_rect = panel.get_rect(center=(cx, screen.height * 0.82))
            screen.screen.blit(panel, panel_rect)

            # ---------- PANEL SAFE AREA ----------
            inner_left = panel_rect.left + 60
            inner_right = panel_rect.right - 60
            key_y = panel_rect.centery  - 40
            label_y = key_y + 18

            # ---------- KEY BOX ----------
            def draw_key_box(text, x, y):
                surf = CTRL_FONT.render(text, True, UI_BLUE)
                rect = surf.get_rect(center=(x, y))
                box = rect.inflate(8, 8)
                pygame.draw.rect(screen.screen, UI_BLUE, box, 2)
                screen.screen.blit(surf, rect)

            # ---------- CONTROLS ----------
            controls = [
                ("A / D", ["SELECT"]),
                ("ENTER", ["BUY", "SELECT"]),
                ("ESC", ["BACK"]),
            ]

            slot_w = (inner_right - inner_left) // len(controls)

            for i, (key, labels) in enumerate(controls):
                x = inner_left + slot_w * i + slot_w // 2

                draw_key_box(key, x, key_y)

                for j, line in enumerate(labels):
                    lbl = CTRL_FONT.render(line, True, UI_BLUE)
                    screen.screen.blit(
                        lbl,
                        lbl.get_rect(center=(x, label_y + j * 16))
                    )


        # -------------------------
        # VOLUME MENU
        # -------------------------
        elif state == VOLUME_MENU:
            draw_centered_text(screen.screen, "Volume", BIG_FONT, (0, 0, 0), -160)

            values = {"Master": audio.MASTER_VOL, "Music": audio.MUSIC_VOL, "SFX": audio.SFX_VOL, "Back": None}
            y0 = -40
            for i, item in enumerate(vol_items):
                y = y0 + i * 45
                selected = (i == vol_index)
                col = (0, 120, 200) if selected else (0, 0, 0)

                if item == "Back":
                    draw_centered_text(screen.screen, "Back", FONT, col, y)
                else:
                    pct = int(values[item] * 100)
                    draw_centered_text(screen.screen, f"{item}: {pct}%  (L/R)", FONT, col, y)

            draw_centered_text(screen.screen, "ESC to return", FONT, (0, 0, 0), 200)

        # -------------------------
        # PLAYING
        # -------------------------
        elif state == PLAYING:
            penguin = game_data["penguin"]

            # --------------------------------------------------
            # WORLD/CAMERA INIT (one-time)
            # --------------------------------------------------
            if "camera_x" not in game_data:
                game_data["camera_x"] = 0.0
                game_data["camera_y"] = 0.0

            # Give player world coords if missing (fixes AttributeError)
            if not hasattr(penguin, "world_x"):
                penguin.world_x = float(screen.width // 2)
                penguin.world_y = float(screen.height // 2)
                # ensure screen-space matches world-space at start
                penguin.x = penguin.world_x - game_data["camera_x"]
                penguin.y = penguin.world_y - game_data["camera_y"]

            # --------------------------------------------------
            # INFINITE BACKGROUND (scrolls with camera)
            # NOTE: this replaces the earlier draw_ice_tile_background call.
            # --------------------------------------------------
            tile = floor_tile
            base_tw, base_th = tile.get_size()
            tw, th = base_tw * 5, base_th * 5
            scaled_tile = pygame.transform.scale(tile, (tw, th))

            offset_x = int((-game_data["camera_x"]) % tw)
            offset_y = int((-game_data["camera_y"]) % th)

            for x in range(-tw, screen.width + tw, tw):
                for y in range(-th, screen.height + th, th):
                    screen.screen.blit(scaled_tile, (x + offset_x, y + offset_y))

            # --------------------------------------------------
            # SHOVEL (world-aware)
            # --------------------------------------------------
            game_data["shovel_timer"] += dt
            if game_data["shovel_timer"] >= 45000 and game_data["shovel"] is None:
                game_data["shovel"] = ShovelPowerUp(screen)
                game_data["shovel_timer"] = 0

            if game_data["shovel"]:
                game_data["shovel"].update(dt)

                # if the entity supports world coords, keep it in world space
                if not hasattr(game_data["shovel"], "world_x"):
                    game_data["shovel"].world_x = float(game_data["shovel"].x)
                    game_data["shovel"].world_y = float(game_data["shovel"].y)

                game_data["shovel"].x = game_data["shovel"].world_x - game_data["camera_x"]
                game_data["shovel"].y = game_data["shovel"].world_y - game_data["camera_y"]
                game_data["shovel"].draw()

                if game_data["shovel"].collides_with(penguin):
                    audio.sound_pickup.play()
                    snow_patches.clear()
                    patch_snowflakes.clear()

                    CLEAR_RADIUS = 200
                    # IMPORTANT: use WORLD coords (so it works with camera)
                    game_data["snowballs"] = [
                        sb for sb in game_data["snowballs"]
                        if (
                            (getattr(sb, "world_x", sb.x) - penguin.world_x) ** 2
                            + (getattr(sb, "world_y", sb.y) - penguin.world_y) ** 2
                            > CLEAR_RADIUS ** 2
                        )
                    ]
                    game_data["shovel"] = None

            # --------------------------------------------------
            # SNOW PATCH PREVIEW + SPAWN (world-aware)
            # pending_patch_rect is SCREEN-space area; convert to WORLD
            # --------------------------------------------------
            # --------------------------------------------------
            # SNOW PATCH PREVIEW → WORLD SPAWN (FIXED)
            # --------------------------------------------------
            
            # --------------------------------------------------
            # SNOW PATCH PREVIEW -> WORLD SPAWN (WORLD-ANCHORED)
            # --------------------------------------------------
            if (not snowfall_active) and now >= next_patch_time:
                snowfall_active = True
                snowfall_start_time = now

                # Choose a SCREEN position, but immediately convert to WORLD rect
                screen_rect = pygame.Rect(
                    random.randint(0, max(0, screen.width - 200)),
                    random.randint(0, max(0, screen.height - 160)),
                    random.randint(160, 240),
                    random.randint(120, 190)
                )

                world_rect = pygame.Rect(
                    int(screen_rect.x + game_data["camera_x"]),
                    int(screen_rect.y + game_data["camera_y"]),
                    screen_rect.w,
                    screen_rect.h
                )

                game_data["pending_patch_world_rect"] = world_rect

                # Preview flakes must also be world-anchored
                pending_flakes = []
                for _ in range(PATCH_FLAKES_PREVIEW):
                    # make a temporary patch-like object with a *world rect*,
                    # but PatchSnowflake expects .rect, so we keep it in SCREEN while drawing ourselves
                    fx = random.randint(world_rect.left, world_rect.right)
                    fy = random.randint(world_rect.top - 200, world_rect.top)
                    pending_flakes.append([float(fx), float(fy), random.uniform(0.6, 1.3)])
                game_data["pending_patch_flakes"] = pending_flakes

            if snowfall_active and game_data["pending_patch_world_rect"]:
                wr = game_data["pending_patch_world_rect"]

                # Draw preview blob in WORLD space (so it moves with camera)
                # (centered dim circle/ellipse-ish; you can keep your blob function but anchored to world)
                # We'll use circle preview to guarantee it tracks the world.
                pulse = 2.5 * (0.5 + 0.5 * math.sin(now * 0.01))
                draw_world_preview_circle(wr.centerx, wr.centery, max(wr.w, wr.h) // 3, 55, pulse=pulse)

                # Draw preview flakes world->screen
                for fl in game_data["pending_patch_flakes"]:
                    fl[1] += fl[2] * 1.6  # fall speed
                    sx = int(fl[0] - game_data["camera_x"])
                    sy = int(fl[1] - game_data["camera_y"])
                    pygame.draw.circle(screen.screen, (255, 255, 255), (sx, sy), 2)

                if now - snowfall_start_time > PATCH_PREVIEW_MS:
                    snowfall_active = False

                    # Spawn the real patch in WORLD space
                    world_rect = game_data["pending_patch_world_rect"]
                    patch = SnowPatch(screen, world_rect)
                    patch.world_rect = world_rect.copy()   # enforce world-awareness
                    snow_patches.append(patch)

                    for _ in range(PATCH_FLAKES_ACTIVE):
                        patch_snowflakes.append(PatchSnowflake(patch))

                    # cleanup
                    game_data["pending_patch_world_rect"] = None
                    game_data["pending_patch_flakes"] = []
                    next_patch_time = now + random.randint(PATCH_SPAWN_MIN, PATCH_SPAWN_MAX)


            if snowfall_active and pending_patch_rect:
                draw_blob_spot(screen.screen, pending_patch_rect, alpha=45)

                for f in pre_snowflakes:
                    f.update()
                    f.draw(screen.screen)

                if now - snowfall_start_time > 2000:
                    snowfall_active = False

                    pwx, pwy = game_data["pending_patch_world"]

                    world_rect = pygame.Rect(
                        int(pwx),
                        int(pwy),
                        pending_patch_rect.w,
                        pending_patch_rect.h
                    )

                    patch = SnowPatch(screen, world_rect)
                    patch.world_rect = world_rect

                    snow_patches.append(patch)

                    audio.sound_snow.play()
                    for _ in range(25):
                        patch_snowflakes.append(PatchSnowflake(patch))

                    pending_patch_rect = None
                    game_data["pending_patch_world"] = None
                    pre_snowflakes.clear()
                    next_patch_time = now + random.randint(5000, 9000)

            # cleanup expired patches
            for p in snow_patches[:]:
                if p.expired():
                    snow_patches.remove(p)
                    patch_snowflakes[:] = [f for f in patch_snowflakes if f.patch != p]

            # draw patches + flakes (camera-relative)
            for p in snow_patches:
                p.draw(
                    screen.screen,
                    game_data["camera_x"],
                    game_data["camera_y"]
                )

            for f in patch_snowflakes:
                f.update()
                f.draw(screen.screen)

            # --------------------------------------------------
            # PLAYER (world movement + undertale camera)
            # --------------------------------------------------
            # Keep player screen-space centered relative to camera before update
            penguin.x = penguin.world_x - game_data["camera_x"]
            penguin.y = penguin.world_y - game_data["camera_y"]

            old_x, old_y = penguin.x, penguin.y
            penguin.update(keys, dt, snow_patches)

            # Convert screen delta -> world delta
            penguin.world_x += (penguin.x - old_x)
            penguin.world_y += (penguin.y - old_y)

            # Apply camera follow AFTER player moves
            update_camera(game_data, penguin)

            # Draw player camera-relative
            penguin.x = penguin.world_x - game_data["camera_x"]
            penguin.y = penguin.world_y - game_data["camera_y"]
            penguin.draw()

            # --------------------------------------------------
            # FISH (world-aware)
            # --------------------------------------------------aa
            game_data["fish_timer"] += dt

            # start preview (no fish yet)
            if game_data["fish_timer"] >= FISH_SPAWN_MS and game_data["fish"] is None and game_data["pending_fish"] is None:
                # pick a world position near camera view
                wx = game_data["camera_x"] + random.randint(60, screen.width - 60)
                wy = game_data["camera_y"] + random.randint(60, screen.height - 60)
                game_data["pending_fish"] = {"t0": now, "x": wx, "y": wy}
                game_data["fish_timer"] = 0

            # draw preview circle and finalize spawn
            if game_data["pending_fish"] is not None:
                pf = game_data["pending_fish"]
                pulse = 2.0 * (0.5 + 0.5 * math.sin(now * 0.015))
                draw_world_preview_circle(pf["x"], pf["y"], 26, 45, pulse=pulse)

                if now - pf["t0"] >= POWERUP_PREVIEW_MS:
                    game_data["fish"] = FishPowerUp(screen)
                    game_data["fish"].world_x = float(pf["x"])
                    game_data["fish"].world_y = float(pf["y"])

                    game_data["pending_fish"] = None

                 

            # update/draw fish world-aware
            if game_data["fish"]:
                game_data["fish"].update(dt)
                if hasattr(game_data["fish"], "world_x"):
                    game_data["fish"].x = game_data["fish"].world_x - game_data["camera_x"]
                    game_data["fish"].y = game_data["fish"].world_y - game_data["camera_y"]
                game_data["fish"].draw()

                if game_data["fish"].collides_with(penguin):
                    audio.sound_pickup.play()
                    game_data["spawn_delay_bonus"] = min(30, game_data["spawn_delay_bonus"] + 5)
                    game_data["fish_collected"] += 1
                    game_data["fish"] = None

            # --------------------------------------------------
            # PEBBLE (stacking shield up to 3, world-aware)
            # --------------------------------------------------
            game_data["pebble_timer"] += dt
            if game_data["pebble_timer"] >= random.randint(15000, 25000) and game_data["pebble"] is None:
                game_data["pebble"] = Pebble(screen)
                game_data["pebble_timer"] = 0
                if not hasattr(game_data["pebble"], "world_x"):
                    game_data["pebble"].world_x = float(game_data["pebble"].x)
                    game_data["pebble"].world_y = float(game_data["pebble"].y)

            if game_data["pebble"]:
                game_data["pebble"].update(dt)
                if hasattr(game_data["pebble"], "world_x"):
                    game_data["pebble"].x = game_data["pebble"].world_x - game_data["camera_x"]
                    game_data["pebble"].y = game_data["pebble"].world_y - game_data["camera_y"]
                game_data["pebble"].draw()

                if game_data["pebble"].collides_with(penguin):
                    audio.sound_pickup.play()
                    game_data["shield_count"] = min(3, game_data["shield_count"] + 1)
                    game_data["pebble"] = None

            # --------------------------------------------------
            # SNOWBALLS (world-aware)
            # --------------------------------------------------
            game_data["spawn_timer"] += dt
            delay_ms = max(250, (60 - game_data["score"] * 2 + game_data["spawn_delay_bonus"]) * 16)

            if game_data["spawn_timer"] >= delay_ms:
                sb = Snowball(screen, game_data["score"])
                # first time: convert to world coords
                if not hasattr(sb, "world_x"):
                    sb.world_x = float(sb.x) + game_data["camera_x"]
                    sb.world_y = float(sb.y) + game_data["camera_y"]
                game_data["snowballs"].append(sb)
                game_data["spawn_timer"] = 0

            for sb in game_data["snowballs"][:]:
                # update motion (if update uses screen coords, we update screen coords then re-sync world)
                if hasattr(sb, "world_x"):
                    # draw position from world
                    sb.x = sb.world_x - game_data["camera_x"]
                    sb.y = sb.world_y - game_data["camera_y"]

                sb.update()

                # after update, re-sync world from screen delta (so movement still works)
                if hasattr(sb, "world_x"):
                    sb.world_x = sb.x + game_data["camera_x"]
                    sb.world_y = sb.y + game_data["camera_y"]

                sb.draw()

                if sb.collides_with(penguin):
                    if game_data["shield_count"] > 0:
                        game_data["shield_count"] -= 1
                        game_data["snowballs"].clear()
                    else:
                        state = GAME_OVER
                        fish_saved_this_gameover = False
                        audio.sound_game_over.play()
                        break
                    
                # offscreen test in WORLD terms: if it's far behind camera
                if hasattr(sb, "world_x"):
                    if sb.world_x < game_data["camera_x"] - 200 or sb.world_x > game_data["camera_x"] + screen.width + 200 \
                       or sb.world_y < game_data["camera_y"] - 200 or sb.world_y > game_data["camera_y"] + screen.height + 200:
                        game_data["snowballs"].remove(sb)
                else:
                    if sb.is_off_screen():
                        game_data["snowballs"].remove(sb)

            # --------------------------------------------------
            # SCORE + HUD
            # --------------------------------------------------
            game_data["score_timer"] += dt
            if game_data["score_timer"] >= 2000:
                game_data["score"] += (2 if game_data["mult_active"] else 1)
                game_data["score_timer"] = 0

            # Score
            screen.screen.blit(FONT.render(f"Score: {game_data['score']}", True, (0, 0, 0)), SCORE_POS)

            # Fish icon + count
            fish_rect = fish_icon.get_rect(midleft=(HUD_X, FISH_ROW_Y))
            screen.screen.blit(fish_icon, fish_rect)
            fish_txt = FONT.render(f"x {game_data['fish_collected']}", True, (0, 0, 0))
            fish_txt_rect = fish_txt.get_rect(midleft=(fish_rect.right + 10, FISH_ROW_Y))
            screen.screen.blit(fish_txt, fish_txt_rect)

            # Pebble shield HUD (smaller boxes)
            EMPTY_BOX = 28  # smaller than before
            for i in range(3):
                x = HUD_X + i * (EMPTY_BOX + PEBBLE_SPACING)
                r = pygame.Rect(x, PEBBLE_ROW_Y - EMPTY_BOX // 2, EMPTY_BOX, EMPTY_BOX)

                if i < game_data["shield_count"]:
                    screen.screen.blit(pebble_icon, pebble_icon.get_rect(center=r.center))
                else:
                    pygame.draw.rect(screen.screen, (0, 0, 0), r, 2)


            if game_data["score"] > highscore:
                highscore = game_data["score"]     # ← THIS WAS MISSING
                save_highscore(highscore)
                game_data["new_high"] = True
            

        # -------------------------
        # GAME OVER
        # -------------------------
        elif state == GAME_OVER:
            if not fish_saved_this_gameover:
                save_fish_total(load_fish_total() + game_data["fish_collected"])
                fish_saved_this_gameover = True

            if "go_penguin" not in game_data:
                go_penguin = Penguin(screen)
                go_penguin.world_x = -200.0
                go_penguin.world_y = float(screen.height // 2)

                game_data.update({
                    "go_penguin": go_penguin,
                    "go_snowballs": [],
                    "go_spawn_timer": 0,
                    "camera_x": 0.0,
                    "camera_y": 0.0,
                    "go_vy": 0.0,
                    "go_anchor_y": go_penguin.world_y,
                    "bg_offset_x": 0.0,
                })
            else:
                go_penguin = game_data["go_penguin"]

            # Infinite background scroll
            game_data["bg_offset_x"] -= 0.3

            # Forward motion
            go_penguin.world_x += 0.6

            # Smooth dodge forces
            vy = game_data["go_vy"]
            anchor_y = game_data["go_anchor_y"]

            force_y = 0.0
            for sb in game_data["go_snowballs"]:
                dx = sb.world_x - go_penguin.world_x
                if -240 < dx < 240:
                    dy = sb.world_y - go_penguin.world_y
                    force_y += (-dy / (dy * dy + 1200)) * 85000

            force_y += (anchor_y - go_penguin.world_y) * 0.015
            vy = (vy + force_y) * 0.88
            vy = max(-2.2, min(2.2, vy))
            go_penguin.world_y += vy
            game_data["go_vy"] = vy

            update_camera(game_data, go_penguin)

            # Spawn nonstop snowballs (full right side)
            game_data["go_spawn_timer"] += dt
            if game_data["go_spawn_timer"] > 180:
                game_data["go_spawn_timer"] = 0
                sb = Snowball(screen, game_data["score"])
                sb.world_x = go_penguin.world_x + screen.width + random.randint(0, 120)
                sb.world_y = random.randint(
                    int(go_penguin.world_y - screen.height // 2),
                    int(go_penguin.world_y + screen.height // 2)
                )
                sb.vx = -random.uniform(1.8, 3.0)
                game_data["go_snowballs"].append(sb)

            # Draw looping background
            tile = pygame.transform.scale(floor_tile, (floor_tile.get_width()*5, floor_tile.get_height()*5))
            tw = tile.get_width()
            ox = int(game_data["bg_offset_x"] % tw)

            for x in range(-tw, screen.width + tw, tw):
                for y in range(0, screen.height, tile.get_height()):
                    screen.screen.blit(tile, (x + ox, y))

            # Draw snowballs
            for sb in game_data["go_snowballs"][:]:
                sb.world_x += sb.vx
                sb.x = sb.world_x - game_data["camera_x"]
                sb.y = sb.world_y - game_data["camera_y"]
                sb.draw()
                if sb.world_x < go_penguin.world_x - screen.width:
                    game_data["go_snowballs"].remove(sb)

            # Draw penguin
            go_penguin.x = go_penguin.world_x - game_data["camera_x"]
            go_penguin.y = go_penguin.world_y - game_data["camera_y"]
            go_penguin.update(KeyProxy({pygame.K_RIGHT: True}), dt, [])
            go_penguin.draw()

            # UI
            draw_centered_text(screen.screen, "GAME OVER", BIG_FONT, (200, 0, 0), -140)
            draw_centered_text(screen.screen, f"Score: {game_data['score']}", FONT, (0, 0, 0), -60)
            draw_centered_text(screen.screen, f"High Score: {highscore}", FONT, (0, 0, 0), -20)
            draw_centered_text(screen.screen, f"Total Fish: {load_fish_total()}", FONT, (0, 100, 200), 40)
            draw_centered_text(screen.screen, "SPACE = Restart", FONT, (0, 0, 0), 120)
            draw_centered_text(screen.screen, "S = Skins    V = Volume", FONT, (0, 0, 0), 160)
            draw_centered_text(screen.screen, "ESC = Quit", FONT, (0, 0, 0), 200)

        pygame.display.update()


if __name__ == "__main__":
    run_game()
