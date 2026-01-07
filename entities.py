import pygame
import random
import math
from utils import resource_path


class FishPowerUp:
    def __init__(self, screen):
        self.screen = screen
        self.sprite_sheet = pygame.image.load(resource_path("powerups/fishy.png")).convert_alpha()
        self.frames = []
        self.current_frame = 0
        self.animation_timer = 0
        self.animation_speed = 100

        sheet_width, sheet_height = self.sprite_sheet.get_size()
        fw = sheet_width // 3
        fh = sheet_height // 3
        scale_factor = 1.5

        for row in range(3):
            for col in range(3):
                x = col * fw
                y = row * fh
                frame = self.sprite_sheet.subsurface(pygame.Rect(x, y, fw, fh))
                frame = pygame.transform.scale(frame, (int(fw * scale_factor), int(fh * scale_factor)))
                self.frames.append(frame)

        self.radius = int(min(self.frames[0].get_width(), self.frames[0].get_height()) * 0.33)
        self.x = random.randint(self.radius, self.screen.width - self.radius)
        self.y = random.randint(self.radius, self.screen.height - self.radius)

    def update(self, dt):
        self.animation_timer += dt
        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0
            self.current_frame = (self.current_frame + 1) % len(self.frames)

    def draw(self):
        frame = self.frames[self.current_frame]
        surf = self.screen.screen

        shadow_w = int(frame.get_width() * 0.55)
        shadow_h = 6
        shadow_surface = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surface, (0, 0, 0, 80), shadow_surface.get_rect())
        surf.blit(shadow_surface, (int(self.x - shadow_w / 2), int(self.y + frame.get_height() * 0.18)))

        surf.blit(frame, frame.get_rect(center=(int(self.x), int(self.y))))

    def collides_with(self, penguin):
        dx = self.x - penguin.x
        dy = self.y - penguin.y
        return math.hypot(dx, dy) < (self.radius + penguin.radius)


class Pebble:
    def __init__(self, screen):
        self.screen = screen
        self.sprite_sheet = pygame.image.load(resource_path("powerups/pebble.png")).convert_alpha()
        self.frames = []
        self.current_frame = 0
        self.animation_timer = 0
        self.animation_speed = 100

        sheet_width, sheet_height = self.sprite_sheet.get_size()
        fw = sheet_width // 3
        fh = sheet_height // 3
        scale_factor = 2.5

        for row in range(3):
            for col in range(3):
                x = col * fw
                y = row * fh
                frame = self.sprite_sheet.subsurface(pygame.Rect(x, y, fw, fh))
                frame = pygame.transform.scale(frame, (int(fw * scale_factor), int(fh * scale_factor)))
                self.frames.append(frame)

        self.radius = int(min(self.frames[0].get_width(), self.frames[0].get_height()) * 0.25)
        self.x = random.randint(self.radius, self.screen.width - self.radius)
        self.y = random.randint(self.radius, self.screen.height - self.radius)

    def update(self, dt):
        self.animation_timer += dt
        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0
            self.current_frame = (self.current_frame + 1) % len(self.frames)

    def draw(self):
        frame = self.frames[self.current_frame]
        surf = self.screen.screen

        shadow_w = int(frame.get_width() * 0.45)
        shadow_h = 6
        shadow_surface = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surface, (0, 0, 0, 80), shadow_surface.get_rect())
        surf.blit(shadow_surface, (int(self.x - shadow_w / 2), int(self.y + frame.get_height() * 0.20)))

        surf.blit(frame, frame.get_rect(center=(int(self.x), int(self.y))))

    def collides_with(self, penguin):
        dx = self.x - penguin.x
        dy = self.y - penguin.y
        return math.hypot(dx, dy) < (self.radius + penguin.radius)


class MultiplierPowerUp:
    def __init__(self, x, y, mult_frames):
        self.x = x
        self.y = y
        self.radius = 16
        self.active = False
        self.duration = 30
        self.timer = 0
        self.frame = 0
        self.frame_timer = 0
        self.mult_frames = mult_frames

    def update(self, dt_seconds):
        self.frame_timer += dt_seconds
        if self.frame_timer > 0.10:
            self.frame = (self.frame + 1) % len(self.mult_frames)
            self.frame_timer = 0.0

        if self.active:
            self.timer -= dt_seconds
            if self.timer <= 0:
                self.active = False

    def draw(self, screen):
        frame_img = self.mult_frames[self.frame]
        surf = screen.screen

        shadow_w = int(frame_img.get_width() * 0.8)
        shadow_h = 6
        shadow_surface = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surface, (0, 0, 0, 80), shadow_surface.get_rect())
        surf.blit(shadow_surface, (int(self.x - shadow_w / 2), int(self.y + frame_img.get_height() * 0.20)))

        surf.blit(frame_img, frame_img.get_rect(center=(int(self.x), int(self.y))))

    def collides_with(self, penguin):
        dx = self.x - penguin.x
        dy = self.y - penguin.y
        return math.hypot(dx, dy) < (self.radius + penguin.radius)


class PatchSnowflake:
    def __init__(self, patch):
        self.patch = patch
        self.reset()

    def reset(self):
        self.x = random.randint(self.patch.rect.left, self.patch.rect.right)
        self.y = random.randint(self.patch.rect.top - 20, self.patch.rect.top)
        self.speed = random.uniform(0.3, 1.0)
        self.size = random.randint(1, 3)

    def update(self):
        self.y += self.speed
        if self.y > self.patch.rect.bottom:
            self.reset()

    def draw(self, surface):
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), self.size)


class SnowPatch:
    def __init__(self, screen, world_rect):
        self.screen = screen

        # -------------------------
        # WORLD-SPACE RECT (PERMANENT)
        # -------------------------
        self.world_rect = world_rect.copy()

        # This will be updated every frame by the game loop
        self._screen_rect = pygame.Rect(
            world_rect.x,
            world_rect.y,
            world_rect.w,
            world_rect.h
        )

        self.spawn_time = pygame.time.get_ticks()
        self.lifetime = 45000

        # -------------------------
        # CREATE SHAPED SURFACES ONCE
        # -------------------------
        self.surface = pygame.Surface(self.world_rect.size, pygame.SRCALPHA)
        self.mask_surface = pygame.Surface(self.world_rect.size, pygame.SRCALPHA)

        points = []
        cx, cy = self.world_rect.width // 2, self.world_rect.height // 2
        rx, ry = self.world_rect.width // 2, self.world_rect.height // 2

        for i in range(14):
            ang = i * (2 * math.pi / 14)
            jitter = random.uniform(0.75, 1.1)
            x = cx + math.cos(ang) * rx * jitter
            y = cy + math.sin(ang) * ry * jitter
            points.append((x, y))

        # Actual snow patch
        pygame.draw.polygon(self.surface, (235, 235, 255, 160), points)

        # Dark preview mask (same shape)
        pygame.draw.polygon(self.mask_surface, (0, 0, 0, 45), points)

    # -------------------------
    # SCREEN-SPACE RECT (for PatchSnowflake compatibility)
    # -------------------------
    @property
    def rect(self):
        return self._screen_rect

    # -------------------------
    # LIFETIME
    # -------------------------
    def expired(self):
        return pygame.time.get_ticks() - self.spawn_time > self.lifetime

    # -------------------------
    # WORLD DRAW
    # -------------------------
    def draw(self, target, camera_x=0, camera_y=0):
        self._screen_rect.topleft = (
            int(self.world_rect.x - camera_x),
            int(self.world_rect.y - camera_y),
        )
        target.blit(self.surface, self._screen_rect.topleft)

    # -------------------------
    # PREVIEW DRAW (SCREEN-SPACE ONLY)
    # -------------------------
    def draw_preview(self, target, screen_rect):
        target.blit(self.mask_surface, screen_rect.topleft)


class Snowball:
    def __init__(self, screen, score):
        self.screen = screen
        self.radius = random.randint(6, 10)
        self.original_image = pygame.image.load(resource_path("snowball/snowball.png")).convert_alpha()
        scale_factor = (self.radius * 2) / self.original_image.get_width()
        self.image = pygame.transform.smoothscale(
            self.original_image,
            (int(self.original_image.get_width() * scale_factor),
             int(self.original_image.get_height() * scale_factor))
        )
        self.rotation_angle = 0

        side = random.randint(0, 3)
        w, h = screen.width, screen.height

        if side == 0:
            self.x = random.randint(0, w)
            self.y = -self.radius
        elif side == 1:
            self.x = w + self.radius
            self.y = random.randint(0, h)
        elif side == 2:
            self.x = random.randint(0, w)
            self.y = h + self.radius
        else:
            self.x = -self.radius
            self.y = random.randint(0, h)

        target_x = random.randint(w // 3, w * 2 // 3)
        target_y = random.randint(h // 3, h * 2 // 3)

        dx = target_x - self.x
        dy = target_y - self.y
        angle = math.atan2(dy, dx)
        speed = min(2 + score * 0.1, 6)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.rotation_angle = (self.rotation_angle + 5) % 360

    def draw(self):
        surf = self.screen.screen

        shadow_color = (0, 0, 0, 100)
        shadow_offset_y = 22
        shadow_scale = 0.5

        shadow_w = self.image.get_width()
        shadow_h = int(self.image.get_height() * shadow_scale)
        shadow_surface = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surface, shadow_color, shadow_surface.get_rect())

        surf.blit(shadow_surface, shadow_surface.get_rect(center=(int(self.x), int(self.y + shadow_offset_y))))

        rotated = pygame.transform.rotate(self.image, self.rotation_angle)
        rect = rotated.get_rect(center=(int(self.x), int(self.y)))
        surf.blit(rotated, rect)

    def is_off_screen(self):
        return (
            self.x < -self.radius or self.x > self.screen.width + self.radius or
            self.y < -self.radius or self.y > self.screen.height + self.radius
        )

    def collides_with(self, penguin):
        dx = self.x - penguin.x
        dy = self.y - penguin.y
        return math.hypot(dx, dy) < (self.radius + penguin.radius)

class ShovelPowerUp:
    def __init__(self, screen):
        self.screen = screen

        sheet = pygame.image.load(
            resource_path("powerups/shovel.png")
        ).convert_alpha()

        self.frames = []
        fw, fh = 32, 32
        scale = 2

        for row in range(3):
            for col in range(3):
                frame = sheet.subsurface((col * fw, row * fh, fw, fh))
                frame = pygame.transform.scale(frame, (fw * scale, fh * scale))
                self.frames.append(frame)

        self.frame = 0
        self.anim_timer = 0
        self.anim_delay = 120  # ms

        self.radius = int(self.frames[0].get_width() * 0.35)

        self.x = random.randint(self.radius, screen.width - self.radius)
        self.y = random.randint(self.radius, screen.height - self.radius)

    def update(self, dt):
        self.anim_timer += dt
        if self.anim_timer >= self.anim_delay:
            self.anim_timer = 0
            self.frame = (self.frame + 1) % len(self.frames)

    def draw(self):
        img = self.frames[self.frame]
        self.screen.screen.blit(
            img, img.get_rect(center=(int(self.x), int(self.y)))
        )

    def collides_with(self, penguin):
        dx = self.x - penguin.x
        dy = self.y - penguin.y
        return dx * dx + dy * dy < (self.radius + penguin.radius) ** 2
