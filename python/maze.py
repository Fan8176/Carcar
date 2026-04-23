import pandas as pd
import logging
import queue
import numpy as np
from enum import IntEnum
from typing import List, Tuple, Dict, Optional
from node import Direction, Node

log = logging.getLogger(__name__)


class Action(IntEnum):
    ADVANCE = 1     # 'f'
    U_TURN = 2      # 'b'
    TURN_RIGHT = 3  # 'r'
    TURN_LEFT = 4   # 'l'
    HALT = 5        # 's'


# ─────────────────────────────────────────────
#  可調整的時間參數（單位：秒）
# ─────────────────────────────────────────────
DEFAULT_TIME_LIMIT      = 60.0   # 總時間限制
DEFAULT_MOVE_TIME       = 1.0    # 每格直行時間（待實測後替換）
DEFAULT_UTURN_TIME      = 3.0    # 抵達端點迴轉時間（待實測後替換）
DEFAULT_TURN_TIME       = 1.5    # 一般轉彎時間（待實測後替換）

# ─────────────────────────────────────────────
#  分數權重參數
# ─────────────────────────────────────────────
# score_power 控制分數的非線性縮放：weighted_score = raw_score ^ score_power
#   score_power = 1.0  → 線性（不調整，原始曼哈頓距離）
#   score_power > 1.0  → 高分端點優勢放大，低分端點更不值得繞遠路
#   score_power < 1.0  → 分數差距壓縮，低分端點相對更值得拜訪
#   score_power = 0.0  → 所有端點視為等值（純最多數量策略）
DEFAULT_SCORE_POWER     = 2.0


class Maze:
    def __init__(self, filepath: str):
        # 1. 讀取 CSV
        self.raw_data = pd.read_csv(filepath)
        self.nodes: List[Node] = []
        self.node_dict: Dict[int, Node] = {}

        # 2. 建立所有 Node 物件
        for index in self.raw_data.iloc[:, 0]:
            new_node = Node(int(index))
            self.nodes.append(new_node)
            self.node_dict[int(index)] = new_node

        # 3. 建立鄰接關係，同時讀入距離欄位 (ND, SD, WD, ED)
        # CSV 格式: index, North, South, West, East, ND, SD, WD, ED
        dir_col_pairs = [
            (Direction.NORTH, 1, 5),
            (Direction.SOUTH, 2, 6),
            (Direction.WEST,  3, 7),
            (Direction.EAST,  4, 8),
        ]
        for _, row in self.raw_data.iterrows():
            cur_node = self.node_dict[int(row.iloc[0])]
            for direction, neighbor_col, dist_col in dir_col_pairs:
                neighbor_val = row.iloc[neighbor_col]
                dist_val     = row.iloc[dist_col]
                if pd.notna(neighbor_val) and neighbor_val != "":
                    length = int(dist_val) if pd.notna(dist_val) else 1
                    cur_node.set_successor(
                        self.node_dict[int(neighbor_val)], direction, length
                    )

    # ──────────────────────────────────────────
    #  基本查詢
    # ──────────────────────────────────────────

    def get_node_dict(self) -> Dict[int, Node]:
        return self.node_dict

    def get_treasure_nodes(self) -> List[Node]:
        """degree == 1 的節點為端點（寶藏點）"""
        return [n for n in self.nodes if len(n.get_successors()) == 1]

    def _manhattan(self, a: Node, b: Node) -> float:
        """以 1-based index 換算 (row, col) 後計算曼哈頓距離（地圖寬度 8）"""
        COLS = 8
        ai, bi = a.index - 1, b.index - 1
        return abs(ai // COLS - bi // COLS) + abs(ai % COLS - bi % COLS)

    # ──────────────────────────────────────────
    #  BFS：回傳最短路徑節點列表
    # ──────────────────────────────────────────

    def BFS_2(self, node_from: Node, node_to: Node) -> List[Node]:
        start, end = node_from.index, node_to.index
        if start == end:
            return [node_from]

        q = queue.Queue()
        q.put(start)
        record = {start: None}

        while not q.empty():
            cur_idx = q.get()
            if cur_idx == end:
                break
            for neighbor, _, _ in self.node_dict[cur_idx].get_successors():
                if neighbor.index not in record:
                    record[neighbor.index] = cur_idx
                    q.put(neighbor.index)

        if end not in record:
            return []

        path = []
        cur = end
        while cur is not None:
            path.append(self.node_dict[cur])
            cur = record[cur]
        return path[::-1]

    # ──────────────────────────────────────────
    #  預計算：時間成本矩陣
    # ──────────────────────────────────────────

    def _build_cost_matrix(
        self,
        targets: List[Node],
        move_time: float,
        uturn_time: float,
        turn_time: float,
    ) -> Tuple[np.ndarray, Dict]:
        """
        回傳：
          cost_matrix[i][j] = 從 targets[i] 移動到 targets[j] 所需總秒數
                               （含在 j 的迴轉成本，若 j 為端點）
          path_segments[(i,j)] = BFS 路徑節點列表
        """
        n = len(targets)
        cost_matrix   = np.zeros((n, n))
        path_segments = {}

        for i in range(n):
            for j in range(i + 1, n):
                path = self.BFS_2(targets[i], targets[j])
                if not path:
                    cost_matrix[i][j] = cost_matrix[j][i] = float('inf')
                    path_segments[(i, j)] = []
                    path_segments[(j, i)] = []
                    continue

                # 計算路徑上的轉彎動作數與迴轉數
                travel_time = self._path_travel_time(
                    path, move_time, uturn_time, turn_time
                )

                # 抵達端點 j 時需要迴轉（以便離開）
                uturn_cost_j = uturn_time if len(targets[j].get_successors()) == 1 else 0
                # 同理，若 i 是端點且不是起點 (i>0)，離開 i 時已計入先前 uturn
                # 這裡只在「抵達 j」時加 uturn
                total = travel_time + uturn_cost_j

                cost_matrix[i][j] = cost_matrix[j][i] = total
                path_segments[(i, j)] = path
                path_segments[(j, i)] = path[::-1]

        return cost_matrix, path_segments

    def _path_travel_time(
        self,
        path: List[Node],
        move_time: float,
        uturn_time: float,
        turn_time: float,
    ) -> float:
        """計算走完一段路徑的時間（直行 + 轉彎），不含終點迴轉"""
        if len(path) < 2:
            return 0.0

        # 每條 edge 的移動時間：取 successor 中存的 distance * move_time
        total = 0.0
        for k in range(len(path) - 1):
            cur, nxt = path[k], path[k + 1]
            dist = 1
            for succ, _, d in cur.get_successors():
                if succ.index == nxt.index:
                    dist = d
                    break
            total += dist * move_time

        # 轉彎成本（第一步不算，因為車子已對準方向）
        if len(path) >= 3:
            # 初始行進方向
            cur_dir = path[0].get_direction(path[1])
            for k in range(1, len(path) - 1):
                next_dir = path[k].get_direction(path[k + 1])
                if next_dir != cur_dir:
                    diff = self._dir_diff(cur_dir, next_dir)
                    if diff == 2:
                        total += uturn_time
                    else:
                        total += turn_time
                cur_dir = next_dir

        return total

    @staticmethod
    def _dir_diff(d_from: Direction, d_to: Direction) -> int:
        """回傳順時針差值 0/1/2/3"""
        order = {Direction.NORTH: 0, Direction.EAST: 1,
                 Direction.SOUTH: 2, Direction.WEST: 3}
        return (order[d_to] - order[d_from]) % 4

    # ──────────────────────────────────────────
    #  核心：Branch & Bound 最大分數搜尋
    # ──────────────────────────────────────────

    def get_max_score_path(
        self,
        start_idx:   int,
        time_limit:  float = DEFAULT_TIME_LIMIT,
        move_time:   float = DEFAULT_MOVE_TIME,
        uturn_time:  float = DEFAULT_UTURN_TIME,
        turn_time:   float = DEFAULT_TURN_TIME,
        score_power: float = DEFAULT_SCORE_POWER,
    ) -> Tuple[float, List[int]]:
        """
        在時間限制內，從 start_idx 出發，最大化拜訪端點的加權分數總和。

        加權分數計算：
          raw_score       = 端點與起點的曼哈頓距離
          weighted_score  = raw_score ^ score_power

          score_power = 1.0  → 原始線性分數（預設）
          score_power > 1.0  → 放大高分端點優勢，低分端點更不划算
          score_power < 1.0  → 壓縮分數差距，低分端點相對更值得拜訪
          score_power = 0.0  → 所有端點等值（最多數量策略）

        回傳：
          (best_weighted_score, node_index_path)
          best_weighted_score 為加權分數總和（float）
          node_index_path     為完整行走路徑的節點編號列表
        """
        if start_idx not in self.node_dict:
            log.error(f"Start index {start_idx} not in maze.")
            return 0.0, []

        start_node = self.node_dict[start_idx]
        treasures  = self.get_treasure_nodes()

        # 起點若不在端點清單則加入（題目保證起點是端點，保險起見）
        if start_node not in treasures:
            treasures.insert(0, start_node)

        # targets[0] = 起點，targets[1:] = 其他端點
        targets = [start_node] + [t for t in treasures if t.index != start_idx]
        n = len(targets)

        # ── 原始分數 & 加權分數 ──
        raw_scores      = [self._manhattan(start_node, t) for t in targets]
        raw_scores[0]   = 0.0   # 起點不計分

        def _apply_weight(raw: float) -> float:
            """raw_score ^ score_power（raw=0 恆回傳 0）"""
            if raw <= 0:
                return 0.0
            return raw ** score_power

        weighted_scores = [_apply_weight(s) for s in raw_scores]

        if n == 1:
            return 0.0, [start_idx]

        # 預計算成本矩陣與路徑片段
        cost_matrix, path_segments = self._build_cost_matrix(
            targets, move_time, uturn_time, turn_time
        )

        # 依「加權分數 / 到起點成本」排序，高 CP 值端點優先展開
        endpoint_indices = list(range(1, n))
        endpoint_indices.sort(
            key=lambda i: weighted_scores[i] / max(cost_matrix[0][i], 1e-9),
            reverse=True,
        )
        sorted_ep = endpoint_indices

        # ── Branch & Bound DFS（以加權分數為目標） ──
        best_score = [0.0]
        best_order = [[]]

        visited_init    = [False] * n
        visited_init[0] = True

        def dfs(
            cur_pos:   int,
            time_left: float,
            visited:   List[bool],
            cur_score: float,
            order:     List[int],
        ):
            if cur_score > best_score[0]:
                best_score[0] = cur_score
                best_order[0] = order[:]

            # 上界剪枝：剩餘加權分數全拿也贏不了 best → 剪掉
            remaining = sum(
                weighted_scores[i] for i in range(1, n) if not visited[i]
            )
            if cur_score + remaining <= best_score[0]:
                return

            for i in sorted_ep:
                if visited[i]:
                    continue
                t = cost_matrix[cur_pos][i]
                if t > time_left:
                    continue

                visited[i] = True
                order.append(i)
                dfs(i, time_left - t, visited,
                    cur_score + weighted_scores[i], order)
                order.pop()
                visited[i] = False

        dfs(0, time_limit, visited_init, 0.0, [0])

        # ── 拼接完整 Node 路徑 ──
        full_path:   List[Node] = []
        visit_order: List[int]  = best_order[0]

        for k in range(len(visit_order) - 1):
            u, v = visit_order[k], visit_order[k + 1]
            seg  = path_segments.get((u, v), [])
            if not seg:
                continue
            full_path.extend(seg if not full_path else seg[1:])

        if not full_path and visit_order:
            full_path = [targets[visit_order[0]]]

        node_index_path = [node.index for node in full_path]
        return best_score[0], node_index_path

    # ──────────────────────────────────────────
    #  原有功能保留：最短遍歷路徑（TSP Bitmask DP）
    # ──────────────────────────────────────────

    def navigate(
        self,
        start_idx:   int,
        time_limit:  float = DEFAULT_TIME_LIMIT,
        move_time:   float = DEFAULT_MOVE_TIME,
        uturn_time:  float = DEFAULT_UTURN_TIME,
        turn_time:   float = DEFAULT_TURN_TIME,
        score_power: float = DEFAULT_SCORE_POWER,
    ) -> Tuple[List[int], str]:
        """
        從 start_idx 出發，計算時間限制內的最佳路徑並轉為指令字串。
 
        回傳：(path, cmd)
          path: 節點編號列表 List[int]
          cmd:  指令字串 str（f/b/r/l/s）
        """
        _, path = self.get_max_score_path(
            start_idx   = start_idx,
            time_limit  = time_limit,
            move_time   = move_time,
            uturn_time  = uturn_time,
            turn_time   = turn_time,
            score_power = score_power,
        )
 
        if not path:
            return [], ""
        if len(path) == 1:
            return path, "s"
 
        node_path = [self.node_dict[i] for i in path]
        actions   = self.getActions(node_path)
        cmd       = self.actions_to_str(actions)
        return path, cmd
    
    def get_shortest_traversal_path(self, start_idx: int) -> Tuple[str, List[int]]:
        """使用 Bitmask DP 解 TSP，遍歷所有寶藏點（無時間限制版）"""
        if start_idx not in self.node_dict:
            log.error(f"Start index {start_idx} not in maze.")
            return "", []

        start_node = self.node_dict[start_idx]
        treasures  = self.get_treasure_nodes()
        targets    = [start_node] + [t for t in treasures if t.index != start_idx]
        n          = len(targets)

        if n == 1:
            return "s", [start_idx]

        dist_matrix   = np.zeros((n, n))
        path_segments = {}
        for i in range(n):
            for j in range(i + 1, n):
                path = self.BFS_2(targets[i], targets[j])
                d    = len(path) - 1
                dist_matrix[i][j] = dist_matrix[j][i] = d
                path_segments[(i, j)] = path
                path_segments[(j, i)] = path[::-1]

        dp = {(1 << 0, 0): (0, -1)}
        for mask in range(1, 1 << n):
            for u in range(n):
                if not (mask & (1 << u)) or (mask, u) not in dp:
                    continue
                curr_dist, _ = dp[(mask, u)]
                for v in range(n):
                    if mask & (1 << v):
                        continue
                    new_mask = mask | (1 << v)
                    new_dist = curr_dist + dist_matrix[u][v]
                    if (new_mask, v) not in dp or new_dist < dp[(new_mask, v)][0]:
                        dp[(new_mask, v)] = (new_dist, u)

        full_mask    = (1 << n) - 1
        best_last    = min(
            (i for i in range(n) if (full_mask, i) in dp),
            key=lambda i: dp[(full_mask, i)][0],
            default=-1,
        )

        order, cur_m, cur_p = [], full_mask, best_last
        while cur_p != -1:
            order.append(cur_p)
            prev_p = dp[(cur_m, cur_p)][1]
            cur_m ^= (1 << cur_p)
            cur_p  = prev_p
        order.reverse()

        full_node_path: List[Node] = []
        for i in range(len(order) - 1):
            seg = path_segments[(order[i], order[i + 1])]
            full_node_path.extend(seg if not full_node_path else seg[1:])

        actions = self.getActions(full_node_path)
        return self.actions_to_str(actions), [nd.index for nd in full_node_path]

    # ──────────────────────────────────────────
    #  Action 轉換（保持原有）
    # ──────────────────────────────────────────

    def getAction(self, car_dir: Direction, node_from: Node, node_to: Node):
        target_dir = node_from.get_direction(node_to)
        diff = self._dir_diff(car_dir, target_dir)
        if diff == 0:
            return Action.ADVANCE, target_dir
        elif diff == 1:
            return Action.TURN_RIGHT, target_dir
        elif diff == 2:
            return Action.U_TURN, target_dir
        elif diff == 3:
            return Action.TURN_LEFT, target_dir
        return None

    def getActions(self, nodes: List[Node]) -> List[Action]:
        if not nodes or len(nodes) < 2:
            return []
        actions     = [Action.ADVANCE]
        cur_car_dir = nodes[0].get_direction(nodes[1])
        for i in range(1, len(nodes) - 1):
            action, cur_car_dir = self.getAction(cur_car_dir, nodes[i], nodes[i + 1])
            actions.append(action)
        return actions

    @staticmethod
    def actions_to_str(actions: List[Action]) -> str:
        cmd_map = {
            Action.ADVANCE:    'f',
            Action.U_TURN:     'b',
            Action.TURN_RIGHT: 'r',
            Action.TURN_LEFT:  'l',
            Action.HALT:       's',
        }
        return "".join(cmd_map[a] for a in actions)