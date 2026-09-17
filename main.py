import sys
import math
import random
import pygame


# =========================
# 基本配置
# =========================

pygame.init()

SCREEN_WIDTH = 760
SCREEN_HEIGHT = 700

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("一箭又一箭")

clock = pygame.time.Clock()

# 颜色
BG_COLOR = (245, 247, 250)
PANEL_COLOR = (255, 255, 255)
GRID_COLOR = (210, 215, 225)
TEXT_COLOR = (35, 40, 50)
BLUE = (65, 125, 220)
DARK_BLUE = (42, 90, 175)
RED = (220, 70, 70)
GREEN = (55, 170, 95)
YELLOW = (245, 185, 50)
ARROW_COLOR = (45, 105, 200)
ARROW_SELECTED_COLOR = (250, 145, 40)
ARROW_COLLISION_COLOR = (220, 65, 65)

# 棋盘配置
ROWS = 6
COLS = 6
CELL_SIZE = 70

BOARD_X = (SCREEN_WIDTH - COLS * CELL_SIZE) // 2
BOARD_Y = 145

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
FLY_DURATION = 350

# 碰撞反馈
collision_position = None
collision_start_time = 0
COLLISION_DURATION = 450

# 碰撞粒子
particles = []

# 本局结果
result_is_win = False


# =========================
# 关卡数据
# =========================

LEVELS = [
    {
        # 四个方向都有
        # (2, 2) 向右会被 (2, 4) 阻挡
        (2, 2): "R",
        (2, 4): "U",
        (4, 1): "L",
        (4, 3): "D",
        (0, 0): "R",
        (5, 5): "D",
    },
    {
        # (1, 1) 向下会被 (4, 1) 阻挡
        # 先点击 (4, 1)，再点击 (1, 1)
        (1, 1): "D",
        # 原来是 "U"：它和 (1, 1) 的 "D" 在同一列互相阻挡，本关就无解了
        (4, 1): "L",
        # 原来这里是 "L"：它和 (2, 1) 的 "R" 互相阻挡，导致本关无解
        (2, 4): "D",
        (2, 1): "R",
        (0, 5): "U",
        (5, 0): "L",
    },
    {
        # (0, 2) 向下会被 (3, 2) 阻挡
        # 先点击 (3, 2)，再点击 (0, 2)
        (0, 2): "D",
        # 原来这里是 "U"：它和 (0, 2) 的 "D" 互相阻挡
        (3, 2): "D",
        # 原来这里是 "R"：它和 (2, 4) 的 "L" 互相阻挡
        (2, 0): "U",
        (2, 4): "L",
        (5, 1): "D",
        (0, 5): "R",
        (4, 4): "U",
    },
]


# =========================
# 字体相关
# =========================

def get_font(size, bold=False):
    """
    尝试使用常见中文字体。
    如果系统没有中文字体，则使用默认字体。
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


TITLE_FONT = get_font(40, True)
LARGE_FONT = get_font(32, True)
NORMAL_FONT = get_font(24)
SMALL_FONT = get_font(18)


# =========================
# 工具函数
# =========================

def draw_text(text, font, color, x, y, center=True):
    """
    在屏幕上绘制文字。
    """
    surface = font.render(text, True, color)

    if center:
        rect = surface.get_rect(center=(x, y))
    else:
        rect = surface.get_rect(topleft=(x, y))

    screen.blit(surface, rect)
    return rect


def draw_button(text, rect, color=BLUE, text_color=(255, 255, 255)):
    """
    绘制按钮。
    """
    pygame.draw.rect(screen, color, rect, border_radius=10)
    pygame.draw.rect(screen, DARK_BLUE, rect, width=2, border_radius=10)

    draw_text(
        text,
        NORMAL_FONT,
        text_color,
        rect.centerx,
        rect.centery
    )


def cell_rect(row, col):
    """
    获取棋盘中某个格子的矩形区域。
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


def direction_symbol(direction):
    """
    用于界面绘制箭头。
    """
    return {
        "U": "↑",
        "D": "↓",
        "L": "←",
        "R": "→"
    }.get(direction, "?")


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

    if level_index is not None:
        current_level_index = level_index

    arrows = dict(LEVELS[current_level_index])
    lives = MAX_MISTAKES

    flying_arrow = None
    flying_start_time = 0

    collision_position = None
    collision_start_time = 0


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

    position 是一个元组，例如 (2, 2)。
    """
    row, col = position
    direction = arrows[position]

    row_change, col_change = direction_vector(direction)

    next_row = row + row_change
    next_col = col + col_change

    # 沿着箭头方向逐格检查
    while 0 <= next_row < ROWS and 0 <= next_col < COLS:
        if (next_row, next_col) in arrows:
            return True

        next_row += row_change
        next_col += col_change

    return False


# =========================
# 箭头绘制
# =========================

def draw_arrow(position, direction, color=ARROW_COLOR, offset_x=0, offset_y=0):
    """
    绘制一个箭头。
    position 是棋盘坐标。
    offset_x 和 offset_y 用于碰撞晃动效果。
    """
    row, col = position
    rect = cell_rect(row, col)

    center_x = rect.centerx + offset_x
    center_y = rect.centery + offset_y

    # 绘制箭头所在的圆形背景
    pygame.draw.circle(
        screen,
        color,
        (center_x, center_y),
        23
    )

    # 箭头主体
    if direction == "U":
        points = [
            (center_x, center_y - 18),
            (center_x - 13, center_y - 3),
            (center_x - 5, center_y - 3),
            (center_x - 5, center_y + 17),
            (center_x + 5, center_y + 17),
            (center_x + 5, center_y - 3),
            (center_x + 13, center_y - 3),
        ]
    elif direction == "D":
        points = [
            (center_x, center_y + 18),
            (center_x - 13, center_y + 3),
            (center_x - 5, center_y + 3),
            (center_x - 5, center_y - 17),
            (center_x + 5, center_y - 17),
            (center_x + 5, center_y + 3),
            (center_x + 13, center_y + 3),
        ]
    elif direction == "L":
        points = [
            (center_x - 18, center_y),
            (center_x - 3, center_y - 13),
            (center_x - 3, center_y - 5),
            (center_x + 17, center_y - 5),
            (center_x + 17, center_y + 5),
            (center_x - 3, center_y + 5),
            (center_x - 3, center_y + 13),
        ]
    else:  # R
        points = [
            (center_x + 18, center_y),
            (center_x + 3, center_y - 13),
            (center_x + 3, center_y - 5),
            (center_x - 17, center_y - 5),
            (center_x - 17, center_y + 5),
            (center_x + 3, center_y + 5),
            (center_x + 3, center_y + 13),
        ]

    pygame.draw.polygon(screen, (255, 255, 255), points)


def create_collision_effect(position):
    """
    在发生碰撞的格子里生成一批粒子。
    """
    global particles

    row, col = position
    rect = cell_rect(row, col)

    center_x = rect.centerx
    center_y = rect.centery

    for _ in range(18):
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(1.5, 4.5)

        particles.append({
            "x": center_x,
            "y": center_y,
            "vx": math.cos(angle) * speed,
            "vy": math.sin(angle) * speed,
            "life": random.randint(20, 35),
            "max_life": 35,
            "size": random.randint(3, 6),
            "color": random.choice([
                (255, 80, 80),
                (255, 150, 60),
                (255, 220, 80)
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

        particle["vy"] += 0.12
        particle["life"] -= 1

        if particle["life"] > 0:
            alive_particles.append(particle)

    particles = alive_particles


def draw_particles():
    """
    绘制所有存活粒子，透明度随寿命衰减。
    """
    for particle in particles:
        alpha = int(
            255 * particle["life"] / particle["max_life"]
        )

        size = max(
            1,
            int(
                particle["size"]
                * particle["life"]
                / particle["max_life"]
            )
        )

        surface = pygame.Surface(
            (size * 2, size * 2),
            pygame.SRCALPHA
        )

        color = (
            particle["color"][0],
            particle["color"][1],
            particle["color"][2],
            alpha
        )

        pygame.draw.circle(surface, color, (size, size), size)

        screen.blit(
            surface,
            (
                int(particle["x"] - size),
                int(particle["y"] - size)
            )
        )


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

    radius = int(CELL_SIZE * 0.35 + CELL_SIZE * 0.45 * progress)
    alpha = int(200 * (1 - progress))

    surface = pygame.Surface(
        (radius * 2 + 4, radius * 2 + 4),
        pygame.SRCALPHA
    )

    pygame.draw.circle(
        surface,
        (220, 65, 65, alpha),
        (radius + 2, radius + 2),
        radius,
        width=3
    )

    screen.blit(
        surface,
        (
            rect.centerx - radius - 2,
            rect.centery - radius - 2
        )
    )


def draw_board():
    """
    绘制棋盘、箭头和飞行动画。
    """
    # 绘制棋盘背景
    board_rect = pygame.Rect(
        BOARD_X,
        BOARD_Y,
        COLS * CELL_SIZE,
        ROWS * CELL_SIZE
    )

    pygame.draw.rect(
        screen,
        PANEL_COLOR,
        board_rect,
        border_radius=8
    )

    # 绘制网格
    for row in range(ROWS):
        for col in range(COLS):
            rect = cell_rect(row, col)
            pygame.draw.rect(
                screen,
                GRID_COLOR,
                rect,
                width=1
            )

    # 绘制普通箭头
    for position, direction in arrows.items():
        color = ARROW_COLOR

        # 如果正在碰撞，就使用红色并进行晃动
        offset_x = 0
        offset_y = 0

        if position == collision_position:
            elapsed = pygame.time.get_ticks() - collision_start_time

            if elapsed < COLLISION_DURATION:
                color = ARROW_COLLISION_COLOR
                offset_x = int(math.sin(elapsed * 0.06) * 6)
            else:
                color = ARROW_COLOR

        draw_arrow(
            position,
            direction,
            color=color,
            offset_x=offset_x,
            offset_y=offset_y
        )

    # 绘制飞出棋盘的箭头
    if flying_arrow is not None:
        position, direction = flying_arrow

        elapsed = pygame.time.get_ticks() - flying_start_time
        progress = min(elapsed / FLY_DURATION, 1.0)

        row, col = position
        row_change, col_change = direction_vector(direction)

        # 箭头飞行距离
        distance = CELL_SIZE * 2.3 * progress

        offset_x = col_change * distance
        offset_y = row_change * distance

        draw_arrow(
            position,
            direction,
            color=GREEN,
            offset_x=offset_x,
            offset_y=offset_y
        )

    # 绘制碰撞圆环和粒子
    draw_collision_ring()
    draw_particles()

    # 碰撞提示文字
    if collision_position is not None:
        elapsed = pygame.time.get_ticks() - collision_start_time

        if elapsed < COLLISION_DURATION:
            draw_text(
                "前方有阻挡",
                NORMAL_FONT,
                RED,
                SCREEN_WIDTH // 2,
                580
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

                if lives <= 0:
                    result_is_win = False
                    game_state = RESULT

                return

            # 没有阻挡，启动飞行动画
            flying_arrow = (position, direction)
            flying_start_time = pygame.time.get_ticks()

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


# =========================
# 绘制不同界面
# =========================

def draw_start_screen():
    """
    绘制开始界面。
    """
    screen.fill(BG_COLOR)

    draw_text(
        "一箭又一箭",
        TITLE_FONT,
        TEXT_COLOR,
        SCREEN_WIDTH // 2,
        150
    )

    draw_text(
        "点击箭头，让所有箭头飞出棋盘",
        NORMAL_FONT,
        TEXT_COLOR,
        SCREEN_WIDTH // 2,
        220
    )

    draw_text(
        "前方没有其他箭头时，箭头才能飞出",
        SMALL_FONT,
        (90, 95, 105),
        SCREEN_WIDTH // 2,
        265
    )

    start_button = pygame.Rect(
        SCREEN_WIDTH // 2 - 100,
        350,
        200,
        60
    )

    draw_button("开始游戏", start_button, GREEN)

    draw_text(
        "使用鼠标点击箭头",
        SMALL_FONT,
        (100, 105, 115),
        SCREEN_WIDTH // 2,
        470
    )


def draw_playing_screen():
    """
    绘制游戏界面。
    """
    screen.fill(BG_COLOR)

    level_text = f"当前关卡：{current_level_index + 1} / {len(LEVELS)}"
    remaining_text = f"剩余箭头：{len(arrows) + (1 if flying_arrow else 0)}"
    lives_text = f"剩余失误次数：{lives}"

    draw_text(
        level_text,
        NORMAL_FONT,
        TEXT_COLOR,
        35,
        35,
        center=False
    )

    draw_text(
        remaining_text,
        NORMAL_FONT,
        TEXT_COLOR,
        35,
        75,
        center=False
    )

    lives_color = RED if lives <= 1 else TEXT_COLOR

    draw_text(
        lives_text,
        NORMAL_FONT,
        lives_color,
        SCREEN_WIDTH - 220,
        35,
        center=False
    )

    restart_button = pygame.Rect(
        SCREEN_WIDTH - 180,
        75,
        140,
        42
    )

    draw_button(
        "重新开始",
        restart_button,
        color=BLUE
    )

    draw_board()

    draw_text(
        "点击没有阻挡的箭头即可消除",
        SMALL_FONT,
        (100, 105, 115),
        SCREEN_WIDTH // 2,
        610
    )


def draw_result_screen():
    """
    绘制通关或失败界面。
    """
    screen.fill(BG_COLOR)

    if result_is_win:
        title = "本关通关！"
        title_color = GREEN
        description = "所有箭头都已经飞出棋盘"
    else:
        title = "挑战失败"
        title_color = RED
        description = "失误次数已经耗尽"

    draw_text(
        title,
        TITLE_FONT,
        title_color,
        SCREEN_WIDTH // 2,
        180
    )

    draw_text(
        description,
        NORMAL_FONT,
        TEXT_COLOR,
        SCREEN_WIDTH // 2,
        250
    )

    if result_is_win:
        if current_level_index + 1 < len(LEVELS):
            next_button = pygame.Rect(
                SCREEN_WIDTH // 2 - 110,
                350,
                220,
                60
            )

            draw_button(
                "进入下一关",
                next_button,
                GREEN
            )
        else:
            draw_text(
                "恭喜你完成全部关卡！",
                LARGE_FONT,
                GREEN,
                SCREEN_WIDTH // 2,
                350
            )

            restart_button = pygame.Rect(
                SCREEN_WIDTH // 2 - 110,
                430,
                220,
                60
            )

            draw_button(
                "重新开始游戏",
                restart_button,
                BLUE
            )
    else:
        restart_button = pygame.Rect(
            SCREEN_WIDTH // 2 - 110,
            350,
            220,
            60
        )

        draw_button(
            "重新开始本关",
            restart_button,
            BLUE
        )

    back_button = pygame.Rect(
        SCREEN_WIDTH // 2 - 110,
        520,
        220,
        55
    )

    draw_button(
        "返回开始界面",
        back_button,
        (120, 125, 135)
    )


# =========================
# 事件处理
# =========================

def handle_mouse_click(position):
    """
    根据当前界面处理鼠标点击。
    """
    global game_state

    x, y = position

    if game_state == START:
        start_button = pygame.Rect(
            SCREEN_WIDTH // 2 - 100,
            350,
            200,
            60
        )

        if start_button.collidepoint(position):
            start_game()

    elif game_state == PLAYING:
        restart_button = pygame.Rect(
            SCREEN_WIDTH - 180,
            75,
            140,
            42
        )

        if restart_button.collidepoint(position):
            restart_current_level()
            return

        handle_arrow_click(position)

    elif game_state == RESULT:
        back_button = pygame.Rect(
            SCREEN_WIDTH // 2 - 110,
            520,
            220,
            55
        )

        if back_button.collidepoint(position):
            game_state = START
            return

        if result_is_win:
            if current_level_index + 1 < len(LEVELS):
                next_button = pygame.Rect(
                    SCREEN_WIDTH // 2 - 110,
                    350,
                    220,
                    60
                )

                if next_button.collidepoint(position):
                    go_to_next_level()
            else:
                restart_button = pygame.Rect(
                    SCREEN_WIDTH // 2 - 110,
                    430,
                    220,
                    60
                )

                if restart_button.collidepoint(position):
                    start_game()
        else:
            restart_button = pygame.Rect(
                SCREEN_WIDTH // 2 - 110,
                350,
                220,
                60
            )

            if restart_button.collidepoint(position):
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
