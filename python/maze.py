import pandas as pd
import logging
import queue
import numpy as np
from enum import IntEnum
from typing import List, Tuple, Dict
from node import Direction, Node

log = logging.getLogger(__name__)

class Action(IntEnum):
    ADVANCE = 1     # 'f'
    U_TURN = 2      # 'b'
    TURN_RIGHT = 3  # 'r'
    TURN_LEFT = 4   # 'l'
    HALT = 5        # 's'

class Maze:
    def __init__(self, filepath: str):
        # 1. 讀取 CSV
        self.raw_data = pd.read_csv(filepath)
        self.nodes = []
        self.node_dict = dict()

        # 2. 建立所有 Node 物件
        for index in self.raw_data.iloc[:, 0]:
            new_node = Node(int(index))
            self.nodes.append(new_node)
            self.node_dict[int(index)] = new_node

        # 3. 建立鄰接關係 (Successors)
        # CSV 格式預期: Index, North, South, West, East
        for _, row in self.raw_data.iterrows():
            cur_idx = int(row[0])
            cur_node = self.node_dict[cur_idx]
            
            # 依序檢查 N(1), S(2), W(3), E(4)
            directions = [Direction.NORTH, Direction.SOUTH, Direction.WEST, Direction.EAST]
            for i, dir_enum in enumerate(directions, 1):
                neighbor = row[i]
                if pd.notna(neighbor) and neighbor != "":
                    cur_node.set_successor(self.node_dict[int(neighbor)], dir_enum)

    def get_node_dict(self) -> Dict[int, Node]:
        """供外部查詢節點物件"""
        return self.node_dict

    def get_treasure_nodes(self) -> List[Node]:
        """
        自動辨認寶藏點：
        根據定義，相鄰方格只有一個的端點（degree == 1）即為寶藏點。
        """
        return [node for node in self.nodes if len(node.get_successors()) == 1]

    def BFS_2(self, node_from: Node, node_to: Node) -> List[Node]:
        """給定兩點，回傳最短路徑的 Node 列表"""
        start_node = node_from.index
        end_node = node_to.index
        
        if start_node == end_node:
            return [node_from]
        
        q = queue.Queue()
        q.put(start_node)
        
        # record[current] = parent (用來回溯路徑)
        record = {start_node: None}
        
        found = False
        while not q.empty():
            cur_idx = q.get()
            if cur_idx == end_node:
                found = True
                break
            
            cur_node = self.node_dict[cur_idx]
            for neighbor_node, _, _ in cur_node.get_successors():
                if neighbor_node.index not in record:
                    record[neighbor_node.index] = cur_idx
                    q.put(neighbor_node.index)
        
        if not found:
            return []

        # 回溯路徑
        path_nodes = []
        curr = end_node
        while curr is not None:
            path_nodes.append(self.node_dict[curr])
            curr = record[curr]
        
        return path_nodes[::-1]

    def get_shortest_traversal_path(self, start_idx: int) -> Tuple[str, List[int]]:
        """
        核心演算法：使用 Bitmask DP 解決 TSP 問題，遍歷所有寶藏點。
        回傳：(指令字串, 節點編號列表)
        """
        if start_idx not in self.node_dict:
            log.error(f"Start index {start_idx} not in maze.")
            return "", []

        start_node = self.node_dict[start_idx]
        treasures = self.get_treasure_nodes()
        
        # 將起點與寶藏點整合，並移除重複點（若起點本身是寶藏點）
        targets = [start_node] + [t for t in treasures if t.index != start_idx]
        n = len(targets)
        
        if n == 1: # 沒有其他寶藏點
            return "s", [start_idx]

        # 1. 預計算點對點距離矩陣
        dist_matrix = np.zeros((n, n))
        path_segments = {}
        for i in range(n):
            for j in range(i + 1, n):
                path = self.BFS_2(targets[i], targets[j])
                d = len(path) - 1
                dist_matrix[i][j] = dist_matrix[j][i] = d
                path_segments[(i, j)] = path
                path_segments[(j, i)] = path[::-1]

        # 2. Dynamic Programming with Bitmask
        # dp[(mask, last_node_index)] = (min_distance, parent_index)
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

        # 3. 找出走完所有點的最短路徑終點
        full_mask = (1 << n) - 1
        best_last_idx = -1
        min_total_dist = float('inf')

        for i in range(n):
            if (full_mask, i) in dp:
                if dp[(full_mask, i)][0] < min_total_dist:
                    min_total_dist, _ = dp[(full_mask, i)]
                    best_last_idx = i

        # 4. 回溯點位順序
        order = []
        curr_m, curr_p = full_mask, best_last_idx
        while curr_p != -1:
            order.append(curr_p)
            prev_p = dp[(curr_m, curr_p)][1]
            curr_m ^= (1 << curr_p)
            curr_p = prev_p
        order.reverse()

        # 5. 拼接完整 Node 路徑
        full_node_path = []
        for i in range(len(order) - 1):
            u, v = order[i], order[i+1]
            segment = path_segments[(u, v)]
            if not full_node_path:
                full_node_path.extend(segment)
            else:
                full_node_path.extend(segment[1:]) # 避開重複的連接點

        # 6. 轉化為指令串
        actions = self.getActions(full_node_path)
        return self.actions_to_str(actions), [node.index for node in full_node_path]

    def getAction(self, car_dir: Direction, node_from: Node, node_to: Node):
        """計算從 node_from 到 node_to 的相對轉向"""
        target_dir = node_from.get_direction(node_to)
        
        # 定義方向轉換順序：北(1), 東(4), 南(2), 西(3) -> 0, 1, 2, 3
        dir_to_val = {
            Direction.NORTH: 0,
            Direction.EAST: 1,
            Direction.SOUTH: 2,
            Direction.WEST: 3
        }
        
        current_val = dir_to_val[car_dir]
        target_val = dir_to_val[target_dir]
        
        # 計算順時針轉向差
        diff = (target_val - current_val) % 4
        
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
        """將 Node 列表轉為 Action 序列"""
        if not nodes or len(nodes) < 2:
            return []
        
        actions = []
        # 第一步永遠是直走 'f' (根據題目假設)
        actions.append(Action.ADVANCE)
        
        # 初始車子面向的方向
        current_car_dir = nodes[0].get_direction(nodes[1])
        
        # 從第二個路段開始計算轉向
        for i in range(1, len(nodes) - 1):
            action, current_car_dir = self.getAction(current_car_dir, nodes[i], nodes[i+1])
            actions.append(action)
            
        return actions

    def actions_to_str(self, actions: List[Action]) -> str:
        """Action Enum 轉字串"""
        cmd_map = {
            Action.ADVANCE: 'f',
            Action.U_TURN: 'b',
            Action.TURN_RIGHT: 'r',
            Action.TURN_LEFT: 'l',
            Action.HALT: 's'
        }
        return "".join([cmd_map[a] for a in actions])