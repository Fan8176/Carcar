import argparse
import logging
import sys
import time
from hm10_esp32 import HM10ESP32Bridge
from maze import Action, Maze
from score import ScoreboardServer, ScoreboardFake

# --- 全域設定 ---
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
log = logging.getLogger(__name__)

TEAM_NAME = "Amanda"
SERVER_URL = "http://carcar.ntuee.org/scoreboard"
MAZE_FILE = "data/big_maze_114.csv"
BT_PORT = "COM3"
EXPECTED_BT_NAME = "carcar"

def get_connected_bridge(port, expected_name):
    """藍牙連線與配置核心邏輯"""
    try:
        bridge = HM10ESP32Bridge(port=port)
        
        # 1. 檢查並修正模組名稱
        current_name = bridge.get_hm10_name()
        if current_name != expected_name:
            log.info(f"偵測到模組名稱為 {current_name}，正在修正為 {expected_name}...")
            if bridge.set_hm10_name(expected_name):
                log.info("✅ 名稱更新成功，正在重置模組...")
                bridge.reset()
                time.sleep(2) 
                bridge.ser.close() 
                bridge = HM10ESP32Bridge(port=port)
            else:
                log.error("❌ 無法變更名稱。")
                return None

        # 2. 檢查連線狀態
        status = bridge.get_status()
        if status != "CONNECTED":
            log.warning(f"⚠️ 藍牙目前狀態：{status}。請確認車車電源已開啟且紅燈恆亮。")
            return None
        
        return bridge
    except Exception as e:
        log.error(f"❌ 藍牙連線發生錯誤: {e}")
        return None

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", help="0: treasure-hunting, 1: self-testing", type=str)
    parser.add_argument("--maze-file", default=MAZE_FILE, help="Maze file", type=str)
    parser.add_argument("--bt-port", default=BT_PORT, help="Bluetooth port", type=str)
    parser.add_argument("--team-name", default=TEAM_NAME, help="Your team name", type=str)
    parser.add_argument("--server-url", default=SERVER_URL, help="Server URL", type=str)
    return parser.parse_args()

def main(mode: str, bt_port: str, team_name: str, server_url: str, maze_file: str):
    maze = Maze(maze_file)
    
    # 1. 初始化計分伺服器 (若伺服器連不上會印出錯誤，網站目前可開)
    try:
        point = ScoreboardServer(team_name, server_url)
        log.info("✅ 已成功連線至計分伺服器")
    except Exception as e:
        log.error(f"❌ 無法連線至伺服器: {e}")
        sys.exit(1)

    # 指令序列與索引 (放在 main 內部，確保迴圈可讀取)

    # 2. 模式選擇
    if mode == "0":
        log.info(f"模式 0：尋寶任務啟動。嘗試連線至 {bt_port}...")
        
        # 呼叫整合進來的連線檢查
        bridge = get_connected_bridge(bt_port, EXPECTED_BT_NAME)
        
        if bridge is None:
            log.error("❌ 藍牙連線失敗，請檢查硬體後重試。")
            sys.exit(1)
        
        log.info("✨ 系統就緒！開始監聽車車訊號...")

        # 這裡可以選擇先發送第一個指令
        # bridge.send(cmd_sequence[cmd_idx])
        # cmd_idx += 1
        # frulfl
        # cmd_sequence = "ffclfbfrrlrbllfrbfc"
        cmd_sequence = "fflfbfrrlrbllfrbff"
        cmd_idx = 3
        # for i in range(cmd_sequence):
        #     bridge.send(cmd_sequence[i])

        uid_list = [
            "10BA617E",
            "33333333",
            "00000000",
            "11111111",
            "9AC053BD",
            "22222222",
            "44444444",
            "55555555",
            "66666666",
            "77777777",
            "88888888",
            "99999999",
            "AAAAAAAA",
            "BBBBBBBB",
            "CCCCCCCC",
            "DDDDDDDD",
            "EEEEEEEE",
            "FFFFFFFF"
        ]

        start = True

        while True: 

            if start:
                # for uid in uid_list:
                #     log.info("Call add_uid")
                    
                #     score, time_remaining = point.add_UID(uid)
                #     current_score = point.get_current_score()
                #     log.info(f"Current score: {current_score}")
                #     time.sleep(1)

                    # 你可以在這裡加入 point.add_UID(uid) 等邏輯
                bridge.send('s')
                time.sleep(4)
                bridge.send(cmd_sequence[0])
                bridge.send(cmd_sequence[1])
                bridge.send(cmd_sequence[2])
                start = False
                
            # log.info(f"當前得分: {point.get_current_score()}")

            msg = bridge.listen() 
            if msg:
                messages = msg.strip().split('\n')
                log.info(f"收到訊號: '{messages}'")
                
                for clean_msg in messages:
                # A. 處理節點指令
                    if "node" in clean_msg:
                        if cmd_idx < len(cmd_sequence):
                            next_action = cmd_sequence[cmd_idx]
                            bridge.send(next_action)
                            log.info(f">>> 發送下一動: {next_action} (目前索引: {cmd_idx})")
                            cmd_idx += 1
                        else:
                            log.warning("所有預設動作指令已發送完畢。")

                    # B. 處理 UID (寶藏上傳)
                    elif clean_msg.startswith("UID"):
                        uid = clean_msg.removeprefix("UID: ").replace(" ", "")
                        if len(uid) != 8:
                            log.info("Invalid UID!!!!")
                        else:
                            log.info(f"發現寶藏！準備上傳 UID: {uid}")

                            score, time_remaining = point.add_UID(uid)
                            log.info(f"當前得分: {point.get_current_score()}")
                    
                    else:
                        log.debug(f"收到非定義訊息: {clean_msg}")
            
            time.sleep(0.1)

    elif mode == "1":
        log.info("模式 1：進入 BFS 測試邏輯...")
        # 這裡可以保留你原本的 BFS ID 輸入與路徑規劃測試
        try:
            # Mode 1 測試：TSP 全遍歷
            start_idx = int(input("起點 Node ID: "))

            # 直接傳入整數 ID，不要傳 node_dict[start_idx]
            commands, node_sequence = maze.get_shortest_traversal_path(start_idx)

            
            print(f"遍歷節點順序: {node_sequence}")
            print(f"全行程指令: {commands}")


            # start_idx = int(input("起點 Node ID: "))
            # end_idx = int(input("終點 Node ID: "))
            # node_dict = maze.get_node_dict()
            # # path = maze.BFS_2(node_dict[start_idx], node_dict[end_idx])
            # path = maze.get_shortest_traversal_path(node_dict[start_idx])
            # if path:
            #     log.info(f"路徑: {[node.index for node in path]}")
            #     actions = maze.getActions(path)
            #     log.info(f"指令字串: {maze.actions_to_str(actions)}")
        except Exception as e:
            log.error(f"測試模式錯誤: {e}")

    else:
        log.error("無效的模式設定")
        sys.exit(1)

if __name__ == "__main__":
    args = parse_args()
    main(**vars(args))