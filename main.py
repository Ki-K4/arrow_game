"""
一箭又一箭 —— 点击式箭头解谜小游戏。

窗口 760×700，界面由圆角卡片、渐变按钮和矢量绘制的箭头组成，
所有元件都用代码画出来，不需要额外的图片素材。
"""

import os
import sys
import math
import random
import struct
import pygame


# 截图保存目录（按 F12 时使用）
SCREENSHOT_DIR = "screenshots"


# =========================
# 可调参数：想改手感就调这里
# =========================

WINDOW_TITLE = "一箭又一箭"

# 圆角与间距
CARD_RADIUS = 16          # 卡片圆角
TILE_GAP = 6              # 棋盘格子之间的缝隙
ARROW_SCALE = 0.66        # 箭头大小占格子的比例

# 碰撞反馈
PARTICLE_COUNT = 22       # 每次碰撞生成的粒子数量
PARTICLE_GRAVITY = 0.09   # 粒子向下的加速度
PARTICLE_LIFE = (20, 34)  # 粒子寿命范围（帧）
SHAKE_AMPLITUDE = 5       # 箭头左右晃动的幅度（像素）

# 音效波形：triangle 柔和，sine 更纯净，square 更复古但偏刺耳
TONE_WAVE = "triangle"
TONE_DECAY = 2.2          # 每个音的衰减速度，越大越短促

# 通关旋律：C5 → E5 → G5 → C6
WIN_NOTES = [
    (523, 523, 0.10),
    (659, 659, 0.10),
    (784, 784, 0.10),
    (1047, 1047, 0.30),
]

# 失败旋律：G4 → D4 → A3，最后一段拖长下滑
FAIL_NOTES = [
    (392, 392, 0.15),
    (294, 294, 0.15),
    (220, 147, 0.50),
]


# =========================
# 基本配置
# =========================

SCREEN_WIDTH = 760
SCREEN_HEIGHT = 700

pygame.mixer.pre_init(
    frequency=44100,
    size=-16,
    channels=1,
    buffer=512
)

pygame.init()

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption(WINDOW_TITLE)

clock = pygame.time.Clock()


# 配色：深色底 + 蓝紫卡片 + 高饱和强调色
BG_TOP = (16, 20, 32)
BG_BOTTOM = (28, 34, 54)

CARD_COLOR = (30, 37, 56)
CARD_BORDER = (48, 58, 88)

TILE_A = (38, 46, 68)
TILE_B = (43, 52, 76)
TILE_EDGE = (52, 62, 92)

TEXT_COLOR = (236, 240, 250)
TEXT_DIM = (140, 150, 178)

BLUE = (74, 132, 244)
GREEN = (46, 196, 128)
RED = (240, 84, 100)
YELLOW = (250, 196, 74)
GRAY = (92, 100, 126)

ARROW_COLOR = (92, 158, 255)
ARROW_COLLISION_COLOR = (255, 96, 112)
ARROW_FLY_COLOR = (58, 214, 148)


# 棋盘配置
ROWS = 6
COLS = 6
CELL_SIZE = 72

BOARD_X = (SCREEN_WIDTH - COLS * CELL_SIZE) // 2
BOARD_Y = 116

# 顶部状态卡片、提示文字和页脚的位置
STATUS_RECT = pygame.Rect(48, 30, SCREEN_WIDTH - 96, 64)
HINT_Y = 582
FOOTER_Y = 676

MAX_MISTAKES = 3


# 游戏状态
START = "start"
PLAYING = "playing"
RESULT = "result"

game_state = START
current_level_index = 0
lives = MAX_MISTAKES

# 当前关卡中的箭头
arrows = {}

# 飞行动画
flying_arrow = None
flying_start_time = 0
FLY_DURATION = 380

# 碰撞反馈
collision_position = None
collision_start_time = 0
COLLISION_DURATION = 480

# 碰撞粒子
particles = []

# 本局结果
result_is_win = False


# 界面上的按钮（绘制和点击检测共用同一组矩形，避免两边对不上）
START_BUTTON = pygame.Rect(280, 540, 200, 56)
RESTART_BUTTON = pygame.Rect(300, 606, 160, 44)
NEXT_BUTTON = pygame.Rect(280, 390, 200, 54)
FINAL_RESTART_BUTTON = pygame.Rect(280, 406, 200, 54)
BACK_BUTTON = pygame.Rect(280, 470, 200, 48)


# =========================
# 关卡数据
# =========================

LEVELS = [
    {
        # 第 1 关：12 个箭头，一开始有 4 个可以点
        (0, 3): "U",
        (1, 0): "L",
        (2, 0): "D",
        (2, 2): "R",
        (2, 4): "D",
        (3, 3): "R",
        (4, 0): "D",
        (4, 1): "R",
        (4, 4): "R",
        (4, 5): "R",
        (5, 0): "R",
        (5, 2): "U",
    },
    {
        # 第 2 关：16 个箭头，一开始只有 3 个可以点
        (0, 1): "D",
        (0, 2): "R",
        (0, 4): "U",
        (1, 2): "U",
        (2, 0): "U",
        (2, 3): "L",
        (2, 4): "U",
        (3, 0): "D",
        (3, 1): "L",
        (3, 2): "U",
        (4, 0): "R",
        (4, 4): "U",
        (4, 5): "D",
        (5, 0): "R",
        (5, 2): "U",
        (5, 4): "U",
    },
    {
        # 第 3 关：20 个箭头，一开始只有 2 个可以点，阻挡链最长
        (0, 1): "R",
        (0, 2): "D",
        (1, 1): "R",
        (1, 3): "R",
        (1, 4): "R",
        (2, 1): "U",
        (2, 4): "L",
        (2, 5): "L",
        (3, 0): "R",
        (3, 3): "D",
        (4, 0): "U",
        (4, 1): "D",
        (4, 3): "R",
        (4, 4): "D",
        (4, 5): "U",
        (5, 1): "L",
        (5, 2): "L",
        (5, 3): "L",
        (5, 4): "R",
        (5, 5): "U",
    },
]


# =========================
# 字体
# =========================

def get_font(size, bold=False):
    """
    尝试使用常见中文字体，找不到就退回默认字体。
    """
    font_names = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "WenQuanYi Zen Hei",
        "Arial",
    ]

    for name in font_names:
        font = pygame.font.SysFont(name, size, bold=bold)
        if font is not None:
            return font

    return pygame.font.Font(None, size)


TITLE_FONT = get_font(52, True)
LARGE_FONT = get_font(34, True)
NORMAL_FONT = get_font(20, True)
SMALL_FONT = get_font(17)
TINY_FONT = get_font(14)


# =========================
# 音效生成
# =========================

def tone_data(start_frequency, duration, volume=0.4, end_frequency=None):
    """
    生成一段单音的原始采样数据。

    波形由 TONE_WAVE 决定：三角波最柔和，正弦波更纯净，方波最复古但也最刺耳。
    每个音都带淡入淡出和指数衰减，避免突然的开始与结束造成爆音。
    """
    sample_rate = 44100
    sample_count = int(sample_rate * duration)

    if end_frequency is None:
        end_frequency = start_frequency

    audio_data = bytearray()
    phase = 0.0

    for i in range(sample_count):
        progress = i / sample_count

        frequency = (
            start_frequency
            + (end_frequency - start_frequency) * progress
        )

        if TONE_WAVE == "square":
            value = 1.0 if phase < 0.5 else -1.0
        elif TONE_WAVE == "triangle":
            value = 4.0 * abs(phase - 0.5) - 1.0
        else:
            value = math.sin(2 * math.pi * phase)

        fade_in = min(i / 700, 1.0)
        fade_out = min((sample_count - i) / 2000, 1.0)
        decay = math.exp(-TONE_DECAY * progress)
        envelope = min(fade_in, fade_out) * decay

        sample = int(32767 * volume * value * envelope)

        audio_data.extend(struct.pack("<h", sample))

        phase += frequency / sample_rate
        phase -= int(phase)

    return bytes(audio_data)


def make_tone(start_frequency, duration, volume=0.4, end_frequency=None):
    """
    生成一段单音音效。
    """
    return pygame.mixer.Sound(
        buffer=tone_data(start_frequency, duration, volume, end_frequency)
    )


def make_melody(notes, volume=0.4):
    """
    把若干段音依次拼接成一小段旋律，用于通关和失败音效。

    notes 中每一项都是 (起始频率, 结束频率, 时长)。
    """
    audio_data = bytearray()

    for start_frequency, end_frequency, duration in notes:
        audio_data.extend(
            tone_data(start_frequency, duration, volume, end_frequency)
        )

    return pygame.mixer.Sound(buffer=bytes(audio_data))


try:
    collision_sound = make_tone(200, 0.16, 0.30, 90)
    fly_sound = make_tone(330, 0.18, 0.22, 660)
    win_sound = make_melody(WIN_NOTES, volume=0.30)
    fail_sound = make_melody(FAIL_NOTES, volume=0.32)
except pygame.error:
    collision_sound = None
    fly_sound = None
    win_sound = None
    fail_sound = None


def play_sound(sound):
    """
    播放音效。音频设备不可用时直接忽略，不影响游戏运行。
    """
    if sound is None:
        return

    try:
        sound.play()
    except pygame.error:
        pass


# =========================
# 绘制工具
# =========================

def mix(color_a, color_b, ratio):
    """
    按比例混合两种颜色，ratio 为 0 时取 color_a，为 1 时取 color_b。
    """
    return tuple(
        int(a + (b - a) * ratio)
        for a, b in zip(color_a, color_b)
    )


def shade(color, factor):
    """
    调亮或调暗一个颜色，factor 大于 1 变亮，小于 1 变暗。
    """
    return tuple(
        max(0, min(255, int(value * factor)))
        for value in color
    )


def draw_text(text, font, color, x, y, center=True, right=False):
    """
    绘制文字。

    center 为 True 时以 (x, y) 为中心；否则 y 始终是文字的垂直中心，
    right 为 True 时 x 作为右边界，否则 x 作为左边界。
    """
    surface = font.render(text, True, color)

    if right:
        rect = surface.get_rect(midright=(x, y))
    elif center:
        rect = surface.get_rect(center=(x, y))
    else:
        rect = surface.get_rect(midleft=(x, y))

    screen.blit(surface, rect)
    return rect


def build_background():
    """
    预先生成上下渐变的背景，每帧只需要贴一次。
    """
    surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    for y in range(SCREEN_HEIGHT):
        color = mix(BG_TOP, BG_BOTTOM, y / SCREEN_HEIGHT)
        pygame.draw.line(surface, color, (0, y), (SCREEN_WIDTH, y))

    # 右上角的柔光
    glow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

    for radius in range(280, 0, -8):
        alpha = int(14 * (1 - radius / 280))
        pygame.draw.circle(
            glow,
            (90, 130, 255, alpha),
            (SCREEN_WIDTH - 60, 40),
            radius
        )

    surface.blit(glow, (0, 0))
    return surface


BACKGROUND = build_background()


def draw_background():
    """
    贴上预先画好的渐变背景。
    """
    screen.blit(BACKGROUND, (0, 0))


def draw_card(rect, fill=CARD_COLOR, border=CARD_BORDER, radius=CARD_RADIUS,
              shadow=True):
    """
    绘制圆角卡片，带一圈描边和一层柔和阴影。
    """
    if shadow:
        shadow_layer = pygame.Surface(
            (rect.width + 24, rect.height + 24),
            pygame.SRCALPHA
        )

        for offset, alpha in ((10, 26), (6, 34), (3, 46)):
            pygame.draw.rect(
                shadow_layer,
                (0, 0, 0, alpha),
                (
                    12 - offset // 2,
                    12 + offset,
                    rect.width + offset,
                    rect.height + offset
                ),
                border_radius=radius + 2
            )

        screen.blit(shadow_layer, (rect.left - 12, rect.top - 12))

    pygame.draw.rect(screen, fill, rect, border_radius=radius)
    pygame.draw.rect(screen, border, rect, width=1, border_radius=radius)


def draw_gradient_rect(rect, top_color, bottom_color, radius=12):
    """
    绘制竖直渐变的圆角矩形，用作按钮底色。
    """
    surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

    for y in range(rect.height):
        color = mix(top_color, bottom_color, y / max(rect.height - 1, 1))
        pygame.draw.line(surface, color, (0, y), (rect.width, y))

    mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(
        mask, (255, 255, 255, 255),
        (0, 0, rect.width, rect.height),
        border_radius=radius
    )
    surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    screen.blit(surface, rect.topleft)


def mouse_position():
    """
    鼠标当前位置。
    """
    return pygame.mouse.get_pos()


def draw_button(text, rect, color=BLUE, font=None, icon=False):
    """
    绘制圆角渐变按钮：鼠标悬停时整体变亮，左侧可以带一个播放三角。
    """
    if font is None:
        font = NORMAL_FONT

    hovered = rect.collidepoint(mouse_position())
    base = shade(color, 1.14) if hovered else color

    draw_gradient_rect(
        rect,
        shade(base, 1.16),
        shade(base, 0.86),
        radius=rect.height // 3
    )
    pygame.draw.rect(
        screen,
        shade(base, 1.3),
        rect,
        width=1,
        border_radius=rect.height // 3
    )

    text_color = (14, 18, 30) if sum(base) > 520 else TEXT_COLOR

    if not icon:
        draw_text(text, font, text_color, rect.centerx, rect.centery)
        return

    # 图标 + 文字作为整体居中
    text_width, _ = font.size(text)
    icon_width = 16
    gap = 12
    left = rect.centerx - (icon_width + gap + text_width) // 2

    size = 11
    pygame.draw.polygon(
        screen,
        text_color,
        [
            (left, rect.centery - size),
            (left + icon_width, rect.centery),
            (left, rect.centery + size),
        ]
    )
    draw_text(
        text,
        font,
        text_color,
        left + icon_width + gap + text_width // 2,
        rect.centery
    )


def cell_rect(row, col):
    """
    返回棋盘上某个格子对应的矩形。
    """
    return pygame.Rect(
        BOARD_X + col * CELL_SIZE,
        BOARD_Y + row * CELL_SIZE,
        CELL_SIZE,
        CELL_SIZE
    )


def direction_vector(direction):
    """
    将方向转换为二维坐标变化。
    """
    if direction == "U":
        return -1, 0
    if direction == "D":
        return 1, 0
    if direction == "L":
        return 0, -1
    if direction == "R":
        return 0, 1

    return 0, 0


# =========================
# 箭头绘制
# =========================

def arrow_shape(center_x, center_y, direction, size):
    """
    计算箭头的外形：一个三角形箭头加一根短杆，返回两组多边形顶点。
    """
    row_change, col_change = direction_vector(direction)
    # 屏幕坐标：x 向右、y 向下
    vx, vy = col_change, row_change
    px, py = -vy, vx

    tip = (center_x + vx * size * 0.5, center_y + vy * size * 0.5)
    base = (tip[0] - vx * size * 0.56, tip[1] - vy * size * 0.56)

    head = [
        tip,
        (base[0] + px * size * 0.40, base[1] + py * size * 0.40),
        (base[0] - px * size * 0.40, base[1] - py * size * 0.40),
    ]

    tail = (base[0] - vx * size * 0.42, base[1] - vy * size * 0.42)
    half = size * 0.13

    shaft = [
        (base[0] + px * half, base[1] + py * half),
        (base[0] - px * half, base[1] - py * half),
        (tail[0] - px * half, tail[1] - py * half),
        (tail[0] + px * half, tail[1] + py * half),
    ]

    return head, shaft


def draw_arrow(position, direction, color=ARROW_COLOR,
               offset_x=0, offset_y=0, glow=False):
    """
    在某个格子里画出箭头：先画深色投影，再画主体，可选一层柔光。
    """
    row, col = position
    rect = cell_rect(row, col)

    center_x = rect.centerx + offset_x
    center_y = rect.centery + offset_y
    size = CELL_SIZE * ARROW_SCALE

    head, shaft = arrow_shape(center_x, center_y, direction, size)

    # 投影
    shadow_head = [
        (x, y + 4) for x, y in head
    ]
    shadow_shaft = [
        (x, y + 4) for x, y in shaft
    ]
    pygame.draw.polygon(screen, (12, 16, 26), shadow_shaft)
    pygame.draw.polygon(screen, (12, 16, 26), shadow_head)

    if glow:
        halo = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(halo, (*color, 60), head)
        pygame.draw.polygon(halo, (*color, 60), shaft)
        screen.blit(halo, (0, 0))

    pygame.draw.polygon(screen, color, shaft)
    pygame.draw.polygon(screen, color, head)

    # 箭头尖端的一点高光，让形状更立体
    highlight = mix(color, (255, 255, 255), 0.35)

    pygame.draw.polygon(
        screen,
        highlight,
        [
            head[0],
            (
                head[0][0] * 0.72 + head[1][0] * 0.28,
                head[0][1] * 0.72 + head[1][1] * 0.28
            ),
            (
                head[0][0] * 0.72 + head[2][0] * 0.28,
                head[0][1] * 0.72 + head[2][1] * 0.28
            ),
        ]
    )


def draw_arrow_at(center_x, center_y, direction, size, color=ARROW_COLOR):
    """
    在指定位置画一个箭头，用于开始界面的示意图。
    """
    head, shaft = arrow_shape(center_x, center_y, direction, size)
    pygame.draw.polygon(screen, color, shaft)
    pygame.draw.polygon(screen, color, head)


# =========================
# 游戏流程
# =========================

def reset_level(level_index=None):
    """
    重置当前关卡。
    """
    global arrows
    global current_level_index
    global lives
    global flying_arrow
    global flying_start_time
    global collision_position
    global collision_start_time
    global particles

    if level_index is not None:
        current_level_index = level_index

    arrows = dict(LEVELS[current_level_index])
    lives = MAX_MISTAKES

    flying_arrow = None
    flying_start_time = 0

    collision_position = None
    collision_start_time = 0

    particles = []


def start_game():
    """
    开始游戏。
    """
    global game_state
    global current_level_index

    current_level_index = 0
    reset_level()
    game_state = PLAYING


def restart_current_level():
    """
    重新开始当前关卡。
    """
    global game_state

    reset_level()
    game_state = PLAYING


def go_to_next_level():
    """
    进入下一关。
    """
    global current_level_index
    global game_state

    if current_level_index + 1 < len(LEVELS):
        current_level_index += 1
        reset_level()
        game_state = PLAYING
    else:
        # 所有关卡完成后回到开始界面
        game_state = START


# =========================
# 核心算法：路径检测
# =========================

def is_blocked(position):
    """
    判断某个箭头沿其方向前进时，前方是否有其他箭头。
    """
    row, col = position
    direction = arrows[position]

    row_change, col_change = direction_vector(direction)

    next_row = row + row_change
    next_col = col + col_change

    while 0 <= next_row < ROWS and 0 <= next_col < COLS:
        if (next_row, next_col) in arrows:
            return True

        next_row += row_change
        next_col += col_change

    return False


# =========================
# 碰撞粒子
# =========================

def create_collision_effect(position):
    """
    在发生碰撞的格子里生成一批粒子。
    """
    global particles

    row, col = position
    rect = cell_rect(row, col)

    for _ in range(PARTICLE_COUNT):
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(1.6, 4.6)

        particles.append({
            "x": rect.centerx,
            "y": rect.centery,
            "vx": math.cos(angle) * speed,
            "vy": math.sin(angle) * speed,
            "life": random.randint(*PARTICLE_LIFE),
            "max_life": PARTICLE_LIFE[1],
            "size": random.uniform(2.5, 5.5),
            "color": random.choice([
                (255, 108, 108),
                (255, 176, 88),
                (255, 226, 120)
            ])
        })


def update_particles():
    """
    更新粒子的位置和剩余寿命。
    """
    global particles

    alive_particles = []

    for particle in particles:
        particle["x"] += particle["vx"]
        particle["y"] += particle["vy"]

        particle["vy"] += PARTICLE_GRAVITY
        particle["life"] -= 1

        if particle["life"] > 0:
            alive_particles.append(particle)

    particles = alive_particles


PARTICLE_LAYER = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)


def draw_particles():
    """
    在透明图层上绘制粒子，颜色和大小都随寿命衰减，最后整层贴到屏幕上。
    """
    PARTICLE_LAYER.fill((0, 0, 0, 0))

    for particle in particles:
        ratio = particle["life"] / particle["max_life"]
        radius = max(1, int(particle["size"] * ratio))
        color = (*particle["color"], int(220 * ratio))

        pygame.draw.circle(
            PARTICLE_LAYER,
            color,
            (int(particle["x"]), int(particle["y"])),
            radius
        )

    screen.blit(PARTICLE_LAYER, (0, 0))


def draw_collision_ring():
    """
    在碰撞格子周围绘制向外扩散的圆环。
    """
    if collision_position is None:
        return

    elapsed = pygame.time.get_ticks() - collision_start_time

    if elapsed >= COLLISION_DURATION:
        return

    row, col = collision_position
    rect = cell_rect(row, col)

    progress = elapsed / COLLISION_DURATION

    PARTICLE_LAYER.fill((0, 0, 0, 0))

    for index, scale in enumerate((1.0, 0.72)):
        radius = int(CELL_SIZE * (0.24 + 0.5 * progress) * scale)
        alpha = int(150 * (1 - progress) / (index + 1))

        pygame.draw.circle(
            PARTICLE_LAYER,
            (255, 110, 120, alpha),
            (rect.centerx, rect.centery),
            radius,
            width=3
        )

    screen.blit(PARTICLE_LAYER, (0, 0))


# =========================
# 界面绘制
# =========================

def draw_status_bar():
    """
    顶部状态卡片：关卡进度和剩余失误次数。
    """
    draw_card(STATUS_RECT)

    draw_text(
        f"第 {current_level_index + 1} / {len(LEVELS)} 关",
        NORMAL_FONT,
        TEXT_COLOR,
        STATUS_RECT.left + 32,
        STATUS_RECT.centery,
        center=False
    )

    # 关卡进度：已完成的关卡点亮
    for index in range(len(LEVELS)):
        pill = pygame.Rect(
            STATUS_RECT.left + 190 + index * 22,
            STATUS_RECT.centery - 6,
            14,
            12
        )
        color = BLUE if index <= current_level_index else (56, 66, 96)
        pygame.draw.rect(screen, color, pill, border_radius=6)

    draw_text(
        "剩余失误",
        SMALL_FONT,
        TEXT_DIM,
        STATUS_RECT.right - 190,
        STATUS_RECT.centery,
        center=False
    )

    for index in range(MAX_MISTAKES):
        pill = pygame.Rect(
            STATUS_RECT.right - 96 + index * 28,
            STATUS_RECT.centery - 11,
            18,
            22
        )

        if index < lives:
            pygame.draw.rect(screen, GREEN, pill, border_radius=6)
            pygame.draw.rect(
                screen,
                shade(GREEN, 1.3),
                pill,
                width=1,
                border_radius=6
            )
        else:
            pygame.draw.rect(screen, (56, 64, 92), pill, border_radius=6)


def draw_board():
    """
    绘制棋盘背景、箭头、飞行动画和碰撞特效。
    """
    board_rect = pygame.Rect(
        BOARD_X - 14,
        BOARD_Y - 14,
        COLS * CELL_SIZE + 28,
        ROWS * CELL_SIZE + 28
    )
    draw_card(board_rect, fill=(26, 32, 50))

    tile_size = CELL_SIZE - TILE_GAP

    # 棋盘格子：深浅交替的圆角方块
    for row in range(ROWS):
        for col in range(COLS):
            rect = cell_rect(row, col)
            tile = pygame.Rect(
                rect.left + TILE_GAP // 2,
                rect.top + TILE_GAP // 2,
                tile_size,
                tile_size
            )
            fill = TILE_A if (row + col) % 2 == 0 else TILE_B

            pygame.draw.rect(screen, fill, tile, border_radius=10)
            pygame.draw.rect(
                screen, TILE_EDGE, tile, width=1, border_radius=10
            )

    # 绘制普通箭头
    for position, direction in arrows.items():
        color = ARROW_COLOR
        offset_x = 0

        if position == collision_position:
            elapsed = pygame.time.get_ticks() - collision_start_time

            if elapsed < COLLISION_DURATION:
                color = ARROW_COLLISION_COLOR
                offset_x = int(math.sin(elapsed * 0.045) * SHAKE_AMPLITUDE)

        draw_arrow(position, direction, color=color, offset_x=offset_x)

    # 绘制飞出棋盘的箭头
    if flying_arrow is not None:
        position, direction = flying_arrow

        elapsed = pygame.time.get_ticks() - flying_start_time
        progress = min(elapsed / FLY_DURATION, 1.0)

        row_change, col_change = direction_vector(direction)
        distance = CELL_SIZE * 2.4 * progress

        # 尾迹：越靠后的箭头越透明
        for trail in (0.5, 0.75):
            trail_distance = distance * trail
            trail_color = mix(ARROW_FLY_COLOR, (26, 32, 50), 0.55)
            draw_arrow(
                position,
                direction,
                color=trail_color,
                offset_x=col_change * trail_distance,
                offset_y=row_change * trail_distance
            )

        draw_arrow(
            position,
            direction,
            color=ARROW_FLY_COLOR,
            offset_x=col_change * distance,
            offset_y=row_change * distance,
            glow=True
        )

    draw_collision_ring()
    draw_particles()


def draw_start_screen():
    """
    绘制开始界面。
    """
    draw_background()

    draw_text(
        WINDOW_TITLE,
        TITLE_FONT,
        TEXT_COLOR,
        SCREEN_WIDTH // 2,
        140
    )

    draw_text(
        "点击箭头，让它们全部离开棋盘",
        SMALL_FONT,
        TEXT_DIM,
        SCREEN_WIDTH // 2,
        190
    )

    # 四个方向的箭头示意图
    arrows_demo = (("U", BLUE), ("R", GREEN), ("D", YELLOW), ("L", RED))

    for index, (direction, color) in enumerate(arrows_demo):
        draw_arrow_at(
            SCREEN_WIDTH // 2 - 114 + index * 76,
            286,
            direction,
            62,
            color
        )

    info_rect = pygame.Rect(140, 360, SCREEN_WIDTH - 280, 140)
    draw_card(info_rect)

    draw_text(
        "点击没有被挡住的箭头",
        NORMAL_FONT,
        TEXT_COLOR,
        SCREEN_WIDTH // 2,
        398
    )
    draw_text(
        "箭头会沿自己的方向飞出棋盘",
        SMALL_FONT,
        TEXT_DIM,
        SCREEN_WIDTH // 2,
        434
    )
    draw_text(
        f"点错会消耗一次失误，共 {MAX_MISTAKES} 次机会",
        SMALL_FONT,
        TEXT_DIM,
        SCREEN_WIDTH // 2,
        468
    )

    draw_button("开始游戏", START_BUTTON, GREEN, icon=True)

    draw_text(
        "鼠标点击操作　F12 截图　ESC 退出",
        TINY_FONT,
        TEXT_DIM,
        SCREEN_WIDTH // 2,
        FOOTER_Y
    )


def draw_playing_screen():
    """
    绘制游戏界面。
    """
    draw_background()
    draw_status_bar()
    draw_board()

    remaining = len(arrows) + (1 if flying_arrow else 0)

    collision_active = (
        collision_position is not None
        and pygame.time.get_ticks() - collision_start_time < COLLISION_DURATION
    )

    if collision_active:
        draw_text(
            "前方有阻挡",
            NORMAL_FONT,
            RED,
            SCREEN_WIDTH // 2,
            HINT_Y
        )
    else:
        draw_text(
            f"剩余箭头 {remaining}　点击没有被挡住的箭头",
            SMALL_FONT,
            TEXT_DIM,
            SCREEN_WIDTH // 2,
            HINT_Y
        )

    draw_button("重新开始", RESTART_BUTTON, BLUE, font=SMALL_FONT)


def star_points(center_x, center_y, outer, inner):
    """
    计算五角星的顶点，用于结果界面的评价图标。
    """
    points = []

    for index in range(10):
        radius = outer if index % 2 == 0 else inner
        angle = -math.pi / 2 + index * math.pi / 5
        points.append((
            center_x + radius * math.cos(angle),
            center_y + radius * math.sin(angle)
        ))

    return points


def draw_result_screen():
    """
    绘制通关或失败界面。
    """
    draw_background()

    if result_is_win:
        title, title_color = "本关通关！", GREEN
        description = "所有箭头都已经飞出棋盘"
    else:
        title, title_color = "挑战失败", RED
        description = "失误次数已经耗尽"

    draw_text(title, TITLE_FONT, title_color, SCREEN_WIDTH // 2, 150)
    draw_text(description, SMALL_FONT, TEXT_DIM, SCREEN_WIDTH // 2, 205)

    if result_is_win:
        # 剩余失误越多，点亮的星星越多
        earned = max(1, lives)

        for index in range(MAX_MISTAKES):
            center_x = SCREEN_WIDTH // 2 - 90 + index * 90
            color = YELLOW if index < earned else (58, 66, 96)

            pygame.draw.polygon(
                screen,
                color,
                star_points(center_x, 286, 34, 14)
            )

        draw_text(
            f"剩余失误 {max(lives, 0)} 次",
            TINY_FONT,
            TEXT_DIM,
            SCREEN_WIDTH // 2,
            338
        )

        if current_level_index + 1 < len(LEVELS):
            draw_button("进入下一关", NEXT_BUTTON, GREEN, icon=True)
        else:
            draw_text(
                "恭喜你完成全部关卡！",
                NORMAL_FONT,
                YELLOW,
                SCREEN_WIDTH // 2,
                380
            )
            draw_button("重新开始游戏", FINAL_RESTART_BUTTON, BLUE)
    else:
        # 失败时画一个叉
        center_x, center_y = SCREEN_WIDTH // 2, 286
        size = 34

        pygame.draw.line(
            screen, shade(RED, 0.9),
            (center_x - size, center_y - size),
            (center_x + size, center_y + size),
            14
        )
        pygame.draw.line(
            screen, shade(RED, 0.9),
            (center_x + size, center_y - size),
            (center_x - size, center_y + size),
            14
        )

        draw_button("重新开始本关", NEXT_BUTTON, BLUE)

    draw_button("返回开始界面", BACK_BUTTON, GRAY, font=SMALL_FONT)

    draw_text(
        f"第 {current_level_index + 1} / {len(LEVELS)} 关",
        TINY_FONT,
        TEXT_DIM,
        SCREEN_WIDTH // 2,
        640
    )


# =========================
# 鼠标点击处理
# =========================

def handle_arrow_click(mouse_position):
    """
    判断鼠标点击了哪个箭头，并执行对应逻辑。
    """
    global lives
    global flying_arrow
    global flying_start_time
    global collision_position
    global collision_start_time
    global game_state
    global result_is_win

    # 动画过程中不允许继续点击
    if flying_arrow is not None:
        return

    for position, direction in list(arrows.items()):
        row, col = position
        rect = cell_rect(row, col)

        if rect.collidepoint(mouse_position):
            # 判断前方是否有箭头
            if is_blocked(position):
                lives -= 1

                collision_position = position
                collision_start_time = pygame.time.get_ticks()

                create_collision_effect(position)
                play_sound(collision_sound)

                if lives <= 0:
                    result_is_win = False
                    game_state = RESULT
                    play_sound(fail_sound)

                return

            # 没有阻挡，启动飞行动画
            flying_arrow = (position, direction)
            flying_start_time = pygame.time.get_ticks()

            play_sound(fly_sound)

            # 立即从棋盘中移除
            del arrows[position]

            return


# =========================
# 更新游戏逻辑
# =========================

def update_game():
    """
    更新飞行动画和关卡状态。
    """
    global flying_arrow
    global game_state
    global result_is_win

    update_particles()

    if flying_arrow is not None:
        elapsed = pygame.time.get_ticks() - flying_start_time

        if elapsed >= FLY_DURATION:
            flying_arrow = None

            # 没有箭头了，表示本关通关
            if len(arrows) == 0:
                result_is_win = True
                game_state = RESULT
                play_sound(win_sound)


def save_screenshot():
    """
    把当前画面保存到 screenshots 目录，按界面状态命名。

    同一个界面连续截图时会自动编号，不会覆盖之前的文件。
    """
    if not os.path.isdir(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR)

    path = os.path.join(SCREENSHOT_DIR, f"{game_state}.png")

    index = 2
    while os.path.exists(path):
        path = os.path.join(
            SCREENSHOT_DIR,
            f"{game_state}-{index}.png"
        )
        index += 1

    pygame.image.save(screen, path)
    print(f"截图已保存：{path}")


def handle_mouse_click(position):
    """
    根据当前界面处理鼠标点击。
    """
    global game_state

    if game_state == START:
        if START_BUTTON.collidepoint(position):
            start_game()

    elif game_state == PLAYING:
        if RESTART_BUTTON.collidepoint(position):
            restart_current_level()
            return

        handle_arrow_click(position)

    elif game_state == RESULT:
        if BACK_BUTTON.collidepoint(position):
            game_state = START
            return

        if result_is_win:
            if current_level_index + 1 < len(LEVELS):
                if NEXT_BUTTON.collidepoint(position):
                    go_to_next_level()
            else:
                if FINAL_RESTART_BUTTON.collidepoint(position):
                    start_game()
        else:
            if NEXT_BUTTON.collidepoint(position):
                restart_current_level()


# =========================
# 主循环
# =========================

def main():
    global game_state

    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    handle_mouse_click(event.pos)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F12:
                    save_screenshot()
                elif event.key == pygame.K_ESCAPE:
                    running = False

        if game_state == PLAYING:
            update_game()

        if game_state == START:
            draw_start_screen()
        elif game_state == PLAYING:
            draw_playing_screen()
        elif game_state == RESULT:
            draw_result_screen()

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
