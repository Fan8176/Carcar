import pandas as pd
import logging
import queue
from enum import IntEnum
from typing import List
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
        # 讀取 CSV
        self.raw_data = pd.read_csv(filepath)
        self.nodes = []
        self.node_dict = dict()

        # 1. 先建立所有 Node 物件
        for index in self.raw_data.iloc[:, 0]:
            new_node = Node(int(index))
            self.nodes.append(new_node)
            self.node_dict[int(index)] = new_node

        # 2. 建立鄰接關係 (Successors)
        # 假設 CSV 格式: Index, North, South, West, East
        for _, row in self.raw_data.iterrows():
            cur_idx = int(row[0])
            cur_node = self.node_dict[cur_idx]
            
            # 依序檢查 N(1), S(2), W(3), E(4)
            for i, dir_enum in enumerate([Direction.NORTH, Direction.SOUTH, Direction.WEST, Direction.EAST], 1):
                neighbor = row[i]
                if pd.notna(neighbor) and neighbor != "":
                    cur_node.set_successor(self.node_dict[int(neighbor)], dir_enum)

    def get_node_dict(self):
        return self.node_dict

    def BFS_2(self, node_from: Node, node_to: Node):
        # 你的 BFS 邏輯實現
        start_node = node_from.index
        end_node = node_to.index
        
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
            return None

        # 回溯路徑 (Path of Nodes)
        path_nodes = []
        curr = end_node
        while curr is not None:
            path_nodes.append(self.node_dict[curr])
            curr = record[curr]
        
        return path_nodes[::-1] # 反轉回來

    def getAction(self, car_dir, node_from: Node, node_to: Node):
        # 取得目標節點相對於當前節點的絕對方向 (1:N, 2:S, 3:W, 4:E)
        target_dir = node_from.get_direction(node_to)
        
        # 定義方向轉換表，將 Direction Enum 轉為順時針數值 (0~3)
        # 這裡假設：North=0, East=1, South=2, West=3 (順時針)
        dir_to_val = {
            Direction.NORTH: 0,
            Direction.EAST: 1,
            Direction.SOUTH: 2,
            Direction.WEST: 3
        }
        
        current_val = dir_to_val[car_dir]
        target_val = dir_to_val[target_dir]
        
        # 計算相對轉向差
        # 1:右轉, 2:迴轉, 3:左轉, 0:直走
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

    def getActions(self, nodes: List[Node]):
        if not nodes or len(nodes) < 2:
            return []
        
        actions = []
        
        # 根據你的規則：剛開始一定放在端點且面向該相鄰節點
        # 所以第一步永遠是直走 'f'
        actions.append(Action.ADVANCE)
        
        # 初始車子面向的方向，是由 nodes[0] 指向 nodes[1] 的絕對方向
        current_car_dir = nodes[0].get_direction(nodes[1])
        
        # 從第二個路段開始計算轉向 (nodes[1] -> nodes[2] ...)
        for i in range(1, len(nodes) - 1):
            action, current_car_dir = self.getAction(current_car_dir, nodes[i], nodes[i+1])
            actions.append(action)
            
        return actions

    def actions_to_str(self, actions):
        # 對應 f, b, r, l, s
        cmd_map = {Action.ADVANCE: 'f', Action.U_TURN: 'b', Action.TURN_RIGHT: 'r', Action.TURN_LEFT: 'l', Action.HALT: 's'}
        cmds = "".join([cmd_map[a] for a in actions])
        log.info(f"Generated commands: {cmds}")
        return cmds