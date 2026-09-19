"""检查 main.py 里的关卡是否都能通关（不需要安装 pygame）。

用法：
    python tools/check_levels.py

规则与游戏里的 is_blocked() 完全一致：箭头沿自己的方向前进，途中只要还有别的
箭头就被挡住；被挡住的箭头点不了（点了只会掉一条命，棋盘不变）。因此如果同一行
或同一列上有两个箭头互相指着对方，两边都会被永久挡住，这一关就无解。

脚本用广度优先搜索穷举所有点击顺序，判断每一关能不能清空；如果无解，会给出卡住
的残局和互相挡住的箭头对。
"""

import ast
import sys
from collections import deque
from pathlib import Path

DELTA = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}
DEFAULT_MAIN = Path(__file__).resolve().parent.parent / "main.py"


def load_levels(path):
    """从 main.py 中取出 ROWS / COLS / LEVELS，不执行这个文件。"""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))

    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            name = getattr(node.targets[0], "id", None)
            if name in {"ROWS", "COLS", "LEVELS"}:
                values[name] = ast.literal_eval(node.value)

    if "LEVELS" not in values:
        raise SystemExit(f"在 {path} 里找不到 LEVELS")

    return values.get("ROWS", 6), values.get("COLS", 6), values["LEVELS"]


def is_blocked(board, position, rows, cols):
    row, col = position
    row_change, col_change = DELTA[board[position]]

    next_row = row + row_change
    next_col = col + col_change

    while 0 <= next_row < rows and 0 <= next_col < cols:
        if (next_row, next_col) in board:
            return True

        next_row += row_change
        next_col += col_change

    return False


def solve(level, rows, cols):
    """返回（一条可以通关的点击顺序，卡住时的残局）。"""
    start = frozenset(level.items())
    seen = {start}
    queue = deque([(start, [])])
    best_stuck = None

    while queue:
        state, path = queue.popleft()
        board = dict(state)

        if not state:
            return path, None

        moves = [
            position for position in sorted(board)
            if not is_blocked(board, position, rows, cols)
        ]

        if not moves and (best_stuck is None or len(state) < len(best_stuck)):
            best_stuck = board

        for position in moves:
            nxt = frozenset((p, d) for p, d in state if p != position)
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, path + [position]))

    return None, best_stuck


def find_facing_pairs(board, rows, cols):
    """找出同一行或同一列上互相指着对方、必然锁死的箭头对。"""
    opposite = {"U": "D", "D": "U", "L": "R", "R": "L"}
    pairs = []

    for position, direction in sorted(board.items()):
        row, col = position
        row_change, col_change = DELTA[direction]

        next_row = row + row_change
        next_col = col + col_change

        while 0 <= next_row < rows and 0 <= next_col < cols:
            other = (next_row, next_col)
            if (other in board and board[other] == opposite[direction]
                    and position < other):
                pairs.append((position, other))

            next_row += row_change
            next_col += col_change

    return pairs


def main(argv):
    path = Path(argv[1]) if len(argv) > 1 else DEFAULT_MAIN
    rows, cols, levels = load_levels(path)

    unsolvable = 0
    for index, level in enumerate(levels, start=1):
        order, stuck = solve(level, rows, cols)

        if order is None:
            unsolvable += 1
            print(f"第 {index} 关：无解  最多只能消掉 "
                  f"{len(level) - len(stuck)}/{len(level)} 个箭头")
            print(f"    卡住的箭头：{stuck}")
            for a, b in find_facing_pairs(stuck, rows, cols):
                print(f"    {a} 和 {b} 正对着对方，互相阻挡")
        else:
            print(f"第 {index} 关：可解  参考点击顺序："
                  + " -> ".join(str(p) for p in order))

    print(f"\n共 {len(levels)} 关，无解 {unsolvable} 关")
    return 1 if unsolvable else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
