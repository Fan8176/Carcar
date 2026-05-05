import logging
import pandas as pd
import queue
import numpy as np
from enum import IntEnum
from typing import List, Tuple, Dict
from node import Direction, Node
from algorithms import dir_diff, build_cost_matrix, TSPBitmaskDP

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  可調整參數（對齊實測值）
# ─────────────────────────────────────────────
DEFAULT_MOVE_TIME  = 1.06
DEFAULT_TURN_TIME  = 1.02
DEFAULT_UTURN_TIME = 1.20


class Action(IntEnum):
    ADVANCE      = 1  # 'f'
    U_TURN       = 2  # 'b'
    TURN_RIGHT   = 3  # 'r'
    TURN_LEFT    = 4  # 'l'
    HALT         = 5  # 's'
    U_TURN_RIGHT = 6  # 'n'
    U_TURN_LEFT  = 7  # 'u'


class Maze:
    def __init__(self, filepath: str):
        self.raw_data = pd.read_csv(filepath)
        self.nodes:     List[Node]      = []
        self.node_dict: Dict[int, Node] = {}

        for index in self.raw_data.iloc[:, 0]:
            node = Node(int(index))
            self.nodes.append(node)
            self.node_dict[int(index)] = node

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

        dir_delta = {
            Direction.NORTH: (-1,  0),
            Direction.SOUTH: ( 1,  0),
            Direction.WEST:  ( 0, -1),
            Direction.EAST:  ( 0,  1),
        }
        first_idx = self.nodes[0].index
        self.coords: Dict[int, Tuple[int, int]] = {first_idx: (0, 0)}
        bfs_q = queue.Queue()
        bfs_q.put(first_idx)
        while not bfs_q.empty():
            cur_idx = bfs_q.get()
            r, c = self.coords[cur_idx]
            for nb_node, direction, _ in self.node_dict[cur_idx].get_successors():
                if nb_node.index not in self.coords:
                    dr, dc = dir_delta[direction]
                    self.coords[nb_node.index] = (r + dr, c + dc)
                    bfs_q.put(nb_node.index)

        self._map_center = self._compute_map_center()

    # ──────────────────────────────────────────
    #  查詢
    # ──────────────────────────────────────────

    def get_treasure_nodes(self) -> List[Node]:
        return [n for n in self.nodes if len(n.get_successors()) == 1]

    # ──────────────────────────────────────────
    #  BFS
    # ──────────────────────────────────────────

    def _bfs(self, node_from: Node, node_to: Node) -> List[Node]:
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
        path, cur = [], end
        while cur is not None:
            path.append(self.node_dict[cur])
            cur = record[cur]
        return path[::-1]

    # ──────────────────────────────────────────
    #  內部共用：前處理
    # ──────────────────────────────────────────

    def _prepare(
        self,
        start_idx:  int,
        move_time:  float,
        uturn_time: float,
        turn_time:  float,
    ) -> Tuple[List[Node], np.ndarray, Dict]:
        start_node = self.node_dict[start_idx]
        treasures  = self.get_treasure_nodes()
        targets    = [start_node] + [t for t in treasures if t.index != start_idx]
        n          = len(targets)

        path_segments: Dict = {}
        for i in range(n):
            for j in range(n):
                if i != j:
                    path_segments[(i, j)] = self._bfs(targets[i], targets[j])

        cost_matrix = build_cost_matrix(
            targets, path_segments, move_time, uturn_time, turn_time
        )
        return targets, cost_matrix, path_segments

    def _tsp_on_subset(
        self,
        subset:        List[int],
        targets:       List[Node],
        cost_matrix:   np.ndarray,
        path_segments: Dict,
        move_time:     float,
        turn_time:     float,
        uturn_time:    float,
    ) -> Tuple[str, List[Node], float, List[int]]:
        sub_cost     = np.array([[cost_matrix[i][j] for j in subset] for i in subset])
        sub_targets  = [targets[i] for i in subset]
        local_order  = TSPBitmaskDP().solve(sub_targets, sub_cost)
        global_order = [subset[k] for k in local_order]
        return self._build_path_from_order(
            global_order, path_segments, move_time, turn_time, uturn_time
        )

    def _build_path_from_order(
        self,
        global_order:  List[int],
        path_segments: Dict,
        move_time:     float,
        turn_time:     float,
        uturn_time:    float,
    ) -> Tuple[str, List[Node], float, List[int]]:
        full_path: List[Node] = []
        for k in range(len(global_order) - 1):
            u, v = global_order[k], global_order[k + 1]
            seg  = path_segments.get((u, v), [])
            if seg:
                full_path.extend(seg if not full_path else seg[1:])
        cmd        = self.actions_to_str(self.getActions(full_path))
        total_time = self.calc_total_time(cmd, move_time, turn_time, uturn_time)
        return cmd, full_path, total_time, global_order

    def _order_tail(
        self,
        last_ti:     int,
        dropped_ti:  List[int],
        cost_matrix: np.ndarray,
    ) -> List[int]:
        """
        從 last_ti 出發，對捨棄的端點做最近鄰貪婪排序。
        回傳捨棄端點的 global target index 順序。
        """
        remaining = list(dropped_ti)
        order     = []
        cur       = last_ti
        while remaining:
            # 選距離 cur 最近的端點
            next_ti = min(remaining, key=lambda j: cost_matrix[cur][j])
            order.append(next_ti)
            remaining.remove(next_ti)
            cur = next_ti
        return order

    # ──────────────────────────────────────────
    #  對外介面一：遍歷所有端點（無時間限制）
    # ──────────────────────────────────────────

    def get_shortest_traversal_path(
        self,
        start_idx:  int,
        move_time:  float = DEFAULT_MOVE_TIME,
        uturn_time: float = DEFAULT_UTURN_TIME,
        turn_time:  float = DEFAULT_TURN_TIME,
    ) -> Tuple[str, List[int], List[int], float]:
        """
        找出遍歷所有端點的最短時間路徑。
        回傳：(cmd, node_path, endpoint_order, total_time)
        """
        if start_idx not in self.node_dict:
            log.error(f"起點 {start_idx} 不存在，可用節點：{sorted(self.node_dict.keys())}")
            return "", [], [], 0.0

        targets, cost_matrix, path_segments = self._prepare(
            start_idx, move_time, uturn_time, turn_time
        )
        if len(targets) == 1:
            return "s", [start_idx], [start_idx], 0.0

        cmd, full_path, total_time, global_order = self._tsp_on_subset(
            list(range(len(targets))), targets, cost_matrix,
            path_segments, move_time, turn_time, uturn_time
        )
        endpoint_order = [targets[i].index for i in global_order]
        return cmd, [n.index for n in full_path], endpoint_order, total_time

    # ──────────────────────────────────────────
    #  對外介面二：時間限制內最佳化路徑
    # ──────────────────────────────────────────

    def get_time_limited_path(
        self,
        start_idx:  int,
        time_limit: float,
        move_time:  float = DEFAULT_MOVE_TIME,
        uturn_time: float = DEFAULT_UTURN_TIME,
        turn_time:  float = DEFAULT_TURN_TIME,
    ) -> Tuple[str, List[int], List[int], float, float]:
        """
        在 time_limit 內找出最佳路徑，捨棄掉的端點接在最後面。

        回傳：(cmd, node_path, endpoint_order, time_base, time_with_tail)
          cmd            : 指令字串（含捨棄端點接尾）
          node_path      : 完整節點路徑（含捨棄端點接尾）
          endpoint_order : 端點拜訪順序（含捨棄端點接尾）
          time_base      : 不含捨棄端點的估計時長（保證 <= time_limit）
          time_with_tail : 含捨棄端點接尾的估計時長（可能超過 time_limit）
        """
        if start_idx not in self.node_dict:
            log.error(f"起點 {start_idx} 不存在，可用節點：{sorted(self.node_dict.keys())}")
            return "", [], [], 0.0, 0.0

        targets, cost_matrix, path_segments = self._prepare(
            start_idx, move_time, uturn_time, turn_time
        )
        n = len(targets)
        if n == 1:
            return "s", [start_idx], [start_idx], 0.0, 0.0

        sr, sc      = self.coords[start_idx]
        active_ti   = list(range(1, n))
        dropped_ti  = []   # 依捨棄順序記錄（最先捨棄的在前）

        while True:
            subset = [0] + active_ti
            cmd, full_path, total_time, global_order = self._tsp_on_subset(
                subset, targets, cost_matrix,
                path_segments, move_time, turn_time, uturn_time
            )

            if total_time <= time_limit or len(active_ti) == 0:
                # ── 找到最佳解，把捨棄端點以最近鄰排序接到最後 ──
                base_endpoint_order = [targets[i].index for i in global_order]
                time_base           = total_time

                if not dropped_ti:
                    # 沒有捨棄端點，兩個時間相同
                    return (
                        cmd,
                        [nd.index for nd in full_path],
                        base_endpoint_order,
                        time_base,
                        time_base,
                    )

                # 從最佳解的最後一個端點出發，排序捨棄端點
                last_ti    = global_order[-1]
                tail_order = self._order_tail(last_ti, dropped_ti, cost_matrix)
                full_order = global_order + tail_order

                _, full_path_with_tail, time_with_tail, _ = self._build_path_from_order(
                    full_order, path_segments, move_time, turn_time, uturn_time
                )
                endpoint_order_with_tail = [targets[i].index for i in full_order]

                log.info(
                    f"最佳解端點：{base_endpoint_order}，估計 {time_base:.2f}s\n"
                    f"含捨棄端點：{endpoint_order_with_tail}，估計 {time_with_tail:.2f}s"
                )
                return (
                    self.actions_to_str(self.getActions(full_path_with_tail)),
                    [nd.index for nd in full_path_with_tail],
                    endpoint_order_with_tail,
                    time_base,
                    time_with_tail,
                )

            # ── 找最不值得拜訪的端點 ──
            worst_ti    = None
            worst_ratio = -1.0

            for ti in active_ti:
                r, c  = self.coords[targets[ti].index]
                score = abs(r - sr) + abs(c - sc)
                remaining = [0] + [x for x in active_ti if x != ti]
                _, _, time_without, _ = self._tsp_on_subset(
                    remaining, targets, cost_matrix,
                    path_segments, move_time, turn_time, uturn_time
                )
                time_saved = total_time - time_without
                ratio      = time_saved / score if score > 0 else float('inf')
                if ratio > worst_ratio:
                    worst_ratio = ratio
                    worst_ti    = ti

            # ── 試著把最差端點移到最後 ──
            remaining_ti = [0] + [x for x in active_ti if x != worst_ti]
            sub_cost     = np.array([[cost_matrix[i][j] for j in remaining_ti]
                                     for i in remaining_ti])
            local_order  = TSPBitmaskDP().solve(
                [targets[i] for i in remaining_ti], sub_cost
            )
            global_order_with_tail = [remaining_ti[k] for k in local_order] + [worst_ti]
            _, path_tail, time_tail, _ = self._build_path_from_order(
                global_order_with_tail, path_segments,
                move_time, turn_time, uturn_time
            )

            if time_tail <= time_limit:
                # 全部端點都塞得進去，worst 排最後即可，無捨棄
                endpoint_order = [targets[i].index for i in global_order_with_tail]
                return (
                    self.actions_to_str(self.getActions(path_tail)),
                    [nd.index for nd in path_tail],
                    endpoint_order,
                    time_tail,
                    time_tail,
                )

            # ── 真的捨棄 worst ──
            active_ti.remove(worst_ti)
            dropped_ti.append(worst_ti)

    # ──────────────────────────────────────────
    #  端點迴轉方向判斷
    # ──────────────────────────────────────────

    def _compute_map_center(self) -> Tuple[float, float]:
        rs = [r for r, c in self.coords.values()]
        cs = [c for r, c in self.coords.values()]
        return sum(rs) / len(rs), sum(cs) / len(cs)

    def _uturn_actions(self, node: Node, arriving_dir: Direction) -> List[Action]:
        dir_vec = {
            Direction.NORTH: ( 0, -1),
            Direction.SOUTH: ( 0,  1),
            Direction.EAST:  ( 1,  0),
            Direction.WEST:  (-1,  0),
        }
        center_r, center_c = self._map_center
        node_r,   node_c   = self.coords[node.index]
        dr = center_r - node_r
        dc = center_c - node_c
        dx_d, dy_d = dir_vec[arriving_dir]
        cross = dx_d * dr - dy_d * dc
        return [Action.U_TURN_RIGHT] if cross > 0 else [Action.U_TURN_LEFT]

    # ──────────────────────────────────────────
    #  Action 轉換
    # ──────────────────────────────────────────

    def _get_action(
        self, car_dir: Direction, node_from: Node, node_to: Node
    ) -> Tuple[Action, Direction]:
        target_dir = node_from.get_direction(node_to)
        diff = dir_diff(car_dir, target_dir)
        if diff == 0:   return Action.ADVANCE,    target_dir
        elif diff == 1: return Action.TURN_RIGHT,  target_dir
        elif diff == 2: return Action.U_TURN,      target_dir
        else:           return Action.TURN_LEFT,   target_dir

    def getActions(self, nodes: List[Node]) -> List[Action]:
        if not nodes or len(nodes) < 2:
            return []
        actions     = [Action.ADVANCE]
        cur_car_dir = nodes[0].get_direction(nodes[1])
        for i in range(1, len(nodes) - 1):
            arriving_dir        = cur_car_dir
            action, cur_car_dir = self._get_action(cur_car_dir, nodes[i], nodes[i + 1])
            if action == Action.U_TURN and len(nodes[i].get_successors()) == 1:
                actions.extend(self._uturn_actions(nodes[i], arriving_dir))
            else:
                actions.append(action)
        return actions

    @staticmethod
    def actions_to_str(actions: List[Action]) -> str:
        cmd_map = {
            Action.ADVANCE:      'f',
            Action.U_TURN:       'b',
            Action.TURN_RIGHT:   'r',
            Action.TURN_LEFT:    'l',
            Action.HALT:         's',
            Action.U_TURN_RIGHT: 'n',
            Action.U_TURN_LEFT:  'u',
        }
        return "".join(cmd_map[a] for a in actions)

    @staticmethod
    def calc_total_time(
        cmd:        str,
        move_time:  float = DEFAULT_MOVE_TIME,
        turn_time:  float = DEFAULT_TURN_TIME,
        uturn_time: float = DEFAULT_UTURN_TIME,
    ) -> float:
        char_time = {
            'f': move_time,
            'r': turn_time,  'l': turn_time,
            'b': uturn_time, 'n': uturn_time, 'u': uturn_time,
            's': 0.0,
        }
        return sum(char_time.get(c, 0.0) for c in cmd)