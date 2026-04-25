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

# 確認名稱連線
# def get_connected_bridge(port, expected_name):
#     """藍牙連線與配置核心邏輯"""
#     try:
#         bridge = HM10ESP32Bridge(port=port)
        
#         # 1. 檢查並修正模組名稱
#         current_name = bridge.get_hm10_name()
#         if current_name != expected_name:
#             log.info(f"偵測到模組名稱為 {current_name}，正在修正為 {expected_name}...")
#             if bridge.set_hm10_name(expected_name):
#                 log.info("✅ 名稱更新成功，正在重置模組...")
#                 bridge.reset()
#                 time.sleep(2) 
#                 bridge.ser.close() 
#                 bridge = HM10ESP32Bridge(port=port)
#             else:
#                 log.error("❌ 無法變更名稱。")
#                 return None

#         # 2. 檢查連線狀態
#         status = bridge.get_status()
#         if status != "CONNECTED":
#             log.warning(f"⚠️ 藍牙目前狀態：{status}。請確認車車電源已開啟且紅燈恆亮。")
#             return None
        
#         # 連線成功後，先清空一次 Python 端的接收緩衝區，避免讀到舊資料
#         bridge.ser.reset_input_buffer()
#         return bridge
#     except Exception as e:
#         log.error(f"❌ 藍牙連線發生錯誤: {e}")
#         return None

def get_connected_bridge(port, expected_name):
    try:
        bridge = HM10ESP32Bridge(port=port)
        status = bridge.get_status()
        if status != "CONNECTED":
            log.warning(f"⚠️ 藍牙目前狀態：{status}")
            return None
        
        bridge.ser.reset_input_buffer()
        return bridge
    except Exception as e:
        log.error(f"❌ 錯誤: {e}")
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
    bridge = None  # 先宣告，以便 finally 區塊引用

    try:
        # 1. 初始化計分伺服器

        
        # uid_list = [
        #     "10BA617E", "33333333", "00000000", "11111111", "9AC053BD",
        #     "22222222", "44444444", "55555555", "66666666", "77777777",
        #     "88888888", "99999999", "AAAAAAAA", "BBBBBBBB", "CCCCCCCC",
        #     "DDDDDDDD", "EEEEEEEE", "FFFFFFFF", "53FE3C31", "5205171E",
        #     "9AC053BD", "F159AF1E","553C6173"
        # ]

        # # --- 啟動初始化階段 ---
        # log.info("正在上傳預設 UID 列表...")
        # for uid in uid_list:
        #     point.add_UID(uid)

        # 2. 模式選擇
        if mode == "0":
            log.info(f"模式 0：尋寶任務啟動。嘗試連線至 {bt_port}...")
            bridge = get_connected_bridge(bt_port, EXPECTED_BT_NAME)
            
            if bridge is None:
                log.error("❌ 藍牙連線失敗，請檢查硬體後重試。")
                sys.exit(1)

            log.info("✨ 藍芽系統就緒！")


            
            try:
                point = ScoreboardServer(team_name, server_url)
                log.info("✅ 已成功連線至計分伺服器")
            except Exception as e:
                log.error(f"❌ 無法連線至伺服器: {e}")
                sys.exit(1)
            
            # cmd_sequence = "fllbrffrrblrlbfblrffrlbrrlbrrlrrfbfrrlrrbfbrlrrffrfbflrflrr" # big maze ( best path)
            cmd_sequence = "fflfbfrrlrbllfrbffc" # medium maze
            # cmd_sequence = "fflfbfrrlrvllfrbffc" # test
            cmd_idx = 3 # 因為 start 階段會先送出 index 0, 1, 2

            # uid_list = [
            #     "10BA617E", "33333333", "00000000", "11111111", "9AC053BD",
            #     "22222222", "44444444", "55555555", "66666666", "77777777",
            #     "88888888", "99999999", "AAAAAAAA", "BBBBBBBB", "CCCCCCCC",
            #     "DDDDDDDD", "EEEEEEEE", "FFFFFFFF", "53FE3C31", "5205171E",
            #     "9AC053BD", "F159AF1E", "553C6173"
            # ]

            # # --- 啟動初始化階段 ---
            # log.info("正在上傳預設 UID 列表...")
            # for uid in uid_list:
            #     point.add_UID(uid)
            
            log.info("發送啟動指令 's' 及初始路徑...")
            bridge.send('s')
            time.sleep(0.5) # 等待車車啟動準備
            # 一次送出前三個指令
            bridge.send(cmd_sequence[0])
            bridge.send(cmd_sequence[1])
            bridge.send(cmd_sequence[2])

            log.info("進入監聽狀態...")
            while True: 
                msg = bridge.listen() 
                if msg:
                    # 處理可能黏在一起的訊息（用換行符號切割）
                    messages = msg.strip().split('\n')
                    
                    for clean_msg in messages:
                        clean_msg = clean_msg.strip()
                        if not clean_msg: continue
                        
                        log.info(f"收到訊號: '{clean_msg}'")
                        
                        # A. 處理節點指令
                        if "node" in clean_msg:
                            if cmd_idx < len(cmd_sequence):
                                next_action = cmd_sequence[cmd_idx]
                                bridge.send(next_action)
                                log.info(f">>> 發送下一動: {next_action} (Index: {cmd_idx})")
                                cmd_idx += 1
                            else:
                                log.warning("所有指令已發送完畢。")

                        # B. 處理 UID (車車現場讀到的)
                        elif "UID" in clean_msg:
                            # 支援 "UID: XXXXXXXX" 或 "UID XXXXXXXX"
                            uid = clean_msg.replace("UID:", "").replace(" ", "").strip()
                            if len(uid) == 8:
                                log.info(f"發現現場寶藏！上傳 UID: {uid}")
                                point.add_UID(uid)
                                log.info(f"當前得分: {point.get_current_score()}")
                            else:
                                log.warning(f"無效的 UID 長度: {uid}")
                
                time.sleep(0.05) # 稍微縮短 sleep 提升反應速度

        elif mode == "1":
            log.info("模式 1：進入 BFS 測試邏輯...")
            start_idx = int(input("起點 Node ID: "))
            commands, node_sequence = maze.navigate(start_idx)
            print(f"遍擬節點順序: {node_sequence}")
            print(f"全行程指令: {commands}")

    except KeyboardInterrupt:
        log.info("\n偵測到使用者中斷程式執行。")
    except Exception as e:
        log.error(f"執行過程中發生未預期錯誤: {e}")
    finally:
        # --- 核心修正：釋放資源 ---
        if bridge and bridge.ser and bridge.ser.is_open:
            log.info("正在關閉藍牙連線並釋放 Port...")
            bridge.ser.close()
        log.info("程式結束。")

if __name__ == "__main__":
    args = parse_args()
    main(**vars(args))