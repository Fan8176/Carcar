import argparse
import logging
import os
import sys
import time

import numpy as np
import pandas
# from BTinterface import BTInterface
from hm10_esp32 import HM10ESP32Bridge
from maze import Action, Maze
from score import ScoreboardServer, ScoreboardFake

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)

# TODO : Fill in the following information
TEAM_NAME = "震撼教"
SERVER_URL = "http://carcar.ntuee.org"
MAZE_FILE = "data/small_maze.csv"
BT_PORT = "COM7"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", help="0: treasure-hunting, 1: self-testing", type=str)
    parser.add_argument("--maze-file", default=MAZE_FILE, help="Maze file", type=str)
    parser.add_argument("--bt-port", default=BT_PORT, help="Bluetooth port", type=str)
    parser.add_argument(
        "--team-name", default=TEAM_NAME, help="Your team name", type=str
    )
    parser.add_argument("--server-url", default=SERVER_URL, help="Server URL", type=str)
    return parser.parse_args()


def main(mode: int, bt_port: str, team_name: str, server_url: str, maze_file: str):
    maze = Maze(maze_file)
    point = ScoreboardServer(team_name, server_url)
    # point = ScoreboardFake("your team name", "data/fakeUID.csv") # for local testing

    ### Bluetooth connection haven't been implemented yet, we will update ASAP ###
    # interface = BTInterface(port=bt_port)
    # TODO : Initialize necessary variables
    log.info(f"準備連接藍牙 (Port: {bt_port})...")
    bridge = HM10ESP32Bridge(port=bt_port)
    
    status = bridge.get_status()
    if status != "CONNECTED":
        log.error(f"ESP32 狀態為 {status}，藍牙未連線成功！程式終止。")
        sys.exit(1)
    log.info("藍牙連線成功！")

    if mode == "0":
        log.info("Mode 0: For treasure-hunting")
        # TODO : for treasure-hunting, which encourages you to hunt as many scores as possible
        while True: 
            msg = bridge.listen()
                
            if msg:
                uid_str = msg.strip() 
                log.info(f"車車從藍牙收到資料: '{uid_str}'")
                
                if len(uid_str) == 8:
                    log.info(f"準備上傳 UID: {uid_str} 至伺服器...")
                    score, time_remaining = point.add_UID(uid_str)
                    
                    # 顯示最新總分
                    current_score = point.get_current_score()
                    log.info(f"目前總分: {current_score}")
                else:
                    log.debug(f"收到非 UID 訊息: {uid_str}")
            
            time.sleep(0.1)
    elif mode == "1":
        log.info("Mode 1: Self-testing mode.")
        # TODO: You can write your code to test specific function.

    else:
        log.error("Invalid mode")
        sys.exit(1)


if __name__ == "__main__":
    args = parse_args()
    main(**vars(args))
