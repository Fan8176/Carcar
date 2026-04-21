from enum import IntEnum

class Direction(IntEnum):
    NORTH = 1
    SOUTH = 2
    WEST = 3
    EAST = 4

class Node:
    def __init__(self, index: int = 0):
        self.index = index
        # store successor as (Node, direction to node, distance)
        self.successors = []

    def get_index(self):
        return self.index

    def get_successors(self):
        return self.successors

    def set_successor(self, successor, direction, length=1):
        self.successors.append((successor, Direction(direction), int(length)))
        return

    def get_direction(self, target_node):
        # 尋找目標節點在目前節點的哪個方向
        for succ, direct, dist in self.successors:
            if succ.index == target_node.index:
                return direct
        print(f"[Error] Node {target_node.index} is not adjacent to {self.index}")
        return 0

    def is_successor(self, node):
        for succ in self.successors:
            if succ[0] == node:
                return True
        return False