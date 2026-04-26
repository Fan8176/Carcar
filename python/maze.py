import pandas as pd
import queue
import numpy as np
from enum import IntEnum
from typing import List, Tuple, Dict
from node import Direction, Node
from algorithms import dir_diff, build_cost_matrix, TSPBitmaskDP


# ─────────────────────────────────────────────
#  可調整參數
# ─────────────────────────────────────────────
DEFAULT_MOVE_TIME  = 1.0   # 偵測到節點後直行到下個節點的時間
DEFAULT_TURN_TIME  = 1.5   # 偵測到節點後轉彎後到下個節點的時間
DEFAULT_UTURN_TIME = 3.0   # 偵測到節點後迴轉再直行回原節點的時間


class Action(IntEnum):
    ADVANCE      = 1  # 'f'
    U_TURN       = 2  # 'b'
    TURN_RIGHT   = 3  # 'r'
    TURN_LEFT    = 4  # 'l'
    HALT         = 5  # 's'
    U_TURN_RIGHT = 6  # 'n'  端點向右迴轉
    U_TURN_LEFT  = 7  # 'u'  端點向左迴轉


class Maze:
    def __init__(self, filepath: str):
        self.raw_data = pd.read_csv(filepath)
        self.nodes:     List[Node]      = []
        self.node_dict: Dict[int, Node] = {}

        for index in self.raw_data.iloc[:, 0]:
            node = Node(int(index))
            self.nodes.append(node)
            self.node_dict[int(index)] = node

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

        # BFS 推算每個節點的 (row, col) 座標
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

        # 地圖幾何中心（端點迴轉方向判斷用）
        self._map_center = self._compute_map_center()

    # ──────────────────────────────────────────
    #  查詢
    # ──────────────────────────────────────────

    def get_treasure_nodes(self) -> List[Node]:
        """degree == 1 的節點為端點"""
        return [n for n in self.nodes if len(n.get_successors()) == 1]

    # ──────────────────────────────────────────
    #  BFS 最短路徑
    # ──────────────────────────────────────────

    def _bfs(self, node_from: Node, node_to: Node) -> List[Node]:
        """回傳從 node_from 到 node_to 的最短路徑節點列表"""
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
    #  對外介面：遍歷所有端點的最短時間路徑
    # ──────────────────────────────────────────

    def get_shortest_traversal_path(
        self,
        start_idx:  int,
        move_time:  float = DEFAULT_MOVE_TIME,
        uturn_time: float = DEFAULT_UTURN_TIME,
        turn_time:  float = DEFAULT_TURN_TIME,
    ) -> Tuple[str, List[int]]:
        """
        使用 TSPBitmaskDP 找出遍歷所有端點的最短時間路徑。
        回傳：(cmd, node_index_path)
        """
        start_node = self.node_dict[start_idx]
        treasures  = self.get_treasure_nodes()
        if start_node not in treasures:
            treasures.insert(0, start_node)

        targets = [start_node] + [t for t in treasures if t.index != start_idx]
        n       = len(targets)

        if n == 1:
            return "s", [start_idx]

        # 預計算所有端點間的 BFS 路徑片段
        path_segments: Dict = {}
        for i in range(n):
            for j in range(n):
                if i != j:
                    path_segments[(i, j)] = self._bfs(targets[i], targets[j])

        cost_matrix = build_cost_matrix(
            targets, path_segments, move_time, uturn_time, turn_time
        )

        visit_order = TSPBitmaskDP().solve(targets, cost_matrix)

        # 拼接完整 Node 路徑
        full_path: List[Node] = []
        for k in range(len(visit_order) - 1):
            u, v = visit_order[k], visit_order[k + 1]
            seg  = path_segments.get((u, v), [])
            if seg:
                full_path.extend(seg if not full_path else seg[1:])

        cmd = self.actions_to_str(self.getActions(full_path))
        return cmd, [node.index for node in full_path]

    # ──────────────────────────────────────────
    #  端點迴轉方向判斷
    # ──────────────────────────────────────────

    def _compute_map_center(self) -> Tuple[float, float]:
        rs = [r for r, c in self.coords.values()]
        cs = [c for r, c in self.coords.values()]
        return sum(rs) / len(rs), sum(cs) / len(cs)

    def _uturn_actions(self, node: Node, arriving_dir: Direction) -> List[Action]:
        """
        在端點做迴轉時，選擇朝向地圖中心那側旋轉。
        用 2D 叉積判斷：d × v = dx·dr − dy·dc
          > 0 → 中心在右 → U_TURN_RIGHT ('n')
          ≤ 0 → 中心在左 → U_TURN_LEFT  ('u')
        """
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
        if diff == 0:
            return Action.ADVANCE, target_dir
        elif diff == 1:
            return Action.TURN_RIGHT, target_dir
        elif diff == 2:
            return Action.U_TURN, target_dir
        else:
            return Action.TURN_LEFT, target_dir

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