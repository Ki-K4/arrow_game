"""
一箭又一箭 —— 点击式箭头解谜小游戏。

窗口 760×700，界面由渐变背景、圆角卡片和矢量箭头组成；
除了基础玩法，还带提示、撤销、计时评星、进度存档、随机关卡和自动求解。
"""

import os
import sys
import json
import math
import random
import struct
import pygame


# 截图保存目录（按 F12 时使用）和存档文件
SCREENSHOT_DIR = "screenshots"
PROGRESS_PATH = "progress.json"


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

# 玩法参数
SECONDS_PER_ARROW = 4.0   # 评星用的目标用时：每个箭头几秒
HINT_DURATION = 2400      # 提示高亮的持续时间（毫秒）
UNDO_LIMIT = 30           # 最多能撤销多少步
AUTO_INTERVAL = 420       # 自动求解时两次点击之间的间隔（毫秒）
RANDOM_MIN_ARROWS = 14    # 随机关卡的最少箭头数
RANDOM_MAX_ARROWS = 22    # 随机关卡的最多箭头数

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
ARROW_HINT_COLOR = (255, 214, 92)


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
SELECT = "select"
PLAYING = "playing"
RESULT = "result"

game_state = START
current_level_index = 0
lives = MAX_MISTAKES
is_random_level = False

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

# 计时、提示、撤销、自动求解
level_start_time = 0
level_end_time = 0
hint_position = None
hint_start_time = 0
hints_used = 0
history = []
auto_queue = []
auto_used = False
auto_next_time = 0

# 本局结果
result_is_win = False
just_unlocked = False

# 是否正在显示“开始新游戏”的确认框
confirm_new_game = False


# 界面上的按钮（绘制和点击检测共用同一组矩形，避免两边对不上）
START_BUTTON = pygame.Rect(280, 402, 200, 48)
CONTINUE_BUTTON = pygame.Rect(280, 458, 200, 48)
SELECT_ENTRY_BUTTON = pygame.Rect(280, 514, 200, 48)
RANDOM_BUTTON = pygame.Rect(280, 570, 200, 48)

SELECT_BACK_BUTTON = pygame.Rect(280, 500, 200, 48)

# 开始新游戏的确认对话框
DIALOG_RECT = pygame.Rect(170, 246, 420, 230)
CONFIRM_BUTTON = pygame.Rect(206, 404, 160, 48)
CANCEL_BUTTON = pygame.Rect(394, 404, 160, 48)

RESTART_BUTTON = pygame.Rect(124, 606, 116, 44)
UNDO_BUTTON = pygame.Rect(256, 606, 116, 44)
HINT_BUTTON = pygame.Rect(388, 606, 116, 44)
AUTO_BUTTON = pygame.Rect(520, 606, 116, 44)

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
        # 第 3 关：20 个箭头，阻挡链最长
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
    {
        # 第 4 关：22 个箭头
        (0, 0): "U",
        (0, 2): "U",
        (0, 5): "L",
        (1, 0): "U",
        (1, 1): "L",
        (1, 2): "R",
        (1, 3): "R",
        (1, 4): "U",
        (2, 0): "R",
        (2, 2): "U",
        (2, 3): "D",
        (3, 1): "D",
        (3, 2): "D",
        (3, 3): "L",
        (3, 4): "R",
        (3, 5): "U",
        (4, 0): "R",
        (4, 2): "D",
        (4, 4): "U",
        (5, 1): "R",
        (5, 2): "R",
        (5, 5): "U",
    },
    {
        # 第 5 关：24 个箭头，棋盘最满
        (0, 0): "D",
        (0, 2): "L",
        (0, 4): "D",
        (0, 5): "R",
        (1, 0): "D",
        (1, 1): "L",
        (1, 2): "U",
        (1, 3): "L",
        (1, 4): "L",
        (1, 5): "D",
        (2, 0): "D",
        (2, 1): "U",
        (2, 3): "L",
        (2, 4): "L",
        (2, 5): "L",
        (3, 0): "L",
        (3, 1): "U",
        (3, 3): "L",
        (4, 0): "D",
        (4, 2): "R",
        (4, 3): "R",
        (4, 4): "D",
        (5, 1): "U",
        (5, 4): "L",
    },
]


# =========================
# 进度存档
# =========================

def default_progress():
    """
    存档结构：每一关的最好成绩、上次玩到第几关、已经解锁到第几关。
    """
    return {"levels": {}, "last_level": 0, "unlocked": 1}


def load_progress():
    """
    读取存档。文件不存在或损坏时返回空存档，不影响游戏运行。
    """
    data = default_progress()

    try:
        with open(PROGRESS_PATH, encoding="utf-8") as file:
            saved = json.load(file)
    except (OSError, ValueError):
        return data

    levels = saved.get("levels", {})
    if isinstance(levels, dict):
        for key, value in levels.items():
            if isinstance(value, dict):
                data["levels"][str(key)] = {
                    "stars": int(value.get("stars", 0)),
                    "best_time": float(value.get("best_time", 0.0)),
                }

    data["last_level"] = int(saved.get("last_level", 0))

    # 解锁进度：至少能玩第 1 关，也不能少于已经通关的关卡数
    cleared = 0

    for index in range(len(LEVELS)):
        if str(index) in data["levels"]:
            cleared = index + 1

    unlocked = max(1, int(saved.get("unlocked", 1)), cleared + 1)
    data["unlocked"] = min(len(LEVELS), unlocked)

    return data


def save_progress():
    """
    把存档写回文件。
    """
    try:
        with open(PROGRESS_PATH, "w", encoding="utf-8") as file:
            json.dump(progress, file, ensure_ascii=False, indent=2)
    except OSError:
        pass


progress = load_progress()


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
        progress_ratio = i / sample_count

        frequency = (
            start_frequency
            + (end_frequency - start_frequency) * progress_ratio
        )

        if TONE_WAVE == "square":
            value = 1.0 if phase < 0.5 else -1.0
        elif TONE_WAVE == "triangle":
            value = 4.0 * abs(phase - 0.5) - 1.0
        else:
            value = math.sin(2 * math.pi * phase)

        fade_in = min(i / 700, 1.0)
        fade_out = min((sample_count - i) / 2000, 1.0)
        decay = math.exp(-TONE_DECAY * progress_ratio)
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
    hint_sound = make_tone(880, 0.12, 0.18, 1180)
    win_sound = make_melody(WIN_NOTES, volume=0.30)
    fail_sound = make_melody(FAIL_NOTES, volume=0.32)
except pygame.error:
    collision_sound = None
    fly_sound = None
    hint_sound = None
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


def draw_button(text, rect, color=BLUE, font=None, icon=False, enabled=True):
    """
    绘制圆角渐变按钮：鼠标悬停时整体变亮，左侧可以带一个播放三角。
    """
    if font is None:
        font = NORMAL_FONT

    if not enabled:
        color = shade(color, 0.45)

    hovered = enabled and rect.collidepoint(mouse_position())
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
    if not enabled:
        text_color = (176, 182, 200)

    if not icon:
        draw_text(text, font, text_color, rect.centerx, rect.centery)
        return

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


def level_card_rect(index):
    """
    选关界面上第 index 个关卡卡片的矩形。
    """
    column = index % 3
    row = index // 3
    return pygame.Rect(56 + column * 224, 130 + row * 146, 200, 130)


def draw_lock(center_x, center_y, size=17, color=TEXT_DIM):
    """
    画一把小锁，用在还没解锁的关卡卡片上。
    """
    body = pygame.Rect(0, 0, size, int(size * 0.72))
    body.center = (center_x, center_y + size * 0.2)
    pygame.draw.rect(screen, color, body, border_radius=3)

    shackle = pygame.Rect(0, 0, int(size * 0.56), int(size * 0.66))
    shackle.center = (center_x, body.top)
    pygame.draw.arc(screen, color, shackle, 0, math.pi, 3)


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


def format_time(seconds):
    """
    把秒数格式化成 分:秒。
    """
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def current_elapsed():
    """
    当前关卡已经用掉的时间（秒）。

    本关一旦结束（通关或者失败），时间就停在结算的那一刻，不再继续走。
    """
    if level_end_time:
        return (level_end_time - level_start_time) / 1000

    return (pygame.time.get_ticks() - level_start_time) / 1000


def stop_timer():
    """
    记录本关结束的时间点，让用时停住。
    """
    global level_end_time

    if not level_end_time:
        level_end_time = pygame.time.get_ticks()

    return (level_end_time - level_start_time) / 1000


def level_stars(lives_left, seconds, arrow_count):
    """
    评星规则：基础 1 星，没用失误加 1 星，用时达标再加 1 星。
    """
    stars = 1

    if lives_left >= MAX_MISTAKES:
        stars += 1

    if seconds <= arrow_count * SECONDS_PER_ARROW:
        stars += 1

    return stars


# =========================
# 箭头绘制
# =========================

def arrow_shape(center_x, center_y, direction, size):
    """
    计算箭头的外形：一个三角形箭头加一根短杆，返回两组多边形顶点。
    """
    row_change, col_change = direction_vector(direction)
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

    shadow_head = [(x, y + 4) for x, y in head]
    shadow_shaft = [(x, y + 4) for x, y in shaft]
    pygame.draw.polygon(screen, (12, 16, 26), shadow_shaft)
    pygame.draw.polygon(screen, (12, 16, 26), shadow_head)

    if glow:
        halo = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(halo, (*color, 60), head)
        pygame.draw.polygon(halo, (*color, 60), shaft)
        screen.blit(halo, (0, 0))

    pygame.draw.polygon(screen, color, shaft)
    pygame.draw.polygon(screen, color, head)

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
    在指定位置画一个箭头，用于开始界面和选关界面的示意图。
    """
    head, shaft = arrow_shape(center_x, center_y, direction, size)
    pygame.draw.polygon(screen, color, shaft)
    pygame.draw.polygon(screen, color, head)


def star_points(center_x, center_y, outer, inner):
    """
    计算五角星的顶点，用于星级评价。
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


def draw_stars(center_x, center_y, stars, spacing=34, outer=13, inner=5,
               total=3):
    """
    画一排星星，点亮的用金色，未点亮的用暗色。
    """
    start_x = center_x - (total - 1) * spacing / 2

    for index in range(total):
        color = YELLOW if index < stars else (58, 66, 96)
        pygame.draw.polygon(
            screen,
            color,
            star_points(start_x + index * spacing, center_y, outer, inner)
        )


# =========================
# 关卡逻辑
# =========================

def is_blocked_on(board, position):
    """
    判断 board 上的某个箭头沿其方向前进时，前方是否有其他箭头。
    """
    row, col = position
    row_change, col_change = direction_vector(board[position])

    next_row = row + row_change
    next_col = col + col_change

    while 0 <= next_row < ROWS and 0 <= next_col < COLS:
        if (next_row, next_col) in board:
            return True

        next_row += row_change
        next_col += col_change

    return False


def is_blocked(position):
    """
    判断当前关卡里某个箭头是否被挡住。
    """
    return is_blocked_on(arrows, position)


def free_positions(board):
    """
    当前没有被挡住的箭头。
    """
    return [position for position in board if not is_blocked_on(board, position)]


def blockers_of(board, position):
    """
    position 前方挡路的箭头数量，用来挑“解锁最多”的箭头。
    """
    count = 0

    for other in board:
        if other == position:
            continue

        row, col = other
        row_change, col_change = direction_vector(board[other])

        next_row = row + row_change
        next_col = col + col_change

        while 0 <= next_row < ROWS and 0 <= next_col < COLS:
            if (next_row, next_col) == position:
                count += 1
                break

            next_row += row_change
            next_col += col_change

    return count


def is_solvable(board):
    """
    关卡是否一定可以清空。

    把“谁挡住谁”看成一个有向图：有环时环上的箭头互相挡着，谁也点不掉；
    没有环时总能找到没有被挡住的箭头，点掉它之后剩下的图仍然没有环。
    所以只要用拓扑排序判断有没有环即可。
    """
    remaining = dict(board)
    pending = set(remaining)

    while pending:
        free = [position for position in pending
                if not is_blocked_on(remaining, position)]

        if not free:
            return False

        for position in free:
            pending.discard(position)
            del remaining[position]

    return True


def solve_order(board):
    """
    给出一串可以通关的点击顺序：每次优先点能解锁更多箭头的那个。
    """
    remaining = dict(board)
    order = []

    while remaining:
        free = free_positions(remaining)

        if not free:
            return []

        free.sort(key=lambda position: -blockers_of(remaining, position))
        chosen = free[0]

        order.append(chosen)
        del remaining[chosen]

    return order


def random_solvable_level(arrow_count=None):
    """
    随机生成一个保证能通关的关卡。
    """
    if arrow_count is None:
        arrow_count = random.randint(RANDOM_MIN_ARROWS, RANDOM_MAX_ARROWS)

    cells = [(row, col) for row in range(ROWS) for col in range(COLS)]

    while True:
        board = {
            cell: random.choice("UDLR")
            for cell in random.sample(cells, arrow_count)
        }

        if is_solvable(board):
            return board


# =========================
# 游戏流程
# =========================

def prepare_level(board, level_index=None, random_level=False):
    """
    把和关卡相关的状态全部重置成给定的棋盘。
    """
    global arrows
    global current_level_index
    global lives
    global is_random_level
    global just_unlocked
    global flying_arrow
    global flying_start_time
    global collision_position
    global collision_start_time
    global particles
    global level_start_time
    global level_end_time
    global hint_position
    global hint_start_time
    global hints_used
    global history
    global auto_queue
    global auto_used
    global auto_next_time

    if level_index is not None:
        current_level_index = level_index

    is_random_level = random_level
    just_unlocked = False
    arrows = dict(board)
    lives = MAX_MISTAKES

    flying_arrow = None
    flying_start_time = 0
    collision_position = None
    collision_start_time = 0
    particles = []

    level_start_time = pygame.time.get_ticks()
    level_end_time = 0
    hint_position = None
    hint_start_time = 0
    hints_used = 0
    history = []
    auto_queue = []
    auto_used = False
    auto_next_time = 0


def start_level(index):
    """
    开始第 index 关。
    """
    global game_state

    progress["last_level"] = index
    save_progress()

    prepare_level(LEVELS[index], level_index=index, random_level=False)
    game_state = PLAYING


def start_random_level():
    """
    开始一个随机生成的关卡。
    """
    global game_state

    prepare_level(random_solvable_level(), random_level=True)
    game_state = PLAYING


def restart_current_level():
    """
    重新开始当前关卡；随机关卡会换一个新棋盘。
    """
    global game_state

    if is_random_level:
        start_random_level()
        return

    prepare_level(
        LEVELS[current_level_index],
        level_index=current_level_index,
        random_level=False
    )
    game_state = PLAYING


def go_to_next_level():
    """
    进入下一关。
    """
    global game_state

    if current_level_index + 1 < len(LEVELS):
        start_level(current_level_index + 1)
    else:
        game_state = SELECT


def back_to_select():
    """
    回到选关界面。
    """
    global game_state

    game_state = SELECT


def total_stars():
    """
    已经拿到的星星总数。
    """
    return sum(
        int(record.get("stars", 0))
        for record in progress["levels"].values()
    )


def unlocked_levels():
    """
    已经解锁的关卡数量：通过第 N 关才会解锁第 N+1 关。
    """
    return max(1, min(len(LEVELS), int(progress.get("unlocked", 1))))


def level_unlocked(index):
    """
    第 index 关是否已经解锁。
    """
    return index < unlocked_levels()


def level_record(index):
    """
    第 index 关的最好成绩。
    """
    return progress["levels"].get(str(index), {"stars": 0, "best_time": 0.0})


def has_save():
    """
    存档里有没有进度：拿过星星、解锁过新关卡或者玩过不止第一关。
    """
    return (
        bool(progress["levels"])
        or int(progress.get("unlocked", 1)) > 1
        or int(progress.get("last_level", 0)) > 0
    )


def start_new_game():
    """
    开始新游戏：清空存档，从第 1 关重新开始。
    """
    global progress
    global confirm_new_game

    progress = default_progress()
    save_progress()

    confirm_new_game = False
    start_level(0)


def continue_saved_game():
    """
    继续游戏：接着存档里上次玩到的关卡。
    """
    target = min(progress.get("last_level", 0), unlocked_levels() - 1)
    start_level(max(0, target))


# =========================
# 撤销 / 提示 / 自动求解
# =========================

def push_history():
    """
    记录当前状态，供撤销使用。
    """
    history.append({
        "arrows": dict(arrows),
        "lives": lives,
        "hints_used": hints_used,
    })

    if len(history) > UNDO_LIMIT:
        history.pop(0)


def undo_step():
    """
    撤销上一步：恢复棋盘、失误次数和提示次数。
    """
    global lives
    global hints_used
    global flying_arrow
    global collision_position
    global auto_queue
    global auto_used

    if not history:
        return False

    snapshot = history.pop()

    arrows.clear()
    arrows.update(snapshot["arrows"])

    lives = snapshot["lives"]
    hints_used = snapshot["hints_used"]

    flying_arrow = None
    collision_position = None
    auto_queue = []
    auto_used = False

    return True


def show_hint():
    """
    高亮一个当前可以点击的箭头。
    """
    global hint_position
    global hint_start_time
    global hints_used

    free = free_positions(arrows)

    if not free:
        return False

    free.sort(key=lambda position: -blockers_of(arrows, position))
    hint_position = free[0]
    hint_start_time = pygame.time.get_ticks()
    hints_used += 1

    play_sound(hint_sound)
    return True


def hint_visible():
    """
    提示高亮是否还在显示。
    """
    return (
        hint_position is not None
        and pygame.time.get_ticks() - hint_start_time < HINT_DURATION
    )


def auto_running():
    """
    自动求解是否正在运行。
    """
    return bool(auto_queue)


def toggle_auto_solve():
    """
    开始或停止自动求解。
    """
    global auto_queue
    global auto_next_time

    if auto_queue:
        auto_queue = []
        return False

    auto_queue = solve_order(arrows)
    auto_next_time = 0
    return True


def update_auto_solve():
    """
    自动求解：按解法顺序定时点掉箭头。
    """
    global auto_queue
    global auto_next_time
    global auto_used

    if not auto_queue or flying_arrow is not None:
        return

    now = pygame.time.get_ticks()

    if now < auto_next_time:
        return

    position = auto_queue.pop(0)

    if position not in arrows:
        return

    if is_blocked(position):
        # 棋盘被手动改过，重新算一遍解法
        auto_queue = solve_order(arrows)
        return

    auto_used = True
    auto_next_time = now + AUTO_INTERVAL
    activate_arrow(position)


def activate_arrow(position):
    """
    点掉一个没有被挡住的箭头，播放飞行动画。
    """
    global flying_arrow
    global flying_start_time

    flying_arrow = (position, arrows[position])
    flying_start_time = pygame.time.get_ticks()

    play_sound(fly_sound)

    del arrows[position]


def hit_blocked_arrow(position):
    """
    点到被挡住的箭头：扣一次失误并播放碰撞反馈。
    """
    global lives
    global collision_position
    global collision_start_time
    global game_state
    global result_is_win
    global auto_queue
    global last_result_time

    lives -= 1
    collision_position = position
    collision_start_time = pygame.time.get_ticks()

    create_collision_effect(position)
    play_sound(collision_sound)

    auto_queue = []

    if lives <= 0:
        result_is_win = False
        game_state = RESULT
        last_result_time = stop_timer()
        play_sound(fail_sound)


def finish_level():
    """
    本关通关：算成绩、写存档。
    """
    global game_state
    global result_is_win
    global auto_queue
    global last_result_time
    global last_result_stars

    result_is_win = True
    game_state = RESULT
    auto_queue = []

    play_sound(win_sound)

    last_result_time = stop_timer()

    if is_random_level:
        last_result_stars = 0
        return

    stars = level_stars(
        lives,
        last_result_time,
        len(LEVELS[current_level_index])
    )
    last_result_stars = stars

    # 通关就解锁下一关，自动求解演示也算通关，只是不记录成绩
    unlock_next_level()

    if auto_used:
        return

    key = str(current_level_index)
    previous = progress["levels"].get(key, {})
    best_stars = max(stars, int(previous.get("stars", 0)))
    old_time = float(previous.get("best_time", 0.0))
    best_time = last_result_time if old_time <= 0 else min(old_time, last_result_time)

    progress["levels"][key] = {
        "stars": best_stars,
        "best_time": best_time,
    }

    save_progress()


def unlock_next_level():
    """
    通过当前关卡之后解锁下一关，返回是否刚刚解锁了新关卡。
    """
    global just_unlocked

    next_index = current_level_index + 1

    if next_index >= len(LEVELS):
        return False

    if next_index < unlocked_levels():
        return False

    progress["unlocked"] = next_index + 1
    save_progress()
    just_unlocked = True
    return True


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
    在透明图层上绘制粒子，颜色和大小都随寿命衰减。
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

    ratio = elapsed / COLLISION_DURATION

    PARTICLE_LAYER.fill((0, 0, 0, 0))

    for index, scale in enumerate((1.0, 0.72)):
        radius = int(CELL_SIZE * (0.24 + 0.5 * ratio) * scale)
        alpha = int(150 * (1 - ratio) / (index + 1))

        pygame.draw.circle(
            PARTICLE_LAYER,
            (255, 110, 120, alpha),
            (rect.centerx, rect.centery),
            radius,
            width=3
        )

    screen.blit(PARTICLE_LAYER, (0, 0))


def draw_hint():
    """
    提示高亮：在可点击的箭头周围画一圈会呼吸的金色圆环。
    """
    if not hint_visible():
        return

    elapsed = pygame.time.get_ticks() - hint_start_time
    pulse = 0.5 + 0.5 * math.sin(elapsed / 140)

    row, col = hint_position
    rect = cell_rect(row, col)

    radius = int(CELL_SIZE * 0.42 + pulse * 5)
    alpha = int(90 + 120 * (1 - elapsed / HINT_DURATION))

    PARTICLE_LAYER.fill((0, 0, 0, 0))
    pygame.draw.circle(
        PARTICLE_LAYER,
        (*ARROW_HINT_COLOR, max(0, min(255, alpha))),
        (rect.centerx, rect.centery),
        radius,
        width=4
    )
    screen.blit(PARTICLE_LAYER, (0, 0))


# 选关界面的“随机关卡”按钮，以及本局的结算信息
SELECT_RANDOM_BUTTON = pygame.Rect(280, 440, 200, 48)

last_result_stars = 0
last_result_time = 0.0


# =========================
# 界面绘制
# =========================

def draw_status_bar():
    """
    顶部状态卡片：关卡进度、用时、提示次数和剩余失误。
    """
    draw_card(STATUS_RECT)

    if is_random_level:
        title = "随机关卡"
    else:
        title = f"第 {current_level_index + 1} / {len(LEVELS)} 关"

    draw_text(
        title,
        NORMAL_FONT,
        TEXT_COLOR,
        STATUS_RECT.left + 32,
        STATUS_RECT.centery - 15,
        center=False
    )

    if not is_random_level:
        for index in range(len(LEVELS)):
            pill = pygame.Rect(
                STATUS_RECT.left + 190 + index * 22,
                STATUS_RECT.centery - 21,
                14,
                12
            )
            color = BLUE if index <= current_level_index else (56, 66, 96)
            pygame.draw.rect(screen, color, pill, border_radius=6)

    draw_text(
        f"用时 {format_time(current_elapsed())}　提示 {hints_used} 次",
        TINY_FONT,
        TEXT_DIM,
        STATUS_RECT.left + 32,
        STATUS_RECT.centery + 15,
        center=False
    )

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
            pygame.draw.rect(screen, TILE_EDGE, tile, width=1, border_radius=10)

    for position, direction in arrows.items():
        color = ARROW_COLOR
        offset_x = 0

        if position == collision_position:
            elapsed = pygame.time.get_ticks() - collision_start_time

            if elapsed < COLLISION_DURATION:
                color = ARROW_COLLISION_COLOR
                offset_x = int(math.sin(elapsed * 0.045) * SHAKE_AMPLITUDE)

        draw_arrow(position, direction, color=color, offset_x=offset_x)

    if flying_arrow is not None:
        position, direction = flying_arrow

        elapsed = pygame.time.get_ticks() - flying_start_time
        ratio = min(elapsed / FLY_DURATION, 1.0)

        row_change, col_change = direction_vector(direction)
        distance = CELL_SIZE * 2.4 * ratio

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

    draw_hint()
    draw_collision_ring()
    draw_particles()


def draw_start_screen():
    """
    绘制开始界面。
    """
    draw_background()

    draw_text(WINDOW_TITLE, TITLE_FONT, TEXT_COLOR, SCREEN_WIDTH // 2, 120)

    draw_text(
        "点击箭头，让它们全部离开棋盘",
        SMALL_FONT,
        TEXT_DIM,
        SCREEN_WIDTH // 2,
        166
    )

    arrows_demo = (("U", BLUE), ("R", GREEN), ("D", YELLOW), ("L", RED))

    for index, (direction, color) in enumerate(arrows_demo):
        draw_arrow_at(
            SCREEN_WIDTH // 2 - 114 + index * 76,
            236,
            direction,
            62,
            color
        )

    info_rect = pygame.Rect(140, 274, SCREEN_WIDTH - 280, 116)
    draw_card(info_rect)

    draw_text(
        "点击没有被挡住的箭头",
        NORMAL_FONT,
        TEXT_COLOR,
        SCREEN_WIDTH // 2,
        306
    )
    draw_text(
        "箭头会沿自己的方向飞出棋盘",
        SMALL_FONT,
        TEXT_DIM,
        SCREEN_WIDTH // 2,
        336
    )
    draw_text(
        f"点错会消耗一次失误，共 {MAX_MISTAKES} 次机会",
        SMALL_FONT,
        TEXT_DIM,
        SCREEN_WIDTH // 2,
        366
    )

    draw_button("开始游戏", START_BUTTON, GREEN, icon=True)
    draw_button("继续游戏", CONTINUE_BUTTON, BLUE, enabled=has_save())
    draw_button("选择关卡", SELECT_ENTRY_BUTTON, GRAY)
    draw_button("随机关卡", RANDOM_BUTTON, GRAY)

    draw_text(
        f"已解锁 {unlocked_levels()} / {len(LEVELS)} 关　"
        f"已获得 {total_stars()} / {len(LEVELS) * 3} 颗星",
        TINY_FONT,
        TEXT_DIM,
        SCREEN_WIDTH // 2,
        646
    )


def draw_confirm_dialog():
    """
    开始新游戏前的确认框，避免误点清空存档。
    """
    dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 150))
    screen.blit(dim, (0, 0))

    draw_card(DIALOG_RECT, fill=shade(CARD_COLOR, 1.1))

    draw_text(
        "开始新游戏？",
        NORMAL_FONT,
        TEXT_COLOR,
        DIALOG_RECT.centerx,
        DIALOG_RECT.top + 42
    )
    draw_text(
        "开始新游戏会清空已保存的星级、最佳用时",
        SMALL_FONT,
        TEXT_DIM,
        DIALOG_RECT.centerx,
        DIALOG_RECT.top + 76
    )
    draw_text(
        "和解锁进度，并从第 1 关重新开始。",
        SMALL_FONT,
        TEXT_DIM,
        DIALOG_RECT.centerx,
        DIALOG_RECT.top + 104
    )
    draw_text(
        "想接着上次的进度玩，请点“取消”后选“继续游戏”。",
        TINY_FONT,
        TEXT_DIM,
        DIALOG_RECT.centerx,
        DIALOG_RECT.top + 134
    )

    draw_button("确定开始", CONFIRM_BUTTON, RED, font=SMALL_FONT)
    draw_button("取消", CANCEL_BUTTON, GRAY, font=SMALL_FONT)


def draw_select_screen():
    """
    绘制选关界面：每一关显示箭头数量、最好成绩和星级。
    """
    draw_background()

    draw_text("选择关卡", LARGE_FONT, TEXT_COLOR, SCREEN_WIDTH // 2, 76)

    for index in range(len(LEVELS)):
        rect = level_card_rect(index)
        locked = not level_unlocked(index)

        hovered = (not locked) and rect.collidepoint(mouse_position())
        fill = CARD_COLOR

        if locked:
            fill = shade(CARD_COLOR, 0.82)
        elif hovered:
            fill = shade(CARD_COLOR, 1.14)

        draw_card(rect, fill=fill)

        draw_text(
            f"第 {index + 1} 关",
            NORMAL_FONT,
            TEXT_DIM if locked else TEXT_COLOR,
            rect.centerx,
            rect.top + 30
        )

        if locked:
            draw_lock(rect.centerx, rect.top + 70)
            draw_text(
                f"通过第 {index} 关后解锁",
                TINY_FONT,
                TEXT_DIM,
                rect.centerx,
                rect.top + 106
            )
            continue

        record = level_record(index)

        draw_text(
            f"{len(LEVELS[index])} 个箭头",
            TINY_FONT,
            TEXT_DIM,
            rect.centerx,
            rect.top + 56
        )

        draw_stars(rect.centerx, rect.top + 84, record["stars"],
                   spacing=30, outer=11, inner=4)

        best = float(record.get("best_time", 0.0))
        draw_text(
            f"最佳 {format_time(best)}" if best else "还没通关",
            TINY_FONT,
            TEXT_DIM,
            rect.centerx,
            rect.top + 110
        )

    draw_button("随机关卡", SELECT_RANDOM_BUTTON, GREEN)
    draw_button("返回开始", SELECT_BACK_BUTTON, GRAY, font=SMALL_FONT)

    draw_text(
        f"已解锁 {unlocked_levels()} / {len(LEVELS)} 关　"
        f"已获得 {total_stars()} / {len(LEVELS) * 3} 颗星　ESC 返回",
        TINY_FONT,
        TEXT_DIM,
        SCREEN_WIDTH // 2,
        580
    )


def draw_playing_screen():
    """
    绘制游戏界面。
    """
    draw_background()
    draw_status_bar()
    draw_board()

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
        remaining = len(arrows) + (1 if flying_arrow else 0)
        text = f"剩余箭头 {remaining}　点击没有被挡住的箭头"

        if auto_running():
            text = "自动求解中，再按一次 S 停止"

        draw_text(text, SMALL_FONT, TEXT_DIM, SCREEN_WIDTH // 2, HINT_Y)

    draw_button("重新开始", RESTART_BUTTON, BLUE, font=SMALL_FONT)
    draw_button("撤销", UNDO_BUTTON, GRAY, font=SMALL_FONT,
                enabled=bool(history))
    draw_button("提示", HINT_BUTTON, YELLOW, font=SMALL_FONT)
    draw_button("停止求解" if auto_running() else "自动求解",
                AUTO_BUTTON, GREEN, font=SMALL_FONT)

    draw_text(
        "H 提示　U 撤销　S 自动求解　R 重开　F12 截图　ESC 返回",
        TINY_FONT,
        TEXT_DIM,
        SCREEN_WIDTH // 2,
        FOOTER_Y
    )


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
        if is_random_level:
            draw_text(
                "随机关卡不限成绩，随时再来一关",
                SMALL_FONT,
                TEXT_DIM,
                SCREEN_WIDTH // 2,
                286
            )
        else:
            draw_stars(SCREEN_WIDTH // 2, 286, last_result_stars,
                       spacing=90, outer=34, inner=14)

        caption = f"用时 {format_time(last_result_time)}"

        if auto_used:
            caption += "　自动求解演示，未记录成绩"
        elif not is_random_level:
            record = level_record(current_level_index)
            best = float(record.get("best_time", 0.0))

            if best:
                caption += f"　最佳 {format_time(best)}"

        draw_text(caption, TINY_FONT, TEXT_DIM, SCREEN_WIDTH // 2, 338)

        if just_unlocked:
            draw_text(
                f"已解锁第 {current_level_index + 2} 关！",
                SMALL_FONT,
                YELLOW,
                SCREEN_WIDTH // 2,
                364
            )
    else:
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

        draw_text(
            f"本关用时 {format_time(last_result_time)}",
            TINY_FONT,
            TEXT_DIM,
            SCREEN_WIDTH // 2,
            338
        )

    if result_is_win:
        if is_random_level:
            draw_button("再来一关", NEXT_BUTTON, GREEN, icon=True)
        elif current_level_index + 1 < len(LEVELS):
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
        draw_button("重新开始本关", NEXT_BUTTON, BLUE)

    draw_button("返回选关", BACK_BUTTON, GRAY, font=SMALL_FONT)

    draw_text(
        f"共 {len(LEVELS)} 关　已获得 {total_stars()} 颗星",
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
    # 动画过程中或自动求解时不接受手动点击
    if flying_arrow is not None or auto_running():
        return

    for position in list(arrows):
        row, col = position

        if cell_rect(row, col).collidepoint(mouse_position):
            push_history()

            if is_blocked(position):
                hit_blocked_arrow(position)
            else:
                activate_arrow(position)

            return


def handle_key_down(key):
    """
    处理快捷键。返回 True 表示按键已经被用掉。
    """
    global game_state
    global confirm_new_game

    if key == pygame.K_F12:
        save_screenshot()
        return True

    if key == pygame.K_ESCAPE:
        if confirm_new_game:
            confirm_new_game = False
            return True

        if game_state == PLAYING:
            game_state = SELECT
        elif game_state == SELECT:
            game_state = START
        else:
            return False
        return True

    if game_state != PLAYING:
        return False

    if key == pygame.K_h:
        show_hint()
    elif key == pygame.K_u:
        undo_step()
    elif key == pygame.K_s:
        toggle_auto_solve()
    elif key == pygame.K_r:
        restart_current_level()
    else:
        return False

    return True


def handle_mouse_click(position):
    """
    根据当前界面处理鼠标点击。
    """
    global game_state
    global confirm_new_game

    # 确认框打开时，只处理它自己的两个按钮
    if confirm_new_game:
        if CONFIRM_BUTTON.collidepoint(position):
            start_new_game()
        elif CANCEL_BUTTON.collidepoint(position):
            confirm_new_game = False
        return

    if game_state == START:
        if START_BUTTON.collidepoint(position):
            if has_save():
                confirm_new_game = True
            else:
                start_new_game()
        elif CONTINUE_BUTTON.collidepoint(position):
            if has_save():
                continue_saved_game()
        elif SELECT_ENTRY_BUTTON.collidepoint(position):
            game_state = SELECT
        elif RANDOM_BUTTON.collidepoint(position):
            start_random_level()

    elif game_state == SELECT:
        for index in range(len(LEVELS)):
            if (level_card_rect(index).collidepoint(position)
                    and level_unlocked(index)):
                start_level(index)
                return

        if SELECT_RANDOM_BUTTON.collidepoint(position):
            start_random_level()
        elif SELECT_BACK_BUTTON.collidepoint(position):
            game_state = START

    elif game_state == PLAYING:
        if RESTART_BUTTON.collidepoint(position):
            restart_current_level()
            return

        if UNDO_BUTTON.collidepoint(position):
            undo_step()
            return

        if HINT_BUTTON.collidepoint(position):
            show_hint()
            return

        if AUTO_BUTTON.collidepoint(position):
            toggle_auto_solve()
            return

        handle_arrow_click(position)

    elif game_state == RESULT:
        if BACK_BUTTON.collidepoint(position):
            game_state = SELECT
            return

        if result_is_win:
            if is_random_level:
                if NEXT_BUTTON.collidepoint(position):
                    start_random_level()
            elif current_level_index + 1 < len(LEVELS):
                if NEXT_BUTTON.collidepoint(position):
                    go_to_next_level()
            else:
                if FINAL_RESTART_BUTTON.collidepoint(position):
                    start_level(0)
        else:
            if NEXT_BUTTON.collidepoint(position):
                restart_current_level()


# =========================
# 更新游戏逻辑
# =========================

def update_game():
    """
    更新飞行动画、粒子和自动求解。
    """
    global flying_arrow

    update_particles()
    update_auto_solve()

    if flying_arrow is not None:
        elapsed = pygame.time.get_ticks() - flying_start_time

        if elapsed >= FLY_DURATION:
            flying_arrow = None

            # 没有箭头了，表示本关通关
            if not arrows:
                finish_level()


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
                if not handle_key_down(event.key):
                    if event.key == pygame.K_ESCAPE:
                        running = False

        if game_state == PLAYING:
            update_game()

        if game_state == START:
            draw_start_screen()

            if confirm_new_game:
                draw_confirm_dialog()
        elif game_state == SELECT:
            draw_select_screen()
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
