"""
algorithms.py — 循跡自走車路徑規劃演算法

功能：找出遍歷所有端點的最短時間路徑（TSP Bitmask DP）
"""

import numpy as np
from typing import List, Dict

from node import Direction, Node


# ─────────────────────────────────────────────────────────────────────
#  基礎工具
# ─────────────────────────────────────────────────────────────────────

_DIR_ORDER = {
    Direction.NORTH: 0,
    Direction.EAST:  1,
    Direction.SOUTH: 2,
    Direction.WEST:  3,
}


def dir_diff(from_dir: Direction, to_dir: Direction) -> int:
    """
    計算從 from_dir 到 to_dir 的旋轉步數。
    回傳：0=直行, 1=右轉90°, 2=迴轉180°, 3=左轉90°
    """
    return (_DIR_ORDER[to_dir] - _DIR_ORDER[from_dir]) % 4


def _step_cost(diff: int, move_time: float,
               turn_time: float, uturn_time: float) -> float:
    if diff == 0:
        return move_time
    elif diff == 2:
        return uturn_time
    else:
        return turn_time


# ─────────────────────────────────────────────────────────────────────
#  成本矩陣
# ─────────────────────────────────────────────────────────────────────

def build_cost_matrix(
    targets:       List[Node],
    path_segments: Dict,
    move_time:     float,
    uturn_time:    float,
    turn_time:     float,
) -> np.ndarray:
    """
    建立 n×n 時間成本矩陣，cost[i][j] = 從 targets[i] 出發到 targets[j] 的最短時間。

    所有 targets 都是 degree=1 的端點，出發方向固定：
      i == 0（起點）：第一個動作為 ADVANCE，出發成本 = move_time
      i >  0（寶藏）：車子抵達後自動迴轉，出發成本 = uturn_time
    從 path[1] 起逐節點用 dir_diff 計算後續成本。
    """
    n    = len(targets)
    cost = np.full((n, n), np.inf)
    np.fill_diagonal(cost, 0.0)

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            path = path_segments.get((i, j), [])
            if len(path) < 2:
                continue

            t       = move_time if i == 0 else uturn_time
            cur_dir = path[0].get_direction(path[1])

            for k in range(1, len(path) - 1):
                nxt_dir = path[k].get_direction(path[k + 1])
                t      += _step_cost(dir_diff(cur_dir, nxt_dir),
                                     move_time, turn_time, uturn_time)
                cur_dir = nxt_dir

            cost[i][j] = t

    return cost


# ─────────────────────────────────────────────────────────────────────
#  TSP Bitmask DP
# ─────────────────────────────────────────────────────────────────────

class TSPBitmaskDP:
    """
    Bitmask DP 找出遍歷所有端點的最短時間路徑。
    複雜度：O(2^n * n^2)，n <= 20 時可行。
    """

    def solve(
        self,
        targets:     List[Node],
        cost_matrix: np.ndarray,
    ) -> List[int]:
        """
        回傳 target index 的拜訪順序（從 0 開始）。
        """
        n   = len(targets)
        INF = float('inf')

        dp     = [[INF] * n for _ in range(1 << n)]
        parent = [[-1]  * n for _ in range(1 << n)]
        dp[1][0] = 0.0

        for mask in range(1 << n):
            for i in range(n):
                if dp[mask][i] == INF or not (mask >> i & 1):
                    continue
                for j in range(n):
                    if mask >> j & 1:
                        continue
                    c = cost_matrix[i][j]
                    if c == INF:
                        continue
                    new_mask = mask | (1 << j)
                    new_time = dp[mask][i] + c
                    if new_time < dp[new_mask][j]:
                        dp[new_mask][j] = new_time
                        parent[new_mask][j] = i

        full     = (1 << n) - 1
        best_end = min(range(n), key=lambda i: dp[full][i])

        path, mask, cur = [], full, best_end
        while cur != -1:
            path.append(cur)
            prev = parent[mask][cur]
            mask ^= (1 << cur)
            cur   = prev

        return path[::-1]