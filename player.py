import pygame
from utils import resource_path, calculate_foot_ratio, circle_rect_overlap


# --------------------------------------------------
# Skins
# --------------------------------------------------

SKINS = {
    "default": {"scale": 3, "radius": 36},
    "otto": {"scale": 2.5, "radius": 30},
}

AVAILABLE_SKINS = ["default", "otto"]
SELECTED_SKIN = "default"


def set_selected_skin(name):
    global SELECTED_SKIN
    SELECTED_SKIN = name


# --------------------------------------------------
# Penguin
# --------------------------------------------------

class Penguin:
    def __init__(self, screen):
        self.screen = screen

        self.x = self.screen.width // 2
        self.y = self.screen.height // 2

        self.vx = 0.0
        self.vy = 0.0
        self.speed = 0.5
        self.friction = 0.9

        skin_cfg = SKINS.get(SELECTED_SKIN, SKINS["default"])
        scale = skin_cfg["scale"]
        skin_path = f"animations/{SELECTED_SKIN}/"

        # load sheets
        sheets = {
            "down":       pygame.image.load(resource_path(skin_path + "walk_down.png")).convert_alpha(),
            "down_left":  pygame.image.load(resource_path(skin_path + "walk_downL.png")).convert_alpha(),
            "down_right": pygame.image.load(resource_path(skin_path + "walk_downR.png")).convert_alpha(),
            "left":       pygame.image.load(resource_path(skin_path + "walk_left.png")).convert_alpha(),
            "right":      pygame.image.load(resource_path(skin_path + "walk_right.png")).convert_alpha(),
            "up":         pygame.image.load(resource_path(skin_path + "walk_up.png")).convert_alpha(),
            "up_left":    pygame.image.load(resource_path(skin_path + "walk_upL.png")).convert_alpha(),
            "up_right":   pygame.image.load(resource_path(skin_path + "walk_upR.png")).convert_alpha(),
        }

        frame_w, frame_h = 32, 32

        # frames + cached data
        self.frames = {k: [] for k in sheets}
        self.foot_ratios = {k: [] for k in sheets}
        self.shadow_x_offsets = {k: [] for k in sheets}

        # ----------------------------------------------
        # Helper: shadow X offset (DEFAULT SKIN ONLY)
        # ----------------------------------------------
        def calc_shadow_x_offset(frame: pygame.Surface) -> float:
            if SELECTED_SKIN != "default":
                return 0.0

            mask = pygame.mask.from_surface(frame)
            rects = mask.get_bounding_rects()
            if not rects:
                return 0.0

            bbox = rects[0].copy()
            for r in rects[1:]:
                bbox.union_ip(r)

            return bbox.centerx - (frame.get_width() / 2.0)

        # load frames
        for key, sheet in sheets.items():
            for i in range(3):
                frame = sheet.subsurface((i * frame_w, 0, frame_w, frame_h))
                frame = pygame.transform.scale(
                    frame,
                    (int(frame_w * scale), int(frame_h * scale))
                )

                self.frames[key].append(frame)
                self.foot_ratios[key].append(calculate_foot_ratio(frame))
                self.shadow_x_offsets[key].append(calc_shadow_x_offset(frame))

        # initial state
        self.direction = "down"
        self.current_frame = 0
        self.frame_timer = 0
        self.frame_delay = 150

        self.image = self.frames["down"][0]
        self.foot_ratio = self.foot_ratios["down"][0]
        self.shadow_x_offset = self.shadow_x_offsets["down"][0]

        fallback_radius = int(min(self.image.get_width(), self.image.get_height()) * 0.35)
        self.radius = int(skin_cfg.get("radius", fallback_radius))

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def get_rect(self):
        return self.image.get_rect(center=(int(self.x), int(self.y)))

    def get_feet_pos(self):
        _, h = self.image.get_size()
        top_y = self.y - (h / 2)
        feet_y = top_y + (self.foot_ratio * h)
        return self.x, feet_y

    def get_feet_hit_radius(self):
        return max(5, int(self.radius * 0.45))

    def _set_anim_frame(self, direction, frame_index):
        self.direction = direction
        self.current_frame = frame_index
        self.image = self.frames[direction][frame_index]
        self.foot_ratio = self.foot_ratios[direction][frame_index]
        self.shadow_x_offset = self.shadow_x_offsets[direction][frame_index]

    # --------------------------------------------------
    # Draw
    # --------------------------------------------------

    def draw(self):
        surf = self.screen.screen

        # shadow (perfectly grounded + centered)
        _, fy = self.get_feet_pos()
        fx = self.x + self.shadow_x_offset

        shadow_w = int(self.radius * 1.5)
        shadow_h = int(self.radius * 0.75)

        shadow = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 90), shadow.get_rect())

        surf.blit(
            shadow,
            (int(fx - shadow_w / 2), int(fy - shadow_h // 2))
        )

        surf.blit(self.image, self.get_rect())

    # --------------------------------------------------
    # Update
    # --------------------------------------------------

    def update(self, keys, dt_ms, snow_patches):
        dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        moving = dx != 0 or dy != 0

        if moving:
            if dy < 0 and dx < 0:
                direction = "up_left"
            elif dy < 0 and dx > 0:
                direction = "up_right"
            elif dy > 0 and dx < 0:
                direction = "down_left"
            elif dy > 0 and dx > 0:
                direction = "down_right"
            elif dy < 0:
                direction = "up"
            elif dy > 0:
                direction = "down"
            elif dx < 0:
                direction = "left"
            else:
                direction = "right"
        else:
            direction = self.direction

        if moving:
            if direction != self.direction:
                self.frame_timer = 0
                self.current_frame = 0

            self.frame_timer += dt_ms
            if self.frame_timer >= self.frame_delay:
                self.frame_timer = 0
                self.current_frame = (self.current_frame + 1) % len(self.frames[direction])

            self._set_anim_frame(direction, self.current_frame)
        else:
            self.frame_timer = 0
            self._set_anim_frame(direction, 0)

        # movement
        self.vx += dx * self.speed
        self.vy += dy * self.speed

        fx, fy = self.get_feet_pos()
        fr = self.get_feet_hit_radius()
        on_snow = any(circle_rect_overlap(fx, fy, fr, p.rect) for p in snow_patches)
        self.friction = 0.70 if on_snow else 0.90

        self.vx *= self.friction
        self.vy *= self.friction

        self.x += self.vx
        self.y += self.vy

        self.x = max(self.radius, min(self.screen.width - self.radius, self.x))
        self.y = max(self.radius, min(self.screen.height - self.radius, self.y))
